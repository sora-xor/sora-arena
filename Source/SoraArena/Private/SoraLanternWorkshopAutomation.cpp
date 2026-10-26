#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraLanternWorkshopRules.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"

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

namespace
{
TArray<ASoraEnemy*> WorkshopEnemies(SoraFieldcraftAutomation::FBeatWorld& W)
{
    TArray<ASoraEnemy*> Enemies;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsEnemy()&&It->IsAlive())Enemies.Add(*It);
    return Enemies;
}
void HoldWorkshopEnemies(SoraFieldcraftAutomation::FBeatWorld& W)
{
    for(auto* E:WorkshopEnemies(W))
    {
        E->SetActorTickEnabled(false);E->GetCharacterMovement()->StopMovementImmediately();
        E->GetCharacterMovement()->SetComponentTickEnabled(false);
        if(auto* C=E->GetController())C->SetActorTickEnabled(false);
    }
}
UStaticMeshComponent* WorkshopPiece(SoraFieldcraftAutomation::FBeatWorld& W,const TCHAR* Name)
{
    TArray<UStaticMeshComponent*> Pieces;W.Mode()->Arena()->GetComponents(Pieces);
    for(auto* P:Pieces)if(P->GetName()==Name)return P;
    return nullptr;
}
bool DoorBlocks(SoraFieldcraftAutomation::FBeatWorld& W)
{
    FHitResult Hit;FCollisionQueryParams Q;Q.AddIgnoredActor(W.Hero());
    return W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,FVector(1900,-1620,150),
        FVector(1900,-1380,150),ECC_Visibility,Q)&&Hit.GetComponent()==WorkshopPiece(W,TEXT("WorkshopBackDoor"));
}
bool SealApproach(SoraFieldcraftAutomation::FBeatWorld& W)
{
    return Walk(W,2000,-1800)&&Walk(W,1900,-1660);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLanternWorkshopSealTest,"SoraArena.Campaign.LanternWorkshop.Seal",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraLanternWorkshopSealTest::RunTest(const FString&)
{
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("WorkshopSeal"),2,7);
    if(!Ready(W))return false;
    W.Harden();
    if(!W.Tick(600))return false;
    TestEqual(TEXT("Waiting alone never releases the workshop waves"),W.Campaign()->TaskProgress().Released,0u);
    TestEqual(TEXT("No opponent arrives before the seal is cut"),WorkshopEnemies(W).Num(),0);
    TestTrue(TEXT("The debt-sealed door physically blocks the opening"),DoorBlocks(W));
    if(!SealApproach(W)||!W.Hold(EKeys::E,90))return false;
    TestTrue(TEXT("A short hold does not cut the seal"),W.Fieldcraft()->NeedsWorkshopSeal());
    TestEqual(TEXT("Released input discards partial progress"),W.Fieldcraft()->Readout(*W.Hero()).HoldProgress,0.f);
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(60)||!W.Press(EKeys::Escape)||!W.Tick(180))return false;
    TestEqual(TEXT("Menu entry discards the seal hold"),W.Fieldcraft()->Readout(*W.Hero()).HoldProgress,0.f);
    TestTrue(TEXT("Paused time cannot finish the cut"),W.Fieldcraft()->NeedsWorkshopSeal());
    W.World->InjectKey(EKeys::E,IE_Released);W.Mode()->ResumePlay();
    if(!W.Tick(3))return false;
    // Deliberate placement probes isolate vertical and inside-face rejection.
    for(const FVector P:{FVector(1900,-1400,135.15),FVector(1900,-1400,540.15)})
    {
        W.Hero()->GetCharacterMovement()->StopMovementImmediately();
        W.Hero()->SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);
        if(!W.Tick(10)||!W.Hold(EKeys::E,130))return false;
        TestTrue(TEXT("The inside and roof positions cannot cut the yard seal"),W.Fieldcraft()->NeedsWorkshopSeal());
    }
    W.Hero()->SetActorLocation(FVector(1900,-1660,90.15),false,nullptr,ETeleportType::TeleportPhysics);
    if(!W.Tick(10)||!W.Hold(EKeys::E,125))return false;
    TestFalse(TEXT("A fresh two-second mapped hold cuts the seal"),W.Fieldcraft()->NeedsWorkshopSeal());
    TestTrue(TEXT("The completed hold raises the physical seal event"),W.Raised(TEXT("workshop_seal_cut")));
    TestEqual(TEXT("The cut releases the first three enforcers"),WorkshopEnemies(W).Num(),3);
    HoldWorkshopEnemies(W);
    auto* Seal=WorkshopPiece(W,TEXT("WorkshopDebtSeal"));auto* Bar=WorkshopPiece(W,TEXT("WorkshopDoorBar"));
    if(!TestNotNull(TEXT("The seal has a world component"),Seal)||!TestNotNull(TEXT("The door has a physical bar"),Bar))return false;
    TestFalse(TEXT("The severed seal is gone"),Seal->IsVisible());
    TestTrue(TEXT("The craftspeople bar the door during defense"),Bar->IsVisible()&&DoorBlocks(W));
    AddInfo(TEXT("Checkpoint-seeded hold, pause and placement probes. Wave AI is frozen after release; ordinary combat and visual craft remain unqualified."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLanternWorkshopShelterTest,"SoraArena.Campaign.LanternWorkshop.ShelterRetry",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraLanternWorkshopShelterTest::RunTest(const FString&)
{
    namespace R=SoraLanternWorkshopRules;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("WorkshopShelter"),2,7);
    if(!Ready(W))return false;
    W.Harden();auto People=W.Fieldcraft()->WorkshopCraftspeople();
    if(!TestEqual(TEXT("Four real craftspeople occupy the workshop"),People.Num(),R::CraftspersonCount))return false;
    for(const auto& P:People)
    {
        if(!TestNotNull(TEXT("Each craftsperson exists"),P.Get()))return false;
        TestFalse(TEXT("The craftspeople cannot be targeted"),P->IsExposed(0));
        const float Hp=P->Health;
        UGameplayStatics::ApplyDamage(P,1000,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
        TestEqual(TEXT("Incidental damage cannot injure a craftsperson"),P->Health,Hp);
        TestTrue(TEXT("World collision is retained while interaction traces ignore the body"),
            P->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_WorldStatic)==ECR_Block&&
            P->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Visibility)==ECR_Ignore);
    }
    if(!SealApproach(W)||!W.Hold(EKeys::E,125))return false;
    HoldWorkshopEnemies(W);
    if(!W.Press(EKeys::Escape)||!W.Tick(3))return false;
    TArray<FVector> Paused;for(const auto& P:People)Paused.Add(P->GetActorLocation());
    if(!W.Tick(60))return false;
    for(int I=0;I<People.Num();++I)TestTrue(TEXT("Menu pause stops shelter movement"),People[I]->GetActorLocation().Equals(Paused[I],1.f));
    W.Mode()->ResumePlay();
    for(int F=0;F<360;++F)
    {
        TArray<FVector> Before;for(const auto& P:People)Before.Add(P->GetActorLocation());
        if(!W.Tick(1))return false;
        for(int I=0;I<People.Num();++I)
            TestTrue(TEXT("Craftspeople walk into shelter without teleporting"),FVector::Dist(Before[I],People[I]->GetActorLocation())<20);
    }
    for(int I=0;I<People.Num();++I)
    {
        const auto P=R::CraftShelter(I);const FVector At=People[I]->GetActorLocation();
        TestTrue(TEXT("Every craftsperson shelters inside on the raised floor"),
            FVector::Dist2D(At,FVector(P.X,P.Y,0))<12&&FMath::Abs(At.Z-135.15)<3&&!People[I]->IsHidden());
    }
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health,nullptr,nullptr,UDamageType::StaticClass());
    if(!TestTrue(TEXT("The fixture reaches real defeat"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter))return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    TestTrue(TEXT("Retry restores the uncut seal and blocking door"),W.Fieldcraft()->NeedsWorkshopSeal()&&DoorBlocks(W));
    TestEqual(TEXT("Retry restores unreleased waves"),W.Campaign()->TaskProgress().Released,0u);
    TestEqual(TEXT("Retry creates exactly four fresh craftspeople"),W.Fieldcraft()->WorkshopCraftspeople().Num(),4);
    for(const auto& P:People)TestFalse(TEXT("Old sheltered actors are destroyed on retry"),IsValid(P));
    AddInfo(TEXT("Actual companion movement, damage admission and mapped retry; hero hardened and wave opponents frozen to isolate shelter behavior."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLanternWorkshopDoorTest,"SoraArena.Campaign.LanternWorkshop.DoorPersistence",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraLanternWorkshopDoorTest::RunTest(const FString&)
{
    {
        SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("WorkshopDoorTransition"),2,7);
        if(!Ready(W))return false;
        W.Harden();if(!SealApproach(W)||!W.Hold(EKeys::E,125))return false;
        int Defeated=0;
        for(int Step=0;Step<1000&&W.Campaign()->ActiveBeat()==7;++Step)
        {
            const auto Enemies=WorkshopEnemies(W);
            for(auto* E:Enemies)
            {
                UGameplayStatics::ApplyDamage(E,E->Health+1000,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
                ++Defeated;
            }
            if(!W.Tick(1))return false;
        }
        TestEqual(TEXT("All eight lethal wave members settle through actual damage"),Defeated,8);
        if(!TestEqual(TEXT("Defense advances into manufacture"),W.Campaign()->ActiveBeat(),8))return false;
        for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
        TestFalse(TEXT("The door opens after defense"),DoorBlocks(W));
        auto* Door=WorkshopPiece(W,TEXT("WorkshopBackDoor"));
        if(!TestNotNull(TEXT("The open panel remains in the world"),Door))return false;
        TestTrue(TEXT("The door parks beside its opening with collision retained"),
            FMath::IsNearlyEqual(Door->GetComponentLocation().X,2046.,.1)&&Door->GetCollisionEnabled()!=ECollisionEnabled::NoCollision);
    }
    {
        // A later genuine chapter checkpoint reconstructs the open door from
        // completed beats, without adding a separate mutable save flag.
        SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("WorkshopDoorLaterCheckpoint"),2,15);
        if(!Ready(W))return false;
        auto* Door=WorkshopPiece(W,TEXT("WorkshopBackDoor"));
        if(!TestNotNull(TEXT("Later chapter geometry retains the workshop door"),Door))return false;
        TestTrue(TEXT("A later checkpoint restores the open door"),FMath::IsNearlyEqual(Door->GetComponentLocation().X,2046.,.1));
        TestFalse(TEXT("The restored opening is physically clear"),DoorBlocks(W));
    }
    AddInfo(TEXT("Scripted damage isolates beat transitions; later-checkpoint seeding verifies persistence. This is not ordinary campaign combat."));
    return !HasAnyErrors();
}
#endif
