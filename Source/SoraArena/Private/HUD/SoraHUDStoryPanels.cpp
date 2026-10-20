#include "HUD/SoraHUDPanels.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraInputStates.h"
#include "SoraRhythmHUDLayout.h"
#include "SoraCaptionLayoutRules.h"
#include "SoraCaptions.h"
#include "SoraSettings.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Engine/Texture2D.h"
#include "Engine/Canvas.h"

namespace
{
// One row of the beat tracker: Japanese and optional English,
// and a bar when Fraction is not negative.
struct FTrackerRow
{
    FString Japanese;
    FString English;
    float Fraction = -1.f;
    FLinearColor Color = FLinearColor::White;
    int32 Target = INDEX_NONE;
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
        Rows.Add({Task.AlternateTreads?FString::Printf(TEXT("踏む（左右一組） %d / %d"),State.Done,Task.Count):
                FString::Printf(TEXT("回す  %d / %d"),State.Done,Task.Count),
            Task.AlternateTreads?FString::Printf(TEXT("Tread pairs: %d of %d"),State.Done,Task.Count):
                FString::Printf(TEXT("Turn the crank: %d of %d"),State.Done,Task.Count),Fraction,Frame.Teal});
        if(Task.AlternateTreads)
        {
            const int32 Band=SoraBeatRules::CrankFlameNotches(State,Task);
            Rows.Add({Band==1?TEXT("火勢 I — 遅い／休止"):Band==2?TEXT("火勢 II — 適正"):TEXT("火勢 III — 速すぎ・体力２倍"),
                Band==1?TEXT("Flame I: slow / idle"):Band==2?TEXT("Flame II: in rhythm"):TEXT("Flame III: too fast, double stamina"),-1.f,
                Band==1?FLinearColor(.9f,.35f,.2f):Band==2?Frame.Gold:Frame.Ivory});
            const bool bPad=G.FrontEnd()&&G.FrontEnd()->Device()==SoraUI::EDevice::Gamepad;
            const auto Hold=SoraUI::ActionKey(&G,TEXT("Interact"));
            const auto Left=bPad?SoraText::FLine{TEXT("左スティック左"),TEXT("left stick left")}:SoraUI::KeyLabel(G.Hero()->ControlKey(SoraInput::FindRemappable(TEXT("MoveRight"),-1),false));
            const auto Right=bPad?SoraText::FLine{TEXT("左スティック右"),TEXT("left stick right")}:SoraUI::KeyLabel(G.Hero()->ControlKey(SoraInput::FindRemappable(TEXT("MoveRight"),1),false));
            if(G.Settings()&&G.Settings()->RhythmAssist())
                Rows.Add({FString::Printf(TEXT("%s 長押し：調子合わせ補助・生産７割"),*Hold.Japanese),
                    FString::Printf(TEXT("Hold %s: rhythm assist, 70%% production speed"),*Hold.English),-1.f,Frame.Muted});
            else if(bPad) Rows.Add({FString::Printf(TEXT("%s 長押し＋左スティック 左→右（毎回中央へ）"),*Hold.Japanese),
                FString::Printf(TEXT("Hold %s + left stick: left then right; center after each tread"),*Hold.English),-1.f,Frame.Muted});
            else Rows.Add({FString::Printf(TEXT("%s 長押し＋左 %s → 右 %s（毎回離す）"),*Hold.Japanese,*Left.Japanese,*Right.Japanese),
                FString::Printf(TEXT("Hold %s + left %s then right %s; release each tread"),*Hold.English,*Left.English,*Right.English),-1.f,Frame.Muted});
            if(Campaign->IsWorkingCrank()&&!(G.Settings()&&G.Settings()->RhythmAssist())) Rows.Add({Campaign->BellowsRightNext()?TEXT("次は右足"):TEXT("次は左足"),
                Campaign->BellowsRightNext()?TEXT("Next: right tread"):TEXT("Next: left tread"),-1.f,Frame.Teal});
        }
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
        // The current operation needs its actual count. Listing every future
        // operation repeats the recipe and pushes instructions off small screens.
        if(Beat->StepKinds.IsValidIndex(State.Step)&&State.Step<Task.StepCount)
            if(const FSoraLabel* Label=FSoraCatalog::Get().StepLabels.Find(Beat->StepKinds[State.Step]))
                Rows.Add({FString::Printf(TEXT("▶ %s  %d / %d"),*Label->Japanese,State.StepDone,Task.Steps[State.Step].Count),
                    FString::Printf(TEXT("Now: %s, %d of %d"),*Label->English,State.StepDone,Task.Steps[State.Step].Count),-1.f,Frame.Gold});
        if(SoraRhythmRules::Supported(State,Task))
        {
            const auto& Cue=Campaign->RhythmState();
            const auto& Step=Task.Steps[State.Step];
            const auto Key=SoraUI::ActionKey(&G,TEXT("Interact"));
            const bool Assist=G.Settings()&&G.Settings()->RhythmAssist();
            const bool Active=Cue.Step==State.Step;
            Rows.Add({Assist?FString::Printf(TEXT("%s 長押し：調子合わせ補助・生産７割"),*Key.Japanese):Active?FString::Printf(TEXT("%s：合図の輪に合わせて一打"),*Key.Japanese):FString::Printf(TEXT("%s：最初の合図を始める"),*Key.Japanese),
                Assist?FString::Printf(TEXT("Hold %s: rhythm assist, 70%% production speed"),*Key.English):Active?FString::Printf(TEXT("%s: one response as the cue ring closes"),*Key.English):FString::Printf(TEXT("%s: ask for the first cue"),*Key.English),-1.f,Frame.Muted});
            if(Cue.Step==State.Step&&Step.PhraseStrikes>1)
                Rows.Add({FString::Printf(TEXT("一節 %d / %d 打・的中 %d（%d 以上）"),Cue.Attempts,Step.PhraseStrikes,Cue.Hits,Step.PhrasePass),
                    FString::Printf(TEXT("Phrase: %d of %d responses; %d hits, need %d"),Cue.Attempts,Step.PhraseStrikes,Cue.Hits,Step.PhrasePass),-1.f,Frame.Teal});
        }
        Rows.Add({FString::Printf(TEXT("工程一覧を要約：完了 %d・後続 %d"),FMath::Min(State.Step,Task.StepCount),FMath::Max(0,Task.StepCount-State.Step-1)),
            FString::Printf(TEXT("Recipe summary: %d completed, %d later steps"),FMath::Min(State.Step,Task.StepCount),FMath::Max(0,Task.StepCount-State.Step-1)),-1.f,Frame.Muted});
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
            Rows.Add({Label->Japanese,Label->English,Health,FMath::Lerp(FLinearColor(.78f,.12f,.08f),Frame.Teal,Health),Target});
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
        if(G->bEnglishSubtitles)
            HUD.Label(Speaker->English,W-35*S-HUD.LabelWidth(Speaker->English,Frame.DialogueEnglishSpeakerScale),
                Top+Layout.SpeakerY,Frame.DialogueEnglishSpeakerScale,Frame.Muted);
    }
    HUD.WrappedLabel(Line.Japanese,35*S,Top+Layout.JapaneseY,Frame.DialogueJapaneseScale,Frame.Ivory,W-70*S,Frame.DialogueJapaneseLineHeight,2);
    if(G->bEnglishSubtitles) HUD.WrappedLabel(Line.English,35*S,Top+Layout.EnglishY,Frame.DialogueEnglishScale,Frame.Muted,W-70*S,Frame.DialogueEnglishLineHeight,2);
}
struct FStoryStrip
{
    FBox2D Bounds=FBox2D(ForceInit);
    TArray<FString> Japanese,English;
    float JapaneseLeading=0,EnglishLeading=0;
};
struct FLowerStoryLayout
{
    FBox2D Dialogue=FBox2D(ForceInit);
    FStoryStrip Notice,Prompt;
    float Top=0,Bottom=0;
};
TArray<FString> StoryStripLines(ASoraHUD& HUD,const FString& Text,float Scale,float Width,float& Leading)
{
    TArray<FString> Lines;
    FString Line;
    for(int32 I=0;I<Text.Len();++I)
    {
        int32 X=0,Y=0;
        UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),Scale,Scale,X,Y,Line+Text.Mid(I,1));
        if(Text[I]=='\n') { Lines.Add(Line); Line.Empty(); continue; }
        if(!Line.IsEmpty()&&X>Width)
        {
            int32 Space=INDEX_NONE;
            if(Line.FindLastChar(' ',Space)&&Space>0)
            { Lines.Add(Line.Left(Space+1)); Line=Line.Mid(Space+1); }
            else { Lines.Add(Line); Line.Empty(); }
        }
        Line+=Text.Mid(I,1);
    }
    if(!Line.IsEmpty()) Lines.Add(Line);
    for(const FString& Wrapped:Lines)
    {
        int32 X=0,Y=0;
        UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),Scale,Scale,X,Y,Wrapped);
        Leading=FMath::Max(Leading,Y+4.f);
    }
    return Lines;
}
FLowerStoryLayout BuildLowerStoryLayout(const FSoraHUDFrame& F)
{
    FLowerStoryLayout L;
    float Bottom=F.H-130*F.S;
    if(const ASoraPlayerCharacter* Hero=F.Mode.Hero())
        for(const FBox2D& Box:SoraHUDPanels::WeaponPanelBounds(F,*Hero))
            Bottom=FMath::Min(Bottom,static_cast<float>(Box.Min.Y)-6*F.S);
    L.Top=Bottom; L.Bottom=Bottom;
    if(F.Mode.Campaign()->CurrentDialogueCue())
    {
        L.Dialogue=FBox2D(FVector2D(20*F.S,Bottom-F.DialogueLayout(F.Mode.bEnglishSubtitles).Height),FVector2D(F.W-20*F.S,Bottom));
        L.Top=L.Dialogue.Min.Y; Bottom=L.Top-6*F.S;
    }
    const auto AddStrip=[&](FStoryStrip& Strip,const SoraText::FLine& Text)
    {
        Strip.JapaneseLeading=F.JapaneseSubtitleLineHeight; Strip.EnglishLeading=F.EnglishSubtitleLineHeight;
        Strip.Japanese=StoryStripLines(F.HUD,Text.Japanese,F.JapaneseSubtitleScale,F.W-70*F.S,Strip.JapaneseLeading);
        if(F.Mode.bEnglishSubtitles)
            Strip.English=StoryStripLines(F.HUD,Text.English,F.EnglishSubtitleScale,F.W-70*F.S,Strip.EnglishLeading);
        const float Height=10*F.S+Strip.Japanese.Num()*Strip.JapaneseLeading+Strip.English.Num()*Strip.EnglishLeading;
        Strip.Bounds=FBox2D(FVector2D(20*F.S,Bottom-Height),FVector2D(F.W-20*F.S,Bottom));
        L.Top=Bottom-Height; Bottom=L.Top-6*F.S;
    };
    if(F.Mode.NoticeTime>0) AddStrip(L.Notice,{F.Mode.Notice,F.Mode.NoticeEnglish});
    if(const FSoraPrompt* Prompt=F.Mode.Campaign()->CurrentPrompt())
        AddStrip(L.Prompt,SoraHUDPanels::KeyPrompt(&F.HUD,Prompt->Japanese,Prompt->English));
    return L;
}
// The upper story stack uses the same measured glyphs for drawing and capture
// qualification. Its bottom is the real lower-story/weapon boundary, not an
// assumed number of rows. No critical task, warning or target row is optional.
struct FUpperStoryText
{
    FString Text;
    FVector2D At;
    float Scale=0;
    FLinearColor Color;
    bool bInkBounds=false;
};
struct FUpperStoryRow
{
    FBox2D Bounds=FBox2D(ForceInit);
    TArray<FUpperStoryText> Text;
    float Fraction=-1;
    FLinearColor Color;
    int32 Target=INDEX_NONE;
    bool bCompact=false;
};
struct FUpperStoryPanel
{
    FBox2D Bounds=FBox2D(ForceInit);
    TArray<FUpperStoryRow> Rows;
    FLinearColor Accent;
    bool bNotice=false;
    float Fade=1;
};
FBox2D RhythmPanelBounds(const FSoraHUDFrame& F);
struct FUpperStoryLayout
{
    FSoraCaptionLayout Captions;
    TArray<FUpperStoryPanel> Panels;
    float Limit=0;
    int32 Targets=0,NoticeTitles=0,NoticeDetails=0;
    TArray<int32> NoticeIndices;
    bool bCondensedNotices=false;
};
FUpperStoryRow MeasureUpperStoryRow(const FSoraHUDFrame& F,const FTrackerRow& Source,float X,float Y,float Width,bool ForceCompact=false)
{
    FUpperStoryRow Row;
    Row.Fraction=Source.Fraction; Row.Color=Source.Color; Row.Target=Source.Target;
    const auto* Captions=F.bSoundCaptions?USoraCaptions::Get(&F.Mode):nullptr;
    Row.bCompact=ForceCompact||(Captions&&!Captions->Live().IsEmpty());
    const float JapaneseScale=FMath::Max(.44f*F.S,.60f),EnglishScale=FMath::Max(.34f*F.S,.55f),Gap=10*F.S;
    float JapaneseLeading=22,EnglishLeading=20;
    const TArray<FString> Japanese=StoryStripLines(F.HUD,Source.Japanese,JapaneseScale,Width,JapaneseLeading);
    TArray<FString> English;
    if(F.Mode.bEnglishSubtitles) English=StoryStripLines(F.HUD,Source.English,EnglishScale,Width,EnglishLeading);
    if(Row.bCompact)
    {
        // Runtime fonts reserve ascent/descent for every glyph in the font.
        // With live captions use the visible glyph bounds, keeping the same
        // readable type and enough leading for every actual wrapped line.
        JapaneseLeading=22; EnglishLeading=20;
        for(const auto& Line:Japanese) JapaneseLeading=FMath::Max(JapaneseLeading,
            static_cast<float>(SoraHUDPanels::CaptionGlyphBounds(F,Line,JapaneseScale).GetSize().Y)+3.f);
        for(const auto& Line:English) EnglishLeading=FMath::Max(EnglishLeading,
            static_cast<float>(SoraHUDPanels::CaptionGlyphBounds(F,Line,EnglishScale).GetSize().Y)+3.f);
    }
    const auto AddText=[&](const FString& Text,FVector2D At,float Scale,FLinearColor Color)
    {
        if(Row.bCompact) At-=SoraHUDPanels::CaptionGlyphBounds(F,Text,Scale).Min;
        Row.Text.Add({Text,At,Scale,Color,Row.bCompact});
    };
    const bool Inline=Japanese.Num()==1&&English.Num()==1&&
        F.HUD.LabelWidth(Source.Japanese,JapaneseScale)+Gap+F.HUD.LabelWidth(Source.English,EnglishScale)<=Width;
    float Next=Y;
    for(const FString& Line:Japanese)
    { AddText(Line,{X,Next},JapaneseScale,Source.Color); Next+=JapaneseLeading; }
    if(Inline)
    {
        AddText(Source.English,{X+F.HUD.LabelWidth(Source.Japanese,JapaneseScale)+Gap,Y},EnglishScale,F.Muted);
        Next=Y+FMath::Max(JapaneseLeading,EnglishLeading);
    }
    else for(const FString& Line:English)
    { AddText(Line,{X,Next},EnglishScale,F.Muted); Next+=EnglishLeading; }
    // Compact target bars occupy the trailing line gap with one clear pixel
    // above them. Other progress rows retain their separate bar space.
    if(Source.Fraction>=0&&!(Row.bCompact&&Row.Target!=INDEX_NONE)) Next+=Row.bCompact?4.f:9*F.S;
    Row.Bounds=FBox2D(FVector2D(X,Y),FVector2D(X+Width,Next));
    return Row;
}
void PlaceCaption(FSoraCaptionPanel Panel,FVector2D At,FSoraCaptionLayout& Out)
{
    Panel.Bounds.Min+=At; Panel.Bounds.Max+=At;
    for(auto& Text:Panel.Text) Text.At+=At;
    Out.Panels.Add(MoveTemp(Panel));
}
void ReserveCaptions(const FSoraHUDFrame& F,FUpperStoryLayout& L,float X,float Width,float NoticeReserve,float& NextY)
{
    const auto Captions=SoraHUDPanels::MeasureCaptions(F,Width);
    if(Captions.IsEmpty()) return;
    const float Gap=6*F.S,Top=87*F.S;
    float Height=0;
    for(const auto& Panel:Captions) Height+=Panel.Bounds.GetSize().Y+Gap;
    auto Obstacles=SoraHUDPanels::UpperGameplayPanelBounds(F);
    const auto Rhythm=RhythmPanelBounds(F);
    if(Rhythm.bIsValid) Obstacles.Add(Rhythm);
    bool Clear=true; float ProbeY=Top;
    for(const auto& Panel:Captions)
    {
        const FBox2D Box({X,ProbeY},{X+Width,ProbeY+Panel.Bounds.GetSize().Y});
        for(const auto& Other:Obstacles) if(Box.Intersect(Other)) Clear=false;
        ProbeY=Box.Max.Y+Gap;
    }
    for(const auto& Panel:L.Panels)
    {
        const FBox2D Shifted(Panel.Bounds.Min+FVector2D(0,Height),Panel.Bounds.Max+FVector2D(0,Height));
        for(const auto& Other:Obstacles) if(Shifted.Intersect(Other)) Clear=false;
    }
    // Ordinary load: captions first in the right column, with the entire
    // measured tracker translated below them. Nothing changes its data.
    if(Clear&&NextY+Height+NoticeReserve<=L.Limit)
    {
        float Y=Top;
        for(const auto& Panel:Captions) { PlaceCaption(Panel,{X,Y},L.Captions); Y+=Panel.Bounds.GetSize().Y+Gap; }
        for(auto& Panel:L.Panels)
        {
            Panel.Bounds.Min.Y+=Height; Panel.Bounds.Max.Y+=Height;
            for(auto& Row:Panel.Rows)
            {
                Row.Bounds.Min.Y+=Height; Row.Bounds.Max.Y+=Height;
                for(auto& Text:Row.Text) Text.At.Y+=Height;
            }
        }
        NextY+=Height;
        return;
    }
    // Dense accessible HUD: preserve the tracker at the top right, then
    // search measured free columns beside/below the actual gameplay panels.
    // The wide lower region permits inline bilingual captions when narrow
    // columns would need extra lines. Panels in overlapping regions still
    // cannot overlap one another.
    using namespace SoraCaptionLayoutRules;
    const float Left=20*F.S,LeftRight=X-Gap,Right=F.W-20*F.S;
    float LeftTop=Top,AllTop=Top,BesideRight=LeftRight,RightTop=NextY,AboveCenter=L.Limit,RightBottom=L.Limit;
    for(const auto& Box:Obstacles)
    {
        AllTop=FMath::Max(AllTop,static_cast<float>(Box.Max.Y)+Gap);
        if(Box.Min.X<Right&&Box.Max.X>X)
        {
            RightTop=FMath::Max(RightTop,static_cast<float>(Box.Max.Y)+Gap);
            if(Box.Min.Y>NextY) RightBottom=FMath::Min(RightBottom,static_cast<float>(Box.Min.Y)-Gap);
        }
        if(Box.Min.X<LeftRight&&Box.Max.X>Left)
        {
            if(Box.Min.X<=Left+10*F.S) LeftTop=FMath::Max(LeftTop,static_cast<float>(Box.Max.Y)+Gap);
            else
            {
                BesideRight=FMath::Min(BesideRight,static_cast<float>(Box.Min.X)-Gap);
                AboveCenter=FMath::Min(AboveCenter,static_cast<float>(Box.Min.Y)-Gap);
            }
        }
    }
    FRect Regions[MaxRegions]; int32 Count=0;
    const auto Region=[&](float RX,float RY,float RW,float Bottom)
    { if(RW>=150.f&&Bottom>RY&&Count<MaxRegions) Regions[Count++]={RX,RY,RW,Bottom-RY}; };
    Region(Left,LeftTop,BesideRight-Left,L.Limit);
    if(AboveCenter<L.Limit) Region(Left,LeftTop,LeftRight-Left,AboveCenter);
    if(AllTop>LeftTop) Region(Left,AllTop,LeftRight-Left,L.Limit);
    if(RightBottom<L.Limit) Region(X,NextY,Width,RightBottom-NoticeReserve);
    Region(X,RightTop,Width,L.Limit-NoticeReserve);
    Region(Left,FMath::Max(AllTop,NextY),Right-Left,L.Limit-NoticeReserve);
    // Full-width story panels end above the weapon stack. The open area
    // beside that stack and above health is usable without moving dialogue,
    // changing speaker alignment or covering any lower HUD information.
    if(const auto* Hero=F.Mode.Hero())
    {
        float WeaponLeft=Right;
        for(const auto& Box:SoraHUDPanels::WeaponPanelBounds(F,*Hero)) WeaponLeft=FMath::Min(WeaponLeft,static_cast<float>(Box.Min.X)-Gap);
        const float BottomTop=BuildLowerStoryLayout(F).Bottom+Gap;
        Region(Left,BottomTop,WeaponLeft-Left,F.H-110*F.S-Gap);
        const float HealthRight=365*F.S+Gap;
        Region(HealthRight,BottomTop,WeaponLeft-HealthRight,F.H-30*F.S);
    }
    TArray<FSoraCaptionPanel> Measured[MaxRegions];
    float Heights[MaxCaptions][MaxRegions]={};
    for(int32 R=0;R<Count;++R)
    {
        Measured[R]=SoraHUDPanels::MeasureCaptions(F,Regions[R].W);
        for(int32 C=0;C<Measured[R].Num()&&C<MaxCaptions;++C) Heights[C][R]=Measured[R][C].Bounds.GetSize().Y;
    }
    const auto Plan=Arrange(Captions.Num(),Regions,Count,Heights,Gap);
    L.Captions.bFits=Plan.Fits;
    if(Plan.Fits)
    {
        for(int32 C=0;C<Captions.Num();++C)
        {
            const auto& At=Plan.Bounds[C];
            PlaceCaption(Measured[Plan.Region[C]][C],{At.X,At.Y},L.Captions);
            if(At.Y<L.Limit&&At.X+At.W>X) NextY=FMath::Max(NextY,At.Y+At.H+Gap);
        }
    }
    else
    {
        // Preserve the text even outside a supported layout; the capture
        // assertion reports the actual capacity failure rather than hiding it.
        float Y=Top;
        for(const auto& Panel:Captions) { PlaceCaption(Panel,{X,Y},L.Captions); Y+=Panel.Bounds.GetSize().Y+Gap; }
    }
}
FUpperStoryLayout BuildUpperStoryLayout(const FSoraHUDFrame& F,bool ForceCompact=false)
{
    FUpperStoryLayout L;
    const USoraCampaignDirector* C=F.Mode.Campaign();
    L.Limit=BuildLowerStoryLayout(F).Top-6*F.S;
    // Wider at 720p, while staying to the right of the objective's panel.
    const float Width=FMath::Min(FMath::Max(435*F.S,540.f),F.W-902*F.S);
    const float X=F.W-20*F.S-Width,Padding=10*F.S,Gap=6*F.S,Inner=Width-2*Padding;
    float Y=87*F.S;
    if(!F.Mode.bCampaign||F.Mode.bDeterministicPractice)
    { ReserveCaptions(F,L,X,Width,0.f,Y); return L; }
    const auto& Notices=C->StoryNotices();
    const bool HasCaptions=!SoraHUDPanels::MeasureCaptions(F,Width).IsEmpty();
    const bool Compact=ForceCompact||HasCaptions;
    const float RowGap=Compact?FMath::Max(2*F.S,1.5f):Gap;
    const float VerticalPadding=Compact?3*F.S:Padding;
    int32 DetailCount=0;
    for(const FSoraStoryNotice& Notice:Notices)
        if(!Notice.Detail.IsEmpty()||(F.Mode.bEnglishSubtitles&&!Notice.DetailEnglish.IsEmpty())) ++DetailCount;
    if(!F.Mode.bChapterComplete&&C->ActiveBeatData()&&C->ActiveChapter())
    {
        TArray<FTrackerRow> Rows=TrackerRows(F);
        const FTrackerRow FullHeading=Rows[0];
        int32 Number=0,Required=0;
        for(int32 I=0;I<C->ActiveChapter()->Rules.Num();++I)
            if(!C->ActiveChapter()->Rules[I].Optional) { ++Required; if(I<=C->ActiveBeat()) ++Number; }
        Rows[0]={FString::Printf(TEXT("第%d場 / %d"),Number,Required),FString::Printf(TEXT("Beat %d of %d"),Number,Required),-1,F.Ivory};
        const auto Tracker=[&]()
        {
            FUpperStoryPanel Panel;
            float At=Y+VerticalPadding;
            for(int32 I=0;I<Rows.Num();++I)
            {
                if(Rows[I].Target==INDEX_NONE)
                {
                    Panel.Rows.Add(MeasureUpperStoryRow(F,Rows[I],X+Padding,At,Inner,Compact));
                    At=Panel.Rows.Last().Bounds.Max.Y+RowGap;
                }
                else
                {
                    // Every defended target keeps its own label and health.
                    // Two columns avoid an eight-person list consuming the HUD.
                    const float Cell=(Inner-Gap)*.5f;
                    const FUpperStoryRow Left=MeasureUpperStoryRow(F,Rows[I],X+Padding,At,Cell,Compact);
                    Panel.Rows.Add(Left);
                    float End=Left.Bounds.Max.Y;
                    if(I+1<Rows.Num()&&Rows[I+1].Target!=INDEX_NONE)
                    {
                        Panel.Rows.Add(MeasureUpperStoryRow(F,Rows[++I],X+Padding+Cell+Gap,At,Cell,Compact));
                        End=FMath::Max(End,static_cast<float>(Panel.Rows.Last().Bounds.Max.Y));
                    }
                    At=End+RowGap;
                }
            }
            Panel.Bounds=FBox2D(FVector2D(X,Y),FVector2D(X+Width,At-RowGap+VerticalPadding));
            return Panel;
        };
        FUpperStoryPanel Panel=Tracker();
        // The active operation and warnings take priority over the full beat
        // title. Its chapter position remains visible even when condensed.
        if(Notices.IsEmpty()&&!HasCaptions)
        {
            Rows[0]=FullHeading;
            FUpperStoryPanel Full=Tracker();
            if(Full.Bounds.Max.Y<=L.Limit) Panel=MoveTemp(Full);
        }
        for(const FUpperStoryRow& Row:Panel.Rows) if(Row.Target!=INDEX_NONE) ++L.Targets;
        Y=Panel.Bounds.Max.Y+Gap;
        L.Panels.Add(MoveTemp(Panel));
    }
    float NoticeReserve=0.f;
    if(!Notices.IsEmpty())
    {
        const auto& Newest=Notices.Last();
        NoticeReserve=MeasureUpperStoryRow(F,{Newest.Japanese,Newest.English,-1,F.Ivory},0,0,Inner,Compact).Bounds.GetSize().Y+2*VerticalPadding+Gap;
        if(Notices.Num()>1||DetailCount>0)
            NoticeReserve+=MeasureUpperStoryRow(F,{
                FString::Printf(TEXT("通知を要約：ほか %d 件・詳細 %d 件"),Notices.Num()-1,DetailCount),
                FString::Printf(TEXT("Condensed: %d more notices; %d details"),Notices.Num()-1,DetailCount),-1,F.Muted},0,0,Inner,Compact).Bounds.GetSize().Y+2*VerticalPadding+Gap;
    }
    ReserveCaptions(F,L,X,Width,NoticeReserve,Y);
    if(Notices.IsEmpty())
    {
        if(!Compact&&Y-Gap>L.Limit) return BuildUpperStoryLayout(F,true);
        return L;
    }
    // Reserve titles before spending space on details. Every item is measured
    // once; a layout trial only translates those rows. Nothing is truncated.
    float NoticeX=X,NoticeWidth=Width,NoticeY=Y;
    TArray<FUpperStoryRow> Titles,Details;
    const auto MeasureNotices=[&]()
    {
        Titles.Reset(); Details.Reset();
        for(int32 I=Notices.Num()-1;I>=0;--I)
        {
            const FSoraStoryNotice& N=Notices[I];
            const FLinearColor Accent=N.Kind==FSoraStoryNotice::EKind::Weapon?F.Gold:N.Kind==FSoraStoryNotice::EKind::Collectible?F.Ivory:F.Teal;
            Titles.Add(MeasureUpperStoryRow(F,{N.Japanese,N.English,-1,Accent},NoticeX+Padding,0,NoticeWidth-2*Padding,Compact));
            Details.Add(MeasureUpperStoryRow(F,{N.Detail,N.DetailEnglish,-1,F.Ivory},NoticeX+Padding,0,NoticeWidth-2*Padding,Compact));
        }
    };
    MeasureNotices();
    const auto PlaceRow=[](FUpperStoryRow Row,float At)
    {
        const float Offset=At-Row.Bounds.Min.Y;
        Row.Bounds.Min.Y+=Offset; Row.Bounds.Max.Y+=Offset;
        for(FUpperStoryText& Text:Row.Text) Text.At.Y+=Offset;
        return Row;
    };
    const auto NoticePanels=[&](int32 Count,const TArray<bool>& ShowDetails)
    {
        TArray<FUpperStoryPanel> Panels;
        float At=NoticeY;
        int32 ShownDetails=0;
        for(int32 I=0;I<Count;++I)
        {
            FUpperStoryPanel Panel;
            Panel.bNotice=true; Panel.Accent=Titles[I].Color;
            Panel.Fade=FMath::Clamp(Notices[Notices.Num()-1-I].Remaining,0.f,1.f);
            Panel.Rows.Add(PlaceRow(Titles[I],At+VerticalPadding));
            float End=Panel.Rows.Last().Bounds.Max.Y;
            if(ShowDetails[I]&&!Details[I].Text.IsEmpty())
            {
                Panel.Rows.Add(PlaceRow(Details[I],End+Gap));
                End=Panel.Rows.Last().Bounds.Max.Y;
                ++ShownDetails;
            }
            Panel.Bounds=FBox2D(FVector2D(NoticeX,At),FVector2D(NoticeX+NoticeWidth,End+VerticalPadding));
            At=Panel.Bounds.Max.Y+Gap;
            Panels.Add(MoveTemp(Panel));
        }
        if(Count<Notices.Num()||ShownDetails<DetailCount)
        {
            FUpperStoryPanel Panel;
            Panel.bNotice=true; Panel.Accent=F.Teal;
            Panel.Rows.Add(MeasureUpperStoryRow(F,{
                FString::Printf(TEXT("通知を要約：ほか %d 件・詳細 %d 件"),Notices.Num()-Count,DetailCount-ShownDetails),
                FString::Printf(TEXT("Condensed: %d more notices; %d details"),Notices.Num()-Count,DetailCount-ShownDetails),-1,F.Muted},NoticeX+Padding,At+VerticalPadding,NoticeWidth-2*Padding,Compact));
            Panel.Bounds=FBox2D(FVector2D(NoticeX,At),FVector2D(NoticeX+NoticeWidth,Panel.Rows.Last().Bounds.Max.Y+VerticalPadding));
            Panels.Add(MoveTemp(Panel));
        }
        return Panels;
    };
    TArray<bool> ShowDetails;
    ShowDetails.Init(true,Notices.Num());
    int32 TitleCount=Notices.Num();
    TArray<FUpperStoryPanel> Panels=NoticePanels(TitleCount,ShowDetails);
    const auto Fits=[&](const TArray<FUpperStoryPanel>& Trial)
        { return Trial.IsEmpty()||Trial.Last().Bounds.Max.Y<=L.Limit; };
    if(!Fits(Panels))
    {
        ShowDetails.Init(false,Notices.Num());
        Panels=NoticePanels(TitleCount,ShowDetails);
        while(TitleCount>0&&!Fits(Panels)) Panels=NoticePanels(--TitleCount,ShowDetails);
        for(int32 I=0;I<TitleCount;++I)
        {
            if(Details[I].Text.IsEmpty()) continue;
            ShowDetails[I]=true;
            TArray<FUpperStoryPanel> Trial=NoticePanels(TitleCount,ShowDetails);
            if(Fits(Trial)) Panels=MoveTemp(Trial);
            else ShowDetails[I]=false;
        }
    }
    if((!Fits(Panels)||TitleCount==0)&&!Compact) return BuildUpperStoryLayout(F,true);
    if(!Fits(Panels)||TitleCount==0)
    {
        // The lower story stack is immutable. Use the free column below the
        // objective and left of the rhythm group before losing the newest
        // notice title. Captions and all fixed gameplay panels are obstacles.
        const float Left=20*F.S;
        float Top=87*F.S,Right=X-Gap;
        auto Obstacles=SoraHUDPanels::UpperGameplayPanelBounds(F);
        const auto Rhythm=RhythmPanelBounds(F);
        if(Rhythm.bIsValid) Obstacles.Add(Rhythm);
        for(const auto& Panel:L.Captions.Panels) Obstacles.Add(Panel.Bounds);
        for(const auto& Box:Obstacles)
            if(Box.Min.X<Right&&Box.Max.X>Left)
            {
                if(Box.Min.X<=Left+10*F.S) Top=FMath::Max(Top,static_cast<float>(Box.Max.Y)+Gap);
                else Right=FMath::Min(Right,static_cast<float>(Box.Min.X)-Gap);
            }
        if(Right-Left>=150.f&&Top<L.Limit)
        {
            const auto Previous=Panels; const auto PreviousDetails=ShowDetails; const int32 PreviousCount=TitleCount;
            NoticeX=Left; NoticeWidth=Right-Left; NoticeY=Top; MeasureNotices();
            ShowDetails.Init(false,Notices.Num()); TitleCount=Notices.Num();
            auto Trial=NoticePanels(TitleCount,ShowDetails);
            while(TitleCount>1&&!Fits(Trial)) Trial=NoticePanels(--TitleCount,ShowDetails);
            if(Fits(Trial))
            {
                Panels=MoveTemp(Trial);
                for(int32 I=0;I<TitleCount;++I)
                {
                    if(Details[I].Text.IsEmpty()) continue;
                    ShowDetails[I]=true; Trial=NoticePanels(TitleCount,ShowDetails);
                    if(Fits(Trial)) Panels=MoveTemp(Trial); else ShowDetails[I]=false;
                }
            }
            else { Panels=Previous; ShowDetails=PreviousDetails; TitleCount=PreviousCount; }
        }
    }
    L.NoticeTitles=TitleCount;
    for(int32 I=0;I<TitleCount;++I)
    {
        L.NoticeIndices.Add(Notices.Num()-1-I);
        if(ShowDetails[I]&&!Details[I].Text.IsEmpty()) ++L.NoticeDetails;
    }
    L.bCondensedNotices=L.NoticeTitles<Notices.Num()||L.NoticeDetails<DetailCount;
    L.Panels.Append(MoveTemp(Panels));
    return L;
}
void DrawUpperStory(const FSoraHUDFrame& F)
{
    for(const FUpperStoryPanel& Panel:BuildUpperStoryLayout(F).Panels)
    {
        const FVector2D Size=Panel.Bounds.GetSize();
        F.HUD.Panel(Panel.Bounds.Min.X,Panel.Bounds.Min.Y,Size.X,Size.Y,Panel.bNotice?
            FLinearColor(.015f,.035f,.045f,.9f*Panel.Fade):FLinearColor(.013f,.027f,.033f,.8f));
        if(Panel.bNotice) F.HUD.Panel(Panel.Bounds.Min.X,Panel.Bounds.Min.Y,4*F.S,Size.Y,Panel.Accent);
        for(const FUpperStoryRow& Row:Panel.Rows)
        {
            for(const FUpperStoryText& Text:Row.Text) F.HUD.Label(Text.Text,Text.At.X,Text.At.Y,Text.Scale,Text.Color);
            if(Row.Fraction>=0)
            {
                const bool CompactTarget=Row.bCompact&&Row.Target!=INDEX_NONE;
                const float BarHeight=Row.bCompact?FMath::Min(4*F.S,2.f):4*F.S;
                const float At=Row.Bounds.Max.Y-(CompactTarget?BarHeight:Row.bCompact?4.f:9*F.S),Width=Row.Bounds.GetSize().X;
                F.HUD.Panel(Row.Bounds.Min.X,At,Width,BarHeight,FLinearColor(.12f,.16f,.18f));
                F.HUD.Panel(Row.Bounds.Min.X,At,Width*FMath::Clamp(Row.Fraction,0.f,1.f),BarHeight,Row.Color);
            }
        }
    }
}

void DrawStoryStrip(const FSoraHUDFrame& F,const FStoryStrip& Strip,FLinearColor Color,float Opacity)
{
    if(!Strip.Bounds.bIsValid) return;
    F.HUD.Panel(Strip.Bounds.Min.X,Strip.Bounds.Min.Y,Strip.Bounds.GetSize().X,Strip.Bounds.GetSize().Y,FLinearColor(.015,.035,.045,Opacity));
    float Y=Strip.Bounds.Min.Y+5*F.S;
    for(const FString& Line:Strip.Japanese) { F.HUD.Label(Line,35*F.S,Y,F.JapaneseSubtitleScale,Color); Y+=Strip.JapaneseLeading; }
    for(const FString& Line:Strip.English) { F.HUD.Label(Line,35*F.S,Y,F.EnglishSubtitleScale,F.Muted); Y+=Strip.EnglishLeading; }
}
}

namespace
{
TArray<SoraText::FLine> InteractionPrompts(const FSoraHUDFrame& F)
{
    TArray<SoraText::FLine> Lines;
    const auto* Hero=F.Mode.Hero();
    if(!Hero||!F.Mode.bCampaign||F.Mode.bDeterministicPractice) return Lines;
    const auto* Campaign=F.Mode.Campaign();
    const auto Key=SoraUI::ActionKey(&F.HUD,TEXT("Interact"));
    FVector Anchor;
    if(Campaign->ObjectiveAnchor(Anchor)&&Campaign->AnchorTakesInteract()&&
        FVector::Dist2D(Anchor,Hero->GetActorLocation())<260.f)
        Lines.Add(SoraText::Format(Campaign->AwaitingCapture()?NSLOCTEXT("SoraArena.HUD","Prompt.Capture","{Interact}  捕らえる")
            :NSLOCTEXT("SoraArena.HUD","Prompt.Work","{Interact}  作業する"),{{TEXT("Interact"),Key}}));
    for(const int32 Cache:Campaign->AvailableCaches())
        if(FVector::Dist2D(Campaign->CacheLocation(Cache),Hero->GetActorLocation())<260.f)
            Lines.Add(SoraText::Format(NSLOCTEXT("SoraArena.HUD","Prompt.Search","{Interact}  調べる"),{{TEXT("Interact"),Key}}));
    for(const int32 Pickup:Campaign->LoosePickups())
        if(FVector::Dist2D(Campaign->PickupLocation(Pickup),Hero->GetActorLocation())<260.f)
            Lines.Add(SoraText::Format(NSLOCTEXT("SoraArena.HUD","Prompt.PickUp","{Interact}  拾う"),{{TEXT("Interact"),Key}}));
    return Lines;
}
TArray<FBox2D> WorldLabelObstacles(const FSoraHUDFrame& F);
SoraCaptionLayoutRules::FLabelPlacement PlaceWorldLabel(const FSoraHUDFrame& F,FVector2D Desired,FVector2D Size);
struct FInteractionLayout
{
    SoraRhythmHUDLayout::FLayout At;
    float Width=0.f, Height=0.f, Scale=0.f, StoryTop=0.f,EnglishY=0.f;
    bool bStackEnglish=false,bFits=true;
};
FInteractionLayout BuildInteractionLayout(const FSoraHUDFrame& F)
{
    FInteractionLayout L;
    const bool bRhythm=F.Mode.Campaign()->RhythmCuePeriodMs()>0;
    L.Scale=bRhythm?FMath::Max(.65f*F.S,.65f):.65f*F.S;
    // Reserve whichever real localized action label is widest/tallest,
    // including rebound keyboard and current gamepad names.
    const auto Key=SoraUI::ActionKey(&F.HUD,TEXT("Interact"));
    const FText Prompts[]={NSLOCTEXT("SoraArena.HUD","Prompt.Capture","{Interact}  捕らえる"),
        NSLOCTEXT("SoraArena.HUD","Prompt.Work","{Interact}  作業する"),
        NSLOCTEXT("SoraArena.HUD","Prompt.Search","{Interact}  調べる"),
        NSLOCTEXT("SoraArena.HUD","Prompt.PickUp","{Interact}  拾う")};
    float JapaneseWidth=0,EnglishWidth=0,JapaneseHeight=0,EnglishHeight=0;
    for(const FText& Prompt:Prompts)
    {
        const auto Line=SoraText::Format(Prompt,{{TEXT("Interact"),Key}});
        int32 JW=0,JH=0,EW=0,EH=0;
        UCanvas::ClippedStrLen(F.HUD.JapaneseFontObject(),L.Scale,L.Scale,JW,JH,Line.Japanese);
        if(F.Mode.bEnglishSubtitles)
            UCanvas::ClippedStrLen(F.HUD.JapaneseFontObject(),L.Scale*.8f,L.Scale*.8f,EW,EH,Line.English);
        JapaneseWidth=FMath::Max(JapaneseWidth,static_cast<float>(JW)); EnglishWidth=FMath::Max(EnglishWidth,static_cast<float>(EW));
        JapaneseHeight=FMath::Max(JapaneseHeight,static_cast<float>(JH)); EnglishHeight=FMath::Max(EnglishHeight,static_cast<float>(EH));
        L.Width=FMath::Max(L.Width,F.HUD.LabelWidth(Line.Japanese,L.Scale)+(F.Mode.bEnglishSubtitles?
            14.f*F.S+F.HUD.LabelWidth(Line.English,L.Scale*.8f):0.f));
        L.Height=FMath::Max(L.Height,FMath::Max(static_cast<float>(JH),F.Mode.bEnglishSubtitles?EH+6.f*L.Scale:0.f));
    }
    if(!bRhythm)
    {
        // Ordinary work/search/pickup cues also need measured space. Their
        // former center position could be painted over by the coaching strip.
        // This branch cannot recurse through RhythmPanelBounds: no cue is live.
        const auto Plan=PlaceWorldLabel(F,{F.W*.5f-75.f*F.S,F.H*.5f+60.f*F.S},{L.Width,L.Height});
        L.At.PromptX=Plan.Bounds.X; L.At.PromptY=Plan.Bounds.Y; L.bFits=Plan.Fits;
        return L;
    }
    const float TrackerWidth=FMath::Min(FMath::Max(435*F.S,540.f),F.W-902*F.S);
    const float TrackerLeft=F.W-20*F.S-TrackerWidth;
    if(F.Mode.bEnglishSubtitles&&F.W*.5f-75*F.S+L.Width>TrackerLeft-6*F.S)
    {
        // In bilingual play the inline translation can cross the right-hand
        // tracker. Stack the same labels at their existing sizes instead.
        L.bStackEnglish=true; L.EnglishY=JapaneseHeight+4.f;
        L.Width=FMath::Max(JapaneseWidth,EnglishWidth); L.Height=L.EnglishY+EnglishHeight;
    }
    L.StoryTop=BuildLowerStoryLayout(F).Top;
    L.At=SoraRhythmHUDLayout::Place(F.W,F.H,F.S,L.Width,L.Height,L.StoryTop);
    return L;
}
void DrawInteractionLabel(const FSoraHUDFrame& F,const SoraText::FLine& Line,const FInteractionLayout& L,FLinearColor Color)
{
    const bool bRhythm=F.Mode.Campaign()->RhythmCuePeriodMs()>0;
    // Earlier site/objective labels and prompts may have claimed space since
    // the frame's rhythm group was measured. Resolve ordinary cues at draw.
    const auto At=bRhythm?L:BuildInteractionLayout(F);
    ensureMsgf(At.bFits,TEXT("Measured interaction prompt cannot fit around the visible HUD panels"));
    if(!bRhythm) F.WorldMarkerBounds.Add(FBox2D({At.At.PromptX,At.At.PromptY},{At.At.PromptX+At.Width,At.At.PromptY+At.Height}));
    if(!At.bStackEnglish) { F.LabelWithEnglish(Line,At.At.PromptX,At.At.PromptY,At.Scale,Color); return; }
    F.HUD.Label(Line.Japanese,At.At.PromptX,At.At.PromptY,At.Scale,Color);
    F.HUD.Label(Line.English,At.At.PromptX,At.At.PromptY+At.EnglishY,At.Scale*.8f,F.Muted);
}
FBox2D RhythmPanelBounds(const FSoraHUDFrame& F)
{
    if(F.Mode.Campaign()->RhythmCuePeriodMs()<=0) return FBox2D(ForceInit);
    const auto L=BuildInteractionLayout(F);
    const float R=SoraRhythmHUDLayout::Radius+SoraRhythmHUDLayout::Stroke;
    return FBox2D({L.At.CenterX-R,FMath::Min(L.At.CenterY-R,L.At.PromptY)},
        {L.At.PromptX+L.Width,FMath::Max(L.At.CenterY+R,L.At.PromptY+L.Height)});
}
TArray<FBox2D> WorldLabelObstacles(const FSoraHUDFrame& F)
{
    auto Occupied=SoraHUDPanels::UpperGameplayPanelBounds(F);
    const auto Rhythm=RhythmPanelBounds(F); if(Rhythm.bIsValid) Occupied.Add(Rhythm);
    const auto Upper=BuildUpperStoryLayout(F);
    for(const auto& Panel:Upper.Panels) Occupied.Add(Panel.Bounds);
    for(const auto& Panel:Upper.Captions.Panels) Occupied.Add(Panel.Bounds);
    const auto Lower=BuildLowerStoryLayout(F);
    for(const auto& Box:{Lower.Dialogue,Lower.Notice.Bounds,Lower.Prompt.Bounds}) if(Box.bIsValid) Occupied.Add(Box);
    if(const auto* Hero=F.Mode.Hero()) Occupied.Append(SoraHUDPanels::WeaponPanelBounds(F,*Hero));
    Occupied.Add(FBox2D({25*F.S,F.H-110*F.S},{365*F.S,F.H-30*F.S}));
    Occupied.Append(F.WorldMarkerBounds);
    return Occupied;
}
SoraCaptionLayoutRules::FLabelPlacement PlaceWorldLabel(const FSoraHUDFrame& F,FVector2D Desired,FVector2D Size)
{
    const auto Occupied=WorldLabelObstacles(F);
    TArray<SoraCaptionLayoutRules::FRect> Obstacles;
    for(const auto& Box:Occupied) Obstacles.Add({static_cast<float>(Box.Min.X),static_cast<float>(Box.Min.Y),
        static_cast<float>(Box.GetSize().X),static_cast<float>(Box.GetSize().Y)});
    return SoraCaptionLayoutRules::PlaceLabel({static_cast<float>(Desired.X),static_cast<float>(Desired.Y),
        static_cast<float>(Size.X),static_cast<float>(Size.Y)},
        {20*F.S,87*F.S,F.W-40*F.S,F.H-207*F.S},Obstacles.GetData(),Obstacles.Num(),4*F.S);
}
}
FVector2D SoraHUDPanels::WorldMarkerPosition(const FSoraHUDFrame& F,FVector2D Desired,FVector2D Size)
{
    const auto Plan=PlaceWorldLabel(F,Desired,Size);
    // Preserve the label if an unsupported screen has no free region, but
    // surface the capacity failure to development/capture qualification.
    ensureMsgf(Plan.Fits,TEXT("Projected world label cannot fit around the measured HUD panels"));
    const FVector2D At(Plan.Bounds.X,Plan.Bounds.Y);
    F.WorldMarkerBounds.Add(FBox2D(At,At+Size));
    return At;
}
FSoraCaptionLayout SoraHUDPanels::CaptionLayout(const FSoraHUDFrame& F) { return BuildUpperStoryLayout(F).Captions; }
bool SoraHUDPanels::CaptionStoryLayoutFits(const FSoraHUDFrame& F,FString& Why)
{
    const auto L=BuildUpperStoryLayout(F);
    if(!L.Captions.bFits) { Why=TEXT("Visible captions cannot fit in the available measured HUD regions"); return false; }
    const auto* Owner=F.bSoundCaptions?USoraCaptions::Get(&F.Mode):nullptr;
    if(L.Captions.Panels.Num()!=(Owner?Owner->Live().Num():0))
    { Why=TEXT("The caption layout dropped a live caption"); return false; }
    TArray<FBox2D> Occupied=SoraHUDPanels::UpperGameplayPanelBounds(F);
    const auto Rhythm=RhythmPanelBounds(F);
    if(Rhythm.bIsValid) Occupied.Add(Rhythm);
    for(const auto& Panel:L.Panels) Occupied.Add(Panel.Bounds);
    const auto Lower=BuildLowerStoryLayout(F);
    for(const auto& Box:{Lower.Dialogue,Lower.Notice.Bounds,Lower.Prompt.Bounds}) if(Box.bIsValid) Occupied.Add(Box);
    if(const auto* Hero=F.Mode.Hero()) Occupied.Append(WeaponPanelBounds(F,*Hero));
    Occupied.Add(FBox2D({25*F.S,F.H-110*F.S},{365*F.S,F.H-30*F.S}));
    for(const auto& Panel:L.Captions.Panels)
    {
        if(Panel.Bounds.Min.X<0||Panel.Bounds.Max.X>F.W||Panel.Bounds.Min.Y<87*F.S||Panel.Bounds.Max.Y>F.H)
        { Why=TEXT("A visible caption exceeds the screen"); return false; }
        for(const auto& Other:Occupied)
            if(Panel.Bounds.Intersect(Other)) { Why=TEXT("A caption overlaps a measured gameplay/story panel"); return false; }
        Occupied.Add(Panel.Bounds);
        for(const auto& Text:Panel.Text)
        {
            const auto Ink=CaptionGlyphBounds(F,Text.Text,Text.Scale);
            const auto Min=Text.At+Ink.Min,Max=Text.At+Ink.Max;
            if(Min.X<Panel.Bounds.Min.X||Min.Y<Panel.Bounds.Min.Y||Max.X>Panel.Bounds.Max.X+.5f||Max.Y>Panel.Bounds.Max.Y+.5f)
            { Why=TEXT("A caption glyph exceeds its measured panel"); return false; }
        }
    }
    return true;
}
float SoraHUDPanels::GameplayStoryTop(const FSoraHUDFrame& F) { return BuildLowerStoryLayout(F).Top; }
bool SoraHUDPanels::RhythmCueLayoutFits(const FSoraHUDFrame& F,FString& Why)
{
    if(F.Mode.Campaign()->RhythmCuePeriodMs()<=0) return true;
    const auto L=BuildInteractionLayout(F);
    if(!SoraRhythmHUDLayout::Fits(L.At,F.W,F.H,L.Width,L.Height,L.StoryTop))
    { Why=TEXT("Rhythm ring or measured Interact text exceeds the viewport or lower story boundary"); return false; }
    return true;
}
bool SoraHUDPanels::InteractionPromptLayoutFits(const FSoraHUDFrame& F,FString& Why)
{
    if(F.Mode.Campaign()->RhythmCuePeriodMs()>0) return RhythmCueLayoutFits(F,Why);
    FSoraHUDFrame Probe=F;
    const auto Prompts=InteractionPrompts(F);
    for(int32 Index=0;Index<Prompts.Num();++Index)
    {
        const auto L=BuildInteractionLayout(Probe);
        const FBox2D Box({L.At.PromptX,L.At.PromptY},{L.At.PromptX+L.Width,L.At.PromptY+L.Height});
        if(!L.bFits||L.Width<=0||L.Height<=0||Box.Min.X<0||Box.Min.Y<0||Box.Max.X>F.W||Box.Max.Y>F.H)
        { Why=TEXT("A visible ordinary interaction prompt cannot fit at its measured text size"); return false; }
        for(const auto& Other:WorldLabelObstacles(Probe))
            if(Box.Intersect(Other))
            {
                Why=FString::Printf(TEXT("Interaction prompt [%.2f,%.2f]-[%.2f,%.2f] overlaps HUD panel [%.2f,%.2f]-[%.2f,%.2f]"),
                    Box.Min.X,Box.Min.Y,Box.Max.X,Box.Max.Y,Other.Min.X,Other.Min.Y,Other.Max.X,Other.Max.Y);
                return false;
            }
        Probe.WorldMarkerBounds.Add(Box);
    }
    return true;
}
bool SoraHUDPanels::StoryTrackerLayoutFits(const FSoraHUDFrame& F,FString& Why)
{
    const FUpperStoryLayout L=BuildUpperStoryLayout(F);
    TArray<FBox2D> TextBounds;
    TArray<FBox2D> PanelBounds;
    for(const FUpperStoryPanel& Panel:L.Panels)
    {
        if(Panel.Bounds.Min.X<(Panel.bNotice?20.f:870.f)*F.S||Panel.Bounds.Min.Y<87*F.S||Panel.Bounds.Max.X>F.W||Panel.Bounds.Max.Y>L.Limit+.5f)
        {
            Why=FString::Printf(TEXT("Measured %s panel [%.2f,%.2f]-[%.2f,%.2f] exceeds viewport %.0fx%.0f or lower-story limit %.2f"),
                Panel.bNotice?TEXT("notice"):TEXT("tracker"),Panel.Bounds.Min.X,Panel.Bounds.Min.Y,Panel.Bounds.Max.X,Panel.Bounds.Max.Y,F.W,F.H,L.Limit);
            return false;
        }
        for(const auto& Previous:PanelBounds)
            if(Panel.Bounds.Intersect(Previous)) { Why=TEXT("Measured tracker/notice panels overlap"); return false; }
        if(Panel.bNotice&&Panel.Bounds.Min.X<870*F.S)
        {
            auto Obstacles=UpperGameplayPanelBounds(F);
            const auto Rhythm=RhythmPanelBounds(F); if(Rhythm.bIsValid) Obstacles.Add(Rhythm);
            for(const auto& Caption:L.Captions.Panels) Obstacles.Add(Caption.Bounds);
            for(const auto& Other:Obstacles)
                if(Panel.Bounds.Intersect(Other)) { Why=TEXT("Alternate notice column overlaps a gameplay panel or caption"); return false; }
        }
        const auto Rhythm=RhythmPanelBounds(F);
        if(Rhythm.bIsValid&&Panel.Bounds.Intersect(Rhythm))
        { Why=TEXT("Measured tracker/notice panel overlaps the rhythm interaction group"); return false; }
        PanelBounds.Add(Panel.Bounds);
        for(const FUpperStoryRow& Row:Panel.Rows)
        {
            if(Row.Target!=INDEX_NONE)
            {
                const auto& Task=F.Mode.Campaign()->ActiveTask();
                const auto& State=F.Mode.Campaign()->TaskProgress();
                if(Row.Target>=Task.TargetCount||Task.TargetHp[Row.Target]<=0||
                    !FMath::IsNearlyEqual(Row.Fraction,static_cast<float>(State.TargetHp[Row.Target])/Task.TargetHp[Row.Target]))
                { Why=TEXT("A defended target's visible health does not match its live task state"); return false; }
            }
            for(const FUpperStoryText& Text:Row.Text)
            {
                int32 W=0,H=0;
                UCanvas::ClippedStrLen(F.HUD.JapaneseFontObject(),Text.Scale,Text.Scale,W,H,Text.Text);
                FBox2D Box(Text.At,Text.At+FVector2D(W,H));
                if(Text.bInkBounds)
                { const auto Ink=CaptionGlyphBounds(F,Text.Text,Text.Scale); Box=FBox2D(Text.At+Ink.Min,Text.At+Ink.Max); }
                const float BarSpace=Row.bCompact?(Row.Target!=INDEX_NONE?FMath::Min(4*F.S,2.f):4.f):9*F.S;
                const float TextBottom=Row.Bounds.Max.Y-(Row.Fraction>=0?BarSpace:0);
                if(Text.Scale<.55f||Box.Min.X<Row.Bounds.Min.X||Box.Max.X>Row.Bounds.Max.X+.5f||Box.Max.Y>TextBottom+.5f)
                { Why=TEXT("Tracker/notice text is too small or escapes its measured row"); return false; }
                for(const FBox2D& Other:TextBounds)
                    if(Box.Min.X<Other.Max.X&&Box.Max.X>Other.Min.X&&Box.Min.Y<Other.Max.Y&&Box.Max.Y>Other.Min.Y)
                    { Why=TEXT("Measured tracker/notice labels overlap"); return false; }
                TextBounds.Add(Box);
            }
        }
    }
    if(F.Mode.bCampaign&&!F.Mode.bDeterministicPractice&&!F.Mode.bChapterComplete&&
        F.Mode.Campaign()->ActiveBeatData()&&L.Targets!=F.Mode.Campaign()->ActiveTask().TargetCount)
    { Why=TEXT("The tracker dropped a defended target"); return false; }
    for(int32 I=0;I<L.NoticeIndices.Num();++I)
        if(L.NoticeIndices[I]!=F.Mode.Campaign()->StoryNotices().Num()-1-I)
        { Why=TEXT("The visible notices do not prioritize the newest titles"); return false; }
    if(L.NoticeTitles<F.Mode.Campaign()->StoryNotices().Num()&&!L.bCondensedNotices)
    { Why=TEXT("Story notices were hidden without a visible condensed summary"); return false; }
    return true;
}

bool SoraHUDPanels::BottomHUDLayoutFits(const FSoraHUDFrame& F,const ASoraPlayerCharacter& Hero,FString& Why)
{
    const FLowerStoryLayout L=BuildLowerStoryLayout(F);
    if(F.bSpeakerNames)
        if(const FSoraDialogueCue* Cue=F.Mode.Campaign()->CurrentDialogueCue())
            if(const auto* Speaker=FSoraCatalog::Get().DialogueSpeaker(Cue->SpeakerId))
            {
                const float JapaneseRight=35*F.S+F.HUD.LabelWidth(Speaker->Japanese,F.DialogueJapaneseSpeakerScale);
                const float EnglishLeft=F.W-35*F.S-F.HUD.LabelWidth(Speaker->English,F.DialogueEnglishSpeakerScale);
                if(JapaneseRight>F.W-35*F.S||(F.Mode.bEnglishSubtitles&&EnglishLeft<JapaneseRight+14*F.S))
                { Why=TEXT("Dialogue speaker names exceed their row or overlap"); return false; }
            }
    TArray<FBox2D> Panels=WeaponPanelBounds(F,Hero);
    Panels.Add(FBox2D(FVector2D(25*F.S,F.H-110*F.S),FVector2D(365*F.S,F.H-30*F.S)));
    for(const FBox2D& Story:{L.Dialogue,L.Notice.Bounds,L.Prompt.Bounds}) if(Story.bIsValid) Panels.Add(Story);
    for(int32 I=0;I<Panels.Num();++I)
    {
        const FBox2D& A=Panels[I];
        if(A.Min.X<0||A.Min.Y<0||A.Max.X>F.W||A.Max.Y>F.H)
        { Why=TEXT("Bottom gameplay panel exceeds viewport"); return false; }
        for(int32 J=0;J<I;++J)
        {
            const FBox2D& B=Panels[J];
            if(A.Min.X<B.Max.X&&A.Max.X>B.Min.X&&A.Min.Y<B.Max.Y&&A.Max.Y>B.Min.Y)
            { Why=TEXT("Weapon, windup, arm notice, vitals or lower story panels overlap"); return false; }
        }
    }
    return true;
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
    const float W=Frame.W,H=Frame.H,S=Frame.S;
    const FLinearColor Ivory=Frame.Ivory,Gold=Frame.Gold,Teal=Frame.Teal;
    const auto Interaction=BuildInteractionLayout(Frame);
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
                const FString Text=G->bEnglishSubtitles?FString::Printf(TEXT("目標 / %dm   Objective"),Distance):FString::Printf(TEXT("目標 / %dm"),Distance);
                int32 TW=0,TH=0; UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),.42*S,.42*S,TW,TH,Text);
                const auto At=WorldMarkerPosition(Frame,{Screen.X-60*S,Screen.Y},{static_cast<float>(TW),static_cast<float>(TH)});
                HUD.Label(Text,At.X,At.Y,.42*S,Gold);
            }
        }
    }
    // Capture/work, nearby caches and loose pickups use the same eligibility
    // and measured placement in live drawing and capture qualification.
    for(const auto& Line:InteractionPrompts(Frame)) DrawInteractionLabel(Frame,Line,Interaction,Gold);
    // A continuously closing, shape-based metronome; no flashing or color-only
    // signal. Its entire sweep stays beside the measured action cue.
    const int32 CuePeriod=Campaign->RhythmCuePeriodMs();
    if(CuePeriod>0)
    {
        const float Radius=22.f+30.f*Campaign->RhythmCueRemainingMs()/CuePeriod;
        const FVector2D Center(Interaction.At.CenterX,Interaction.At.CenterY);
        for(int32 Segment=0;Segment<48;++Segment)
        {
            const float A=Segment*2.f*PI/48.f,B=(Segment+1)*2.f*PI/48.f;
            HUD.DrawLine(Center.X+FMath::Cos(A)*Radius,Center.Y+FMath::Sin(A)*Radius,
                Center.X+FMath::Cos(B)*Radius,Center.Y+FMath::Sin(B)*Radius,Frame.Gold,2.f);
        }
    }
    // The beat tracker, and story notices beneath it.
    DrawUpperStory(Frame);
    // Story lines and notices share the lower third; play and objective
    // timers continue beneath a line.
    const auto* Cue=Campaign->CurrentDialogueCue();
    const FLowerStoryLayout Lower=BuildLowerStoryLayout(Frame);
    if(Cue) DrawLine(Frame,*Cue,Lower.Dialogue.Max.Y);
    DrawStoryStrip(Frame,Lower.Notice,Ivory,.94f);
    DrawStoryStrip(Frame,Lower.Prompt,Teal,.90f);
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
    if(ShowsRegistry(Frame.Mode)) { DrawRegistry(Frame); return; }
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
