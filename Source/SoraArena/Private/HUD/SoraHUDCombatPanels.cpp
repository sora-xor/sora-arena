#include "HUD/SoraHUDPanels.h"
#include "ArenaKernelSubsystem.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeDirector.h"
#include "SoraWorldBuilder.h"

void SoraHUDPanels::DrawObjective(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,S=Frame.S,EnglishSubtitleScale=Frame.EnglishSubtitleScale,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Teal=Frame.Teal,Muted=Frame.Muted;
    HUD.Panel(20*S,87*S,FMath::Min(W-40*S,850*S),G->bEnglishSubtitles?125*S:90*S,
        FLinearColor(.013f,.027f,.033f,.78f));
    const FString HeaderTitle=G->bCampaign?FSoraCatalog::Get().Chapter(G->Campaign()->ChapterId).Title:FSoraCatalog::Get().Map(G->MapId).Name;
    HUD.Label(HeaderTitle,30*S,95*S,.82*S,Ivory);
    if(G->bEnglishSubtitles)
    {
        const float TitleW=HUD.LabelWidth(HeaderTitle,.82*S);
        HUD.Label(G->bCampaign?FSoraCatalog::Get().Chapter(G->Campaign()->ChapterId).TitleEnglish:FSoraCatalog::Get().Map(G->MapId).NameEnglish,
            30*S+TitleW+18*S,106*S,.45*S,Muted);
    }
    HUD.Label(G->ObjectiveText(),30*S,137*S,.52*S,Teal);
    if(G->bEnglishSubtitles)
        HUD.WrappedLabel(G->ObjectiveTextEnglish(),30*S,164*S,EnglishSubtitleScale,Muted,
            W-60*S,EnglishSubtitleLineHeight,2);
}
void SoraHUDPanels::DrawDojoLesson(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float S=Frame.S,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Muted=Frame.Muted;
    if(G->bCampaign&&G->Campaign()->ChapterId==0&&G->Campaign()->DojoLessonStage()<4)
    {
        const float LessonTop=G->bEnglishSubtitles
            ?FMath::Max(217*S,164*S+2*EnglishSubtitleLineHeight+8*S):169*S;
        HUD.Panel(25*S,LessonTop,720*S,G->bEnglishSubtitles?72*S:47*S,FLinearColor(.013,.027,.033,.88f));
        HUD.Label(G->Campaign()->DojoLessonText(false),40*S,LessonTop+6*S,.46*S,Ivory);
        if(G->bEnglishSubtitles) HUD.Label(G->Campaign()->DojoLessonText(true),40*S,LessonTop+36*S,.34*S,Muted);
    }
}
void SoraHUDPanels::DrawBoss(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,S=Frame.S,JapaneseSubtitleScale=Frame.JapaneseSubtitleScale,EnglishSubtitleScale=Frame.EnglishSubtitleScale;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    if(const ASoraBoss* Boss=G->Campaign()->CampaignBoss())
    {
        const float BossWidth=FMath::Min(W-20.f,FMath::Max(560.f*S,470.f));
        const float BossX=(W-BossWidth)*.5f,
            BossY=FMath::Max(G->bEnglishSubtitles?222.f*S:178.f*S,165.f);
        HUD.Panel(BossX,BossY,BossWidth,114.f,FLinearColor(.013f,.027f,.033f,.91f));
        HUD.Label(TEXT("異星の徴収官"),BossX+17.f,BossY+7.f,JapaneseSubtitleScale,Gold);
        if(G->bEnglishSubtitles) HUD.Label(TEXT("ALIEN COLLECTOR"),BossX+BossWidth-185.f,BossY+9.f,EnglishSubtitleScale,Muted);
        HUD.Panel(BossX+17.f,BossY+36.f,BossWidth-34.f,7.f,FLinearColor(.15f,.18f,.20f));
        HUD.Panel(BossX+17.f,BossY+36.f,(BossWidth-34.f)*FMath::Clamp(Boss->Health/Boss->MaxHealth,0.f,1.f),7.f,Gold);
        if(Boss->IsBossTelegraphing())
        {
            HUD.Label(Boss->IsBossBeamWindup()?TEXT("債務光線の予兆 ― 線から離れよ"):TEXT("斬撃の予兆 ― 受けるか、合わせるか、間合いから離れよ"),
                BossX+17.f,BossY+51.f,JapaneseSubtitleScale,Ivory);
            if(G->bEnglishSubtitles)
                HUD.Label(Boss->IsBossBeamWindup()?TEXT("DEBT BEAM: evade the line"):TEXT("CLEAVE: guard, parry, or leave the arc"),
                    BossX+17.f,BossY+78.f,EnglishSubtitleScale,Muted);
            HUD.Label(FString::Printf(TEXT("%.1f s"),Boss->BossWarningSeconds()),BossX+BossWidth-88.f,BossY+76.f,.48f,Gold);
            HUD.Panel(BossX+BossWidth-108.f,BossY+101.f,90.f,4.f,FLinearColor(.15f,.18f,.20f));
            HUD.Panel(BossX+BossWidth-108.f,BossY+101.f,90.f*Boss->BossWarningProgress(),4.f,Teal);
        }
    }
}
void SoraHUDPanels::DrawHero(const FSoraHUDFrame& Frame,const ASoraPlayerCharacter& Hero)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,H=Frame.H,S=Frame.S;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    const ASoraPlayerCharacter* P=&Hero; const USoraEquipmentComponent* Kit=Hero.GetEquipment();
    if(P->DamageFlash>0) { HUD.Panel(0,0,12*S,H,FLinearColor(.8,0,0,.65)); HUD.Panel(W-12*S,0,12*S,H,FLinearColor(.8,0,0,.65)); }
    const float CX=W*.5f,CY=H*.5f; const FLinearColor Cross=P->HitMarkerTime>0?Gold:Ivory;
    HUD.DrawLine(CX-10,CY,CX-4,CY,Cross,1.5); HUD.DrawLine(CX+4,CY,CX+10,CY,Cross,1.5); HUD.DrawLine(CX,CY-10,CX,CY-4,Cross,1.5); HUD.DrawLine(CX,CY+4,CX,CY+10,Cross,1.5);
    HUD.Panel(25*S,H-110*S,340*S,80*S,FLinearColor(.015,.035,.05,.9));
    HUD.Label(FString::Printf(TEXT("%03d"),FMath::CeilToInt(P->Health)),45*S,H-103*S,1.5*S,Ivory);
    HUD.Label(FSoraCatalog::Get().Class(P->ClassId).Name,140*S,H-82*S,.65*S,Teal);
    HUD.Panel(45*S,H-45*S,290*S,4*S,FLinearColor(.12,.19,.21)); HUD.Panel(45*S,H-45*S,290*S*FMath::Clamp(P->Health/P->MaxHealth,0.f,1.f),4*S,Teal);
    const auto& Weapon=FSoraCatalog::Get().Weapon(P->WeaponId);
    HUD.Panel(W-390*S,H-110*S,365*S,80*S,FLinearColor(.015,.035,.05,.9));
    HUD.Label(G->bCampaign&&G->Campaign()->ChapterId==0?TEXT("木刀 / 非致死の立合い"):Weapon.Name,W-365*S,H-96*S,.72*S,Ivory);
    if(G->bDeterministicPractice)
    {
        if(auto* K=G->Kernel()) if(K->PracticePlayers.Num()>0)
        {
            const auto& State=K->PracticePlayers[0];
            const FString Ammunition=State.Magazine==0?TEXT("剣術 / 右クリック"):
                State.ReloadTicks>0?FString::Printf(TEXT("装填中 %.1f 秒   %d / %d"),State.ReloadTicks/60.f,State.Ammo,State.Magazine):
                FString::Printf(TEXT("弾数 %02d / %02d   R 装填"),State.Ammo,State.Magazine);
            HUD.Label(Ammunition,W-365*S,H-71*S,.46*S,Gold);
            HUD.Label(FString::Printf(TEXT("気力 %d / 100    待機 %.2f 秒"),State.Stamina,State.Cooldown/60.f),W-365*S,H-48*S,.33*S,Muted);
            if(State.Alive&&State.ChargeRequired>0&&State.ChargeTicks>0)
            {
                const float Progress=FMath::Clamp(static_cast<float>(State.ChargeTicks)/State.ChargeRequired,0.f,1.f);
                HUD.Panel(W-390*S,H-145*S,365*S,29*S,FLinearColor(.015,.035,.05,.92));
                HUD.Label(FString::Printf(TEXT("構え %d / %d"),State.ChargeTicks,State.ChargeRequired),W-365*S,H-142*S,.37*S,Gold);
                if(G->bEnglishSubtitles) HUD.Label(TEXT("WINDUP"),W-125*S,H-141*S,.28*S,Muted);
                HUD.Panel(W-365*S,H-122*S,320*S,4*S,FLinearColor(.12,.19,.21));
                HUD.Panel(W-365*S,H-122*S,320*S*Progress,4*S,Gold);
            }
            if(!State.Alive)
            {
                HUD.Panel(W*.25,H*.35,W*.5,120*S,FLinearColor(.013,.027,.033,.88f));
                HUD.Label(FString::Printf(TEXT("%.1f 秒後に復帰します"),State.RespawnTicks/60.f),W*.3,H*.38,.9*S,Gold);
                if(G->bEnglishSubtitles) HUD.Label(TEXT("Respawning — no stake is at risk."),W*.3,H*.38+48*S,.45*S,Ivory);
            }
            if(G->Practice()->bSlowed) HUD.Label(TEXT("処理負荷により、稽古時間を減速しています"),30*S,200*S,.4*S,Gold);
        }
    }
    else
    {
        HUD.Label(Kit->bReloading?TEXT("装填中"):Weapon.Kind==TEXT("melee")?TEXT("間合い / 斬突と残心"):
            Weapon.Kind==TEXT("bow")?FString::Printf(TEXT("矢 %02d / %02d   長押し→離して射る"),Kit->Ammo,Weapon.Magazine):
            FString::Printf(TEXT("%02d / %02d   R 装填"),Kit->Ammo,Weapon.Magazine),W-365*S,H-59*S,.54*S,Gold);
        if(Kit->IsBowDrawing()||Kit->IsCommittedStrike())
        {
            const bool bDraw=Kit->IsBowDrawing();
            const float Progress=bDraw?Kit->BowDrawProgress():Kit->StrikeWindupProgress();
            HUD.Panel(W-390*S,H-145*S,365*S,29*S,FLinearColor(.015,.035,.05,.92));
            HUD.Label(bDraw?TEXT("会 / 引き分け"):TEXT("打突の構え"),W-365*S,H-142*S,.37*S,Gold);
            if(G->bEnglishSubtitles) HUD.Label(bDraw?TEXT("DRAW / RELEASE"):TEXT("COMMITTED STRIKE"),W-160*S,H-141*S,.28*S,Muted);
            HUD.Panel(W-365*S,H-122*S,320*S,4*S,FLinearColor(.12,.19,.21));
            HUD.Panel(W-365*S,H-122*S,320*S*Progress,4*S,Gold);
        }
        if(G->bCampaign&&G->Campaign()->ChapterId>0&&
            (P->WeaponId==0||P->WeaponId==19||P->WeaponId==20))
        {
            HUD.Panel(W-365*S,H-35*S,320*S,3*S,FLinearColor(.12,.19,.21));
            HUD.Panel(W-365*S,H-35*S,320*S*FMath::Clamp(Kit->GuardReserve()/100.f,0.f,1.f),3*S,Teal);
        }
    }
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
                    HUD.Label(FString::Printf(TEXT("%s / %dm"),*SiteName,M),Screen.X-75*S,Screen.Y,.42*S,Teal);
                }
            }
        }
        const bool NearSite=G->Arena()->NearestInactiveNode(P->GetActorLocation())!=INDEX_NONE;
        bool Near=NearSite;
        Near|=FVector::Dist2D(G->Arena()->ExitPoint(),P->GetActorLocation())<270;
        if(Near) HUD.Label(TEXT("E  調べる"),CX-75*S,CY+60*S,.65*S,Gold);
    }
}
