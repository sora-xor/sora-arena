#include "HUD/SoraHUDPanels.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Engine/Texture2D.h"

namespace
{
// One row of the beat tracker: a Japanese label with its English beneath,
// and a bar when Fraction is not negative.
struct FTrackerRow
{
    FString Japanese;
    FString English;
    float Fraction = -1.f;
    FLinearColor Color = FLinearColor::White;
};
const TCHAR* const GaitJapanese[] = {TEXT("停止"), TEXT("常歩"), TEXT("速歩"), TEXT("駈歩"), TEXT("襲歩")};
const TCHAR* const GaitEnglish[] = {TEXT("halt"), TEXT("walk"), TEXT("trot"), TEXT("canter"), TEXT("gallop")};
FString HorseName(FName Horse, bool bEnglish)
{
    return Horse==TEXT("kurimaru")?(bEnglish?TEXT("Kurimaru"):TEXT("栗丸")):Horse==TEXT("arashi")?(bEnglish?TEXT("Arashi"):TEXT("嵐"))
        :(bEnglish?TEXT("Pack horse"):TEXT("荷駄馬"));
}
FString TackName(FName Part, bool bEnglish)
{
    return Part==TEXT("kura")?(bEnglish?TEXT("saddle (kura)"):TEXT("鞍")):Part==TEXT("haruobi")?(bEnglish?TEXT("girth (haruobi)"):TEXT("腹帯"))
        :Part==TEXT("abumi")?(bEnglish?TEXT("stirrups (abumi)"):TEXT("鐙")):(bEnglish?TEXT("bit and reins (kutsuwa, tazuna)"):TEXT("轡と手綱"));
}
// The active beat: where it stands in the chapter, its task's progress and
// what that task needs now, and the horse of a ride.
TArray<FTrackerRow> TrackerRows(const FSoraHUDFrame& Frame)
{
    TArray<FTrackerRow> Rows;
    const ASoraGameMode& G=Frame.Mode;
    const USoraCampaignDirector* Campaign=G.Campaign();
    const FSoraBeat* Beat=Campaign->ActiveBeatData();
    const FSoraChapter* Chapter=Campaign->ActiveChapter();
    const SoraBeatRules::FTask& Task=Campaign->ActiveTask();
    const SoraBeatRules::FTaskState& State=Campaign->TaskProgress();
    const float Fraction=SoraBeatRules::ProgressPermille(State,Task)/1000.f;
    int32 Required=0,Number=0;
    for(int32 Index=0;Index<Chapter->Rules.Num();++Index)
        if(!Chapter->Rules[Index].Optional) { ++Required; if(Index<=Campaign->ActiveBeat()) ++Number; }
    Rows.Add({FString::Printf(TEXT("第%d場  %s"),Number,*Beat->Title),FString::Printf(TEXT("Beat %d of %d: %s"),Number,Required,*Beat->TitleEnglish),-1.f,Frame.Ivory});
    using SoraBeatRules::EGoal;
    switch(Task.Goal)
    {
    case EGoal::WavesCleared:
        Rows.Add({FString::Printf(TEXT("侵略者を退ける  %d / %d"),SoraBeatRules::Defeated(State,Task),SoraBeatRules::TotalLethal(Task)),
            FString::Printf(TEXT("Drive off the invaders: %d of %d"),SoraBeatRules::Defeated(State,Task),SoraBeatRules::TotalLethal(Task)),Fraction,Frame.Gold});
        break;
    case EGoal::Objectives:
        Rows.Add({FString::Printf(TEXT("目標  %d / %d"),State.Done,Task.Count),FString::Printf(TEXT("Objectives: %d of %d"),State.Done,Task.Count),Fraction,Frame.Gold});
        break;
    case EGoal::Survive:
        Rows.Add({FString::Printf(TEXT("持ちこたえる  残り %d 秒"),FMath::DivideAndRoundUp(Task.DurationMs-State.Progress,1000)),
            FString::Printf(TEXT("Hold out: %d s left"),FMath::DivideAndRoundUp(Task.DurationMs-State.Progress,1000)),Fraction,Frame.Gold});
        break;
    case EGoal::Points:
        Rows.Add({FString::Printf(TEXT("一本  %d 対 %d"),State.Done,State.RivalPoints),FString::Printf(TEXT("Points: %d to %d"),State.Done,State.RivalPoints),-1.f,Frame.Gold});
        break;
    case EGoal::Lessons:
        Rows.Add({TEXT("型と立合い"),TEXT("Forms and bouts"),Fraction,Frame.Gold});
        break;
    case EGoal::OpponentDown:
        Rows.Add({FString::Printf(TEXT("相手を倒す  第%d段 / %d"),State.Phase+1,Task.PhaseCount),
            FString::Printf(TEXT("Defeat your opponent: phase %d of %d"),State.Phase+1,Task.PhaseCount),1.f-Fraction,Frame.Gold});
        break;
    case EGoal::Exit:
        Rows.Add({FString::Printf(TEXT("%s  %d%%"),Beat->Is(SoraBeatRules::EType::HorsebackRide)?TEXT("目的地まで"):TEXT("出口まで"),FMath::RoundToInt32(Fraction*100.f)),
            FString::Printf(TEXT("%d%% of the way"),FMath::RoundToInt32(Fraction*100.f)),Fraction,Frame.Gold});
        break;
    case EGoal::Hold:
        Rows.Add({FString::Printf(TEXT("持ちこたえる  %d / %d 秒"),State.Progress/1000,FMath::DivideAndRoundUp(Task.DurationMs,1000)),
            FString::Printf(TEXT("Hold the ground: %d of %d s"),State.Progress/1000,FMath::DivideAndRoundUp(Task.DurationMs,1000)),Fraction,Frame.Teal});
        break;
    case EGoal::Turns:
        Rows.Add({FString::Printf(TEXT("回す  %d / %d"),State.Done,Task.Count),FString::Printf(TEXT("Turn the crank: %d of %d"),State.Done,Task.Count),Fraction,Frame.Teal});
        if(SoraBeatRules::CrankSlipping(State,Task))
            Rows.Add({TEXT("緩んでいる。一定の調子で回し続けろ"),TEXT("Slipping back: keep a steady rhythm"),-1.f,FLinearColor(.9f,.35f,.2f)});
        break;
    case EGoal::Escort:
    {
        Rows.Add({FString::Printf(TEXT("護衛  %d%%"),FMath::RoundToInt32(Fraction*100.f)),FString::Printf(TEXT("Escort: %d%% of the way"),FMath::RoundToInt32(Fraction*100.f)),Fraction,Frame.Teal});
        const ASoraPlayerCharacter* Hero=G.Hero();
        if(Hero&&FVector::Dist2D(Hero->GetActorLocation(),Campaign->PartyLocation())>Task.WaitCm)
            Rows.Add({TEXT("一行が待っている。そばへ戻れ"),TEXT("The party waits for you: stay close"),-1.f,FLinearColor(.9f,.6f,.2f)});
        break;
    }
    case EGoal::Deliveries:
        Rows.Add({FString::Printf(TEXT("運ぶ  %d / %d"),State.Done,Task.Count),FString::Printf(TEXT("Delivered: %d of %d"),State.Done,Task.Count),Fraction,Frame.Teal});
        if(State.Carrying)
            Rows.Add({TEXT("荷を抱えている：足が遅く、刀は片手"),TEXT("Carrying a load: slower, katana one-handed at most"),-1.f,Frame.Muted});
        break;
    case EGoal::Steps:
    {
        Rows.Add({FString::Printf(TEXT("工程  %d / %d"),FMath::Min(State.Step+1,Task.StepCount),Task.StepCount),
            FString::Printf(TEXT("Step %d of %d"),FMath::Min(State.Step+1,Task.StepCount),Task.StepCount),Fraction,Frame.Teal});
        for(int32 Step=0;Step<Beat->StepKinds.Num();++Step)
            if(const FSoraLabel* Label=FSoraCatalog::Get().StepLabels.Find(Beat->StepKinds[Step]))
                Rows.Add({FString::Printf(TEXT("%s %s ×%d"),Step<State.Step?TEXT("済"):Step==State.Step?TEXT("▶"):TEXT("・"),*Label->Japanese,Task.Steps[Step].Count),
                    FString::Printf(TEXT("%s %s x%d"),Step<State.Step?TEXT("done"):Step==State.Step?TEXT("now"):TEXT("next"),*Label->English,Task.Steps[Step].Count),
                    -1.f,Step<State.Step?Frame.Teal:Step==State.Step?Frame.Gold:Frame.Muted});
        break;
    }
    default:
        break;
    }
    // Defended targets and how much of each still stands.
    for(int32 Target=0;Target<Task.TargetCount&&Target<Beat->Targets.Num();++Target)
        if(const FSoraLabel* Label=FSoraCatalog::Get().TargetLabels.Find(Beat->Targets[Target]))
        {
            const float Health=Task.TargetHp[Target]>0?static_cast<float>(State.TargetHp[Target])/Task.TargetHp[Target]:0.f;
            Rows.Add({Label->Japanese,Label->English,Health,FMath::Lerp(FLinearColor(.78f,.12f,.08f),Frame.Teal,Health)});
        }
    // A hold fills only while the hero stands on the ground he holds.
    const ASoraPlayerCharacter* Holder=G.Hero();
    if(Task.Goal==EGoal::Hold&&Holder&&State.Progress<Task.DurationMs&&
        FVector::Dist2D(ASoraWorldBuilder::Floor(Beat->Space.Anchor),Holder->GetActorLocation())>420.f)
        Rows.Add({TEXT("持ち場を離れている"),TEXT("You have left the ground you hold"),-1.f,FLinearColor(.9f,.6f,.2f)});
    // The horse of a ride: her gait, pace and wind, and what E does with her.
    if(const ASoraHorse* Horse=Campaign->Steed())
    {
        const int32 Gait=SoraMountRules::Index(Horse->Gait());
        const FName Name=Beat->Space.bMount?Beat->Space.Mount.Horse:FName(TEXT("kurimaru"));
        Rows.Add({FString::Printf(TEXT("%s  %s  %.1f m/s"),*HorseName(Name,false),GaitJapanese[Gait],Horse->SpeedCmS()/100.f),
            FString::Printf(TEXT("%s: %s, %.1f m/s"),*HorseName(Name,true),GaitEnglish[Gait],Horse->SpeedCmS()/100.f),
            Horse->StaminaPoints()/100.f,Horse->IsWinded()?FLinearColor(.85f,.3f,.15f):Frame.Gold});
        if(Horse->IsSpooked()) Rows.Add({TEXT("驚いている。手綱を引かず落ち着かせよ"),TEXT("Spooked: ease the reins and let her settle"),-1.f,FLinearColor(.9f,.6f,.2f)});
        if(!Campaign->IsMounted()&&Beat->Space.bMount)
        {
            const TArray<FSoraTackStep>& Tack=Beat->Space.Mount.Tack;
            if(Campaign->TackDone()<Tack.Num())
                Rows.Add({TEXT("E  馬具を付ける：")+TackName(Tack[Campaign->TackDone()].Part,false),
                    TEXT("E  Tack up: ")+TackName(Tack[Campaign->TackDone()].Part,true),-1.f,Frame.Gold});
            else Rows.Add({TEXT("E  右側から乗る"),TEXT("E  Mount from her right side"),-1.f,Frame.Gold});
        }
        else if(Campaign->IsMounted())
        {
            Rows.Add({TEXT("前進で歩ませ、Shift で促し、後退で手綱を引く"),TEXT("Forward to walk on, Shift to urge, back to rein in"),-1.f,Frame.Muted});
            if(Beat->Space.bMount&&Beat->Space.Mount.bDismount) Rows.Add({TEXT("E  降りる（右側へ）"),TEXT("E  Dismount (to her right)"),-1.f,Frame.Muted});
        }
    }
    return Rows;
}
// The beat tracker, top right under the bar.
float DrawBeatTracker(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode& G=Frame.Mode;
    const USoraCampaignDirector* Campaign=G.Campaign();
    const float W=Frame.W,S=Frame.S,X=W-455*S,Width=435*S,Top=87*S;
    if(!G.bCampaign||G.bDeterministicPractice||G.bChapterComplete||!Campaign->ActiveBeatData()||!Campaign->ActiveChapter()) return Top;
    const TArray<FTrackerRow> Rows=TrackerRows(Frame);
    const bool bEnglish=G.bEnglishSubtitles;
    float Height=10*S;
    for(const FTrackerRow& Row:Rows) Height+=24*S+(bEnglish?18*S:0.f)+(Row.Fraction>=0.f?9*S:0.f);
    HUD.Panel(X,Top,Width,Height,FLinearColor(.013f,.027f,.033f,.8f));
    float Y=Top+6*S;
    for(const FTrackerRow& Row:Rows)
    {
        HUD.Label(Row.Japanese,X+12*S,Y,.44*S,Row.Color);
        Y+=24*S;
        if(bEnglish) { HUD.Label(Row.English,X+12*S,Y-2*S,.34*S,Frame.Muted); Y+=18*S; }
        if(Row.Fraction>=0.f)
        {
            HUD.Panel(X+12*S,Y,Width-24*S,4*S,FLinearColor(.12f,.16f,.18f));
            HUD.Panel(X+12*S,Y,(Width-24*S)*FMath::Clamp(Row.Fraction,0.f,1.f),4*S,Row.Color);
            Y+=9*S;
        }
    }
    return Top+Height;
}
// Unlocks, finds and restored sites, newest at the bottom, under the tracker.
void DrawStoryNotices(const FSoraHUDFrame& Frame,float Top)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode& G=Frame.Mode;
    const float W=Frame.W,S=Frame.S,X=W-455*S,Width=435*S;
    if(!G.bCampaign||G.bDeterministicPractice) return;
    float Y=Top+8*S;
    for(const FSoraStoryNotice& Notice:G.Campaign()->StoryNotices())
    {
        const FLinearColor Accent=Notice.Kind==FSoraStoryNotice::EKind::Weapon?Frame.Gold
            :Notice.Kind==FSoraStoryNotice::EKind::Collectible?Frame.Ivory:Frame.Teal;
        const bool bDetail=!Notice.Detail.IsEmpty();
        const float Height=12*S+26*S+(G.bEnglishSubtitles?20*S:0.f)+(bDetail?40*S+(G.bEnglishSubtitles?36*S:0.f):0.f);
        const float Fade=FMath::Clamp(Notice.Remaining,0.f,1.f);
        HUD.Panel(X,Y,Width,Height,FLinearColor(.015f,.035f,.045f,.9f*Fade));
        HUD.Panel(X,Y,4*S,Height,Accent);
        float Line=Y+6*S;
        HUD.Label(Notice.Japanese,X+14*S,Line,.48*S,Accent); Line+=26*S;
        if(G.bEnglishSubtitles) { HUD.Label(Notice.English,X+14*S,Line-2*S,.36*S,Frame.Muted); Line+=20*S; }
        if(bDetail)
        {
            Line+=HUD.WrappedLabel(Notice.Detail,X+14*S,Line,.36*S,Frame.Ivory,Width-28*S,20*S,2)*20*S;
            if(G.bEnglishSubtitles) HUD.WrappedLabel(Notice.DetailEnglish,X+14*S,Line,.32*S,Frame.Muted,Width-28*S,18*S,2);
        }
        Y+=Height+6*S;
    }
}
// A line with its speaker: Japanese first, English beneath when enabled.
void DrawLine(const FSoraHUDFrame& Frame,const FSoraDialogueCue& Line,float Bottom)
{
    // The subtitle-size and speaker-name settings shape the panel, which
    // grows upwards from Bottom.
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,S=Frame.S;
    const FSoraDialogueLayout Layout=Frame.DialogueLayout(G->bEnglishSubtitles);
    const float Top=Bottom-Layout.Height;
    HUD.Panel(20*S,Top,W-40*S,Layout.Height,FLinearColor(.013,.027,.033,.88));
    if(const auto* Speaker=Frame.bSpeakerNames?FSoraCatalog::Get().DialogueSpeaker(Line.SpeakerId):nullptr)
    {
        HUD.Label(Speaker->Japanese,35*S,Top+Layout.SpeakerY,Frame.DialogueJapaneseSpeakerScale,Frame.Gold);
        if(G->bEnglishSubtitles) HUD.Label(Speaker->English,W-285*S,Top+Layout.SpeakerY,Frame.DialogueEnglishSpeakerScale,Frame.Muted);
    }
    HUD.WrappedLabel(Line.Japanese,35*S,Top+Layout.JapaneseY,Frame.DialogueJapaneseScale,Frame.Ivory,W-70*S,Frame.DialogueJapaneseLineHeight,2);
    if(G->bEnglishSubtitles) HUD.WrappedLabel(Line.English,35*S,Top+Layout.EnglishY,Frame.DialogueEnglishScale,Frame.Muted,W-70*S,Frame.DialogueEnglishLineHeight,2);
}
}

void SoraHUDPanels::DrawTitleCard(const FSoraHUDFrame& Frame,const FSoraChapter& Card)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const USoraCampaignDirector* Campaign=G->Campaign();
    const float W=Frame.W,H=Frame.H,S=Frame.S,JapaneseSubtitleScale=Frame.JapaneseSubtitleScale,EnglishSubtitleScale=Frame.EnglishSubtitleScale,JapaneseSubtitleLineHeight=Frame.JapaneseSubtitleLineHeight,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    const FSoraBeat* Beat=Campaign->ActiveBeatData();
    // Cinematics play on this card until Sequencer shots land: a letterboxed
    // in-engine frame with the cinematic's subtitles on its own clock. A
    // fresh chapter's opening cinematic shows the chapter's title card first.
    const bool bCinematic=Beat&&Beat->Is(SoraBeatRules::EType::Cinematic);
    const float Duration=bCinematic?Beat->Task.DurationMs/1000.f:ASoraGameMode::TitleCardSeconds;
    if(!bCinematic||(Campaign->IsChapterOpening()&&Campaign->CinematicElapsed()<ASoraGameMode::TitleCardSeconds))
    {
        UTexture2D* Logo=HUD.ResistanceLogo();
        HUD.Panel(0,75*S,W,H-75*S,FLinearColor(.013,.027,.033,.95f));
        const float CardX=120*S,TextW=W-2*CardX;
        float Y=140*S;
        const float InsigniaSize=110*S;
        if(Logo) HUD.DrawTexture(Logo,CardX,Y,InsigniaSize,InsigniaSize,0,0,1,1,FLinearColor::White);
        const float TitleX=Logo?CardX+InsigniaSize+30*S:CardX;
        HUD.Label(G->bEnglishSubtitles?FString::Printf(TEXT("第 %02d 章   CHAPTER %d"),Campaign->ChapterId+1,Campaign->ChapterId+1)
            :FString::Printf(TEXT("第 %02d 章"),Campaign->ChapterId+1),TitleX,Y,.55*S,Gold);
        HUD.Label(Card.Title,TitleX,Y+30*S,1.7*S,Ivory);
        if(G->bEnglishSubtitles) HUD.Label(Card.TitleEnglish,TitleX,Y+112*S,.72*S,Muted);
        Y+=175*S;
        Y+=HUD.WrappedLabel(Card.Narrative,CardX,Y,JapaneseSubtitleScale,Ivory,TextW,JapaneseSubtitleLineHeight,4)*JapaneseSubtitleLineHeight+10*S;
        if(G->bEnglishSubtitles)
            Y+=HUD.WrappedLabel(Card.NarrativeEnglish,CardX,Y,EnglishSubtitleScale,Muted,TextW,EnglishSubtitleLineHeight,4)*EnglishSubtitleLineHeight+10*S;
        Y+=20*S;
        HUD.Label(G->bEnglishSubtitles?TEXT("目的   OBJECTIVE"):TEXT("目的"),CardX,Y,.5*S,Gold);
        Y+=32*S;
        Y+=HUD.WrappedLabel(Card.Objective,CardX,Y,JapaneseSubtitleScale,Teal,TextW,JapaneseSubtitleLineHeight,2)*JapaneseSubtitleLineHeight+6*S;
        if(G->bEnglishSubtitles) HUD.WrappedLabel(Card.ObjectiveEnglish,CardX,Y,EnglishSubtitleScale,Muted,TextW,EnglishSubtitleLineHeight,2);
    }
    else
    {
        HUD.Panel(0,75*S,W,95*S,FLinearColor(0,0,0,.96f));
        HUD.Panel(0,H-150*S,W,150*S,FLinearColor(0,0,0,.96f));
        HUD.Label(Beat->Title,40*S,98*S,.72*S,Ivory);
        if(G->bEnglishSubtitles) HUD.Label(Beat->TitleEnglish,40*S,136*S,.45*S,Muted);
    }
    // Cinematic subtitles sit above the letterbox's lower bar.
    if(const FSoraDialogueCue* Line=Campaign->CurrentDialogueCue()) DrawLine(Frame,*Line,H-160*S);
    // The key that skips the card or cinematic, on the device in hand.
    if(!bCinematic||Beat->Task.Skippable)
    {
        const SoraText::FLine Skip=bCinematic
            ?SoraText::Format(NSLOCTEXT("SoraArena.HUD","TitleCard.Skip","{Enter}  とばす"),{{TEXT("Enter"),SoraUI::ActionKey(&HUD,TEXT("Enter"))}})
            :SoraText::Format(NSLOCTEXT("SoraArena.HUD","TitleCard.Begin","{Enter}  はじめる"),{{TEXT("Enter"),SoraUI::ActionKey(&HUD,TEXT("Enter"))}});
        HUD.Label(G->bEnglishSubtitles?Skip.Japanese+TEXT("   ")+Skip.English:Skip.Japanese,120*S,H-120*S,.55*S,Ivory);
    }
    const float Remaining=FMath::Clamp(G->TitleCardTime/FMath::Max(Duration,1.f),0.f,1.f);
    HUD.Panel(120*S,H-78*S,W-240*S,4*S,FLinearColor(.12,.19,.21));
    HUD.Panel(120*S,H-78*S,(W-240*S)*Remaining,4*S,Gold);
}
void SoraHUDPanels::DrawDialogue(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const USoraCampaignDirector* Campaign=G->Campaign();
    const float W=Frame.W,H=Frame.H,S=Frame.S,JapaneseSubtitleScale=Frame.JapaneseSubtitleScale,EnglishSubtitleScale=Frame.EnglishSubtitleScale,JapaneseSubtitleLineHeight=Frame.JapaneseSubtitleLineHeight,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    // The active beat's objective marker, and E when the hero can work it or
    // stands at an explore cache. Caches carry no marker (bible §12.2).
    const ASoraPlayerCharacter* Hero=G->Hero();
    FVector Anchor;
    if(Hero&&G->bCampaign&&!G->bDeterministicPractice&&Campaign->ObjectiveAnchor(Anchor))
    {
        const FVector Position=Anchor+FVector(0,0,330);
        const float Metres=FVector::Dist2D(Anchor,Hero->GetActorLocation())/100.f;
        if(FVector::DotProduct(Position-Hero->GetActorLocation(),Hero->GetActorForwardVector())>0)
        {
            const FVector Screen=HUD.Project(Position);
            if(Screen.X>0&&Screen.X<W&&Screen.Y>170*S&&Screen.Y<H-120*S)
            {
                const int32 Distance=FMath::RoundToInt32(Metres);
                HUD.Label(G->bEnglishSubtitles?FString::Printf(TEXT("目標 / %dm   Objective"),Distance):FString::Printf(TEXT("目標 / %dm"),Distance),
                    Screen.X-60*S,Screen.Y,.42*S,Gold);
            }
        }
        // Interact binds a yielded boss; elsewhere it works the task.
        const bool bCapture=Campaign->AwaitingCapture();
        if(Campaign->AnchorTakesInteract()&&Metres<2.6f)
            Frame.LabelWithEnglish(SoraText::Format(bCapture?NSLOCTEXT("SoraArena.HUD","Prompt.Capture","{Interact}  捕らえる")
                :NSLOCTEXT("SoraArena.HUD","Prompt.Work","{Interact}  作業する"),{{TEXT("Interact"),SoraUI::ActionKey(&HUD,TEXT("Interact"))}}),
                W*.5f-75*S,H*.5f+60*S,.65*S,Gold);
    }
    if(Hero&&G->bCampaign&&!G->bDeterministicPractice)
    {
        const SoraText::FLine Interact=SoraUI::ActionKey(&HUD,TEXT("Interact"));
        for(const int32 Cache:Campaign->AvailableCaches())
            if(FVector::Dist2D(Campaign->CacheLocation(Cache),Hero->GetActorLocation())<260.f)
                Frame.LabelWithEnglish(SoraText::Format(NSLOCTEXT("SoraArena.HUD","Prompt.Search","{Interact}  調べる"),{{TEXT("Interact"),Interact}}),
                    W*.5f-75*S,H*.5f+60*S,.65*S,Gold);
        // A loose collectible within reach.
        for(const int32 Pickup:Campaign->LoosePickups())
            if(FVector::Dist2D(Campaign->PickupLocation(Pickup),Hero->GetActorLocation())<260.f)
                Frame.LabelWithEnglish(SoraText::Format(NSLOCTEXT("SoraArena.HUD","Prompt.PickUp","{Interact}  拾う"),{{TEXT("Interact"),Interact}}),
                    W*.5f-75*S,H*.5f+60*S,.65*S,Gold);
    }
    // The beat tracker, and story notices beneath it.
    DrawStoryNotices(Frame,DrawBeatTracker(Frame));
    // Story lines and notices share the lower third; play and objective
    // timers continue beneath a line.
    const auto* Cue=Campaign->CurrentDialogueCue();
    if(Cue) DrawLine(Frame,*Cue,H-130*S);
    float StripBottom=Cue?H-130*S-Frame.DialogueLayout(G->bEnglishSubtitles).Height-6*S:H-130*S;
    if(G->NoticeTime>0)
    {
        // A notice raised during a line takes one compact strip above it
        // rather than flickering into the short gaps between lines.
        const int32 Lines=Cue?1:2;
        const float StripH=10*S+JapaneseSubtitleLineHeight*Lines+(G->bEnglishSubtitles?EnglishSubtitleLineHeight*Lines:0.f);
        const float StripY=StripBottom-StripH;
        HUD.Panel(20*S,StripY,W-40*S,StripH,FLinearColor(.015,.035,.045,.94));
        HUD.WrappedLabel(G->Notice,35*S,StripY+5*S,JapaneseSubtitleScale,Ivory,W-70*S,JapaneseSubtitleLineHeight,Lines);
        if(G->bEnglishSubtitles)
            HUD.WrappedLabel(G->NoticeEnglish,35*S,StripY+5*S+JapaneseSubtitleLineHeight*Lines,EnglishSubtitleScale,Muted,W-70*S,EnglishSubtitleLineHeight,Lines);
        StripBottom=StripY-6*S;
    }
    if(const FSoraPrompt* Prompt=Campaign->CurrentPrompt())
    {
        // HUD prompts are UI strings, set apart from voiced lines in teal.
        const float StripH=10*S+JapaneseSubtitleLineHeight+(G->bEnglishSubtitles?EnglishSubtitleLineHeight:0.f);
        const float StripY=StripBottom-StripH;
        HUD.Panel(20*S,StripY,W-40*S,StripH,FLinearColor(.015,.035,.045,.90));
        // Its keys are the player's own, following the device and rebinding.
        const SoraText::FLine Line=KeyPrompt(&HUD,Prompt->Japanese,Prompt->English);
        HUD.WrappedLabel(Line.Japanese,35*S,StripY+5*S,JapaneseSubtitleScale,Teal,W-70*S,JapaneseSubtitleLineHeight,1);
        if(G->bEnglishSubtitles)
            HUD.WrappedLabel(Line.English,35*S,StripY+5*S+JapaneseSubtitleLineHeight,EnglishSubtitleScale,Muted,W-70*S,EnglishSubtitleLineHeight,1);
    }
}
SoraText::FLine SoraHUDPanels::KeyPrompt(const UObject* WorldContext,const FString& Japanese,const FString& English)
{
    const auto Resolve=[WorldContext](const FString& Text,bool bEnglish)
    {
        FString Out;
        for(int32 At=0;At<Text.Len();)
        {
            int32 Close=INDEX_NONE;
            if(Text[At]==TEXT('{')) Close=Text.Find(TEXT("}"),ESearchCase::CaseSensitive,ESearchDir::FromStart,At);
            if(Close==INDEX_NONE) { Out.AppendChar(Text[At++]); continue; }
            const SoraText::FLine Key=SoraUI::ActionKey(WorldContext,FName(*Text.Mid(At+1,Close-At-1)));
            Out+=bEnglish?TEXT("[")+Key.English+TEXT("]"):TEXT("［")+Key.Japanese+TEXT("］");
            At=Close+1;
        }
        return Out;
    };
    return {Resolve(Japanese,false),Resolve(English,true)};
}
SoraText::FLine SoraHUDPanels::ResultHeadline(const ASoraGameMode& G)
{
    if(G.bDeterministicPractice) return SoraText::Line(NSLOCTEXT("SoraArena.HUD","Result.PracticeOver","稽古終了"));
    if(G.bDefeated) return SoraText::Line(NSLOCTEXT("SoraArena.HUD","Result.RiseAgain","ふたたび立ち上がれ"));
    if(!G.bCampaign) return SoraText::Line(NSLOCTEXT("SoraArena.HUD","Result.ArenaCleared","稽古場を制した"));
    if(G.Campaign()->bCampaignComplete) return SoraText::Line(NSLOCTEXT("SoraArena.HUD","Result.Liberated","猫柳生、解放"));
    // Chapter one ends the dojo's training; every later chapter frees a district.
    if(G.Campaign()->ChapterId==0) return SoraText::Line(NSLOCTEXT("SoraArena.HUD","Result.DojoComplete","道場の修行を終えた"));
    return SoraText::Line(NSLOCTEXT("SoraArena.HUD","Result.DistrictLiberated","街区を解放した"));
}
void SoraHUDPanels::DrawResult(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,H=Frame.H,S=Frame.S,EnglishSubtitleScale=Frame.EnglishSubtitleScale,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    if(G->bDefeated||G->bChapterComplete)
    {
        HUD.Panel(0,H*.3,W,H*.35,FLinearColor(.012,.026,.034,.94));
        const SoraText::FLine Headline=ResultHeadline(*G);
        HUD.Label(Headline.Japanese,W*.2,H*.36,1.8*S,G->bDefeated?Gold:Teal);
        if(G->bEnglishSubtitles) HUD.Label(Headline.English,W*.2,H*.418,.8*S,Muted);
        HUD.WrappedLabel(G->Notice,W*.2,H*.48,.65*S,Ivory,W*.65,29*S,2);
        if(G->bEnglishSubtitles) HUD.WrappedLabel(G->NoticeEnglish,W*.2,H*.535,EnglishSubtitleScale,Muted,W*.65,EnglishSubtitleLineHeight,2);
        const SoraText::FLine Next=SoraText::Format(NSLOCTEXT("SoraArena.HUD","Result.Next","{Enter}  続ける    |    {Menu}  メニュー"),
            {{TEXT("Enter"),SoraUI::ActionKey(&HUD,TEXT("Enter"))},{TEXT("Menu"),SoraUI::ActionKey(&HUD,TEXT("Menu"))}});
        HUD.Label(G->bEnglishSubtitles?Next.Japanese+TEXT("    ")+Next.English:Next.Japanese,W*.2,H*.56,.65*S,Muted);
    }
}
