#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCopyDeskAutomation.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"

namespace
{
using SoraFieldcraftAutomation::FBeatWorld;
ASoraEnemy* FreezeGuards(FBeatWorld& W)
{
    ASoraEnemy* First=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(!First) First=*It;
        It->SetActorTickEnabled(false); It->SetActorEnableCollision(false);
        It->GetCharacterMovement()->StopMovementImmediately();
        It->GetCharacterMovement()->SetComponentTickEnabled(false);
        It->SetActorLocation(FVector(W.BeatData().Space.Entry+FVector2D(0,8000),90));
        if(auto* Brain=Cast<ASoraEnemyController>(It->GetController()))
        {
            // Freezing a controller otherwise retains its last sight sample.
            // This fixture isolates physical contest, so reset its patrol first.
            Brain->BeginPatrol(FSoraPatrolRoute{});
            Brain->SetActorTickEnabled(false);
        }
    }
    return First;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCopyDesksTest,"SoraArena.Campaign.CopyDesks",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCopyDesksTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("CopyDesks"),5,7);
    if(!W.Start()) return false;
    W.Harden();
    ASoraEnemy* Guard=FreezeGuards(W);
    auto* C=W.Campaign();
    const auto& Space=W.BeatData().Space;
    if(!TestNotNull(TEXT("The encounter still has its authored guards"),Guard)||
        !TestEqual(TEXT("The loader keeps all three desks"),C->ActiveTask().HoldPointCount,3)) return false;
    TArray<UStaticMeshComponent*> Pieces; W.Mode()->Arena()->GetComponents(Pieces);
    int32 Desks=0,Copies=0;
    for(auto* Piece:Pieces)
    {
        Desks+=Piece->ComponentHasTag(TEXT("CopyDesk"));
        Copies+=Piece->ComponentHasTag(TEXT("LedgerCopy"));
        TestFalse(TEXT("Copying has no generic hold circle"),Piece->GetName().Contains(TEXT("KitHoldRing")));
    }
    TestEqual(TEXT("Three physical writing desks"),Desks,3);
    TestEqual(TEXT("Each desk shows its own copy"),Copies,3);
    TestTrue(TEXT("The registry loads its authored stepped hall"),Space.RegistryHall.bEnabled);
    for(int32 I=0;I<3;++I)
    {
        FHitResult FloorHit;
        const FVector At(Space.Objectives[I],SoraRegistryRules::DeskFloor[I]);
        const bool Hit=W.World->GetTestWorld()->LineTraceSingleByChannel(FloorHit,At+FVector(0,0,50),At-FVector(0,0,100),ECC_Visibility);
        TestTrue(FString::Printf(TEXT("Desk %d has real support at %d cm"),I,SoraRegistryRules::DeskFloor[I]),
            Hit&&!FloorHit.bStartPenetrating&&FMath::IsNearlyEqual(FloorHit.ImpactPoint.Z,float(SoraRegistryRules::DeskFloor[I]),1.f));
    }
    W.Stand(FVector(Space.Anchor,0));
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("Standing at the old anchor cannot copy"),C->TaskProgress().Progress,0);
    const FVector Desk(Space.Objectives[2],Space.FloorAt(Space.Objectives[2]));
    W.Stand(Desk);
    if(!W.Tick(2)) return false;
    C->Interact(*W.Hero());
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("Standing or a direct unheld interaction copies nothing"),C->TaskProgress().Progress,0);
    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("The controls menu rebinds Interact"),W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G))||
        !W.Press(EKeys::Escape)||!W.Press(EKeys::E)||!W.Tick(2)) return false;
    TestFalse(TEXT("The old binding cannot start copying"),C->IsCopying());
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(120)) return false;
    const int32 Partial=C->TaskProgress().Progress;
    AddInfo(FString::Printf(TEXT("Mapped desk state: copying=%d hidden=%d held=%d watched=%d progress=%d desks=%d,%d,%d pos=%s move=%d play=%d"),
        C->IsCopying(),W.Hero()->GetViewmodel()->bHiddenInGame,W.Hero()->IsActionHeld(TEXT("Interact")),C->IsHeldWorkWatched(),Partial,
        C->TaskProgress().HoldProgress[0],C->TaskProgress().HoldProgress[1],C->TaskProgress().HoldProgress[2],
        *W.Hero()->GetActorLocation().ToString(),int32(W.Hero()->GetCharacterMovement()->MovementMode),W.Hero()->CanPlay()));
    if(!TestTrue(TEXT("A mapped held press copies the chosen third desk only"),C->IsCopying()&&W.Hero()->GetViewmodel()->bHiddenInGame&&Partial>0&&Partial<3000&&
        C->TaskProgress().HoldProgress[2]==Partial&&C->TaskProgress().HoldProgress[0]==0&&C->TaskProgress().HoldProgress[1]==0)) return false;
    if(!W.World->InjectKey(EKeys::G,IE_Released)) return false;
    TestTrue(TEXT("Release immediately frees the hands and retains that desk's partial copy"),
        !C->IsCopying()&&!W.Hero()->GetViewmodel()->bHiddenInGame&&C->TaskProgress().Progress==Partial);
    if(!W.Tick(120)) return false;
    TestEqual(TEXT("Released work remains paused"),C->TaskProgress().Progress,Partial);
    auto* Barrier=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!TestNotNull(TEXT("The desk obstruction fixture spawns"),Barrier)) return false;
    auto* Wall=NewObject<UBoxComponent>(Barrier);
    Barrier->SetRootComponent(Wall); Barrier->AddInstanceComponent(Wall);
    Wall->SetBoxExtent(FVector(90,5,150));
    Wall->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Wall->SetCollisionResponseToAllChannels(ECR_Ignore);
    Wall->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    Wall->SetCanEverAffectNavigation(false); Wall->RegisterComponent();
    Barrier->SetActorLocation(Desk+FVector(0,55,150));
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(60)) return false;
    TestTrue(TEXT("A nearby obstructed ledger cannot start copying"),!C->IsCopying()&&C->TaskProgress().Progress==Partial);
    Wall->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(!W.Tick(60)) return false;
    TestTrue(TEXT("Clearing the obstruction requires a new press"),!C->IsCopying()&&C->TaskProgress().Progress==Partial);
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(60)) return false;
    const int32 BeforeBlock=C->TaskProgress().Progress;
    TestTrue(TEXT("A clear ledger resumes the retained partial copy"),C->IsCopying()&&BeforeBlock>Partial);
    Wall->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    if(!W.Tick(60)) return false;
    TestTrue(TEXT("An obstruction cancels active work and frees the hands without losing progress"),
        !C->IsCopying()&&!W.Hero()->GetViewmodel()->bHiddenInGame&&C->TaskProgress().Progress==BeforeBlock);
    Barrier->Destroy();
    if(!W.World->InjectKey(EKeys::G,IE_Released)) return false;
    Guard->SetActorLocation(Desk+FVector(0,-180,90));
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(120)) return false;
    TestTrue(TEXT("A guard at this desk pauses and preserves the copy"),C->IsCopying()&&C->IsHeldWorkWatched()&&C->TaskProgress().Progress==BeforeBlock);
    FreezeGuards(W);
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("The copy resumes when the desk clears"),C->TaskProgress().Progress>BeforeBlock&&!C->IsHeldWorkWatched());
    const int32 Weapon=W.Hero()->WeaponId,Ammo=W.Hero()->GetEquipment()->Ammo;
    for(const TCHAR* Name:{TEXT("Fire"),TEXT("Melee"),TEXT("Reload"),TEXT("WeaponThree")})
        for(const FKey& Key:W.Hero()->GetActionKeys(Name)) if(!Key.IsGamepadKey()) { if(!W.Press(Key)) return false;break; }
    TestTrue(TEXT("Copying occupies the hands without firing or changing arms"),C->IsCopying()&&W.Hero()->WeaponId==Weapon&&W.Hero()->GetEquipment()->Ammo==Ammo);
    W.Stand(Desk+FVector(-600,0,0));
    if(!W.Tick(2)) return false;
    const int32 Left=C->TaskProgress().Progress;
    W.Stand(Desk);
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Leaving cancels the interaction; returning requires another press"),!C->IsCopying()&&C->TaskProgress().Progress==Left);
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(60)||!W.Press(EKeys::Escape)) return false;
    const int32 Paused=C->TaskProgress().Progress;
    TestTrue(TEXT("Pause frees the hands while keeping the copies"),W.Mode()->bMenu&&!C->IsCopying());
    if(!W.Tick(120)||!W.World->InjectKey(EKeys::G,IE_Released)||!W.Press(EKeys::Escape)||!W.Tick(2)) return false;
    TestEqual(TEXT("Menu time cannot write a copy"),C->TaskProgress().Progress,Paused);
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(30)) return false;
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000.f);
    if(!W.Tick(2)||!TestTrue(TEXT("Death cancels the held interaction"),W.Mode()->bDefeated&&!C->IsCopying())||
        !W.World->InjectKey(EKeys::G,IE_Released)||!W.Press(EKeys::Enter)) return false;
    W.Harden(); Guard=FreezeGuards(W);
    if(!W.Tick(3)) return false;
    TestTrue(TEXT("Checkpoint retry resets every desk and its fractional work"),C->ActiveBeat()==7&&C->TaskProgress().Progress==0&&
        C->TaskProgress().Done==0&&C->TaskProgress().PointsMask==0&&C->TaskProgress().HoldProgress[2]==0&&C->TaskProgress().HoldRateCarry[2]==0);
    if(!TestNotNull(TEXT("Retry has an auditor for the fallen-body interaction regression"),Guard)) return false;
    Guard->SetActorLocation(Desk+FVector(0,0,Guard->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2));
    FBeatWorld::Hurt(*Guard,Guard->Health+1000.f);
    if(!TestTrue(TEXT("A defeated auditor leaves a real draggable body at the writing desk"),Guard->IsBody())) return false;
    for(int32 Point:{2,0,1})
    {
        if(!TestTrue(TEXT("Walk to and copy a distinct desk through the mapped input"),SoraCopyDeskAutomation::Copy(*W.World,Point))) return false;
        if(Point==2) TestTrue(TEXT("The copy approach drags the body clear of the desk and releases it"),
            Guard->IsBody()&&FVector::Dist2D(Guard->GetActorLocation(),Desk)>SoraStealthRules::DragReachCm&&!W.Stealth()->IsDragging());
        if(Point!=1) TestTrue(TEXT("One or two completed desks cannot complete the beat"),C->ActiveBeat()==7&&C->TaskProgress().HoldProgress[Point]==30000);
    }
    TestTrue(TEXT("Only all three desk copies finish the beat"),C->ActiveBeat()!=7);
    AddInfo(TEXT("Directed desk interaction test: guards frozen except the positioned contest fixture; not ordinary stealth encounter difficulty or final art acceptance."));
    return true;
}
#endif
