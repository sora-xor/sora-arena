#include "SoraHUD.h"
#include "HUD/SoraHUDPanels.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "SoraText.h"
#include "UI/SSoraFrontEnd.h"
#include "Engine/Canvas.h"
#include "Engine/Font.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Fonts/CompositeFont.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"

FSoraHUDFrame::FSoraHUDFrame(ASoraHUD& InHUD,const ASoraGameMode& InMode,float Width,float Height)
    : HUD(InHUD), Mode(InMode), W(Width), H(Height)
{
    S=FMath::Clamp(FMath::Min(W/1600.f,H/1000.f),.45f,1.5f);
    // Story text needs a readable floor when the rest of the HUD scales down.
    JapaneseSubtitleScale=FMath::Max(.65f*S,.65f);
    EnglishSubtitleScale=FMath::Max(.60f*S,.60f);
    JapaneseSpeakerScale=FMath::Max(.55f*S,.55f);
    EnglishSpeakerScale=FMath::Max(.52f*S,.52f);
    JapaneseSubtitleLineHeight=FMath::Max(24.f*S,22.f);
    EnglishSubtitleLineHeight=FMath::Max(20.f*S,20.f);
    if(const USoraSettings* Settings=Mode.Settings())
    {
        const float Size=SoraAccessibility::SubtitleScale(Settings->SubtitleSize());
        DialogueJapaneseScale=JapaneseSubtitleScale*Size; DialogueEnglishScale=EnglishSubtitleScale*Size;
        DialogueJapaneseSpeakerScale=JapaneseSpeakerScale*Size; DialogueEnglishSpeakerScale=EnglishSpeakerScale*Size;
        DialogueJapaneseLineHeight=JapaneseSubtitleLineHeight*Size; DialogueEnglishLineHeight=EnglishSubtitleLineHeight*Size;
        bSpeakerNames=Settings->SpeakerNames(); bSoundCaptions=Settings->SoundCaptions(); bReduceFlashing=Settings->ReduceFlashing();
    }
    else
    {
        DialogueJapaneseScale=JapaneseSubtitleScale; DialogueEnglishScale=EnglishSubtitleScale;
        DialogueJapaneseSpeakerScale=JapaneseSpeakerScale; DialogueEnglishSpeakerScale=EnglishSpeakerScale;
        DialogueJapaneseLineHeight=JapaneseSubtitleLineHeight; DialogueEnglishLineHeight=EnglishSubtitleLineHeight;
    }
    Ivory=FLinearColor(.93,.90,.80); Gold=FLinearColor(.94,.65,.21); Teal=FLinearColor(.22,.81,.75); Muted=FLinearColor(.56,.63,.65);
}
FSoraDialogueLayout FSoraHUDFrame::DialogueLayout(bool bEnglish) const
{
    // At the standard size this is the original panel at every resolution:
    // 170*S tall with its bottom at H-130*S, the speaker at 10*S, Japanese at
    // 40*S and English at 105*S. A larger size grows each block by exactly
    // what its lines grew, so it keeps the standard spacing between them.
    const float JapaneseGrowth=DialogueJapaneseLineHeight-JapaneseSubtitleLineHeight;
    const float EnglishGrowth=DialogueEnglishLineHeight-EnglishSubtitleLineHeight;
    FSoraDialogueLayout Layout;
    Layout.SpeakerY=10*S;
    Layout.JapaneseY=Layout.SpeakerY+(bSpeakerNames?30*S+JapaneseGrowth:0.f);
    Layout.EnglishY=Layout.JapaneseY+65*S+2*JapaneseGrowth;
    Layout.Height=FMath::Max(170*S,Layout.EnglishY+65*S+(bEnglish?2*EnglishGrowth:0.f));
    Layout.Top=H-130*S-Layout.Height;
    return Layout;
}
void FSoraHUDFrame::LabelWithEnglish(const SoraText::FLine& Line,float X,float Y,float Scale,FLinearColor Color) const
{
    HUD.Label(Line.Japanese,X,Y,Scale,Color);
    if(!Mode.bEnglishSubtitles||Line.English.IsEmpty()) return;
    // Smaller, lowered to about the same baseline (the font's ascent is about
    // 30 canvas units per unit of scale).
    const float EnglishScale=.8f*Scale;
    HUD.Label(Line.English,X+HUD.LabelWidth(Line.Japanese,Scale)+14*S,Y+30*(Scale-EnglishScale),EnglishScale,Muted);
}
void ASoraHUD::BeginPlay()
{
    Super::BeginPlay();
    // Only a local player with a game viewport gets the Slate front end; a
    // viewportless automation world drives USoraFrontEnd directly.
    auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    UGameViewportClient* Viewport=GetWorld()->GetGameViewport();
    if(!G||!G->FrontEnd()||!Viewport||!PlayerOwner||!PlayerOwner->IsLocalController()||!FSlateApplication::IsInitialized()) return;
    FrontEnd=G->FrontEnd();
    FrontEndWidget=SNew(SSoraFrontEnd).FrontEnd(FrontEnd).Font(JapaneseFontObject()).TitleArt(TitleArt()).Logo(ResistanceLogo());
    Viewport->AddViewportWidgetContent(FrontEndWidget.ToSharedRef(),10);
    DeviceTracker=MakeShared<FSoraInputDeviceTracker>(FrontEnd);
    FSlateApplication::Get().RegisterInputPreProcessor(DeviceTracker);
    FrontEndChanged=G->FrontEnd()->OnChanged.AddUObject(this,&ASoraHUD::SyncFrontEnd);
    SyncFrontEnd();
}
void ASoraHUD::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if(USoraFrontEnd* Model=FrontEnd.Get()) Model->OnChanged.Remove(FrontEndChanged);
    if(DeviceTracker&&FSlateApplication::IsInitialized()) FSlateApplication::Get().UnregisterInputPreProcessor(DeviceTracker);
    if(FrontEndWidget) if(UGameViewportClient* Viewport=GetWorld()->GetGameViewport()) Viewport->RemoveViewportWidgetContent(FrontEndWidget.ToSharedRef());
    DeviceTracker.Reset(); FrontEndWidget.Reset();
    Super::EndPlay(EndPlayReason);
}
void ASoraHUD::SyncFrontEnd()
{
    USoraFrontEnd* Model=FrontEnd.Get();
    if(!Model||!FrontEndWidget||!PlayerOwner) return;
    FrontEndWidget->Refresh();
    const bool bOpen=Model->IsOpen();
    if(bOpen!=bFrontEndHasInput)
    {
        // Keys held when the menu opens or closes must not act on the other side.
        if(PlayerOwner->PlayerInput) PlayerOwner->PlayerInput->FlushPressedKeys();
        if(bOpen) FocusFrontEnd();
        else PlayerOwner->SetInputMode(FInputModeGameOnly());
        bFrontEndHasInput=bOpen;
    }
    // The cursor shows in menus only while the player uses the mouse or keyboard.
    PlayerOwner->SetShowMouseCursor(bOpen&&Model->Device()==SoraUI::EDevice::KeyboardMouse);
}
void ASoraHUD::FocusFrontEnd()
{
    FInputModeUIOnly Input;
    Input.SetWidgetToFocus(FrontEndWidget);
    Input.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    PlayerOwner->SetInputMode(Input);
}
UFont* ASoraHUD::JapaneseFontObject()
{
    if(!JapaneseFont)
    {
        JapaneseFont=NewObject<UFont>(this);
        JapaneseFont->FontCacheType=EFontCacheType::Runtime;
        JapaneseFont->LegacyFontSize=28;
        JapaneseFont->LegacyFontName=FName(TEXT("Regular"));
        JapaneseFont->GetMutableInternalCompositeFont()=FCompositeFont(FName(TEXT("Regular")),FPaths::ProjectContentDir()/TEXT("SourceArt/Fonts/NotoSansCJKjp-Regular.otf"),EFontHinting::Default,EFontLoadingPolicy::LazyLoad);
    }
    return JapaneseFont;
}
void ASoraHUD::Label(const FString& T,float X,float Y,float S,FLinearColor C)
{
    DrawText(T,C,X,Y,JapaneseFontObject(),S,false);
}
int32 ASoraHUD::WrappedLabel(const FString& Text,float X,float Y,float Scale,FLinearColor Color,float MaxWidth,float LineHeight,int32 MaxLines)
{
    FString Line; int32 Count=0;
    for(int32 I=0;I<Text.Len();++I)
    {
        const FString Candidate=Line+Text.Mid(I,1); float Width=0,Height=0;
        GetTextSize(Candidate,Width,Height,JapaneseFontObject(),Scale);
        if((Width>MaxWidth&&!Line.IsEmpty())||Text[I]=='\n')
        {
            Label(Line,X,Y+Count*LineHeight,Scale,Color); ++Count; Line.Empty();
            if(Count>=MaxLines) return Count;
        }
        if(Text[I]!='\n') Line+=Text.Mid(I,1);
    }
    if(!Line.IsEmpty()&&Count<MaxLines) { Label(Line,X,Y+Count*LineHeight,Scale,Color); ++Count; }
    return Count;
}
void ASoraHUD::Panel(float X,float Y,float W,float H,FLinearColor C) { DrawRect(C,X,Y,W,H); }
float ASoraHUD::LabelWidth(const FString& Text,float Scale) const
{
    float Width=0,Height=0; GetTextSize(Text,Width,Height,JapaneseFont,Scale);
    return Width;
}
UTexture2D* ASoraHUD::ResistanceLogo()
{
    if(!bResistanceLogoResolved)
    {
        ResistanceLogoTexture=LoadObject<UTexture2D>(nullptr,TEXT("/Game/Generated/UI/T_SoraResistanceLogo.T_SoraResistanceLogo"),nullptr,LOAD_NoWarn);
        bResistanceLogoResolved=true;
    }
    return ResistanceLogoTexture;
}
UTexture2D* ASoraHUD::TitleArt()
{
    if(!bTitleArtResolved)
    {
        TitleArtTexture=LoadObject<UTexture2D>(nullptr,TEXT("/Game/Generated/UI/T_NyaagyuTitle.T_NyaagyuTitle"),nullptr,LOAD_NoWarn); bTitleArtResolved=true;
    }
    return TitleArtTexture;
}
void ASoraHUD::DrawHUD()
{
    Super::DrawHUD(); if(!Canvas) return;
    auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    auto* P=Cast<ASoraPlayerCharacter>(UGameplayStatics::GetPlayerPawn(this,0)); if(!G) return;
    // The Slate front end draws every menu over the paused world. If the
    // player clicked away and focus fell back to the bare game viewport, the
    // open front end takes it back.
    if(G->bMenu)
    {
        if(FrontEndWidget&&bFrontEndHasInput&&!FrontEndWidget->HasAnyUserFocus())
        {
            const UGameViewportClient* Viewport=GetWorld()->GetGameViewport();
            const TSharedPtr<SWidget> Focused=FSlateApplication::Get().GetKeyboardFocusedWidget();
            if(!Focused.IsValid()||(Viewport&&Focused==Viewport->GetGameViewportWidget())) FocusFrontEnd();
        }
        return;
    }
    const FSoraHUDFrame Frame(*this,*G,Canvas->SizeX,Canvas->SizeY);
    if(!FSoraCatalog::Get().IsReady())
    {
        // The loader's reason is developer English; the heading carries both languages.
        const SoraText::FLine Heading=SoraText::Line(NSLOCTEXT("SoraArena.HUD","ContentError","SORA ARENA / コンテンツの読み込みエラー"));
        Label(Heading.Japanese,50,60,1,Frame.Gold);
        if(G->bEnglishSubtitles) Label(Heading.English,50,100,.6,Frame.Muted);
        Label(FSoraCatalog::Get().Error,50,G->bEnglishSubtitles?135:110,.65,Frame.Ivory);
        return;
    }
    SoraHUDPanels::DrawTopBar(Frame);
    // The chapter opens on its title card; dialogue and the round timer start
    // when it closes.
    if(const FSoraChapter* Card=G->TitleCardChapter()) { SoraHUDPanels::DrawTitleCard(Frame,*Card); return; }
    SoraHUDPanels::DrawObjective(Frame);
    SoraHUDPanels::DrawDojoLesson(Frame);
    SoraHUDPanels::DrawBoss(Frame);
    if(P) SoraHUDPanels::DrawHero(Frame,*P);
    SoraHUDPanels::DrawDialogue(Frame);
    SoraHUDPanels::DrawCaptions(Frame,P);
    SoraHUDPanels::DrawResult(Frame);
}
void SoraHUDPanels::DrawTopBar(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const float W=Frame.W,S=Frame.S;
    HUD.Panel(0,0,W,75*S,FLinearColor(.018,.035,.045,.86));
    UTexture2D* Logo=HUD.ResistanceLogo();
    if(Logo) HUD.DrawTexture(Logo,28*S,13*S,48*S,48*S,0,0,1,1,FLinearColor::White);
    // The title line is the game's name; the build note has its English
    // beneath while subtitles are on.
    HUD.Label(NSLOCTEXT("SoraArena.HUD","TopBar.Title","SORA 抵抗軍  /  猫柳生").ToString(),Logo?90*S:30*S,18*S,.9*S,Frame.Ivory);
    const SoraText::FLine Note=SoraText::Line(NSLOCTEXT("SoraArena.HUD","TopBar.OfflineBuild","オフライン開発版  |  XOR・NFT の送金は行いません"));
    HUD.Label(Note.Japanese,W-650*S,24*S,.47*S,Frame.Teal);
    if(Frame.Mode.bEnglishSubtitles) HUD.Label(Note.English,W-650*S,46*S,FMath::Max(.36f*S,.4f),Frame.Muted);
}
