#include "HUD/SoraHUDPanels.h"
#include "ArenaKernelSubsystem.h"
#include "SoraArmsRules.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraHistoricalArms.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeDirector.h"
#include "Engine/Canvas.h"
#include "Engine/World.h"

namespace SoraWeaponHUD
{
FVector2D TextSize(ASoraHUD& HUD,const FString& Text,float Scale)
{
    int32 Width=0,Height=0;
    UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),Scale,Scale,Width,Height,Text);
    return FVector2D(Width,Height);
}
struct FBlock
{
    FString Source;
    TArray<FString> Lines;
    float Scale=0,Leading=0,Y=0;
    FLinearColor Color;
    float Height() const { return Lines.Num()*Leading; }
};
struct FPanel
{
    TArray<FBlock> Blocks;
    float X=0,Y=0,Width=0,Height=0,Padding=0;
    float Bar=-1,BarHeight=0;
    float Opacity=.9f;
    FLinearColor BarColor;
    float TextWidth() const { return Width-2*Padding; }
};
struct FLayout
{
    FPanel Weapon,Windup,TakenUp;
};
// Keep every character. Prefer a word boundary in English; Japanese and
// individual oversized words still wrap at measured glyph boundaries.
void AddText(const FSoraHUDFrame& F,FPanel& Panel,const FString& Text,float Scale,FLinearColor Color)
{
    if(Text.IsEmpty()) return;
    FBlock Block;
    Block.Source=Text; Block.Scale=Scale; Block.Color=Color; Block.Y=Panel.Height;
    FString Line;
    for(int32 Index=0;Index<Text.Len();++Index)
    {
        const FString Character=Text.Mid(Index,1);
        if(Text[Index]=='\n') { Block.Lines.Add(Line); Line.Empty(); continue; }
        if(!Line.IsEmpty()&&TextSize(F.HUD,Line+Character,Scale).X>Panel.TextWidth())
        {
            int32 Space=INDEX_NONE;
            if(Line.FindLastChar(' ',Space)&&Space>0)
            {
                Block.Lines.Add(Line.Left(Space+1)); Line=Line.Mid(Space+1);
            }
            else { Block.Lines.Add(Line); Line.Empty(); }
        }
        Line+=Character;
    }
    if(!Line.IsEmpty()) Block.Lines.Add(Line);
    for(const FString& Wrapped:Block.Lines)
        Block.Leading=FMath::Max(Block.Leading,static_cast<float>(TextSize(F.HUD,Wrapped,Scale).Y)+4.f);
    Panel.Height+=Block.Height(); Panel.Blocks.Add(MoveTemp(Block));
}
void AddBilingual(const FSoraHUDFrame& F,FPanel& Panel,const SoraText::FLine& Text,float JapaneseScale,FLinearColor Color)
{
    AddText(F,Panel,Text.Japanese,FMath::Max(JapaneseScale*F.S,.55f),Color);
    if(F.Mode.bEnglishSubtitles) AddText(F,Panel,Text.English,FMath::Max(.8f*JapaneseScale*F.S,.5f),F.Muted);
}
FLayout Build(const FSoraHUDFrame& F,const ASoraPlayerCharacter& Hero)
{
    FLayout L;
    FPanel& Main=L.Weapon;
    const ASoraGameMode& G=F.Mode;
    const USoraEquipmentComponent* Kit=Hero.GetEquipment();
    const FSoraWeapon& Weapon=FSoraCatalog::Get().Weapon(Hero.WeaponId);
    Main.Width=365*F.S; Main.Padding=25*F.S; Main.X=F.W-25*F.S-Main.Width; Main.Height=10*F.S;
    const SoraText::FLine Arm=G.bCampaign&&G.Campaign()->ChapterId==0&&Hero.WeaponId==0
        ?SoraText::Line(NSLOCTEXT("SoraArena.Arms","Bokken","木刀 / 非致死の立合い"))
        :SoraText::FLine{Weapon.Name,Weapon.NameEnglish};
    AddText(F,Main,Arm.Japanese,FMath::Max(.72f*F.S,.6f),F.Ivory);
    if(G.bEnglishSubtitles) AddText(F,Main,Arm.English,FMath::Max(.36f*F.S,.5f),F.Muted);
    Main.Height+=4*F.S;
    SoraText::FLine Charge;
    float Progress=-1.f;
    if(G.bDeterministicPractice)
    {
        if(const auto* K=G.Kernel()) if(K->PracticePlayers.Num()>0)
        {
            const auto& State=K->PracticePlayers[0];
            const SoraText::FLine Ammunition=State.Magazine==0
                ?SoraText::Format(NSLOCTEXT("SoraArena.HUD","Ammo.Swordplay","剣術　{Melee}"),{{TEXT("Melee"),SoraUI::ActionKey(&F.HUD,TEXT("Melee"))}})
                :State.ReloadTicks>0
                ?SoraText::Format(NSLOCTEXT("SoraArena.HUD","Ammo.ReloadingFor","装填中 {Seconds} 秒   {Ammo} / {Magazine}"),
                    {{TEXT("Seconds"),FString::Printf(TEXT("%.1f"),State.ReloadTicks/60.f)},{TEXT("Ammo"),State.Ammo},{TEXT("Magazine"),State.Magazine}})
                :SoraText::Format(NSLOCTEXT("SoraArena.HUD","Ammo.Rounds","弾数 {Ammo} / {Magazine}   {Reload} 装填"),
                    {{TEXT("Ammo"),FString::Printf(TEXT("%02d"),State.Ammo)},{TEXT("Magazine"),FString::Printf(TEXT("%02d"),State.Magazine)},
                    {TEXT("Reload"),SoraUI::ActionKey(&F.HUD,TEXT("Reload"))}});
            AddBilingual(F,Main,Ammunition,.46f,F.Gold);
            AddText(F,Main,FString::Printf(TEXT("気力 %d / 100    待機 %.2f 秒"),State.Stamina,State.Cooldown/60.f),
                FMath::Max(.33f*F.S,.5f),F.Muted);
            if(State.Alive&&State.ChargeRequired>0&&State.ChargeTicks>0)
            {
                Progress=FMath::Clamp(static_cast<float>(State.ChargeTicks)/State.ChargeRequired,0.f,1.f);
                Charge={FString::Printf(TEXT("構え %d / %d"),State.ChargeTicks,State.ChargeRequired),TEXT("WINDUP")};
            }
        }
    }
    else
    {
        if(Kit->IsSheathing())
            AddBilingual(F,Main,Kit->IsSheathed()?SoraText::Line(NSLOCTEXT("SoraArena.HUD","Ammo.Sheathed","納刀 ― 無刀の構え"))
                :SoraText::Line(NSLOCTEXT("SoraArena.HUD","Ammo.Sheathing","納刀中……")),.54f,F.Gold);
        else
        {
            const FString Ammo=FString::Printf(TEXT("%02d"),Kit->Ammo),Magazine=FString::Printf(TEXT("%02d"),Weapon.Magazine);
            AddBilingual(F,Main,Kit->bReloading?SoraText::Line(NSLOCTEXT("SoraArena.HUD","Ammo.Reloading","装填中"))
                :Weapon.Kind==TEXT("melee")?SoraText::Line(NSLOCTEXT("SoraArena.HUD","Ammo.Melee","間合い / 斬突と残心"))
                :Weapon.Kind==TEXT("bow")?SoraText::Format(NSLOCTEXT("SoraArena.HUD","Ammo.Arrows","矢 {Ammo} / {Magazine}   {Fire} 長押し→離して射る"),
                    {{TEXT("Ammo"),Ammo},{TEXT("Magazine"),Magazine},{TEXT("Fire"),SoraUI::ActionKey(&F.HUD,TEXT("Fire"))}})
                :SoraText::Format(NSLOCTEXT("SoraArena.HUD","Ammo.Magazine","{Ammo} / {Magazine}   {Reload} 装填"),
                    {{TEXT("Ammo"),Ammo},{TEXT("Magazine"),Magazine},{TEXT("Reload"),SoraUI::ActionKey(&F.HUD,TEXT("Reload"))}}),.54f,F.Gold);
        }
        if(Kit->IsBowDrawing()||Kit->IsCommittedStrike())
        {
            const bool bDraw=Kit->IsBowDrawing();
            Progress=bDraw?Kit->BowDrawProgress():Kit->StrikeWindupProgress();
            Charge={bDraw?TEXT("会 / 引き分け"):TEXT("打突の構え"),bDraw?TEXT("DRAW / RELEASE"):TEXT("COMMITTED STRIKE")};
        }
        if(G.bCampaign&&G.Campaign()->ChapterId>0&&SoraHistoricalArms::IsMelee(Hero.WeaponId))
        {
            Main.Bar=FMath::Clamp(Kit->GuardReserve()/100.f,0.f,1.f); Main.BarHeight=3*F.S; Main.BarColor=F.Teal;
        }
    }
    Main.Height+=8*F.S+Main.BarHeight;
    Main.Y=F.H-30*F.S-Main.Height;
    if(Progress>=0.f)
    {
        FPanel& Windup=L.Windup;
        Windup.Width=Main.Width; Windup.Padding=Main.Padding; Windup.X=Main.X; Windup.Height=6*F.S;
        AddBilingual(F,Windup,Charge,.37f,F.Gold);
        Windup.Bar=Progress; Windup.BarHeight=4*F.S; Windup.BarColor=F.Gold;
        Windup.Height+=8*F.S+Windup.BarHeight;
        Windup.Y=Main.Y-6*F.S-Windup.Height;
    }
    const float Since=Hero.GetWorld()->GetTimeSeconds()-Hero.ArmsTakenAt();
    const int32 Group=SoraArmsRules::GroupOf(Hero.WeaponId);
    if(!Hero.ArmsWheel().bOpen&&Since<1.6f&&Group>=0&&Hero.IsCampaignHero())
    {
        FPanel& Notice=L.TakenUp;
        Notice.Width=Main.Width; Notice.Padding=Main.Padding; Notice.X=Main.X; Notice.Height=6*F.S;
        const SoraText::FLine Text=SoraText::Format(NSLOCTEXT("SoraArena.Arms","TakenUp","{Group}　{Arm}"),
            {{TEXT("Group"),SoraText::Line(SoraUI::ArmsGroupName(Group))},{TEXT("Arm"),SoraText::FLine{Weapon.Name,Weapon.NameEnglish}}});
        AddBilingual(F,Notice,Text,.5f,F.Gold);
        Notice.Height+=6*F.S;
        Notice.Opacity=.9f*FMath::Clamp(1.6f-Since,0.f,1.f);
        Notice.Y=(L.Windup.Height>0?L.Windup.Y:Main.Y)-6*F.S-Notice.Height;
    }
    return L;
}
void DrawPanel(const FSoraHUDFrame& F,const FPanel& Panel)
{
    if(Panel.Height<=0) return;
    F.HUD.Panel(Panel.X,Panel.Y,Panel.Width,Panel.Height,FLinearColor(.015,.035,.05,Panel.Opacity));
    for(const FBlock& Block:Panel.Blocks)
    {
        float Y=Panel.Y+Block.Y;
        for(const FString& Line:Block.Lines) { F.HUD.Label(Line,Panel.X+Panel.Padding,Y,Block.Scale,Block.Color); Y+=Block.Leading; }
    }
    if(Panel.Bar>=0.f)
    {
        const float Y=Panel.Y+Panel.Height-4*F.S-Panel.BarHeight;
        F.HUD.Panel(Panel.X+Panel.Padding,Y,Panel.TextWidth(),Panel.BarHeight,FLinearColor(.12,.19,.21));
        F.HUD.Panel(Panel.X+Panel.Padding,Y,Panel.TextWidth()*Panel.Bar,Panel.BarHeight,Panel.BarColor);
    }
}
}
void SoraHUDPanels::DrawWeapon(const FSoraHUDFrame& F,const ASoraPlayerCharacter& Hero)
{
    const SoraWeaponHUD::FLayout L=SoraWeaponHUD::Build(F,Hero);
    SoraWeaponHUD::DrawPanel(F,L.Weapon); SoraWeaponHUD::DrawPanel(F,L.Windup);
    if(F.Mode.bDeterministicPractice&&F.Mode.Practice()->bSlowed)
        F.HUD.Label(TEXT("処理負荷により、稽古時間を減速しています"),30*F.S,200*F.S,.4*F.S,F.Gold);
}
void SoraHUDPanels::DrawArmsNotice(const FSoraHUDFrame& F,const ASoraPlayerCharacter& Hero)
{
    SoraWeaponHUD::DrawPanel(F,SoraWeaponHUD::Build(F,Hero).TakenUp);
}
TArray<FBox2D> SoraHUDPanels::WeaponPanelBounds(const FSoraHUDFrame& F,const ASoraPlayerCharacter& Hero)
{
    const SoraWeaponHUD::FLayout L=SoraWeaponHUD::Build(F,Hero);
    TArray<FBox2D> Bounds;
    for(const SoraWeaponHUD::FPanel* Panel:{&L.Weapon,&L.Windup,&L.TakenUp})
        if(Panel->Height>0) Bounds.Add(FBox2D(FVector2D(Panel->X,Panel->Y),FVector2D(Panel->X+Panel->Width,Panel->Y+Panel->Height)));
    return Bounds;
}
bool SoraHUDPanels::WeaponLayoutFits(const FSoraHUDFrame& F,const ASoraPlayerCharacter& Hero,FString& Why)
{
    const SoraWeaponHUD::FLayout L=SoraWeaponHUD::Build(F,Hero);
    for(const SoraWeaponHUD::FPanel* Panel:{&L.Weapon,&L.Windup,&L.TakenUp})
    {
        if(Panel->Height<=0) continue;
        if(Panel->X<0||Panel->Y<0||Panel->X+Panel->Width>F.W||Panel->Y+Panel->Height>F.H)
        { Why=TEXT("Weapon panel exceeds viewport"); return false; }
        float PreviousEnd=0;
        for(const SoraWeaponHUD::FBlock& Block:Panel->Blocks)
        {
            if(Block.Scale<.5f||Block.Y<PreviousEnd||Block.Y+Block.Height()>Panel->Height-Panel->BarHeight-4*F.S||
                FString::Join(Block.Lines,TEXT(""))!=Block.Source.Replace(TEXT("\n"),TEXT("")))
            { Why=TEXT("Weapon text is unreadable, overlapping or incomplete"); return false; }
            for(const FString& Line:Block.Lines)
            {
                const FVector2D Size=SoraWeaponHUD::TextSize(F.HUD,Line,Block.Scale);
                if(Size.X>Panel->TextWidth()||Size.Y+3.f>Block.Leading)
                { Why=FString::Printf(TEXT("Weapon line exceeds measured bounds: %s"),*Line); return false; }
            }
            PreviousEnd=Block.Y+Block.Height();
        }
    }
    if(L.Windup.Height>0&&L.Windup.Y+L.Windup.Height>L.Weapon.Y)
    { Why=TEXT("Weapon and windup panels overlap"); return false; }
    return true;
}
