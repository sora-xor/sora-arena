#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraRecoveryAutomation.h"
#include "SoraTenementRules.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"

namespace
{
bool Ready(SoraFieldcraftAutomation::FBeatWorld& W)
{
    if(!W.Start())return false;
    SoraLiftAutomation::HoldThreats(*W.World);
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    return W.Test.TestTrue(TEXT("Tenement checkpoint releases normal controls"),W.Mode()->IsPlaying());
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTenementSolidsTest,"SoraArena.Campaign.Tenements.Solids",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTenementSolidsTest::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load())return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("TenementSolids"),2,4);
    if(!Ready(W))return false;
    TArray<UStaticMeshComponent*> Components;
    W.Mode()->Arena()->GetComponents(Components);
    int Count=0;
    for(const auto* Component:Components)if(Component->GetName().StartsWith(TEXT("TenementSolid")))++Count;
    TestEqual(TEXT("Every authored solid is in the real world"),Count,int(SoraTenementRules::Solids().size()));
    FCollisionQueryParams Query;Query.AddIgnoredActor(W.Hero());
    FHitResult Hit;
    const auto Trace=[&](FVector From,FVector To)
    { return W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,Query); };
    if(!TestTrue(TEXT("The open shaft has an actual bottom"),Trace(FVector(-3100,3200,-100),FVector(-3100,3200,-900))))return false;
    TestTrue(TEXT("The bottom lies seven metres below court level"),FMath::IsNearlyEqual(Hit.ImpactPoint.Z,-700.,.5));
    if(!TestTrue(TEXT("The shaft has a solid east lining"),Trace(FVector(-3100,3200,-400),FVector(-3000,3200,-400))))return false;
    TestTrue(TEXT("The east face leaves a ninety-centimetre bore"),FMath::IsNearlyEqual(Hit.ImpactPoint.X,-3055.,.5));
    if(!TestTrue(TEXT("The curb is solid"),Trace(FVector(-3045,3200,120),FVector(-3045,3200,-20))))return false;
    TestTrue(TEXT("The curb top is seventy-five centimetres high"),FMath::IsNearlyEqual(Hit.ImpactPoint.Z,75.,.5));
    if(!TestTrue(TEXT("The manager room has a raised floor"),Trace(FVector(-2800,3850,100),FVector(-2800,3850,-100))))return false;
    TestTrue(TEXT("The room floor is forty-five centimetres high"),FMath::IsNearlyEqual(Hit.ImpactPoint.Z,45.,.5));
    if(!TestTrue(TEXT("The noren interrupts the street sightline"),Trace(FVector(-2800,800,150),FVector(-2800,1150,150))))return false;
    TestTrue(TEXT("The sight hit is the cloth, not a hidden wall"),Hit.GetComponent()&&Hit.GetComponent()->GetName().StartsWith(TEXT("TenementSightScreen")));
    AddInfo(TEXT("Actual collision/visibility queries with opponents held. This does not qualify cloth art, live stealth, ordinary play or performance."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTenementRoutesTest,"SoraArena.Campaign.Tenements.Routes",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTenementRoutesTest::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load())return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("TenementRoutes"),2,4);
    if(!Ready(W))return false;
    const auto Walk=[&](double X,double Y,double Floor=0)
    { return SoraRecoveryAutomation::WalkTo(*W.World,FVector(X,Y,Floor+90.15)); };
    if(!TestTrue(TEXT("Mapped walking and held rope input recover the arms"),SoraRecoveryAutomation::Recover(*W.World)))return false;
    if(!TestTrue(TEXT("The hoist is reachable beside its curb"),Walk(-2600,2950)))return false;
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(170))return false;
    TestFalse(TEXT("A short hold cannot produce a tool crate"),W.Campaign()->TaskProgress().Carrying);
    if(!W.Tick(15)||!W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(2))return false;
    if(!TestTrue(TEXT("Three seconds hoists a real carry load"),W.Campaign()->TaskProgress().Carrying))return false;
    TestFalse(TEXT("The loaded carry denies the bow"),W.Campaign()->CanHold(18,false));
    for(const FVector2D P:{FVector2D(-2800,2900),FVector2D(-2800,1050),FVector2D(-2550,1050)})
        if(!TestTrue(TEXT("Mapped movement carries the crate through court, alley and storeroom door"),Walk(P.X,P.Y)))return false;
    if(!W.World->PressKey(EKeys::E))return false;
    TestEqual(TEXT("One delivered crate is credited"),W.Campaign()->TaskProgress().Done,1);
    TestFalse(TEXT("The delivered crate releases the hands"),W.Campaign()->TaskProgress().Carrying);
    if(!Walk(-2800,1050)||!Walk(-2800,2900)||!Walk(-2440,3450)||!Walk(-2460,3660,45)||!Walk(-2800,3850,45))return false;
    TestTrue(TEXT("CharacterMovement climbs the two steps and stands in the manager room"),
        W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&FMath::IsNearlyEqual(W.Hero()->GetActorLocation().Z,135.15,3.));
    if(!Walk(-2460,3660,45)||!Walk(-2440,3450)||!Walk(-2400,3000)||!Walk(-1000,3000)||!Walk(-1000,700)||!Walk(-730,700))return false;
    TestTrue(TEXT("The side passage reaches the notice-board approach on foot"),W.Hero()->GetCharacterMovement()->IsMovingOnGround());
    AddInfo(TEXT("Mapped movement, hoisting and delivery with guards held. Live patrol pressure, b10 continuation, final art and ordinary campaign acceptance remain separate."));
    return !HasAnyErrors();
}
#endif
