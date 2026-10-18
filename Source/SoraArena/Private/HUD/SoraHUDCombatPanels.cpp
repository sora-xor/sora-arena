#include "HUD/SoraHUDPanels.h"
#include "ArenaKernelSubsystem.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraDefense.h"
#include "SoraBoss.h"
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
#include "Components/CapsuleComponent.h"
#include "GameFramework/PlayerController.h"

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
    const ASoraBoss* Boss=G->Campaign()->CampaignBoss();
    const FSoraBossData* Info=Boss?Boss->Data():nullptr;
    if(!Info) return;
    // Name, health with its phase marks, then the defenses in play and the
    // captioned telegraph of the attack under way (bosses.json, bilingual).
    const FLinearColor Amber(1.f,.68f,.16f),Cyan(.04f,.85f,.95f);
    const float BossWidth=FMath::Min(W-20.f,FMath::Max(600.f*S,480.f));
    const float BossX=(W-BossWidth)*.5f,
        BossY=FMath::Max(G->bEnglishSubtitles?222.f*S:178.f*S,165.f);
    const bool bEnglish=G->bEnglishSubtitles;
    // The answer the attack under way allows, by the actions that give it:
    // mutō-dori from a sheathed hand, or 転 in its last stretch.
    const FSoraBossAttack* Attack=Boss->BossAttack();
    const auto* Hero=Cast<ASoraPlayerCharacter>(HUD.GetOwningPawn());
    FString HintJapanese,HintEnglish;
    if(Attack&&Boss->IsBossTelegraphing()&&Attack->bMuto&&Info->bMutoFinisher)
    {
        const bool bSheathed=Hero&&Hero->GetEquipment()->IsSheathing();
        HintJapanese=bSheathed?TEXT("納刀済 ― 斬撃の寸前に［防御］で無刀取り"):TEXT("［納刀］で納め、斬撃の寸前に［防御］で無刀取り");
        HintEnglish=bSheathed?TEXT("Sheathed: [Guard] just before the cut lands for mutō-dori"):
            TEXT("[Sheathe], then [Guard] just before the cut lands for mutō-dori");
    }
    else if(Attack&&Boss->IsBossTelegraphing()&&Attack->MarobashiMs>0)
    {
        HintJapanese=TEXT("転 ― 着く寸前に 左右＋［跳躍］で脇へ");
        HintEnglish=TEXT("Marobashi: Left/Right + [Jump] just before it lands to reach the flank");
    }
    const float Base=bEnglish?142.f:116.f;
    const float Hints=HintJapanese.IsEmpty()?0.f:bEnglish?40.f:22.f;
    HUD.Panel(BossX,BossY,BossWidth,Base+Hints,FLinearColor(.013f,.027f,.033f,.91f));
    if(!HintJapanese.IsEmpty())
    {
        HUD.Label(HintJapanese,BossX+17.f,BossY+Base,.36f,Gold);
        if(bEnglish) HUD.Label(HintEnglish,BossX+17.f,BossY+Base+19.f,.32f,Muted);
    }
    HUD.Label(Info->NameJapanese,BossX+17.f,BossY+7.f,JapaneseSubtitleScale,Gold);
    if(bEnglish) HUD.Label(Info->NameEnglish,BossX+BossWidth-17.f-HUD.LabelWidth(Info->NameEnglish,EnglishSubtitleScale),BossY+9.f,EnglishSubtitleScale,Muted);
    const float BarX=BossX+17.f,BarW=BossWidth-34.f,BarY=BossY+36.f;
    HUD.Panel(BarX,BarY,BarW,7.f,FLinearColor(.15f,.18f,.20f));
    HUD.Panel(BarX,BarY,BarW*FMath::Clamp(Boss->Health/Boss->MaxHealth,0.f,1.f),7.f,Boss->IsInvulnerable()?Muted:Gold);
    for(int32 Index=1;Index<Info->Phases.Num();++Index)
        HUD.Panel(BarX+BarW*Info->Phases[Index].FromPermille/1000.f-1.f,BarY-3.f,2.f,13.f,Ivory);
    if(Boss->HasBarrier()&&Info->Barrier.Health>0)
    {
        HUD.Panel(BarX,BarY+10.f,BarW,3.f,FLinearColor(.15f,.18f,.20f));
        HUD.Panel(BarX,BarY+10.f,BarW*FMath::Clamp(Boss->BarrierPoints()/static_cast<float>(Info->Barrier.Health),0.f,1.f),3.f,
            FLinearColor(.78f,.74f,.92f));
    }
    // What is open or closed right now, in both languages.
    TArray<FString> Japanese,English;
    if(Boss->IsInvulnerable()) { Japanese.Add(TEXT("無敵")); English.Add(TEXT("INVULNERABLE")); }
    if(Boss->IsShieldUp()) { Japanese.Add(TEXT("大盾：正面不可")); English.Add(TEXT("SHIELD: front blocked")); }
    if(Boss->HasBarrier()) { Japanese.Add(Boss->IsBarrierOffline()?TEXT("障壁：停止中"):TEXT("障壁")); English.Add(Boss->IsBarrierOffline()?TEXT("BARRIER: down"):TEXT("BARRIER")); }
    if(Boss->IsMantleUp()) { Japanese.Add(TEXT("冷却外套：被害七割減")); English.Add(TEXT("MANTLE: 70% less damage")); }
    if(Boss->IsStaggered()) { Japanese.Add(TEXT("崩れ：好機")); English.Add(TEXT("STAGGERED: strike now")); }
    for(int32 Index=0;Index<Info->WeakPoints.Num();++Index)
        if(Boss->IsWeakPointOpen(Index)) { Japanese.Add(Info->WeakPoints[Index].NameJapanese); English.Add(Info->WeakPoints[Index].NameEnglish); }
    if(Boss->LiveWards()>0&&Info->Wards.IsValidIndex(Boss->CurrentPhase()->Ward))
    {
        const FSoraBossWard& Ward=Info->Wards[Boss->CurrentPhase()->Ward];
        Japanese.Add(FString::Printf(TEXT("%s ×%d"),*Ward.NameJapanese,Boss->LiveWards()));
        English.Add(FString::Printf(TEXT("%s x%d"),*Ward.NameEnglish,Boss->LiveWards()));
    }
    for(const FSoraBossAttack& Limited:Info->Attacks)
        if(Limited.EventLimit>0)
        {
            Japanese.Add(FString::Printf(TEXT("差押え %d / %d"),Boss->Seals(),Limited.EventLimit));
            English.Add(FString::Printf(TEXT("SEIZED %d / %d"),Boss->Seals(),Limited.EventLimit));
        }
    if(Japanese.Num())
        HUD.Label(FString::Join(Japanese,TEXT("　")),BarX,BarY+15.f,.34f,Teal);
    if(bEnglish&&English.Num())
        HUD.Label(FString::Join(English,TEXT("  ")),BarX+BarW*.5f,BarY+16.f,.3f,Muted);
    if(Attack&&Boss->IsBossTelegraphing())
    {
        const FLinearColor Warning=Attack->Telegraph==ESoraBossTelegraph::Cyan?Cyan:Amber;
        HUD.Label(Attack->TellJapanese,BossX+17.f,BossY+66.f,JapaneseSubtitleScale,Attack->Telegraph==ESoraBossTelegraph::None?Ivory:Warning);
        if(bEnglish)
            HUD.Label(Attack->TellEnglish,BossX+17.f,BossY+93.f,EnglishSubtitleScale,Muted);
        HUD.Label(FString::Printf(TEXT("%.1f s"),Boss->BossWarningSeconds()),BossX+BossWidth-88.f,BossY+(bEnglish?112.f:88.f),.48f,Gold);
        HUD.Panel(BossX+BossWidth-108.f,BossY+(bEnglish?134.f:110.f),90.f,4.f,FLinearColor(.15f,.18f,.20f));
        HUD.Panel(BossX+BossWidth-108.f,BossY+(bEnglish?134.f:110.f),90.f*Boss->BossWarningProgress(),4.f,Warning);
    }
    else if(!Info->StyleJapanese.IsEmpty())
    {
        HUD.Label(Info->StyleJapanese,BossX+17.f,BossY+66.f,.42f,Muted);
        if(bEnglish) HUD.Label(Info->StyleEnglish,BossX+17.f,BossY+93.f,.34f,Muted);
    }
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
    const float CX=W*.5f,CY=H*.5f; const FLinearColor Cross=P->HitMarkerTime>0?Gold:Ivory;
    HUD.DrawLine(CX-10,CY,CX-4,CY,Cross,1.5); HUD.DrawLine(CX+4,CY,CX+10,CY,Cross,1.5); HUD.DrawLine(CX,CY-10,CX,CY-4,Cross,1.5); HUD.DrawLine(CX,CY+4,CX,CY+10,Cross,1.5);
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
                    HUD.Label(FString::Printf(TEXT("%s / %dm"),*SiteName,M),Screen.X-75*S,Screen.Y,.42*S,Teal);
                }
            }
        }
        const bool NearSite=G->Arena()->NearestInactiveNode(P->GetActorLocation())!=INDEX_NONE;
        bool Near=NearSite;
        Near|=FVector::Dist2D(G->Arena()->ExitPoint(),P->GetActorLocation())<270;
        if(Near)
            Frame.LabelWithEnglish(SoraText::Format(NSLOCTEXT("SoraArena.HUD","Prompt.Examine","{Interact}  調べる"),
                {{TEXT("Interact"),SoraUI::ActionKey(&HUD,TEXT("Interact"))}}),CX-75*S,CY+60*S,.65*S,Gold);
    }
}
