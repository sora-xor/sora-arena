#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "SoraHUD.generated.h"
class FSoraInputDeviceTracker;
class SSoraFrontEnd;
class UFont;
class USoraFrontEnd;
class UTexture2D;

// The game's HUD. Play is drawn on the canvas: DrawHUD picks the panels, each
// drawn by a function in Private/HUD (story and combat panels) with these
// shared helpers. Every menu is the Slate front end (Private/UI), which this
// HUD adds to the viewport and hands keyboard, pad and mouse focus while a
// screen is open.
UCLASS()
class SORAARENA_API ASoraHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void DrawHUD() override;
    // Text in the bundled Noto Sans CJK JP font.
    void Label(const FString& Text,float X,float Y,float Scale,FLinearColor Color);
    int32 WrappedLabel(const FString& Text,float X,float Y,float Scale,FLinearColor Color,float MaxWidth,float LineHeight,int32 MaxLines = 3);
    void Panel(float X,float Y,float W,float H,FLinearColor Color);
    float LabelWidth(const FString& Text,float Scale);
    // The runtime Noto Sans CJK JP font, shared by the canvas and the front end.
    UFont* JapaneseFontObject();
    // Imported UI art, resolved once; null before the art is imported.
    UTexture2D* ResistanceLogo();
    UTexture2D* TitleArt();
private:
    UPROPERTY() TObjectPtr<UFont> JapaneseFont;
    UPROPERTY() TObjectPtr<UTexture2D> TitleArtTexture;
    UPROPERTY() TObjectPtr<UTexture2D> ResistanceLogoTexture;
    bool bTitleArtResolved = false;
    bool bResistanceLogoResolved = false;
    TSharedPtr<SSoraFrontEnd> FrontEndWidget;
    TSharedPtr<FSoraInputDeviceTracker> DeviceTracker;
    TWeakObjectPtr<USoraFrontEnd> FrontEnd;
    FDelegateHandle FrontEndChanged;
    bool bFrontEndHasInput = false;
    // Redraws the front end and gives input to it while open, to play otherwise.
    void SyncFrontEnd();
    void FocusFrontEnd();
};
