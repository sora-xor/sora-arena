#include "SoraHUD.h"
#include "HUD/SoraHUDPanels.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "Engine/Canvas.h"
#include "Engine/Font.h"
#include "Engine/Texture2D.h"
#include "Fonts/CompositeFont.h"
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
    Ivory=FLinearColor(.93,.90,.80); Gold=FLinearColor(.94,.65,.21); Teal=FLinearColor(.22,.81,.75); Muted=FLinearColor(.56,.63,.65);
}
void ASoraHUD::Label(const FString& T,float X,float Y,float S,FLinearColor C)
{
    if(!JapaneseFont)
    {
        JapaneseFont=NewObject<UFont>(this);
        JapaneseFont->FontCacheType=EFontCacheType::Runtime;
        JapaneseFont->LegacyFontSize=28;
        JapaneseFont->LegacyFontName=FName(TEXT("Regular"));
        JapaneseFont->GetMutableInternalCompositeFont()=FCompositeFont(FName(TEXT("Regular")),FPaths::ProjectContentDir()/TEXT("SourceArt/Fonts/NotoSansCJKjp-Regular.otf"),EFontHinting::Default,EFontLoadingPolicy::LazyLoad);
    }
    DrawText(T,C,X,Y,JapaneseFont,S,false);
}
int32 ASoraHUD::WrappedLabel(const FString& Text,float X,float Y,float Scale,FLinearColor Color,float MaxWidth,float LineHeight,int32 MaxLines)
{
    FString Line; int32 Count=0;
    for(int32 I=0;I<Text.Len();++I)
    {
        const FString Candidate=Line+Text.Mid(I,1); float Width=0,Height=0;
        GetTextSize(Candidate,Width,Height,JapaneseFont,Scale);
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
    const FSoraHUDFrame Frame(*this,*G,Canvas->SizeX,Canvas->SizeY);
    if(!FSoraCatalog::Get().IsReady()) { Label(TEXT("SORA ARENA / コンテンツの読み込みエラー"),50,60,1,Frame.Gold); Label(FSoraCatalog::Get().Error,50,110,.65,Frame.Ivory); return; }
    SoraHUDPanels::DrawTopBar(Frame);
    if(G->bMenu) { SoraHUDPanels::DrawMenu(Frame); return; }
    // The chapter opens on its title card; dialogue and the round timer start
    // when it closes.
    if(const FSoraChapter* Card=G->TitleCardChapter()) { SoraHUDPanels::DrawTitleCard(Frame,*Card); return; }
    SoraHUDPanels::DrawObjective(Frame);
    SoraHUDPanels::DrawDojoLesson(Frame);
    SoraHUDPanels::DrawBoss(Frame);
    if(P) SoraHUDPanels::DrawStealth(Frame,*P);
    if(P) SoraHUDPanels::DrawHero(Frame,*P);
    SoraHUDPanels::DrawDialogue(Frame);
    SoraHUDPanels::DrawResult(Frame);
}
void SoraHUDPanels::DrawTopBar(const FSoraHUDFrame& Frame)
{
    ASoraHUD& HUD=Frame.HUD;
    const float W=Frame.W,S=Frame.S;
    HUD.Panel(0,0,W,75*S,FLinearColor(.018,.035,.045,.86));
    UTexture2D* Logo=HUD.ResistanceLogo();
    if(Logo) HUD.DrawTexture(Logo,28*S,13*S,48*S,48*S,0,0,1,1,FLinearColor::White);
    HUD.Label(TEXT("SORA 抵抗軍  /  猫柳生"),Logo?90*S:30*S,18*S,.9*S,Frame.Ivory);
    HUD.Label(TEXT("オフライン開発版  |  XOR・NFT の送金は行いません"),W-650*S,24*S,.47*S,Frame.Teal);
}
