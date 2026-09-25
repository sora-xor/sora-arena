#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "SoraHUD.generated.h"
class UFont;
class UTexture2D;

// Canvas HUD. DrawHUD picks the screen; each panel is drawn by a function in
// Private/HUD (menu, story and combat panels) with these shared helpers.
UCLASS()
class SORAARENA_API ASoraHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
    // Text in the bundled Noto Sans CJK JP font.
    void Label(const FString& Text,float X,float Y,float Scale,FLinearColor Color);
    int32 WrappedLabel(const FString& Text,float X,float Y,float Scale,FLinearColor Color,float MaxWidth,float LineHeight,int32 MaxLines = 3);
    void Panel(float X,float Y,float W,float H,FLinearColor Color);
    float LabelWidth(const FString& Text,float Scale) const;
    // Imported UI art, resolved once; null before the art is imported.
    UTexture2D* ResistanceLogo();
    UTexture2D* TitleArt();
private:
    UPROPERTY() TObjectPtr<UFont> JapaneseFont;
    UPROPERTY() TObjectPtr<UTexture2D> TitleArtTexture;
    UPROPERTY() TObjectPtr<UTexture2D> ResistanceLogoTexture;
    bool bTitleArtResolved = false;
    bool bResistanceLogoResolved = false;
};
