#include "HUD/SoraHUDPanels.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "Engine/Texture2D.h"

namespace
{
// A line with its speaker: Japanese first, English beneath when enabled.
void DrawLine(const FSoraHUDFrame& Frame,const FSoraDialogueCue& Line,float Top)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,S=Frame.S;
    HUD.Panel(20*S,Top,W-40*S,170*S,FLinearColor(.013,.027,.033,.88));
    if(const auto* Speaker=FSoraCatalog::Get().DialogueSpeaker(Line.SpeakerId))
    {
        HUD.Label(Speaker->Japanese,35*S,Top+10*S,Frame.JapaneseSpeakerScale,Frame.Gold);
        if(G->bEnglishSubtitles) HUD.Label(Speaker->English,W-285*S,Top+10*S,Frame.EnglishSpeakerScale,Frame.Muted);
    }
    HUD.WrappedLabel(Line.Japanese,35*S,Top+40*S,Frame.JapaneseSubtitleScale,Frame.Ivory,W-70*S,Frame.JapaneseSubtitleLineHeight,2);
    if(G->bEnglishSubtitles) HUD.WrappedLabel(Line.English,35*S,Top+105*S,Frame.EnglishSubtitleScale,Frame.Muted,W-70*S,Frame.EnglishSubtitleLineHeight,2);
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
    const bool bCinematic=Beat&&Beat->Goal==ESoraBeatGoal::Cinematic;
    const float Duration=bCinematic?Beat->GoalSeconds:ASoraGameMode::TitleCardSeconds;
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
    if(const FSoraDialogueCue* Line=Campaign->CurrentDialogueCue()) DrawLine(Frame,*Line,H-330*S);
    if(!bCinematic||Beat->bSkippable)
        HUD.Label(G->bEnglishSubtitles?TEXT("ENTER  とばす   Press Enter to skip"):TEXT("ENTER  とばす"),120*S,H-120*S,.55*S,Ivory);
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
                HUD.Label(FString::Printf(TEXT("目標 / %dm"),FMath::RoundToInt32(Metres)),Screen.X-60*S,Screen.Y,.42*S,Gold);
        }
        const FSoraBeat* Beat=Campaign->ActiveBeatData();
        const bool bWork=Beat&&(Beat->Goal==ESoraBeatGoal::Interact||
            (Beat->Goal==ESoraBeatGoal::Lines&&Beat->bLinesOnInteract&&!Campaign->LinesStarted()));
        if(bWork&&Metres<2.6f) HUD.Label(TEXT("E  作業する"),W*.5f-75*S,H*.5f+60*S,.65*S,Gold);
    }
    if(Hero&&G->bCampaign&&!G->bDeterministicPractice)
        for(const int32 Cache:Campaign->AvailableCaches())
            if(FVector::Dist2D(Campaign->CacheLocation(Cache),Hero->GetActorLocation())<260.f)
                HUD.Label(TEXT("E  調べる"),W*.5f-75*S,H*.5f+60*S,.65*S,Gold);
    // Story lines and notices share the lower third; play and objective
    // timers continue beneath a line.
    const auto* Cue=Campaign->CurrentDialogueCue();
    if(Cue) DrawLine(Frame,*Cue,H-300*S);
    float StripBottom=Cue?H-306*S:H-130*S;
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
        HUD.WrappedLabel(Prompt->Japanese,35*S,StripY+5*S,JapaneseSubtitleScale,Teal,W-70*S,JapaneseSubtitleLineHeight,1);
        if(G->bEnglishSubtitles)
            HUD.WrappedLabel(Prompt->English,35*S,StripY+5*S+JapaneseSubtitleLineHeight,EnglishSubtitleScale,Muted,W-70*S,EnglishSubtitleLineHeight,1);
    }
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
        HUD.Label(G->bDeterministicPractice?TEXT("稽古終了"):G->bDefeated?TEXT("ふたたび立ち上がれ"):G->Campaign()->bCampaignComplete?TEXT("猫柳生、解放"):TEXT("街区を解放した"),W*.2,H*.36,1.8*S,G->bDefeated?Gold:Teal);
        HUD.WrappedLabel(G->Notice,W*.2,H*.48,.65*S,Ivory,W*.65,29*S,2);
        if(G->bEnglishSubtitles) HUD.WrappedLabel(G->NoticeEnglish,W*.2,H*.535,EnglishSubtitleScale,Muted,W*.65,EnglishSubtitleLineHeight,2);
        HUD.Label(TEXT("ENTER  続ける    |    ESC  メニュー"),W*.2,H*.56,.65*S,Muted);
    }
}
