#include "SoraWorldBuilder.h"
#include "SoraLanternWorkshopRules.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"

void ASoraWorldBuilder::BuildLanternWorkshop()
{
    namespace R=SoraLanternWorkshopRules;
    int Index=0;
    for(const auto& S:R::Solids())
    {
        const TCHAR* Role=S.Surface==R::ESurface::Stone?TEXT("Stone"):
            S.Surface==R::ESurface::Soil?TEXT("Soil"):TEXT("Timber");
        Box(FString::Printf(TEXT("LanternWorkshopSolid%d"),Index++),FVector(S.X,S.Y,S.Z),
            FVector(S.SX,S.SY,S.SZ),FLinearColor(.31f,.25f,.18f),true,FRotator::ZeroRotator,Role);
    }
    WorkshopDoor=Box(TEXT("WorkshopBackDoor"),FVector(1900,-1500,152.5),FVector(140,12,215),
        FLinearColor(.25f,.18f,.10f),true,FRotator::ZeroRotator,TEXT("Timber"));
    WorkshopSeal=Box(TEXT("WorkshopDebtSeal"),FVector(1900,-1508,145),FVector(26,2,52),FLinearColor(.03f,.8f,.9f),false);
    WorkshopBar=Box(TEXT("WorkshopDoorBar"),FVector(1900,-1490,140),FVector(160,8,10),
        FLinearColor(.22f,.15f,.08f),false,FRotator::ZeroRotator,TEXT("Timber"));
    WorkshopDoor->SetMobility(EComponentMobility::Movable);
    ShowWorkshopDoor(false,false);
    for(int I=0;I<2;++I)
    {
        const FVector P(1880+280*I,-390,210);
        Box(FString::Printf(TEXT("WorkshopWindowFrame%d"),I),P,FVector(160,10,130),
            FLinearColor(.18f,.12f,.07f),false,FRotator::ZeroRotator,TEXT("Timber"));
        Box(FString::Printf(TEXT("WorkshopWindowDark%d"),I),P+FVector(0,6,0),FVector(140,2,110),
            FLinearColor(.025f,.02f,.015f),false);
        auto* Pane=Box(FString::Printf(TEXT("WorkshopWindowWarm%d"),I),P+FVector(0,8,0),FVector(140,2,110),
            FLinearColor(1.f,.64f,.25f),false);
        Pane->ComponentTags.Add(TEXT("WorkshopWarmWindow"));WorkshopWindows.Add(Pane);
        auto* Light=GetWorld()->SpawnActor<APointLight>(P+FVector(0,45,0),FRotator::ZeroRotator);
        Light->Tags.Add(TEXT("WorkshopWindowLight"));
        auto* Glow=Light->PointLightComponent.Get();
        Glow->SetIntensityUnits(ELightUnits::Lumens);Glow->SetIntensity(240.f);
        Glow->SetAttenuationRadius(350.f);Glow->SetSourceRadius(35.f);
        Glow->SetUseTemperature(true);Glow->SetTemperature(2700.f);Glow->SetCastShadows(false);
        WorkshopWindowLights.Add(Light);DecorActors.Add(Light);
    }
    ShowWorkshopRestored(false);
}

void ASoraWorldBuilder::ShowWorkshopRestored(bool Restored)
{
    for(auto* Pane:WorkshopWindows)if(IsValid(Pane))Pane->SetVisibility(Restored);
    for(auto* Light:WorkshopWindowLights)if(IsValid(Light))Light->PointLightComponent->SetVisibility(Restored);
}

void ASoraWorldBuilder::ShowWorkshopDoor(bool FightComplete,bool SealCut)
{
    if(!IsValid(WorkshopDoor))return;
    // After the defense the panel parks beside the opening for the rest of
    // the chapter. Checkpoint restoration derives this from completed beats.
    WorkshopDoor->SetWorldLocation(FVector(FightComplete?2046:1900,-1500,152.5));
    if(IsValid(WorkshopSeal))WorkshopSeal->SetVisibility(!FightComplete&&!SealCut);
    if(IsValid(WorkshopBar))WorkshopBar->SetVisibility(!FightComplete&&SealCut);
}
