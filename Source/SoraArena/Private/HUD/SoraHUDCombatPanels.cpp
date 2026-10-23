#include "HUD/SoraHUDPanels.h"
#include "ArenaKernelSubsystem.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraDefense.h"
#include "SoraBoss.h"
#include "SoraAimHUDLayout.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCombatRules.h"
#include "SoraEquipmentComponent.h"
#include "SoraEnemy.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraHistoricalArms.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeDirector.h"
#include "SoraWorldBuilder.h"
#include "SoraSettings.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Canvas.h"
#include "GameFramework/PlayerController.h"

namespace
{
struct FObjectiveText
{
    FString Text;
    FVector2D At;
    float Scale=0;
    FLinearColor Color;
    int32 Group=0;
};
struct FObjectiveLayout
{
    FBox2D Bounds=FBox2D(ForceInit);
    TArray<FObjectiveText> Text;
    FString Original[4];
};
FObjectiveLayout ObjectiveLayout(const FSoraHUDFrame& F)
{
    FObjectiveLayout L;
    const float S=F.S,Left=30*S,Right=20*S+FMath::Min(F.W-40*S,850*S)-10*S,Gap=4*S;
    const auto Add=[&](int32 Group,float X,float Y,float Scale,float Advance,FLinearColor Color)
    {
        TArray<FString> Lines; FString Line;
        const auto& Text=L.Original[Group];
        for(int32 I=0;I<Text.Len();++I)
        {
            if(Text[I]=='\n') { Lines.Add(Line); Line.Empty(); continue; }
            if(!Line.IsEmpty()&&F.HUD.LabelWidth(Line+Text.Mid(I,1),Scale)>Right-X)
            {
                int32 Space=INDEX_NONE;
                if(Line.FindLastChar(' ',Space)&&Space>0) { Lines.Add(Line.Left(Space+1)); Line=Line.Mid(Space+1); }
                else { Lines.Add(Line); Line.Empty(); }
            }
            Line+=Text.Mid(I,1);
        }
        if(!Line.IsEmpty()) Lines.Add(Line);
        float Bottom=Y;
        for(const auto& Row:Lines)
        {
            int32 W=0,H=0; UCanvas::ClippedStrLen(F.HUD.JapaneseFontObject(),Scale,Scale,W,H,Row);
            L.Text.Add({Row,{X,Y},Scale,Color,Group}); Bottom=Y+H; Y+=FMath::Max(Advance,H+Gap);
        }
        return Bottom;
    };
    L.Original[0]=F.Mode.bCampaign?FSoraCatalog::Get().Chapter(F.Mode.Campaign()->ChapterId).Title:FSoraCatalog::Get().Map(F.Mode.MapId).Name;
    float HeaderBottom=Add(0,Left,95*S,.82f*S,26*S,F.Ivory);
    if(F.Mode.bEnglishSubtitles)
    {
        L.Original[1]=F.Mode.bCampaign?FSoraCatalog::Get().Chapter(F.Mode.Campaign()->ChapterId).TitleEnglish:FSoraCatalog::Get().Map(F.Mode.MapId).NameEnglish;
        const float InlineX=Left+F.HUD.LabelWidth(L.Original[0],.82f*S)+18*S;
        const bool Inline=Right-InlineX>=150*S;
        HeaderBottom=FMath::Max(HeaderBottom,Add(1,Inline?InlineX:Left,Inline?106*S:HeaderBottom+Gap,.45f*S,18*S,F.Muted));
    }
    L.Original[2]=F.Mode.ObjectiveText();
    float Bottom=Add(2,Left,FMath::Max(137*S,HeaderBottom+Gap),.52f*S,20*S,F.Teal);
    if(F.Mode.bEnglishSubtitles)
    {
        L.Original[3]=F.Mode.ObjectiveTextEnglish();
        Bottom=Add(3,Left,FMath::Max(164*S,Bottom+Gap),F.EnglishSubtitleScale,F.EnglishSubtitleLineHeight,F.Muted);
    }
    L.Bounds=FBox2D({20*S,87*S},{Right+10*S,FMath::Max((F.Mode.bEnglishSubtitles?212.f:177.f)*S,Bottom+Gap)});
    return L;
}
FBox2D ObjectivePanelBounds(const FSoraHUDFrame& F) { return ObjectiveLayout(F).Bounds; }
FBox2D DojoPanelBounds(const FSoraHUDFrame& F)
{
    if(!F.Mode.bCampaign||F.Mode.Campaign()->ChapterId!=0||F.Mode.Campaign()->DojoLessonStage()>=4) return FBox2D(ForceInit);
    const float Top=FMath::Max(static_cast<float>(ObjectivePanelBounds(F).Max.Y)+4*F.S,F.Mode.bEnglishSubtitles?FMath::Max(217*F.S,164*F.S+2*F.EnglishSubtitleLineHeight+8*F.S):169*F.S);
    return FBox2D({25*F.S,Top},{745*F.S,Top+(F.Mode.bEnglishSubtitles?72:47)*F.S});
}
struct FBossRect { FBox2D Bounds; FLinearColor Color; };
struct FBossLayout
{
    FBox2D Bounds=FBox2D(ForceInit);
    TArray<FObjectiveText> Text;
    TArray<FString> Original;
    TArray<FBossRect> Rects;
    bool bFits=false;
};
FBossLayout MeasureBoss(const FSoraHUDFrame& F,float Width)
{
    FBossLayout L;
    const auto* Boss=F.Mode.Campaign()->CampaignBoss(); const auto* Info=Boss?Boss->Data():nullptr;
    if(!Info) return L;
    const float Padding=17.f,Inner=Width-2*Padding,Gap=4.f;
    float Y=7.f;
    const auto TextWidth=[&](const FString& Text,float Scale)
    { return FMath::Max(F.HUD.LabelWidth(Text,Scale),static_cast<float>(SoraHUDPanels::CaptionGlyphBounds(F,Text,Scale).GetSize().X)); };
    const auto Row=[&](const FString& Text,float X,float At,float Scale,FLinearColor Color,int32 Group)
    {
        const auto Ink=SoraHUDPanels::CaptionGlyphBounds(F,Text,Scale);
        L.Text.Add({Text,FVector2D(X,At)-Ink.Min,Scale,Color,Group});
        return static_cast<float>(Ink.GetSize().Y);
    };
    const auto Block=[&](const FString& Text,float Scale,FLinearColor Color,int32 Group)
    {
        TArray<FString> Lines; FString Line;
        for(int32 I=0;I<Text.Len();++I)
        {
            if(Text[I]=='\n') { Lines.Add(Line); Line.Empty(); continue; }
            if(!Line.IsEmpty()&&TextWidth(Line+Text.Mid(I,1),Scale)>Inner)
            {
                int32 Space=INDEX_NONE;
                if(Line.FindLastChar(' ',Space)&&Space>0) { Lines.Add(Line.Left(Space+1)); Line=Line.Mid(Space+1); }
                else { Lines.Add(Line); Line.Empty(); }
            }
            Line+=Text.Mid(I,1);
        }
        if(!Line.IsEmpty()) Lines.Add(Line);
        for(const auto& Part:Lines) Y+=Row(Part,Padding,Y,Scale,Color,Group)+Gap;
    };
    const auto Pair=[&](const FString& JA,const FString& EN,float JS,float ES,FLinearColor Color)
    {
        const int32 J=L.Original.Add(JA),E=F.Mode.bEnglishSubtitles?L.Original.Add(EN):INDEX_NONE;
        // Use complete inline translations when they fit; otherwise wrap the
        // same text at the existing sizes. Trim only empty font ascent/descent.
        if(E!=INDEX_NONE&&!JA.IsEmpty()&&!EN.IsEmpty()&&!JA.Contains(TEXT("\n"))&&!EN.Contains(TEXT("\n"))&&
            TextWidth(JA,JS)+14.f+TextWidth(EN,ES)<=Inner)
        {
            const float JH=Row(JA,Padding,Y,JS,Color,J);
            const float EH=Row(EN,Padding+TextWidth(JA,JS)+14.f,Y,ES,F.Muted,E);
            Y+=FMath::Max(JH,EH)+Gap;
        }
        else { Block(JA,JS,Color,J); if(E!=INDEX_NONE) Block(EN,ES,F.Muted,E); }
    };
    const auto Rect=[&](float X,float At,float W,float H,FLinearColor Color)
    { L.Rects.Add({FBox2D({X,At},{X+W,At+H}),Color}); };
    Pair(Info->NameJapanese,Info->NameEnglish,F.JapaneseSubtitleScale,F.EnglishSubtitleScale,F.Gold);
    Y+=3.f; // Phase marks extend three pixels above/below the health bar.
    Rect(Padding,Y,Inner,7.f,FLinearColor(.15f,.18f,.20f));
    Rect(Padding,Y,Inner*FMath::Clamp(Boss->Health/Boss->MaxHealth,0.f,1.f),7.f,Boss->IsInvulnerable()?F.Muted:F.Gold);
    for(int32 I=1;I<Info->Phases.Num();++I)
        Rect(Padding+Inner*Info->Phases[I].FromPermille/1000.f-1.f,Y-3.f,2.f,13.f,F.Ivory);
    if(Boss->HasBarrier()&&Info->Barrier.Health>0)
    {
        Rect(Padding,Y+10.f,Inner,3.f,FLinearColor(.15f,.18f,.20f));
        Rect(Padding,Y+10.f,Inner*FMath::Clamp(Boss->BarrierPoints()/static_cast<float>(Info->Barrier.Health),0.f,1.f),3.f,FLinearColor(.78f,.74f,.92f));
    }
    Y+=17.f;
    TArray<FString> Japanese,English;
    if(Boss->IsInvulnerable()) { Japanese.Add(TEXT("無敵")); English.Add(TEXT("INVULNERABLE")); }
    if(Boss->IsShieldUp()) { Japanese.Add(TEXT("大盾：正面不可")); English.Add(TEXT("SHIELD: front blocked")); }
    if(Boss->HasBarrier()) { Japanese.Add(Boss->IsBarrierOffline()?TEXT("障壁：停止中"):TEXT("障壁")); English.Add(Boss->IsBarrierOffline()?TEXT("BARRIER: down"):TEXT("BARRIER")); }
    if(Boss->IsMantleUp()) { Japanese.Add(TEXT("冷却外套：被害七割減")); English.Add(TEXT("MANTLE: 70% less damage")); }
    if(Boss->IsStaggered()) { Japanese.Add(TEXT("崩れ：好機")); English.Add(TEXT("STAGGERED: strike now")); }
    for(int32 I=0;I<Info->WeakPoints.Num();++I)
        if(Boss->IsWeakPointOpen(I)) { Japanese.Add(Info->WeakPoints[I].NameJapanese); English.Add(Info->WeakPoints[I].NameEnglish); }
    if(Boss->LiveWards()>0&&Info->Wards.IsValidIndex(Boss->CurrentPhase()->Ward))
    {
        const auto& Ward=Info->Wards[Boss->CurrentPhase()->Ward];
        Japanese.Add(FString::Printf(TEXT("%s ×%d"),*Ward.NameJapanese,Boss->LiveWards()));
        English.Add(FString::Printf(TEXT("%s x%d"),*Ward.NameEnglish,Boss->LiveWards()));
    }
    for(const auto& Limited:Info->Attacks) if(Limited.EventLimit>0)
    {
        Japanese.Add(FString::Printf(TEXT("差押え %d / %d"),Boss->Seals(),Limited.EventLimit));
        English.Add(FString::Printf(TEXT("SEIZED %d / %d"),Boss->Seals(),Limited.EventLimit));
    }
    Pair(FString::Join(Japanese,TEXT("　")),FString::Join(English,TEXT("  ")),.34f,.30f,F.Teal);
    const auto* Attack=Boss->BossAttack();
    if(Attack&&Boss->IsBossTelegraphing())
    {
        const FLinearColor Warning=Attack->Telegraph==ESoraBossTelegraph::Cyan?FLinearColor(.04f,.85f,.95f):FLinearColor(1.f,.68f,.16f);
        Pair(Attack->TellJapanese,Attack->TellEnglish,F.JapaneseSubtitleScale,F.EnglishSubtitleScale,
            Attack->Telegraph==ESoraBossTelegraph::None?F.Ivory:Warning);
        Pair(FString::Printf(TEXT("%.1f s"),Boss->BossWarningSeconds()),FString(),.48f,.48f,F.Gold);
        Rect(Padding,Y,Inner,4.f,FLinearColor(.15f,.18f,.20f));
        Rect(Padding,Y,Inner*Boss->BossWarningProgress(),4.f,Warning); Y+=4.f+Gap;
        const auto* Hero=Cast<ASoraPlayerCharacter>(F.HUD.GetOwningPawn());
        if(Attack->bMuto&&Info->bMutoFinisher)
        {
            const bool Sheathed=Hero&&Hero->GetEquipment()->IsSheathing();
            Pair(Sheathed?TEXT("納刀済 ― 斬撃の寸前に［防御］で無刀取り"):TEXT("［納刀］で納め、斬撃の寸前に［防御］で無刀取り"),
                Sheathed?TEXT("Sheathed: [Guard] just before the cut lands for mutō-dori"):TEXT("[Sheathe], then [Guard] just before the cut lands for mutō-dori"),.36f,.32f,F.Gold);
        }
        else if(Attack->MarobashiMs>0)
            Pair(TEXT("転 ― 着く寸前に 左右＋［跳躍］で脇へ"),TEXT("Marobashi: Left/Right + [Jump] just before it lands to reach the flank"),.36f,.32f,F.Gold);
    }
    else if(!Info->StyleJapanese.IsEmpty()) Pair(Info->StyleJapanese,Info->StyleEnglish,.42f,.34f,F.Muted);
    L.Bounds=FBox2D({0,0},{Width,Y+7.f});
    return L;
}
FBossLayout BossLayout(const FSoraHUDFrame& F)
{
    const float Width=FMath::Min(F.W-20.f,FMath::Max(600.f*F.S,480.f));
    auto L=MeasureBoss(F,Width); if(!L.Bounds.bIsValid) return L;
    const auto Obstacles=SoraHUDPanels::BossLayoutObstacles(F);
    const float Gap=6*F.S;
    const FBox2D View({20*F.S,87*F.S},{F.W-20*F.S,F.H-30*F.S});
    const auto Place=[](FBossLayout Layout,FVector2D At)
    {
        Layout.Bounds.Min+=At; Layout.Bounds.Max+=At;
        for(auto& Row:Layout.Text) Row.At+=At;
        for(auto& Rect:Layout.Rects) { Rect.Bounds.Min+=At; Rect.Bounds.Max+=At; }
        return Layout;
    };
    const auto Clear=[&](const FBossLayout& Candidate)
    {
        const auto& B=Candidate.Bounds;
        if(B.Min.X<View.Min.X||B.Min.Y<View.Min.Y||B.Max.X>View.Max.X||B.Max.Y>View.Max.Y) return false;
        for(const auto& Other:Obstacles) if(B.Intersect(Other)) return false;
        return true;
    };
    auto Preferred=Place(L,{(F.W-Width)*.5f,FMath::Max(F.Mode.bEnglishSubtitles?222.f*F.S:178.f*F.S,165.f)});
    if(Clear(Preferred)) { Preferred.bFits=true; return Preferred; }
    using namespace SoraCaptionLayoutRules;
    TArray<FRect> Blocks;
    for(const auto& Box:Obstacles) Blocks.Add({static_cast<float>(Box.Min.X),static_cast<float>(Box.Min.Y),
        static_cast<float>(Box.GetSize().X),static_cast<float>(Box.GetSize().Y)});
    const auto Regions=SoraAimHUDLayout::FreeRegions({static_cast<float>(View.Min.X),static_cast<float>(View.Min.Y),
        static_cast<float>(View.GetSize().X),static_cast<float>(View.GetSize().Y)},Blocks.GetData(),Blocks.Num(),Gap);
    for(int32 I=0;I<Regions.Count;++I)
    {
        const auto& R=Regions.Bounds[I];
        auto Trial=MeasureBoss(F,R.W);
        if(Trial.Bounds.GetSize().Y>R.H) continue;
        Trial=Place(MoveTemp(Trial),{R.X,R.Y});
        if(Clear(Trial)) { Trial.bFits=true; return Trial; }
    }
    // Preserve all content when capacity is unsupported. Shared render
    // qualification reports failure rather than silently hiding boss text.
    return Preferred;
}
FBox2D BossPanelBounds(const FSoraHUDFrame& F) { return BossLayout(F).Bounds; }
}
TArray<FBox2D> SoraHUDPanels::FixedGameplayPanelBounds(const FSoraHUDFrame& F)
{
    TArray<FBox2D> Bounds={ObjectivePanelBounds(F)};
    const auto Dojo=DojoPanelBounds(F); if(Dojo.bIsValid) Bounds.Add(Dojo);
    if(const auto* Hero=F.Mode.Hero()) Bounds.Append(SoraHUDPanels::StealthPanelBounds(F,*Hero));
    return Bounds;
}

TArray<FBox2D> SoraHUDPanels::UpperGameplayPanelBounds(const FSoraHUDFrame& F)
{
    auto Bounds=FixedGameplayPanelBounds(F);
    const auto Boss=BossPanelBounds(F); if(Boss.bIsValid) Bounds.Add(Boss);
    return Bounds;
}

void SoraHUDPanels::DrawObjective(const FSoraHUDFrame& Frame)
{
    const auto L=ObjectiveLayout(Frame);
    Frame.HUD.Panel(L.Bounds.Min.X,L.Bounds.Min.Y,L.Bounds.GetSize().X,L.Bounds.GetSize().Y,FLinearColor(.013f,.027f,.033f,.78f));
    for(const auto& Row:L.Text) Frame.HUD.Label(Row.Text,Row.At.X,Row.At.Y,Row.Scale,Row.Color);
}
bool SoraHUDPanels::ObjectiveLayoutFits(const FSoraHUDFrame& F,FString& Why)
{
    // Validate the exact rows DrawObjective renders, including retained text,
    // actual font dimensions, panel padding and separation from each other.
    const auto L=ObjectiveLayout(F); TArray<FBox2D> Occupied; FString Joined[4];
    if(L.Bounds.Min.X<0||L.Bounds.Max.X>F.W||L.Bounds.Min.Y<0||L.Bounds.Max.Y>F.H)
    { Why=TEXT("Objective panel exceeds the viewport"); return false; }
    for(const auto& Row:L.Text)
    {
        int32 W=0,H=0; UCanvas::ClippedStrLen(F.HUD.JapaneseFontObject(),Row.Scale,Row.Scale,W,H,Row.Text);
        const FBox2D Box(Row.At,Row.At+FVector2D(W,H));
        if(Box.Min.X<L.Bounds.Min.X+10*F.S-.5f||Box.Max.X>L.Bounds.Max.X-10*F.S+.5f||
            Box.Min.Y<L.Bounds.Min.Y||Box.Max.Y>L.Bounds.Max.Y+.5f)
        { Why=TEXT("Measured objective text escapes its allocated panel width or height"); return false; }
        for(const auto& Other:Occupied) if(Box.Intersect(Other))
        { Why=TEXT("Measured objective text rows overlap"); return false; }
        Occupied.Add(Box); Joined[Row.Group]+=Row.Text;
    }
    for(int32 I=0;I<4;++I) if(Joined[I]!=L.Original[I].Replace(TEXT("\n"),TEXT("")))
    { Why=TEXT("Objective wrapping lost localized text"); return false; }
    return true;
}
void SoraHUDPanels::DrawDojoLesson(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float S=Frame.S;
    const FLinearColor Ivory=Frame.Ivory,Muted=Frame.Muted;
    if(G->bCampaign&&G->Campaign()->ChapterId==0&&G->Campaign()->DojoLessonStage()<4)
    {
        const auto Panel=DojoPanelBounds(Frame);
        const float LessonTop=Panel.Min.Y;
        HUD.Panel(Panel.Min.X,Panel.Min.Y,Panel.GetSize().X,Panel.GetSize().Y,FLinearColor(.013,.027,.033,.88f));
        HUD.Label(G->Campaign()->DojoLessonText(false),40*S,LessonTop+6*S,.46*S,Ivory);
        if(G->bEnglishSubtitles) HUD.Label(G->Campaign()->DojoLessonText(true),40*S,LessonTop+36*S,.34*S,Muted);
    }
}
void SoraHUDPanels::DrawBoss(const FSoraHUDFrame& Frame)
{
    const auto L=BossLayout(Frame); if(!L.Bounds.bIsValid) return;
    Frame.HUD.Panel(L.Bounds.Min.X,L.Bounds.Min.Y,L.Bounds.GetSize().X,L.Bounds.GetSize().Y,FLinearColor(.013f,.027f,.033f,.91f));
    for(const auto& Rect:L.Rects)
        Frame.HUD.Panel(Rect.Bounds.Min.X,Rect.Bounds.Min.Y,Rect.Bounds.GetSize().X,Rect.Bounds.GetSize().Y,Rect.Color);
    for(const auto& Row:L.Text) Frame.HUD.Label(Row.Text,Row.At.X,Row.At.Y,Row.Scale,Row.Color);
}
bool SoraHUDPanels::BossLayoutFits(const FSoraHUDFrame& F,FString& Why)
{
    const auto L=BossLayout(F); if(!L.Bounds.bIsValid) return true;
    if(!L.bFits) { Why=TEXT("Complete boss readout cannot fit around the measured gameplay/story panels"); return false; }
    // Validate the actual draw rows/meters and every story rectangle, not an
    // assumed upper-story limit. Boss placement may use space below dialogue.
    if(L.Bounds.Min.X<20*F.S||L.Bounds.Min.Y<87*F.S||L.Bounds.Max.X>F.W-20*F.S||L.Bounds.Max.Y>F.H-30*F.S)
    { Why=TEXT("Measured boss panel exceeds the gameplay viewport"); return false; }
    for(const auto& Other:BossLayoutObstacles(F)) if(L.Bounds.Intersect(Other))
    {
        Why=FString::Printf(TEXT("Measured boss panel [%.2f,%.2f]-[%.2f,%.2f] overlaps HUD panel [%.2f,%.2f]-[%.2f,%.2f]"),
            L.Bounds.Min.X,L.Bounds.Min.Y,L.Bounds.Max.X,L.Bounds.Max.Y,Other.Min.X,Other.Min.Y,Other.Max.X,Other.Max.Y);
        return false;
    }
    TArray<FBox2D> InkBounds; TArray<FString> Joined; Joined.SetNum(L.Original.Num());
    const auto Contains=[&](const FBox2D& Box)
    { return Box.Min.X>=L.Bounds.Min.X&&Box.Min.Y>=L.Bounds.Min.Y&&Box.Max.X<=L.Bounds.Max.X+.5f&&Box.Max.Y<=L.Bounds.Max.Y+.5f; };
    for(const auto& Rect:L.Rects) if(!Contains(Rect.Bounds))
    { Why=TEXT("Boss health, phase, barrier or warning meter escapes its measured panel"); return false; }
    for(const auto& Row:L.Text)
    {
        const auto Ink=CaptionGlyphBounds(F,Row.Text,Row.Scale);
        const FBox2D Box(Row.At+Ink.Min,Row.At+Ink.Max);
        if(!Contains(Box)) { Why=TEXT("Boss text escapes its measured panel"); return false; }
        for(const auto& Other:InkBounds) if(Box.Intersect(Other))
        { Why=TEXT("Measured boss text rows overlap"); return false; }
        for(const auto& Rect:L.Rects) if(Box.Intersect(Rect.Bounds))
        { Why=TEXT("Measured boss text overlaps a health, phase, barrier or warning meter"); return false; }
        InkBounds.Add(Box); Joined[Row.Group]+=Row.Text;
    }
    for(int32 I=0;I<Joined.Num();++I) if(Joined[I]!=L.Original[I].Replace(TEXT("\n"),TEXT("")))
    { Why=TEXT("Boss wrapping lost localized content"); return false; }
    return true;
}
void SoraHUDPanels::DrawHero(const FSoraHUDFrame& Frame,const ASoraPlayerCharacter& Hero)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,H=Frame.H,S=Frame.S;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    const ASoraPlayerCharacter* P=&Hero; const USoraEquipmentComponent* Kit=Hero.GetEquipment();
    if(P->DamageFlash>0)
    {
        // Reduce flashing: a faint edge that fades out instead of a bright blink.
        const float Edge=Frame.bReduceFlashing?.25f*FMath::Clamp(P->DamageFlash/.3f,0.f,1.f):.65f;
        HUD.Panel(0,0,12*S,H,FLinearColor(.8,0,0,Edge)); HUD.Panel(W-12*S,0,12*S,H,FLinearColor(.8,0,0,Edge));
    }
    float CX=W*.5f,CY=H*.5f;
    if(!G->bDeterministicPractice&&P->WeaponId==18&&Kit->IsBowDrawing())
    {
        // Project the same camera-origin ray ReleaseBow uses. This is aim,
        // not an impact predictor: ordinary arrow drop remains visible.
        const FVector Aim=HUD.Project(P->GetCamera()->GetComponentLocation()+Kit->BowAimDirection()*10000.f);
        CX=Aim.X; CY=Aim.Y;
    }
    const FLinearColor Cross=P->HitMarkerTime>0?Gold:Ivory;
    HUD.DrawLine(CX-10,CY,CX-4,CY,Cross,1.5); HUD.DrawLine(CX+4,CY,CX+10,CY,Cross,1.5); HUD.DrawLine(CX,CY-10,CX,CY-4,Cross,1.5); HUD.DrawLine(CX,CY+4,CX,CY+10,Cross,1.5);
#if WITH_DEV_AUTOMATION_TESTS
    HUD.OnReticleDrawn.Broadcast(FVector2D(CX,CY));
#endif
    if(!G->bDeterministicPractice)
    {
        // 水月: a faint moon ring round the reticle while the opponent it
        // points at stands in the drawn blade's maai.
        const USoraCampaignDirector* Campaign=G->Campaign();
        if(Campaign->IsMaaiLesson()?Campaign->MaaiInBand():Kit->InMaai())
        {
            const FLinearColor Moon(.78f,.86f,.95f,.6f);
            constexpr int32 Segments=24;
            const float Radius=22.f*S;
            for(int32 I=0;I<Segments;++I)
            {
                const float A=2.f*PI*I/Segments,B=2.f*PI*(I+1)/Segments;
                HUD.DrawLine(CX+Radius*FMath::Cos(A),CY+Radius*FMath::Sin(A),CX+Radius*FMath::Cos(B),CY+Radius*FMath::Sin(B),Moon,1.2f);
            }
        }
        if(Campaign->MaaiReady())
        {
            if(SoraAccessibility::CampaignDifficulty(G)==SoraAccessibility::EDifficulty::Easy)
                HUD.Label(FString::Printf(TEXT("%.0f cm  [%d–%d cm]"),Campaign->MaaiDistance(),
                    Campaign->ActiveTask().Maai.InnerCm,Campaign->ActiveTask().Maai.OuterCm),CX-74*S,CY+38*S,.38*S,Ivory);
            const ASoraEnemy* Mentor=Campaign->MaaiMentor();
            const APlayerController* Controller=HUD.GetOwningPlayerController();
            if(Campaign->MaaiNeedsHelp()&&Mentor&&Controller)
            {
                // Project the two boundaries onto the dojo floor. This hint
                // appears only after six seconds without a confirmed step.
                const FVector Center=Mentor->GetActorLocation()-FVector(0,0,Mentor->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-3.f);
                const auto& Maai=Campaign->ActiveTask().Maai;
                for(const float Radius:{static_cast<float>(Maai.InnerCm),static_cast<float>(Maai.OuterCm)})
                    for(int32 Segment=0;Segment<64;++Segment)
                    {
                        const float A=2.f*PI*Segment/64.f,B=2.f*PI*(Segment+1)/64.f;
                        FVector2D From,To;
                        if(Controller->ProjectWorldLocationToScreen(Center+FVector(FMath::Cos(A)*Radius,FMath::Sin(A)*Radius,0),From)&&
                            Controller->ProjectWorldLocationToScreen(Center+FVector(FMath::Cos(B)*Radius,FMath::Sin(B)*Radius,0),To))
                            HUD.DrawLine(From.X,From.Y,To.X,To.Y,Frame.Teal,2.f*S);
                    }
            }
        }
        // 転: the step is open (after an awase, or in a blow's last stretch).
        if(!Kit->IsStepping()&&SoraDefense::MarobashiTarget(Hero))
        {
            HUD.Label(TEXT("転 ― 左右＋［跳躍］"),CX-70*S,CY-72*S,.5*S,Gold);
            if(G->bEnglishSubtitles) HUD.Label(TEXT("MAROBASHI: Left/Right + [Jump]"),CX-82*S,CY-48*S,.32*S,Muted);
        }
        // 残心: the lingering guard gave back its share.
        if(P->GetWorld()->GetTimeSeconds()-Kit->LastZanshinAt()<1.2f)
        {
            HUD.Label(FString::Printf(TEXT("残心 ＋%d"),SoraCombatRules::ZanshinStamina),CX+30*S,CY+14*S,.42*S,Teal);
            if(G->bEnglishSubtitles) HUD.Label(FString::Printf(TEXT("ZANSHIN +%d"),SoraCombatRules::ZanshinStamina),CX+30*S,CY+34*S,.3*S,Muted);
        }
    }
    HUD.Panel(25*S,H-110*S,340*S,80*S,FLinearColor(.015,.035,.05,.9));
    HUD.Label(FString::Printf(TEXT("%03d"),FMath::CeilToInt(P->Health)),45*S,H-103*S,1.5*S,Ivory);
    HUD.Label(FSoraCatalog::Get().Class(P->ClassId).Name,140*S,H-82*S,.65*S,Teal);
    HUD.Panel(45*S,H-45*S,290*S,4*S,FLinearColor(.12,.19,.21)); HUD.Panel(45*S,H-45*S,290*S*FMath::Clamp(P->Health/P->MaxHealth,0.f,1.f),4*S,Teal);
    DrawWeapon(Frame,Hero);
    if(G->Arena()&&!G->bDeterministicPractice)
    {
        for(int32 I=0;I<G->Arena()->NodePositions.Num();++I)
        {
            if((G->Arena()->ActivatedMask()&(1<<I))!=0) continue;
            const FVector Position=G->Arena()->NodePositions[I]+FVector(0,0,250);
            if(FVector::DotProduct(Position-P->GetActorLocation(),P->GetActorForwardVector())>0)
            {
                const FVector Screen=HUD.Project(Position); const int32 M=FMath::RoundToInt(FVector::Dist2D(Position,P->GetActorLocation())/100);
                if(Screen.X>0&&Screen.X<W&&Screen.Y>170*S&&Screen.Y<H-120*S)
                {
                    const FString SiteName=G->bCampaign?FSoraCatalog::Get().Chapter(G->Campaign()->ChapterId).Sites[I].Name:FString::Printf(TEXT("工房 %d"),I+1);
                    const FString Text=FString::Printf(TEXT("%s / %dm"),*SiteName,M);
                    int32 TW=0,TH=0; UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),.42*S,.42*S,TW,TH,Text);
                    const auto At=DrawWorldLabelBacking(Frame,{Screen.X-75*S,Screen.Y},{static_cast<float>(TW),static_cast<float>(TH)});
                    HUD.Label(Text,At.X,At.Y,.42*S,Teal);
                }
            }
        }
        const bool NearSite=G->Arena()->NearestInactiveNode(P->GetActorLocation())!=INDEX_NONE;
        bool Near=NearSite;
        Near|=FVector::Dist2D(G->Arena()->ExitPoint(),P->GetActorLocation())<270;
        if(Near)
        {
            const auto Line=SoraText::Format(NSLOCTEXT("SoraArena.HUD","Prompt.Examine","{Interact}  調べる"),
                {{TEXT("Interact"),SoraUI::ActionKey(&HUD,TEXT("Interact"))}});
            int32 JW=0,JH=0,EW=0,EH=0;
            UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),.65*S,.65*S,JW,JH,Line.Japanese);
            if(G->bEnglishSubtitles) UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),.52*S,.52*S,EW,EH,Line.English);
            const auto At=DrawWorldLabelBacking(Frame,{CX-75*S,CY+60*S},
                {static_cast<float>(JW)+(G->bEnglishSubtitles?14*S+EW:0),FMath::Max(static_cast<float>(JH),EH+3.9f*S)});
            Frame.LabelWithEnglish(Line,At.X,At.Y,.65*S,Gold);
        }
    }
}
