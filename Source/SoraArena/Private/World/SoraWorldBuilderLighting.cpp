#include "SoraWorldBuilder.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/TextureCube.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"

void ASoraWorldBuilder::Lighting(int32 MapId)
{
    const bool bEstate=MapId==0;
    const bool bOccupiedStreet=MapId==1;
    auto* Sun=GetWorld()->SpawnActor<ADirectionalLight>(FVector(0,0,1200),FRotator(bOccupiedStreet?-10.f:-28.f,-35.f,0));
    Sun->SetMobility(EComponentMobility::Movable);
    // The Estate's earlier 0.45-lux key left roofs and tabby faces nearly
    // black against a bright overcast dome. A packaged M1 diagnostic A/B at
    // the same camera found 25 lux readable while 250 washed out the paving.
    Sun->GetLightComponent()->SetIntensity(bEstate?25.f:(bOccupiedStreet?1.8f:4.f));
    Sun->SetLightColor(bEstate?FLinearColor(.83f,.89f,1.f):FLinearColor(1.f,.82f,.66f));
    auto* SunComponent=CastChecked<UDirectionalLightComponent>(Sun->GetLightComponent());
    SunComponent->SetAtmosphereSunLight(true);
    if(bEstate) SunComponent->SetLightSourceAngle(6.f);
    DecorActors.Add(Sun);

    // The atmosphere must exist before the movable sky capture. The estate
    // uses its licensed overcast HDRI for diffuse/reflection lighting instead.
    auto* Atmosphere=GetWorld()->SpawnActor<ASkyAtmosphere>();
    if(!bEstate) Atmosphere->GetComponent()->SetMieScatteringScale(bOccupiedStreet?2.f:1.35f);
    DecorActors.Add(Atmosphere);
    auto* Sky=GetWorld()->SpawnActor<ASkyLight>();
    Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Sky->GetLightComponent()->bRealTimeCapture=true;
    Sky->GetLightComponent()->SetIntensity(bEstate?.65f:.7f);
    DecorActors.Add(Sky);
    if(MapId==0)
    {
        if(auto* HDRI=LoadObject<UTextureCube>(nullptr,TEXT("/Game/Generated/Environment/Textures/T_NyaagyuOvercast.T_NyaagyuOvercast"),nullptr,LOAD_NoWarn))
        {
            Sky->GetLightComponent()->bRealTimeCapture=false; Sky->GetLightComponent()->SourceType=SLS_SpecifiedCubemap;
            Sky->GetLightComponent()->SetCubemap(HDRI);
            if(auto* SkyMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Environment/M_Nyaagyu_Sky.M_Nyaagyu_Sky"),nullptr,LOAD_NoWarn))
            {
                auto* Dome=Shape(this,RootComponent,TEXT("OvercastSky"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(3000),FLinearColor::White);
                Dome->SetMaterial(0,SkyMaterial); Dome->SetCastShadow(false); Pieces.Add(Dome);
            }
        }
    }
    Sky->GetLightComponent()->RecaptureSky();

    auto* Fog=GetWorld()->SpawnActor<AExponentialHeightFog>();
    auto* FogComponent=Fog->GetComponent();
    FogComponent->SetFogDensity(bEstate?.0045f:.0035f);
    FogComponent->SetStartDistance(350.f);
    FogComponent->SetFogMaxOpacity(.58f);
    FogComponent->SetFogInscatteringColor(bEstate?FLinearColor(.38f,.43f,.47f):FLinearColor(.25f,.30f,.35f));
#if PLATFORM_WINDOWS
    FogComponent->SetVolumetricFog(true);
    FogComponent->SetVolumetricFogDistance(4500.f);
    FogComponent->SetVolumetricFogStartDistance(350.f);
    FogComponent->SetVolumetricFogScatteringDistribution(.35f);
    FogComponent->SetVolumetricFogExtinctionScale(.55f);
#endif
    DecorActors.Add(Fog);

    auto* Grade=GetWorld()->SpawnActor<APostProcessVolume>();
    Grade->bUnbound=true;
    auto& Settings=Grade->Settings;
    // Keep silhouettes readable and prevent the sky and lanterns from driving
    // large exposure swings as the first-person camera turns during combat.
    Settings.bOverride_AutoExposureMethod=1;
    Settings.AutoExposureMethod=AEM_Histogram;
    Settings.bOverride_AutoExposureLowPercent=1;
    Settings.AutoExposureLowPercent=12.f;
    Settings.bOverride_AutoExposureHighPercent=1;
    Settings.AutoExposureHighPercent=88.f;
    Settings.bOverride_AutoExposureSpeedUp=1;
    Settings.AutoExposureSpeedUp=1.2f;
    Settings.bOverride_AutoExposureSpeedDown=1;
    Settings.AutoExposureSpeedDown=.7f;
    Settings.bOverride_AutoExposureBias=1;
    Settings.AutoExposureBias=bEstate?-.45f:(bOccupiedStreet?-.3f:0.f);
    Settings.bOverride_ColorSaturation=1;
    Settings.ColorSaturation=FVector4(.96f,.96f,.96f,1.f);
    Settings.bOverride_BloomIntensity=1;
    Settings.BloomIntensity=bOccupiedStreet?.28f:.2f;
    DecorActors.Add(Grade);
}
