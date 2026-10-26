#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraLanternWorkshopRules.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"

namespace
{
bool Ready(SoraFieldcraftAutomation::FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    return W.Test.TestTrue(TEXT("The workshop checkpoint releases normal controls"),W.Mode()->IsPlaying());
}
bool Walk(SoraFieldcraftAutomation::FBeatWorld& W,double X,double Y,double Height=0)
{
    return W.Test.TestTrue(TEXT("Mapped movement reaches the workshop waypoint"),
        SoraLiftAutomation::Walk(*W.World,FVector(X,Y,Height)))&&
        W.Test.TestTrue(TEXT("The hero stands on the expected authored floor"),
            W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&
            FMath::IsNearlyEqual(W.Hero()->GetActorLocation().Z,Height+90.15,3.));
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLanternWorkshopSolidsTest,"SoraArena.Campaign.LanternWorkshop.Solids",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraLanternWorkshopSolidsTest::RunTest(const FString&)
{
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("LanternWorkshopSolids"),2,8);
    if(!Ready(W))return false;
    TArray<UStaticMeshComponent*> Components;W.Mode()->Arena()->GetComponents(Components);
    int Count=0;
    for(const auto* C:Components)if(C->GetName().StartsWith(TEXT("LanternWorkshopSolid")))++Count;
    TestEqual(TEXT("The game builds every authored workshop solid"),Count,int(SoraLanternWorkshopRules::Solids().size()));
    FCollisionQueryParams Query;Query.AddIgnoredActor(W.Hero());FHitResult Hit;
    const auto Floor=[&](FVector From,double Height)
    {
        return TestTrue(TEXT("The real floor collision is present"),W.World->GetTestWorld()->LineTraceSingleByChannel(
            Hit,From,From-FVector(0,0,250),ECC_Visibility,Query))&&
            TestTrue(TEXT("The real floor collision has its authored height"),FMath::IsNearlyEqual(Hit.ImpactPoint.Z,Height,.5));
    };
    if(!Floor(FVector(1655,-950,120),0)||!Floor(FVector(1745,-950,120),22.5)||
       !Floor(FVector(1900,-1535,120),22.5)||!Floor(FVector(1900,-950,120),45)||
       !Floor(FVector(3150,-1900,120),0)||!Floor(FVector(3150,-1900,800),650))return false;
    int Benches=0;
    for(const auto* C:Components)
        if(C->GetName().StartsWith(TEXT("KitBench")))
        {
            ++Benches;
            const FVector P=C->GetComponentLocation();
            TestTrue(TEXT("Station benches stand on their own floor"),
                FMath::IsNearlyEqual(P.Z,SoraLanternWorkshopRules::FloorAt(P.X,P.Y)+40,.5));
        }
    TestEqual(TEXT("All four stations have physical benches"),Benches,4);
    const int Before=W.Campaign()->TaskProgress().StepDone;
    // FBeatWorld::Stand only changes XY. Place this rejection probe on the
    // roof explicitly, and assert its real floor before testing Interact.
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->SetActorLocation(FVector(1950,-620,450+W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),
        false,nullptr,ETeleportType::TeleportPhysics);
    if(!W.Tick(10)||!TestTrue(TEXT("The rejection probe actually stands on the roof"),
        W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&FMath::IsNearlyEqual(W.Hero()->GetActorLocation().Z,540.15,3.))||
        !W.Press(EKeys::E))return false;
    TestEqual(TEXT("Standing above the rib form on the roof cannot manufacture through the ceiling"),
        W.Campaign()->TaskProgress().StepDone,Before);
    AddInfo(TEXT("Real world collision and station heights from a seeded b09 checkpoint. Final art, combat and ordinary play are not established."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLanternWorkshopRoutesTest,"SoraArena.Campaign.LanternWorkshop.Routes",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraLanternWorkshopRoutesTest::RunTest(const FString&)
{
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("LanternWorkshopRoutes"),2,8);
    if(!Ready(W))return false;
    if(!Walk(W,2000,-1800)||!Walk(W,1900,-1660)||!Walk(W,1900,-1450,45)||
       !Walk(W,1950,-620,45))return false;
    const int Before=W.Campaign()->TaskProgress().StepDone;
    if(!W.Press(EKeys::E))return false;
    TestEqual(TEXT("Mapped Interact works at the raised rib form"),W.Campaign()->TaskProgress().StepDone,Before+1);
    if(!Walk(W,1900,-950,45)||!Walk(W,1745,-950,22.5)||!Walk(W,1655,-950)||
       !Walk(W,1745,-950,22.5)||!Walk(W,1900,-950,45)||!Walk(W,1900,-1450,45)||
       !Walk(W,1900,-1660)||!Walk(W,2440,-1660)||!Walk(W,2440,-1030)||
       !Walk(W,3280,-1030)||!Walk(W,3480,-1030)||!Walk(W,3480,0)||!Walk(W,3000,0)||
       !Walk(W,3480,0)||!Walk(W,3480,-1030)||!Walk(W,3280,-1030)||!Walk(W,2440,-1030)||
       !Walk(W,2440,-1800)||!Walk(W,2650,-1800)||!Walk(W,2650,-1900)||!Walk(W,3150,-1900)||
       !Walk(W,3150,-2000))return false;
    TestEqual(TEXT("Traversal preserves the unfinished manufacturing beat"),W.Campaign()->ActiveBeat(),8);
    AddInfo(TEXT("Seeded b09 with real mapped walking, half-height steps and one work stroke. It does not test the seal, waves, hazards, completed recipe or ordinary chapter pacing."));
    return !HasAnyErrors();
}
#endif
