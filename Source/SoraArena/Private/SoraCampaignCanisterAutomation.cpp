#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraFuelCanister.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Misc/ScopeExit.h"

namespace SoraCanisterTest
{
using SoraFieldcraftAutomation::FBeatWorld;
namespace Fuel=SoraFuelCanisterRules;
// Directed b08 fixture: checkpoint and health are seeded, enemy AI is frozen.
// The player uses actual mapped walking/fire/bow input and collision. The
// separate blast fixture relocates real registered opponents and one temporary
// cover box; this is damage/credit coverage, not encounter or art acceptance.
void Freeze(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(!It->IsAlive()) continue;
        It->SetActorTickEnabled(false); It->GetCharacterMovement()->StopMovementImmediately();
        if(auto* Brain=Cast<ASoraEnemyController>(It->GetController())) { Brain->StopMovement(); Brain->SetActorTickEnabled(false); }
    }
}
bool Tick(FBeatWorld& W,int Frames)
{ for(int I=0;I<Frames;++I) { Freeze(W); if(!W.Tick(1)) return false; } return true; }
TArray<ASoraFuelCanister*> Canisters(FBeatWorld& W)
{
    TArray<ASoraFuelCanister*> Found;
    for(TActorIterator<ASoraFuelCanister> It(W.World->GetTestWorld());It;++It) if(!It->IsActorBeingDestroyed()) Found.Add(*It);
    Found.Sort([](const ASoraFuelCanister& A,const ASoraFuelCanister& B) { return A.CanisterId().LexicalLess(B.CanisterId()); });
    return Found;
}
bool Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    W.Harden(); for(int I=0;I<1800&&!W.Mode()->IsPlaying();++I) if(!Tick(W,1)) return false;
    return W.Test.TestTrue(TEXT("Hangar b08 has three staged authored canisters"),W.Mode()->IsPlaying()&&
        W.Campaign()->ActiveBeat()==7&&W.BeatData().Space.FuelCanisters.Num()==3&&Canisters(W).Num()==3);
}
FKey Fire(FBeatWorld& W)
{ for(const auto& Key:W.Hero()->GetActionKeys(TEXT("Fire"))) if(!Key.IsGamepadKey()) return Key; return FKey(); }
bool Tap(FBeatWorld& W)
{ return W.World->InjectKey(Fire(W),IE_Pressed)&&Tick(W,1)&&W.World->InjectKey(Fire(W),IE_Released)&&Tick(W,2); }
bool Walk(FBeatWorld& W,FVector2D At)
{
    for(int I=0;I<1800&&FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),At)>15;++I)
    {
        W.Look((FVector(At,0)-W.Hero()->GetActorLocation()).GetSafeNormal2D().Rotation());
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,1)) return false;
    }
    if(!W.World->InjectKey(EKeys::W,IE_Released)||!Tick(W,12)) return false;
    return W.Test.TestTrue(TEXT("Mapped walk reaches the open hangar aisle with collision"),
        FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),At)<45&&W.Hero()->GetActorEnableCollision());
}
bool Aim(FBeatWorld& W,ASoraFuelCanister& Canister)
{
    W.LookAt(Canister.BlastPoint());
    const FVector Eye=W.Hero()->GetCamera()->GetComponentLocation();
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(CanisterActualAim),false,W.Hero());
    return W.Test.TestTrue(TEXT("Actual weapon visibility trace first hits the intact canister"),
        W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+W.Hero()->GetCamera()->GetForwardVector()*2000,ECC_Visibility,Query)&&Hit.GetActor()==&Canister);
}
void Place(ASoraEnemy& Enemy,const FVector& Center)
{
    Enemy.SetActorLocation(FVector(Center.X,Center.Y,Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.5f),false,nullptr,ETeleportType::TeleportPhysics);
    Enemy.GetCharacterMovement()->StopMovementImmediately(); Enemy.GetCharacterMovement()->SetMovementMode(MOVE_Falling);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCanisterShotsTest,"SoraArena.Campaign.HangarCanisterShots",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCanisterShotsTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraCanisterTest;
    FBeatWorld W(*this,TEXT("HangarCanisterShots"),6,7); if(!Ready(W)) return false;
    auto Found=Canisters(W); auto* Kit=W.Hero()->GetEquipment(); auto* Bus=USoraGameEvents::Get(W.Hero());
    if(!TestNotNull(TEXT("Damage/shot bus"),Bus)) return false;
    for(int I=0;I<3;++I)
    {
        const auto& Data=W.BeatData().Space.FuelCanisters[I];
        TestTrue(TEXT("Canister ID and floor transform match authored frame"),Found[I]->CanisterId()==Data.Id&&
            Found[I]->GetActorLocation().Equals(Data.Floor+FVector(0,0,Fuel::BodyHalfHeightCm),.01)&&!Found[I]->IsBurst());
    }
    int Detonations=0,Arrows=0,Rounds=0,Deaths=0; float PlayerDamage=0;
    const auto Burst=Bus->OnDetonated.AddLambda([&](const FSoraDetonatedEvent& E)
    { if(E.Instigator==W.Hero()&&E.Radius==Fuel::BlastRadiusCm&&E.Damage==Fuel::Damage) ++Detonations; });
    const auto Shot=Bus->OnWeaponFired.AddLambda([&](const FSoraWeaponFiredEvent& E)
    { if(E.Shooter==W.Hero()) { Arrows+=E.Kind==ESoraShotKind::Arrow; Rounds+=E.Kind==ESoraShotKind::Hitscan; } });
    const auto Hurt=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
    { if(E.Victim==W.Hero()&&Cast<ASoraFuelCanister>(E.Causer.Get())) PlayerDamage+=E.Amount; });
    const auto Died=Bus->OnDied.AddLambda([&](const FSoraDiedEvent& E) { if(E.Victim==W.Hero()) ++Deaths; });
    ON_SCOPE_EXIT { Bus->OnDetonated.Remove(Burst); Bus->OnWeaponFired.Remove(Shot); Bus->OnDamaged.Remove(Hurt); Bus->OnDied.Remove(Died); };
    if(!Kit->EquipCampaignWeapon(3)||!Tick(W,30)||!Walk(W,FVector2D(39000,-1650))||!Walk(W,FVector2D(40550,-1050))) return false;
    // Physical approach must stop at the actual canister capsule, not pass
    // through the visual mesh before a shot has disabled its collision.
    W.Look(FRotator(0,0,0));
    if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,90)||!W.World->InjectKey(EKeys::W,IE_Released)) return false;
    const float Separation=FVector::Dist2D(W.Hero()->GetActorLocation(),Found[0]->GetActorLocation());
    TestTrue(TEXT("Intact canister blocks ordinary mapped walking"),Separation>=Fuel::BodyRadiusCm+W.Hero()->GetCapsuleComponent()->GetScaledCapsuleRadius()-3&&Separation<120);
    if(!Walk(W,FVector2D(40550,-1050))||!Aim(W,*Found[0])) return false;
    FHitResult Contact; Contact.ImpactPoint=Found[0]->BlastPoint();
    SoraDamage::Strike(Found[0],999,FSoraHit::Melee(W.Hero()->GetActorLocation(),0),FVector::ForwardVector,Contact,W.Hero()->GetController(),W.Hero());
    TestFalse(TEXT("A melee hit cannot consume the shot-triggered fuel"),Found[0]->IsBurst());
    if(!W.Press(EKeys::Escape)) return false;
    const int Ammo=Kit->Ammo;
    if(!Tap(W)) return false;
    TestTrue(TEXT("Paused mapped fire spends neither ammo nor canister"),W.Mode()->bMenu&&Kit->Ammo==Ammo&&!Found[0]->IsBurst()&&Detonations==0);
    if(!W.Press(EKeys::Escape)||!Aim(W,*Found[0])||!Tap(W)) return false;
    TestTrue(TEXT("Real mapped hitscan produces one fuel detonation and full self damage"),Found[0]->IsBurst()&&Detonations==1&&Rounds==1&&PlayerDamage==80);
    if(!Tick(W,30)||!Tap(W)||!Tick(W,30)) return false;
    TestTrue(TEXT("The spent canister cannot detonate or hurt twice"),Detonations==1&&PlayerDamage==80);
    if(!Walk(W,FVector2D(42950,-1050))||!Kit->EquipCampaignWeapon(18)||!Tick(W,30)||!Aim(W,*Found[1])) return false;
    if(!W.World->InjectKey(Fire(W),IE_Pressed)||!Tick(W,60)||!W.World->InjectKey(Fire(W),IE_Released)||!Tick(W,120)) return false;
    TestTrue(TEXT("Actual released bow projectile triggers the second canister"),Found[1]->IsBurst()&&Arrows==1&&Detonations==2&&PlayerDamage==160);
    if(!Walk(W,FVector2D(43300,-1050))||!Walk(W,FVector2D(43300,1550))||!Walk(W,FVector2D(42250,1550))||
       !Kit->EquipCampaignWeapon(3)||!Tick(W,30)||!Aim(W,*Found[2])) return false;
    W.Hero()->Health=1; // Boundary setup; the real shot/fuel blast must cause defeat.
    if(!Tap(W)||!Tick(W,30)) return false;
    TestTrue(TEXT("Fuel self damage reaches ordinary defeat exactly once"),Found[2]->IsBurst()&&Detonations==3&&Deaths==1&&W.Mode()->bDefeated);
    TWeakObjectPtr<ASoraFuelCanister> Old=Found[0];
    if(!W.Tick(120)||!W.Press(EKeys::Enter)||!Tick(W,4)) return false;
    Found=Canisters(W);
    TestTrue(TEXT("Enter retry replaces all three spent actors with intact canisters"),!W.Mode()->bDefeated&&W.Campaign()->ActiveBeat()==7&&Found.Num()==3&&
        (!Old.IsValid()||Old->IsActorBeingDestroyed())&&Found.FilterByPredicate([](const auto* C){return C->IsBurst();}).IsEmpty());
    W.Fieldcraft()->Clear(); if(!Tick(W,60)) return false;
    TestTrue(TEXT("Encounter teardown removes every owned canister and effect"),Canisters(W).IsEmpty()&&Detonations==3);
    AddInfo(TEXT("Directed b08 fixture: seeded checkpoint/hardened health/frozen AI; actual mapped walking, collision, hitscan, released arrow, pause and lethal-shot Enter retry. No shell/chain-reaction, art or encounter-difficulty acceptance."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCanisterBlastTest,"SoraArena.Campaign.HangarCanisterBlast",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCanisterBlastTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraCanisterTest;
    FBeatWorld W(*this,TEXT("HangarCanisterBlast"),6,7); if(!Ready(W)) return false;
    const auto Found=Canisters(W); ASoraEnemy* Target=nullptr; TArray<ASoraEnemy*> Others;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It) if(It->IsAlive())
        { if(It->ArchetypeId()==TEXT("marksman")) Target=*It; else Others.Add(*It); }
    if(!TestNotNull(TEXT("Registered first-wave marksman"),Target)||!TestEqual(TEXT("Other first-wave bodies"),Others.Num(),3)) return false;
    const FVector At=Found[0]->BlastPoint(); Target->Health=Target->MaxHealth=1000;
    Place(*Target,At+FVector(0,200,0)); Target->SetActorRotation(FRotator(0,-90,0));
    Place(*Others[0],At+FVector(0,-230,0)); Place(*Others[1],At+FVector(0,400,0)); Place(*Others[2],At+FVector(-800,-400,0));
    auto* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!TestNotNull(TEXT("Temporary cover actor"),Wall)) return false;
    auto* Cover=NewObject<UBoxComponent>(Wall); Wall->SetRootComponent(Cover); Cover->SetBoxExtent(FVector(100,10,120));
    Cover->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Cover->SetCollisionObjectType(ECC_WorldStatic); Cover->SetCollisionResponseToAllChannels(ECR_Block);
    Cover->RegisterComponent(); Wall->AddInstanceComponent(Cover); Wall->SetActorLocation(At+FVector(0,-120,0));
    ON_SCOPE_EXIT { if(IsValid(Wall)) Wall->Destroy(); };
    auto* Bus=USoraGameEvents::Get(W.Hero()); if(!TestNotNull(TEXT("Damage bus"),Bus)) return false;
    float Damage=0,Blocked=0,Outside=0; int Deaths=0; bool Credit=false;
    const auto Hurt=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
    { if(E.Victim==Target) Damage+=E.Amount; if(E.Victim==Others[0]) Blocked+=E.Amount; if(E.Victim==Others[1]) Outside+=E.Amount; });
    const auto Died=Bus->OnDied.AddLambda([&](const FSoraDiedEvent& E)
    { if(E.Victim==Target) { ++Deaths; Credit=Cast<ASoraFuelCanister>(E.Killer.Get())&&E.Killer->GetInstigator()==W.Hero(); } });
    ON_SCOPE_EXIT { Bus->OnDamaged.Remove(Hurt); Bus->OnDied.Remove(Died); };
    auto* Kit=W.Hero()->GetEquipment(); if(!Kit->EquipCampaignWeapon(3)||!Tick(W,30)) return false;
    W.Stand(At+FVector(-600,0,0)); if(!Tick(W,2)||!Aim(W,*Found[0])) return false;
    FCollisionObjectQueryParams Solid; Solid.AddObjectTypesToQuery(ECC_WorldStatic); Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(CanisterCoverFixture),false,Found[0]); Q.AddIgnoredActor(Others[0]);
    TestTrue(TEXT("Temporary fixture cover physically occludes the inside-radius control"),
        FVector::Dist(At,Others[0]->GetActorLocation())<360&&W.World->GetTestWorld()->LineTraceTestByObjectType(At,Others[0]->GetActorLocation(),Solid,Q));
    TestTrue(TEXT("Outside control is physically beyond the authored sphere"),FVector::Dist(At,Others[1]->GetActorLocation())>360);
    if(!Tap(W)) return false;
    TestTrue(TEXT("Clear ordinary enemy takes 80 base damage; cover and radius controls take none"),Damage==80&&Blocked==0&&Outside==0&&Deaths==0);
    const int Down=W.Campaign()->TaskProgress().Down[0];
    Target->Health=60; Place(*Target,Found[1]->BlastPoint()+FVector(0,200,0)); Target->SetActorRotation(FRotator(0,-90,0));
    W.Stand(Found[1]->BlastPoint()+FVector(-600,0,0));
    if(!Tick(W,30)||!Aim(W,*Found[1])||!Tap(W)||!Tick(W,60)) return false;
    TestTrue(TEXT("Fuel defeat uses the real registered wave and retains the shooter instigator"),Deaths==1&&Credit&&
        W.Campaign()->TaskProgress().Down[0]==Down+1&&W.Campaign()->TaskProgress().Down[1]==0);
    if(!Tap(W)||!Tick(W,90)) return false;
    TestTrue(TEXT("Repeated fire and a remaining corpse never duplicate enemy credit"),Deaths==1&&W.Campaign()->TaskProgress().Down[0]==Down+1);
    AddInfo(TEXT("Directed blast fixture: real registered first-wave enemies repositioned, target HP seeded, AI frozen, one temporary occluding box, player positioned outside radius; real mapped hitscan/TakeDamage/Blast/OnDied and wave accounting. No enemy lure-AI or full encounter qualification."));
    return !HasAnyErrors();
}
#endif
