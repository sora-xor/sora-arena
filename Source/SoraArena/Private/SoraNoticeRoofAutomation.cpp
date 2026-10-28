#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraWorldBuilder.h"
#include "SoraEnemy.h"
#include "SoraNoticeSquareRules.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/PointLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "ProceduralMeshComponent.h"

namespace SoraNoticeRoofTest
{
using SoraFieldcraftAutomation::FBeatWorld;
bool Controls(FBeatWorld& W)
{
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    return W.Test.TestTrue(TEXT("The authored introduction releases controls"),W.Mode()->IsPlaying());
}
UStaticMeshComponent* Part(FBeatWorld& W,const TCHAR* Name)
{
    TArray<UStaticMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
    for(auto* P:Parts)if(P->GetName().StartsWith(Name))return P;
    return nullptr;
}
int Bodies(FBeatWorld& W)
{
    TArray<UProceduralMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
    int Count=0;for(auto* P:Parts)if(P->GetName().StartsWith(TEXT("NoticeMoneyChangerBody")))++Count;
    return Count;
}
ASoraEnemy* Marksman(FBeatWorld& W,bool RemoveOthers)
{
    ASoraEnemy* Mark=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(It->ArchetypeId()==TEXT("marksman"))Mark=*It;
        else if(RemoveOthers)It->Destroy();
    }
    return Mark;
}
FVector Feet(FBeatWorld& W)
{
    return W.Hero()->GetActorLocation()-FVector(0,0,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}
bool Walk(FBeatWorld& W,FVector2D Point,bool Controller)
{
    bool Grounded=true;float Largest=0;
    for(int I=0;I<1800&&FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),Point)>12;++I)
    {
        W.Look((FVector(Point,0)-W.Hero()->GetActorLocation()).GetSafeNormal2D().Rotation());
        const FVector Before=W.Hero()->GetActorLocation();
        if(!(Controller?W.World->InjectAxis(EKeys::Gamepad_LeftY,.6f):W.World->InjectKey(EKeys::W,IE_Pressed))||!W.Tick(1))return false;
        Grounded&=W.Hero()->GetCharacterMovement()->IsMovingOnGround();
        Largest=FMath::Max(Largest,float(FVector::Dist(Before,W.Hero()->GetActorLocation())));
    }
    if(!(Controller?W.World->InjectAxis(EKeys::Gamepad_LeftY,0):W.World->InjectKey(EKeys::W,IE_Released))||!W.Tick(4))return false;
    W.Test.AddInfo(FString::Printf(TEXT("Walk toward %s: feet %s, maximum step %.3f cm, grounded %d"),*Point.ToString(),*Feet(W).ToString(),Largest,Grounded));
    return W.Test.TestTrue(TEXT("The route segment uses continuous grounded movement"),Grounded&&Largest<15&&
        FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),Point)<30);
}
bool Flight(FBeatWorld& W,const FSoraLadder& L,bool Up,bool Controller,bool Pause=false)
{
    W.Look(FRotator(0,L.Yaw+(Up?0:180),0));
    if(!W.Test.TestTrue(TEXT("The physical ladder end is usable"),W.Fieldcraft()->Readout(*W.Hero()).bAtLadder)||
       !W.Press(Controller?EKeys::Gamepad_FaceButton_Bottom:EKeys::J)||
       !W.Test.TestTrue(TEXT("Mapped jump takes the ladder"),W.Fieldcraft()->IsOnLadder()))return false;
    float Largest=0;
    for(int I=0;I<600&&W.Fieldcraft()->IsOnLadder();++I)
    {
        const FVector Before=W.Hero()->GetActorLocation();
        if(!W.Tick(1))return false;
        Largest=FMath::Max(Largest,float(FVector::Dist(Before,W.Hero()->GetActorLocation())));
        if(Pause&&I==40)
        {
            if(!W.Press(EKeys::Escape))return false;
            const FVector Held=W.Hero()->GetActorLocation();
            if(!W.Tick(120)||!W.Test.TestTrue(TEXT("Pause holds the real ladder position"),Held.Equals(W.Hero()->GetActorLocation(),.01f))||!W.Press(EKeys::Escape))return false;
        }
    }
    W.Test.AddInfo(FString::Printf(TEXT("%s %s: feet %s, maximum step %.3f cm"),*L.Id,Up?TEXT("up"):TEXT("down"),*Feet(W).ToString(),Largest));
    return W.Test.TestTrue(TEXT("Ladder movement respects its 150 cm/s limit"),Largest<=2.6f);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeRoofSolidsTest,"SoraArena.Campaign.NoticeSquare.RoofSolids",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeRoofSolidsTest::RunTest(const FString&)
{
    using namespace SoraNoticeRoofTest;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("NoticeRoofSolids"),2,9);
    if(!W.Start()||!Controls(W))return false;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)It->Destroy();
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(NoticeRoofSolids),false,W.Hero());
    for(const FVector P:{FVector(900,800,750),FVector(960,400,560),FVector(600,350,536.25),
        FVector(650,1250,536.25),FVector(650,1350,488.75),FVector(500,1200,320)})
    {
        FHitResult Hit;
        const bool Found=W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,P+FVector(0,0,500),P-FVector(0,0,100),ECC_Visibility,Query);
        AddInfo(FString::Printf(TEXT("Roof probe %s hit %s at %s"),*P.ToString(),*GetNameSafe(Hit.GetComponent()),*Hit.ImpactPoint.ToString()));
        TestTrue(TEXT("The visible roof has the specified physical surface"),Found&&FMath::Abs(Hit.ImpactPoint.Z-P.Z)<.2);
    }
    FHitResult Wall;
    TestTrue(TEXT("The gabled building is closed to street movement"),W.World->GetTestWorld()->LineTraceSingleByChannel(
        Wall,FVector(500,1000,100),FVector(700,1000,100),ECC_Visibility,Query)&&FMath::Abs(Wall.ImpactPoint.X-600)<.2);
    const auto* Capsule=W.Hero()->GetCapsuleComponent();
    FCollisionObjectQueryParams Solids;Solids.AddObjectTypesToQuery(ECC_WorldStatic);Solids.AddObjectTypesToQuery(ECC_WorldDynamic);
    for(const auto& L:W.Craft().Ladders)
    {
        const FVector Foot(L.Foot,L.BaseHeightCm+Capsule->GetScaledCapsuleHalfHeight()+2.15f);
        const FVector Above=Foot+FVector(0,0,L.RiseCm()),Top=Above+FRotator(0,L.Yaw,0).Vector()*150;
        for(const auto Segment:{TPair<FVector,FVector>(Foot,Above),TPair<FVector,FVector>(Above,Top)})
        {
            FHitResult Hit;
            const bool Blocked=W.World->GetTestWorld()->SweepSingleByObjectType(Hit,Segment.Key,Segment.Value,FQuat::Identity,
                Solids,
                FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),Query);
            if(Blocked)AddInfo(FString::Printf(TEXT("%s blocked by %s at %s"),*L.Id,*GetNameSafe(Hit.GetComponent()),*Hit.Location.ToString()));
            TestFalse(TEXT("A full standing capsule clears the authored ladder segments"),Blocked);
        }
    }
    TestEqual(TEXT("Only the board canopy amplifies steps"),W.Stealth()->SurfaceAt(FVector(500,1200,322)).StepPermille,1500);
    TestEqual(TEXT("Kawara does not inherit board noise"),W.Stealth()->SurfaceAt(FVector(900,800,752)).StepPermille,1000);
    TestEqual(TEXT("The building consists of two closed convex halves"),Bodies(W),2);
    TestNull(TEXT("The world roof does not stage the old floating slab"),Part(W,TEXT("Roof_ladder_b10")));
    // Removing physical support is isolated from enemy injury: a hit is
    // correctly allowed to release the grip and must not obscure this check.
    W.Stand(FVector(500,1750,0),-90);
    if(!W.Tick(10)||!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Jump"),EKeys::J)||!W.Press(EKeys::Escape))return false;
    const auto A=W.Craft().Ladders[0],B=W.Craft().Ladders[1];
    if(!Walk(W,A.Foot,false)||!Flight(W,A,true,false)||!W.Tick(5)||!Walk(W,B.Foot,false))return false;
    auto* Roof=Part(W,TEXT("NoticeMoneyChangerRoofNorth"));
    if(!TestNotNull(TEXT("The real upper roof can be removed in the support fixture"),Roof))return false;
    const auto Collision=Roof->GetCollisionEnabled();Roof->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(!Flight(W,B,true,false))return false;
    FFindFloorResult Floor;W.Hero()->GetCharacterMovement()->FindFloor(W.Hero()->GetActorLocation(),Floor,false);
    AddInfo(FString::Printf(TEXT("Removed roof: held=%d reached=%d released=%d floor=%s distance=%.3f feet=%s"),
        W.Fieldcraft()->IsOnLadder(),W.Raised(TEXT("roof_reached:")+B.Id),W.Raised(TEXT("ladder_release:")+B.Id),
        *GetNameSafe(Floor.HitResult.GetComponent()),Floor.FloorDist,*Feet(W).ToString()));
    TestTrue(TEXT("The missing pitched roof cannot award arrival"),W.Fieldcraft()->IsOnLadder()&&!W.Raised(TEXT("roof_reached:")+B.Id));
    Roof->SetCollisionEnabled(Collision);
    if(!W.Tick(10))return false;
    TestTrue(TEXT("Restoring the roof completes the held climb exactly once"),!W.Fieldcraft()->IsOnLadder()&&
        W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&W.Count(*(TEXT("roof_reached:")+B.Id))==1);
    return !HasAnyErrors();
}

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FSoraNoticeRoofRouteTest,"SoraArena.Campaign.NoticeSquare.RoofRoute",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
void FSoraNoticeRoofRouteTest::GetTests(TArray<FString>& Names,TArray<FString>& Commands)const
{
    Names.Add(TEXT("Keyboard"));Commands.Add(TEXT("Keyboard"));
    Names.Add(TEXT("Controller"));Commands.Add(TEXT("Controller"));
}
bool FSoraNoticeRoofRouteTest::RunTest(const FString& Parameters)
{
    using namespace SoraNoticeRoofTest;
    const bool Controller=Parameters==TEXT("Controller");
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,Controller?TEXT("NoticeRoofPad"):TEXT("NoticeRoofKeys"),2,9);
    if(!W.Start()||!Controls(W))return false;
    ASoraEnemy* Mark=Marksman(W,true);
    if(!TestNotNull(TEXT("The actual ridge marksman is live"),Mark))return false;
    AddInfo(TEXT("Only the initial street fixture is placed. Six other guards are removed; the marksman's normal senses and scan remain active. This qualifies traversal and rear takedown, not seven-guard stealth difficulty."));
    W.Harden();W.Stand(FVector(500,1750,0),-90);
    if(!W.Tick(10))return false;
    if(!Controller&&(!W.Press(EKeys::Escape)||!TestTrue(TEXT("The menu permits rebinding Jump"),W.Hero()->RemapCombatAction(TEXT("Jump"),EKeys::J))||!W.Press(EKeys::Escape)))return false;
    const auto A=W.Craft().Ladders[0],B=W.Craft().Ladders[1];
    if(!Walk(W,A.Foot,Controller)||!Flight(W,A,true,Controller,true)||!W.Tick(5)||
       !TestTrue(TEXT("The first flight ends on its supported canopy"),!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet(W).Z-322.15)<1)||
       !Walk(W,B.Foot,Controller))return false;
    if(!Flight(W,B,true,Controller))return false;
    if(!TestTrue(TEXT("The second flight finishes on the real roof"),!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround())||
       !W.Press(Controller?EKeys::Gamepad_RightThumbstick:EKeys::C)||!W.Tick(3))return false;
    for(const FVector2D Point:{FVector2D(1100,1000),FVector2D(1100,800),FVector2D(1010,800)})if(!Walk(W,Point,Controller))return false;
    W.LookAt(Mark->GetActorLocation());
    if(!TestTrue(TEXT("The east approach offers a rear takedown on the live scanning marksman"),W.Stealth()->TakedownTarget(*W.Hero())==Mark)||
       !W.Press(Controller?EKeys::Gamepad_FaceButton_Right:EKeys::RightMouseButton)||!W.Tick(180)||
       !TestTrue(TEXT("The mapped melee input completes the lethal takedown"),Mark->IsBody()&&!Mark->IsUnconscious()))return false;
    for(const FVector2D Point:{FVector2D(1100,800),FVector2D(1100,1000),FVector2D(650,1250)})if(!Walk(W,Point,Controller))return false;
    if(!W.Press(Controller?EKeys::Gamepad_RightThumbstick:EKeys::C)||!W.Tick(3)||!Flight(W,B,false,Controller)||!W.Tick(5)||
       !TestTrue(TEXT("The upper descent returns to the supported canopy"),!W.Fieldcraft()->IsOnLadder()&&FMath::Abs(Feet(W).Z-322.15)<1)||
       !Walk(W,FVector2D(500,1450),Controller)||!Flight(W,A,false,Controller)||!W.Tick(5)||!Walk(W,FVector2D(500,1750),Controller))return false;
    TestTrue(TEXT("Both return flights end at street level"),!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet(W).Z-2.15)<1);
    TestEqual(TEXT("Each roof arrival is emitted once"),W.Count(*(TEXT("roof_reached:")+B.Id)),1);
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000);
    if(!W.Tick(2)||!TestTrue(TEXT("Death offers checkpoint retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!Controls(W))return false;
    auto* Fresh=Marksman(W,false);
    TestTrue(TEXT("Retry replaces the defeated rooftop guard at the actual ridge"),Fresh&&Fresh!=Mark&&!Fresh->IsBody()&&
        FVector::Dist2D(Fresh->GetActorLocation(),FVector(900,800,0))<10&&Fresh->GetActorLocation().Z>830);
    TestTrue(TEXT("Retry restores both flights without duplicate building bodies or a held ladder"),W.Craft().Ladders.Num()==2&&Bodies(W)==2&&!W.Fieldcraft()->IsOnLadder());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeNightLightTest,"SoraArena.Campaign.NoticeSquare.NightLight",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeNightLightTest::RunTest(const FString&)
{
    using namespace SoraNoticeRoofTest;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("NoticeNightLight"),2,9);
    if(!W.Start()||!Controls(W))return false;
    ADirectionalLight* Key=nullptr;ASkyLight* Sky=nullptr;APostProcessVolume* Grade=nullptr;
    AExponentialHeightFog* Fog=nullptr;
    for(TActorIterator<ADirectionalLight> It(W.World->GetTestWorld());It;++It)Key=*It;
    for(TActorIterator<ASkyLight> It(W.World->GetTestWorld());It;++It)Sky=*It;
    for(TActorIterator<AExponentialHeightFog> It(W.World->GetTestWorld());It;++It)Fog=*It;
    for(TActorIterator<APostProcessVolume> It(W.World->GetTestWorld());It;++It)if(It->bUnbound)Grade=*It;
    if(!TestNotNull(TEXT("A single world key exists"),Key)||!TestNotNull(TEXT("The night has diffuse sky light"),Sky)||!TestNotNull(TEXT("The world exposure volume exists"),Grade)||!TestNotNull(TEXT("The night fog exists"),Fog))return false;
    auto* K=CastChecked<UDirectionalLightComponent>(Key->GetLightComponent());
    TestTrue(TEXT("Early-night key is cool, broad, dim and not an atmospheric sun"),K->bUseTemperature&&K->Temperature>=8500&&
        K->Intensity>=1&&K->Intensity<=4&&K->LightSourceAngle>=8&&!K->bAtmosphereSunLight);
    TestTrue(TEXT("A dim existing overcast capture supplies diffuse night illumination"),Sky->GetLightComponent()->SourceType==SLS_SpecifiedCubemap&&
        Sky->GetLightComponent()->Cubemap&&Sky->GetLightComponent()->Intensity>0&&Sky->GetLightComponent()->Intensity<.2f);
    TestTrue(TEXT("The notice zone explicitly bounds both ends of auto-exposure"),Grade->Settings.bOverride_AutoExposureMinBrightness&&
        Grade->Settings.bOverride_AutoExposureMaxBrightness&&Grade->Settings.AutoExposureMinBrightness<Grade->Settings.AutoExposureMaxBrightness);
    const FLinearColor NightFog=Fog->GetComponent()->FogInscatteringLuminance;
    TestTrue(TEXT("Night fog does not emit the map's bright daytime horizon"),FMath::Max3(NightFog.R,NightFog.G,NightFog.B)<.02f&&NightFog.B>NightFog.R);
    const FVector Canopy(500,1250,410),Alley(-1000,2200,90),Ridge(1100,800,840);
    const int Lit=W.Stealth()->LightAt(Canopy),AlleyLit=W.Stealth()->LightAt(Alley),RidgeLit=W.Stealth()->LightAt(Ridge);
    int Windows=0;
    for(TActorIterator<APointLight> It(W.World->GetTestWorld());It;++It)if(It->ActorHasTag(TEXT("NoticeRouteWindow")))
    {
        ++Windows;const auto* L=It->PointLightComponent.Get();
        TestTrue(TEXT("Window spill is a finite warm shadowed world light"),L->Intensity>0&&L->Intensity<=300&&L->Temperature==1900&&L->CastShadows&&L->AttenuationRadius<=500);
        It->PointLightComponent->SetVisibility(false);
    }
    TestEqual(TEXT("Only two house-window pools mark the ladder ends"),Windows,2);
    const int Dark=W.Stealth()->LightAt(Canopy);
    TestTrue(TEXT("Guard perception sees the same window light that reveals the canopy"),Lit>Dark+100);
    TestEqual(TEXT("The distant alley stays outside both window pools"),W.Stealth()->LightAt(Alley),AlleyLit);
    TestEqual(TEXT("The rear ridge stays outside both warm pools"),W.Stealth()->LightAt(Ridge),RidgeLit);
    TestTrue(TEXT("The ridge retains a low ambient exposure to guards"),RidgeLit>=100&&RidgeLit<200);
    AddInfo(FString::Printf(TEXT("Actual world illumination proxy: canopy lit=%d dark=%d alley=%d ridge=%d"),Lit,Dark,AlleyLit,RidgeLit));
    // Staging changes the one existing rig, then restores its defaults when
    // leaving the square. It must not leave this exposure clamp in later beats.
    const auto& Chapter=*W.Campaign()->ActiveChapter();
    for(int Beat:{10,11})
    {
        W.Mode()->Arena()->StageKit(Chapter,Beat);
        TestTrue(TEXT("Both post-charge square beats retain the night profile"),Grade->Settings.bOverride_AutoExposureMinBrightness&&!K->bAtmosphereSunLight);
    }
    W.Mode()->Arena()->StageKit(Chapter,12);
    TestTrue(TEXT("Leaving the square restores the map's exposure and atmospheric rig"),!Grade->Settings.bOverride_AutoExposureMinBrightness&&
        !Grade->Settings.bOverride_AutoExposureMaxBrightness&&K->bAtmosphereSunLight&&FMath::IsNearlyEqual(K->Intensity,1.8f));
    TestTrue(TEXT("Leaving the square restores its original fog"),Fog->GetComponent()->FogInscatteringLuminance.Equals(FLinearColor(.25f,.30f,.35f)));
    return !HasAnyErrors();
}
#endif
