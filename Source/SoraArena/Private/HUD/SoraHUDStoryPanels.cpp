#include "HUD/SoraHUDPanels.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "Engine/Texture2D.h"

void SoraHUDPanels::DrawTitleCard(const FSoraHUDFrame& Frame,const FSoraChapter& Card)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,H=Frame.H,S=Frame.S,JapaneseSubtitleScale=Frame.JapaneseSubtitleScale,EnglishSubtitleScale=Frame.EnglishSubtitleScale,JapaneseSubtitleLineHeight=Frame.JapaneseSubtitleLineHeight,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal,Muted=Frame.Muted;
    UTexture2D* Logo=HUD.ResistanceLogo();
    // The chapter opens on this card; dialogue and the round timer start
    // when it closes. Enter skips it.
    HUD.Panel(0,75*S,W,H-75*S,FLinearColor(.013,.027,.033,.95f));
    const float CardX=120*S,TextW=W-2*CardX;
    float Y=140*S;
    const float InsigniaSize=110*S;
    if(Logo) HUD.DrawTexture(Logo,CardX,Y,InsigniaSize,InsigniaSize,0,0,1,1,FLinearColor::White);
    const float TitleX=Logo?CardX+InsigniaSize+30*S:CardX;
    HUD.Label(G->bEnglishSubtitles?FString::Printf(TEXT("第 %02d 章   CHAPTER %d"),G->Campaign()->ChapterId+1,G->Campaign()->ChapterId+1)
        :FString::Printf(TEXT("第 %02d 章"),G->Campaign()->ChapterId+1),TitleX,Y,.55*S,Gold);
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
    // The key that skips the card, on the device in hand.
    const SoraText::FLine Begin=SoraText::Format(NSLOCTEXT("SoraArena.HUD","TitleCard.Begin","{Enter}  はじめる"),
        {{TEXT("Enter"),SoraUI::ActionKey(&HUD,TEXT("Enter"))}});
    HUD.Label(G->bEnglishSubtitles?Begin.Japanese+TEXT("   ")+Begin.English:Begin.Japanese,CardX,H-120*S,.55*S,Ivory);
    const float Remaining=FMath::Clamp(G->TitleCardTime/ASoraGameMode::TitleCardSeconds,0.f,1.f);
    HUD.Panel(CardX,H-78*S,TextW,4*S,FLinearColor(.12,.19,.21));
    HUD.Panel(CardX,H-78*S,TextW*Remaining,4*S,Gold);
}
void SoraHUDPanels::DrawDialogue(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const ASoraGameMode* G=&Frame.Mode;
    const float W=Frame.W,H=Frame.H,S=Frame.S,JapaneseSubtitleScale=Frame.JapaneseSubtitleScale,EnglishSubtitleScale=Frame.EnglishSubtitleScale,JapaneseSubtitleLineHeight=Frame.JapaneseSubtitleLineHeight,EnglishSubtitleLineHeight=Frame.EnglishSubtitleLineHeight;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Muted=Frame.Muted;
    const auto* Cue=G->Campaign()->CurrentDialogueCue();
    // The subtitle-size and speaker-name settings shape the cue's panel.
    const FSoraDialogueLayout Line=Frame.DialogueLayout(G->bEnglishSubtitles);
    if(Cue)
    {
        // Story dialogue and the chapter summary share the lower-third space.
        // Drawing both at once covered nearly half a 720p gameplay frame.
        // Gameplay input and objective timers continue beneath the cue.
        HUD.Panel(20*S,Line.Top,W-40*S,Line.Height,FLinearColor(.013,.027,.033,.88));
        if(const auto* Speaker=Frame.bSpeakerNames?FSoraCatalog::Get().DialogueSpeaker(Cue->SpeakerId):nullptr)
        {
            HUD.Label(Speaker->Japanese,35*S,Line.Top+Line.SpeakerY,Frame.DialogueJapaneseSpeakerScale,Gold);
            if(G->bEnglishSubtitles) HUD.Label(Speaker->English,W-285*S,Line.Top+Line.SpeakerY,Frame.DialogueEnglishSpeakerScale,Muted);
        }
        HUD.WrappedLabel(Cue->Japanese,35*S,Line.Top+Line.JapaneseY,Frame.DialogueJapaneseScale,Ivory,W-70*S,Frame.DialogueJapaneseLineHeight,2);
        if(G->bEnglishSubtitles) HUD.WrappedLabel(Cue->English,35*S,Line.Top+Line.EnglishY,Frame.DialogueEnglishScale,Muted,W-70*S,Frame.DialogueEnglishLineHeight,2);
    }
    if(Cue&&G->NoticeTime>0)
    {
        // A notice raised during dialogue takes one compact strip above the cue
        // rather than flickering into the short gaps between lines.
        const float StripH=10*S+JapaneseSubtitleLineHeight+(G->bEnglishSubtitles?EnglishSubtitleLineHeight:0.f);
        const float StripY=Line.Top-StripH-6*S;
        HUD.Panel(20*S,StripY,W-40*S,StripH,FLinearColor(.015,.035,.045,.94));
        HUD.WrappedLabel(G->Notice,35*S,StripY+5*S,JapaneseSubtitleScale,Ivory,W-70*S,JapaneseSubtitleLineHeight,1);
        if(G->bEnglishSubtitles) HUD.WrappedLabel(G->NoticeEnglish,35*S,StripY+5*S+JapaneseSubtitleLineHeight,EnglishSubtitleScale,Muted,W-70*S,EnglishSubtitleLineHeight,1);
    }
    else if(G->NoticeTime>0)
    {
        HUD.Panel(20*S,H-255*S,W-40*S,125*S,FLinearColor(.015,.035,.045,.94));
        HUD.WrappedLabel(G->Notice,35*S,H-245*S,JapaneseSubtitleScale,Ivory,W-70*S,JapaneseSubtitleLineHeight,2);
        if(G->bEnglishSubtitles) HUD.WrappedLabel(G->NoticeEnglish,35*S,H-185*S,EnglishSubtitleScale,Muted,W-70*S,EnglishSubtitleLineHeight,2);
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
        const SoraText::FLine Next=SoraText::Format(NSLOCTEXT("SoraArena.HUD","Result.Next","{Enter}  続ける    |    {Menu}  メニュー"),
            {{TEXT("Enter"),SoraUI::ActionKey(&HUD,TEXT("Enter"))},{TEXT("Menu"),SoraUI::ActionKey(&HUD,TEXT("Menu"))}});
        HUD.Label(G->bEnglishSubtitles?Next.Japanese+TEXT("    ")+Next.English:Next.Japanese,W*.2,H*.56,.65*S,Muted);
    }
}
