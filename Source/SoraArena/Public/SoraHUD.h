#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "SoraHUD.generated.h"
UCLASS()
class SORAARENA_API ASoraHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
private:
    UPROPERTY() TObjectPtr<class UFont> JapaneseFont;
    UPROPERTY() TObjectPtr<class UTexture2D> TitleArt;
    UPROPERTY() TObjectPtr<class UTexture2D> ResistanceLogo;
    bool bTitleArtResolved = false;
    bool bResistanceLogoResolved = false;
    void Label(const FString& Text,float X,float Y,float Scale,FLinearColor Color);
    int32 WrappedLabel(const FString& Text,float X,float Y,float Scale,FLinearColor Color,float MaxWidth,float LineHeight,int32 MaxLines = 3);
    void Panel(float X,float Y,float W,float H,FLinearColor Color);
};
