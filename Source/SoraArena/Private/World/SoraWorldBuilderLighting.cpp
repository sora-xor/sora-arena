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
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "SoraCatalog.h"

namespace
{
// Look-dev only: volumetric fog off Windows (the Mac's SM6 path) stays off by
// default until its paired images and GPU cost are measured.
TAutoConsoleVariable<int32> CVarLookDevVolumetricFog(TEXT("sora.LookDevVolumetricFog"),0,
    TEXT("1: volumetric fog on non-Windows renderers too (look-dev; unmeasured)."));

// Chapter 1's authored day (docs/campaign/chapter-01.md section 2): the sun's
// compass bearing and elevation (degrees; 90 is +X, east), its colour
// temperature, and whether the estate's overcast dome or the atmosphere is the
// sky. Only direction, colour and sky change: stealth reads the key's
// intensity, which, like the sky light, exposure and fog, stays the map's own.
struct FBeatLight { const TCHAR* Beat; float Azimuth,Elevation,Kelvin; bool bAtmosphere; };
const FBeatLight BeatLights[]={
    {TEXT("ch01.b01"), 72.f, 2.f,4500.f,true},    // dawn through thin cloud, raking through the east windows
    {TEXT("ch01.b02"), 78.f, 8.f,5200.f,false},   // thin high overcast
    {TEXT("ch01.b03"), 86.f,20.f,5200.f,false},
    {TEXT("ch01.b04"), 95.f,35.f,5200.f,false},
    {TEXT("ch01.b05"),104.f,45.f,5200.f,true},    // clearing
    {TEXT("ch01.b06"),118.f,55.f,5400.f,true},
    {TEXT("ch01.b07"),139.f,62.f,5600.f,true},
    {TEXT("ch01.b08"),155.f,67.f,5600.f,true},
    {TEXT("ch01.b09"),200.f,69.f,6000.f,true},
    {TEXT("ch01.b10"),255.f,40.f,4500.f,true},
    {TEXT("ch01.b11"),265.f,28.f,3800.f,true},    // golden hour: low western side light
    {TEXT("ch01.b12"),275.f,16.f,3500.f,true},
    {TEXT("ch01.b13"),288.f, 1.f,3000.f,true},    // sunset
};
}

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
    const FLinearColor SunColor=bEstate?FLinearColor(.83f,.89f,1.f):FLinearColor(1.f,.82f,.66f);
    Sun->SetLightColor(SunColor);
    auto* SunComponent=CastChecked<UDirectionalLightComponent>(Sun->GetLightComponent());
    SunComponent->SetAtmosphereSunLight(true);
    if(bEstate) SunComponent->SetLightSourceAngle(6.f);
    DecorActors.Add(Sun);
    RigSun=Sun;
    RigDefaultRotation=Sun->GetActorRotation();
    RigDefaultColor=SunColor;
    RigDefaultKeyIntensity=SunComponent->Intensity;
    RigDefaultSourceAngle=SunComponent->LightSourceAngle;
    RigDome=nullptr;
    RigOvercast=nullptr;
    RigBeat.Reset();

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
    RigSky=Sky;
    RigDefaultSkyIntensity=Sky->GetLightComponent()->Intensity;
    if(MapId==0)
    {
        if(auto* HDRI=LoadObject<UTextureCube>(nullptr,TEXT("/Game/Generated/Environment/Textures/T_NyaagyuOvercast.T_NyaagyuOvercast"),nullptr,LOAD_NoWarn))
        {
            Sky->GetLightComponent()->bRealTimeCapture=false; Sky->GetLightComponent()->SourceType=SLS_SpecifiedCubemap;
            Sky->GetLightComponent()->SetCubemap(HDRI);
            RigOvercast=HDRI;
            if(auto* SkyMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Environment/M_Nyaagyu_Sky.M_Nyaagyu_Sky"),nullptr,LOAD_NoWarn))
            {
                auto* Dome=Shape(this,RootComponent,TEXT("OvercastSky"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(3000),FLinearColor::White);
                Dome->SetMaterial(0,SkyMaterial); Dome->SetCastShadow(false); Pieces.Add(Dome);
                RigDome=Dome;
            }
        }
    }
    Sky->GetLightComponent()->RecaptureSky();
    bRigDefaultRealTimeCapture=Sky->GetLightComponent()->bRealTimeCapture;
    bRigAuthored=false;

    auto* Fog=GetWorld()->SpawnActor<AExponentialHeightFog>();
    auto* FogComponent=Fog->GetComponent();
    FogComponent->SetFogDensity(bEstate?.0045f:.0035f);
    FogComponent->SetStartDistance(350.f);
    FogComponent->SetFogMaxOpacity(.58f);
    FogComponent->SetFogInscatteringColor(bEstate?FLinearColor(.38f,.43f,.47f):FLinearColor(.25f,.30f,.35f));
    // Volumetric fog on Windows; elsewhere (the Mac's SM6 path) only as the
    // explicit look-dev option, until it is measured.
    if(PLATFORM_WINDOWS||CVarLookDevVolumetricFog.GetValueOnGameThread()!=0)
    {
        FogComponent->SetVolumetricFog(true);
        FogComponent->SetVolumetricFogDistance(4500.f);
        FogComponent->SetVolumetricFogStartDistance(350.f);
        FogComponent->SetVolumetricFogScatteringDistribution(.35f);
        FogComponent->SetVolumetricFogExtinctionScale(.55f);
    }
    DecorActors.Add(Fog);
    RigFog=Fog;

    auto* Grade=GetWorld()->SpawnActor<APostProcessVolume>();
    RigGrade=Grade;
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

void ASoraWorldBuilder::BeatLight(const FSoraBeat& Beat)
{
    // One rig for every beat and retry: re-aimed only when the beat changes,
    // and a beat without an authored light leaves the map's rig as built.
    if(!RigSun||!RigSky||Beat.Id==RigBeat) return;
    RigBeat=Beat.Id;
    const FBeatLight* Light=nullptr;
    for(const FBeatLight& Entry:BeatLights)
        if(Beat.Id==Entry.Beat) { Light=&Entry; break; }
    const bool bNoticeNight=Beat.Id==TEXT("ch03.b10")||Beat.Id==TEXT("ch03.b11")||Beat.Id==TEXT("ch03.b12");
    const FBeatLight Night={TEXT("notice-night"),300.f,35.f,9000.f,false};
    if(bNoticeNight)Light=&Night;
    if(!Light&&!bRigAuthored) return;
    auto* Key=CastChecked<UDirectionalLightComponent>(RigSun->GetLightComponent());
    USkyLightComponent* Sky=RigSky->GetLightComponent();
    // A broad cool cloud key, not a visible sun. Its actual illuminance
    // enters USoraStealth::LightAt; the window pools use real point lights.
    Key->SetIntensity(bNoticeNight?3.f:RigDefaultKeyIntensity);
    Key->SetLightSourceAngle(bNoticeNight?12.f:RigDefaultSourceAngle);
    Key->SetAtmosphereSunLight(!bNoticeNight);
    Sky->SetIntensity(bNoticeNight?.08f:RigDefaultSkyIntensity);
    Sky->SetLightColor(bNoticeNight?FLinearColor::MakeFromColorTemperature(9000.f):FLinearColor::White);
    if(RigGrade)
    {
        auto& Grade=RigGrade->Settings;
        Grade.bOverride_AutoExposureMinBrightness=bNoticeNight;
        Grade.bOverride_AutoExposureMaxBrightness=bNoticeNight;
        // One stop of adaptation within the night zone; looking at the sky
        // cannot erase its footholds, nor can looking down reveal every shadow.
        // Match UE's white-point conversion if extended EV100 units are on.
        const auto* Extended=IConsoleManager::Get().FindConsoleVariable(TEXT("r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange"));
        const auto* Lens=IConsoleManager::Get().FindConsoleVariable(TEXT("r.EyeAdaptation.LensAttenuation"));
        const float LuminanceMax=.78f/FMath::Max(Lens?Lens->GetFloat():.78f,.01f);
        const auto Units=[&](float L){return Extended&&Extended->GetInt()!=0?FMath::Log2(L/LuminanceMax):L;};
        Grade.AutoExposureMinBrightness=Units(.06f);
        Grade.AutoExposureMaxBrightness=Units(.12f);
    }
    const bool bAtmosphere=Light&&Light->bAtmosphere;
    if(Light)
    {
        // The key travels from the sun's bearing towards the ground.
        const float A=FMath::DegreesToRadians(Light->Azimuth),E=FMath::DegreesToRadians(Light->Elevation);
        const FVector Toward=-FVector(FMath::Sin(A)*FMath::Cos(E),FMath::Cos(A)*FMath::Cos(E),FMath::Sin(E));
        RigSun->SetActorRotation(Toward.Rotation());
        Key->SetLightColor(FLinearColor::White);
        Key->SetUseTemperature(true);
        Key->SetTemperature(Light->Kelvin);
    }
    else
    {
        RigSun->SetActorRotation(RigDefaultRotation);
        Key->SetUseTemperature(false);
        Key->SetLightColor(RigDefaultColor);
    }
    bRigAuthored=Light!=nullptr;
    // The sky: the estate's overcast dome and HDRI, or the atmosphere captured
    // once for this beat (never per tick); unauthored, the map's own capture.
    if(RigDome) RigDome->SetVisibility(!bAtmosphere);
    if(bNoticeNight)
    {
        // Reuse the existing licensed overcast capture as dim diffuse light.
        // The atmospheric background has no sun; no bright daytime dome is shown.
        Sky->bRealTimeCapture=false;
        if(auto* Cloud=LoadObject<UTextureCube>(nullptr,TEXT("/Game/Generated/Environment/Textures/T_NyaagyuOvercast.T_NyaagyuOvercast"),nullptr,LOAD_NoWarn))
        {Sky->SourceType=SLS_SpecifiedCubemap;Sky->SetCubemap(Cloud);}
        else Sky->SourceType=SLS_CapturedScene;
    }
    else if(bAtmosphere)
    {
        Sky->bRealTimeCapture=false;
        Sky->SourceType=SLS_CapturedScene;
    }
    else if(RigOvercast)
    {
        Sky->bRealTimeCapture=false;
        Sky->SourceType=SLS_SpecifiedCubemap;
        Sky->SetCubemap(RigOvercast);
    }
    else
    {
        Sky->bRealTimeCapture=bRigDefaultRealTimeCapture;
        Sky->SourceType=SLS_CapturedScene;
    }
    Sky->RecaptureSky();
}
