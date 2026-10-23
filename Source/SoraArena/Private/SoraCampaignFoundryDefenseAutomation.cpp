#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraEnemy.h"
#include "SoraFoundryFurnace.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraViewmodelComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"
#include "Misc/ScopeExit.h"
namespace SoraFoundryTest
{
using SoraFieldcraftAutomation::FBeatWorld;
using Work=SoraFoundryDefenseRules::EWork;
// Directed mechanic fixtures: hero health is hardened; unrelated opponents
// are frozen or killed through real damage. This is not a difficulty pass.
void Isolate(FBeatWorld& W,FName Keep=NAME_None,bool Remove=false)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(!It->IsAlive()||It->ArchetypeId()==Keep) continue;
        if(Remove) { FBeatWorld::Hurt(**It,100000); continue; }
        It->SetActorTickEnabled(false); It->GetCharacterMovement()->StopMovementImmediately();
        It->GetCharacterMovement()->SetComponentTickEnabled(false);
        if(It->GetController()) It->GetController()->SetActorTickEnabled(false);
    }
}
bool Tick(FBeatWorld& W,int Frames,FName Keep=NAME_None,bool Remove=false)
{
    for(int I=0;I<Frames;++I) { Isolate(W,Keep,Remove); if(!W.Tick(1)) return false; } return true;
}
bool Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    W.Harden();
    for(int I=0;I<1800&&!W.Mode()->IsPlaying();++I) if(!Tick(W,1)) return false;
    return W.Test.TestTrue(TEXT("The foundry is in live play"),W.Mode()->IsPlaying()&&W.Campaign()->IsFoundryDefense()&&
        W.Campaign()->FoundryFurnace()&&W.Campaign()->FoundryKozo());
}
FKey Action(FBeatWorld& W,const TCHAR* Name)
{
    for(const FKey& K:W.Hero()->GetActionKeys(Name)) if(!K.IsGamepadKey()) return K;
    return FKey();
}
void RepairState(FBeatWorld& W,const TCHAR* Label,int Index=0)
{
    const auto* C=W.Campaign();const auto* H=W.Hero();const auto* K=H->GetEquipment();const auto& S=C->FoundryState();
    const FVector Target=C->FoundryWorkPoint(Work::Repair,Index);FHitResult Hit;
    const bool Blocked=W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,H->GetEye()->GetComponentLocation(),
        Target+FVector(0,0,35),ECC_Visibility,FCollisionQueryParams(SCENE_QUERY_STAT(FoundryRepairState),false,H));
    W.Test.AddInfo(FString::Printf(TEXT("Foundry repair %s: elapsed=%d hp=%d work=%d index=%d held_ms=%d used=%u input=%d can_play=%d dialogue=%d key=%d grounded=%d hidden=%d weapon=%d ammo=%d guard=%d reload=%d strike=%d step=%d stagger=%d distance=%.3f hero=%s blocked=%d actor=%s component=%s"),
        Label,C->TaskProgress().ElapsedMs,C->TaskProgress().TargetHp[0],int(S.Work),S.Index,S.HeldMs,S.Used,int(W.Mode()->InputState()),H->CanPlay(),C->IsDialogueBlocking(),
        H->IsActionHeld(TEXT("Interact")),H->GetCharacterMovement()->IsMovingOnGround(),H->GetViewmodel()->bHiddenInGame,H->WeaponId,K->Ammo,
        K->IsGuardHeld(),K->bReloading,K->IsCommittedStrike(),K->IsStepping(),K->IsStaggered(),FVector::Dist2D(H->GetActorLocation(),Target),
        *H->GetActorLocation().ToString(),Blocked,*GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent())));
}
bool WalkTo(FBeatWorld& W,const FVector& At,FName Keep=NAME_None)
{
    auto* Hero=W.Hero();auto* Nav=USoraNavigation::Get(Hero);TArray<FVector> Path;
    if(!Nav||!Nav->Settle()||!Nav->FindPath(Hero->GetActorLocation(),At,*Hero,Path)||Path.IsEmpty()) return false;
    Path.Add(At);
    for(const FVector& Point:Path)
    {
        for(int Frame=0;Frame<1200&&FVector::Dist2D(Hero->GetActorLocation(),Point)>30;++Frame)
        {
            const FRotator Facing=(Point-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
            Hero->GetController()->SetControlRotation(Facing);Hero->FaceRotation(Facing,0);
            if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,1,Keep)) return false;
        }
        if(FVector::Dist2D(Hero->GetActorLocation(),Point)>40)
        {
            FHitResult Hit;const auto* Capsule=Hero->GetCapsuleComponent();
            const FVector Start=Hero->GetActorLocation(),End(Point.X,Point.Y,Start.Z);
            const bool Blocked=W.World->GetTestWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Pawn,
                FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),
                FCollisionQueryParams(SCENE_QUERY_STAT(FoundryWalkBlocked),false,Hero));
            W.Test.AddInfo(FString::Printf(TEXT("Foundry walk stalled: hero=%s waypoint=%s blocked=%d actor=%s component=%s impact=%s"),
                *Start.ToString(),*Point.ToString(),Blocked,*GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()),*Hit.ImpactPoint.ToString()));
            W.World->InjectKey(EKeys::W,IE_Released);return false;
        }
    }
    return W.World->InjectKey(EKeys::W,IE_Released)&&Tick(W,4,Keep);
}
bool Walk(FBeatWorld& W,Work Kind,int Index)
{
    // Walk the real capsule to an exposed approach; never edit location or task progress.
    FVector At=W.Campaign()->FoundryWorkPoint(Kind,Index)+FVector(-140,0,0); At.Z=0;
    if(Kind==Work::Repair)
    {
        // The nav path can cross the 50 cm tub even though the real capsule
        // cannot step onto it. Walk through the open aisles around the kit;
        // retain collision and the same final approach/acceptance distances.
        const FVector Furnace=W.Campaign()->FoundryFurnace()->GetActorLocation();
        const float South=Furnace.Y-620,North=Furnace.Y+600,East=Furnace.X+600;
        if(!WalkTo(W,FVector(W.Hero()->GetActorLocation().X,South,0))) return false;
        if(Index==2)
        {
            if(!WalkTo(W,FVector(East,South,0))||!WalkTo(W,FVector(East,North,0))||
                !WalkTo(W,FVector(At.X,North,0))) return false;
        }
        else if(!WalkTo(W,FVector(At.X,South,0))) return false;
    }
    const bool Reached=WalkTo(W,At,Kind==Work::Net?FName(TEXT("drone")):NAME_None);
    if(!Reached) W.Test.AddError(FString::Printf(TEXT("Foundry approach failed: kind=%d index=%d hero=%s goal=%s"),
        int(Kind),Index,*W.Hero()->GetActorLocation().ToString(),*At.ToString()));
    return Reached;
}
bool Hold(FBeatWorld& W,int Frames,FName Keep=NAME_None)
{
    const auto K=Action(W,TEXT("Interact"));
    return W.World->InjectKey(K,IE_Pressed)&&Tick(W,Frames,Keep)&&W.World->InjectKey(K,IE_Released)&&Tick(W,1,Keep);
}
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true); W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.World->Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)) return false;
    W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName Event) { W.Events.Add(Event.ToString()); });
    W.Harden(); for(int I=0;I<1800&&!W.Mode()->IsPlaying();++I) if(!Tick(W,1)) return false;
    return W.Mode()->IsPlaying()&&W.Campaign()->IsFoundryDefense();
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFoundryRepairTest,"SoraArena.Campaign.FoundryRepairHolds",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraFoundryRepairTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    SoraFoundryTest::FBeatWorld W(*this,TEXT("FoundryRepairHolds"),4,6);
    if(!SoraFoundryTest::Ready(W)) return false;
    auto* C=W.Campaign(); const auto Use=SoraFoundryTest::Action(W,TEXT("Interact"));
    if(!SoraFoundryTest::Walk(W,SoraFoundryTest::Work::Repair,0)||!SoraFoundryTest::Hold(W,185)) return false;
    TestEqual(TEXT("A full furnace refuses consumption"),C->FoundryState().Used,0u);
    SoraFoundryTest::FBeatWorld::Hurt(*C->FoundryFurnace(),600);
    if(!TestEqual(TEXT("Ordinary actor damage reaches the defended furnace"),C->TaskProgress().TargetHp[0],900)) return false;
    SoraFoundryTest::RepairState(W,TEXT("before_partial"));
    if(!W.World->InjectKey(Use,IE_Pressed)||!SoraFoundryTest::Tick(W,90)) return false;
    SoraFoundryTest::RepairState(W,TEXT("after_partial"));
    TestTrue(TEXT("Mapped held input reserves hands and earns partial work"),C->FoundryOccupiesHands()&&C->FoundryState().HeldMs>=1400&&W.Hero()->GetViewmodel()->bHiddenInGame);
    if(!W.World->InjectKey(Use,IE_Released)) return false;
    TestTrue(TEXT("Release immediately discards all partial credit"),!C->FoundryOccupiesHands()&&C->FoundryState().HeldMs==0&&C->FoundryState().Used==0);
    if(!SoraFoundryTest::Hold(W,100)) return false;
    TestEqual(TEXT("Separate short holds do not accumulate"),C->TaskProgress().TargetHp[0],900);
    if(!W.World->InjectKey(Use,IE_Pressed)||!SoraFoundryTest::Tick(W,60)) return false;
    const int32 Weapon=W.Hero()->WeaponId,Ammo=W.Hero()->GetEquipment()->Ammo;
    for(const TCHAR* Name:{TEXT("Fire"),TEXT("Melee"),TEXT("Reload"),TEXT("Block"),TEXT("WeaponThree")})
        if(!W.Press(SoraFoundryTest::Action(W,Name))) return false;
    SoraFoundryTest::RepairState(W,TEXT("after_reserved_inputs"));
    TestTrue(TEXT("Working hands cannot attack, guard, reload or change the selected arm"),
        C->FoundryOccupiesHands()&&!W.Hero()->GetEquipment()->IsCommittedStrike()&&!W.Hero()->GetEquipment()->IsGuardHeld()&&
        !W.Hero()->GetEquipment()->bReloading&&W.Hero()->WeaponId==Weapon&&W.Hero()->GetEquipment()->Ammo==Ammo);
    SoraFoundryTest::FBeatWorld::Hurt(*W.Hero(),1);
    TestTrue(TEXT("A real hit cancels held repair immediately"),!C->FoundryOccupiesHands()&&C->FoundryState().HeldMs==0);
    if(!SoraFoundryTest::Tick(W,185)||!W.World->InjectKey(Use,IE_Released)) return false;
    TestEqual(TEXT("The still-held key after damage earns no automatic repair"),C->TaskProgress().TargetHp[0],900);
    // Face away from the nearby clay tub so Jump tests a jump, not its low-cover vault.
    W.Look(FRotator(0,180,0));
    const auto Jump=SoraFoundryTest::Action(W,TEXT("Jump"));
    if(!W.World->InjectKey(Use,IE_Pressed)||!SoraFoundryTest::Tick(W,30)||!W.World->InjectKey(Jump,IE_Pressed)||!SoraFoundryTest::Tick(W,2)) return false;
    const float Feet=W.Hero()->GetActorLocation().Z-W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    TestTrue(TEXT("Normal jump cancels work while still within the old 60 cm height tolerance"),
        !W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&Feet>0&&Feet<60&&!C->FoundryOccupiesHands()&&C->FoundryState().HeldMs==0);
    if(!W.World->InjectKey(Use,IE_Released)||!W.World->InjectKey(Use,IE_Pressed)||!SoraFoundryTest::Tick(W,2)) return false;
    TestFalse(TEXT("A fresh mapped Interact cannot admit airborne work"),C->FoundryOccupiesHands());
    if(!W.World->InjectKey(Jump,IE_Released)||!SoraFoundryTest::Tick(W,90)||!W.World->InjectKey(Use,IE_Released)) return false;
    TestTrue(TEXT("Landing requires a fresh hold and preserves unused clay"),W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&C->FoundryState().Used==0&&!C->FoundryOccupiesHands());
    if(!W.World->InjectKey(Use,IE_Pressed)||!SoraFoundryTest::Tick(W,60)||!W.Press(EKeys::Escape)) return false;
    TestTrue(TEXT("Opening the real menu cancels the active hold"),W.Mode()->bMenu&&!C->FoundryOccupiesHands()&&C->FoundryState().HeldMs==0);
    const int32 Clock=C->TaskProgress().ElapsedMs;
    if(!W.Tick(120)||!W.World->InjectKey(Use,IE_Released)) return false;
    TestEqual(TEXT("Menu time does not run the encounter"),C->TaskProgress().ElapsedMs,Clock);
    if(!W.Press(EKeys::Escape)||!SoraFoundryTest::Tick(W,2)) return false;
    if(!W.World->InjectKey(Use,IE_Pressed)||!SoraFoundryTest::Tick(W,60)) return false;
    FVector Away=C->FoundryWorkPoint(SoraFoundryTest::Work::Repair,0)+FVector(-500,0,0); Away.Z=0;
    if(!SoraFoundryTest::WalkTo(W,Away)||!W.World->InjectKey(Use,IE_Released)) return false;
    TestTrue(TEXT("Walking out of reach cancels without consuming clay"),!C->FoundryOccupiesHands()&&C->FoundryState().Used==0);
    for(int I=0;I<3;++I)
    {
        if(!SoraFoundryTest::Walk(W,SoraFoundryTest::Work::Repair,I)||!SoraFoundryTest::Hold(W,185)) return false;
        TestEqual(TEXT("Each unique tub heals exactly 150 once"),C->TaskProgress().TargetHp[0],900+(I+1)*150);
        TestEqual(TEXT("The completed tub is consumed"),C->FoundryState().Used,(1u<<(I+1))-1u);
        if(!SoraFoundryTest::Hold(W,185)) return false;
        TestEqual(TEXT("Reusing the same tub cannot repair again"),C->TaskProgress().TargetHp[0],900+(I+1)*150);
    }
    if(!W.Press(EKeys::Escape)||!W.Tick(60)||!W.Press(EKeys::Escape)) return false;
    TestEqual(TEXT("Used supplies persist across the menu"),C->FoundryState().Used,7u);
    auto* Pawn=W.Hero();SoraFoundryTest::FBeatWorld::Hurt(*Pawn,200000);
    if(!TestTrue(TEXT("Actual hero death enters ordinary defeat"),W.Mode()->bDefeated)||!W.Tick(120)||!W.Press(EKeys::Enter)||!SoraFoundryTest::Tick(W,4)) return false;
    TestTrue(TEXT("Death retry retains the pawn but resets all consumed attempt supplies"),W.Hero()==Pawn&&!W.Mode()->bDefeated&&C->FoundryState().Used==0&&C->TaskProgress().TargetHp[0]==1500);
    W.Harden();SoraFoundryTest::FBeatWorld::Hurt(*C->FoundryFurnace(),300);
    if(!SoraFoundryTest::Walk(W,SoraFoundryTest::Work::Repair,0)||!SoraFoundryTest::Hold(W,185)) return false;
    if(!TestEqual(TEXT("One real consumed tub is present before saving"),C->FoundryState().Used,1u)) return false;
    C->SaveProgress();
    if(!SoraFoundryTest::Reload(W)) return false;
    TestTrue(TEXT("Fresh checkpoint load resets attempt supplies and HP"),W.Campaign()->FoundryState().Used==0&&W.Campaign()->TaskProgress().TargetHp[0]==1500);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFoundryKozoTest,"SoraArena.Campaign.FoundryKozoRescue",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraFoundryKozoTest::RunTest(const FString& Parameters)
{
    (void)Parameters;SoraFoundryTest::FBeatWorld W(*this,TEXT("FoundryKozoRescue"),4,6);
    if(!SoraFoundryTest::Ready(W)||!SoraFoundryTest::Walk(W,SoraFoundryTest::Work::Revive,0)) return false;
    auto* C=W.Campaign();auto* Kozo=C->FoundryKozo();
    SoraFoundryTest::FBeatWorld::Hurt(*Kozo,300);
    TestTrue(TEXT("Actual 300 HP actor downing starts rescue instead of instant failure"),Kozo->IsDown()&&Kozo->Health==0&&!W.Mode()->bDefeated);
    if(!SoraFoundryTest::Hold(W,180)) return false;
    TestTrue(TEXT("Three seconds cannot revive Kōzō"),Kozo->IsDown()&&C->FoundryState().HeldMs==0);
    if(!SoraFoundryTest::Hold(W,245)) return false;
    TestTrue(TEXT("An uninterrupted four seconds raises the actual companion"),!Kozo->IsDown()&&Kozo->Health==150&&C->TaskProgress().TargetHp[1]==150&&C->FoundryState().DownMs==0);
    TestTrue(TEXT("Revival broadcasts the production companion event"),W.Events.Contains(TEXT("npc_revived:kozo")));
    SoraFoundryTest::FBeatWorld::Hurt(*Kozo,150);
    if(!SoraFoundryTest::Tick(W,1200)) return false;
    TestTrue(TEXT("Second down gets a new deadline and still permits a timely rescue"),Kozo->IsDown()&&!W.Mode()->bDefeated&&C->FoundryState().DownMs>=19900);
    if(!SoraFoundryTest::Hold(W,245)) return false;
    TestTrue(TEXT("Timely late rescue preserves the encounter"),!Kozo->IsDown()&&!W.Mode()->bDefeated);
    for(int Frame=0;Frame<10800&&C->TaskProgress().ElapsedMs<176000;++Frame)
        if(!SoraFoundryTest::Tick(W,1)) return false;
    if(!TestTrue(TEXT("The actual survival clock reaches its last four seconds"),C->IsFoundryDefense()&&C->TaskProgress().ElapsedMs>=176000)) return false;
    SoraFoundryTest::FBeatWorld::Hurt(*Kozo,150);
    if(!SoraFoundryTest::Tick(W,360)) return false;
    TestTrue(TEXT("The 180 second survival cannot skip an outstanding rescue"),C->ActiveBeat()==6&&C->TaskProgress().Progress==180000&&Kozo->IsDown()&&!W.Mode()->bDefeated);
    if(!SoraFoundryTest::Hold(W,245)) return false;
    TestTrue(TEXT("Actual revival completes the finished defense through its ordinary transition"),C->ActiveBeat()==7&&!W.Mode()->bDefeated&&!C->FoundryOccupiesHands());
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFoundryDeadlineTest,"SoraArena.Campaign.FoundryKozoDeadline",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraFoundryDeadlineTest::RunTest(const FString& Parameters)
{
    (void)Parameters;SoraFoundryTest::FBeatWorld W(*this,TEXT("FoundryKozoDeadline"),4,6);
    if(!SoraFoundryTest::Ready(W)||!SoraFoundryTest::Walk(W,SoraFoundryTest::Work::Revive,0)) return false;
    auto* C=W.Campaign();auto* Pawn=W.Hero();
    SoraFoundryTest::FBeatWorld::Hurt(*C->FoundryKozo(),300);
    if(!SoraFoundryTest::Tick(W,1440)) return false;
    TestFalse(TEXT("Kōzō is not lost at 24 seconds"),W.Mode()->bDefeated);
    const auto Use=SoraFoundryTest::Action(W,TEXT("Interact"));
    if(!W.World->InjectKey(Use,IE_Pressed)||!SoraFoundryTest::Tick(W,65)) return false;
    TestTrue(TEXT("Actual downing fails the checkpoint at 25 seconds"),W.Mode()->bDefeated&&C->FoundryState().Failed&&C->FoundryState().DownMs==25000&&!C->FoundryOccupiesHands());
    if(!W.World->InjectKey(Use,IE_Released)||!W.Tick(180)||!W.Press(EKeys::Enter)||!SoraFoundryTest::Tick(W,4)) return false;
    TestTrue(TEXT("Ordinary retry retains the pawn and restores Kōzō and supplies"),W.Hero()==Pawn&&C->IsFoundryDefense()&&!W.Mode()->bDefeated&&C->FoundryKozo()->Health==300&&C->FoundryState().Used==0&&C->FoundryState().DownMs==0);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFoundryGrenadeTest,"SoraArena.Campaign.FoundryGrenadierPriority",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraFoundryGrenadeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;SoraFoundryTest::FBeatWorld W(*this,TEXT("FoundryGrenadierPriority"),4,6);
    if(!SoraFoundryTest::Ready(W)) return false;
    auto* C=W.Campaign();int Shots=0;bool WrongTarget=false;
    auto* Events=USoraGameEvents::Get(W.World->GetTestWorld());
    const auto Handle=Events->OnWeaponFired.AddLambda([&](const FSoraWeaponFiredEvent& E)
    {
        const auto* Enemy=Cast<ASoraEnemy>(E.Shooter);
        if(Enemy&&Enemy->ArchetypeId()==TEXT("grenadier")&&E.Kind==ESoraShotKind::Shell)
        { ++Shots;WrongTarget|=FVector::Dist2D(E.End,C->FoundryFurnace()->GetActorLocation())>1; }
    });
    ON_SCOPE_EXIT { Events->OnWeaponFired.Remove(Handle); };
    for(int Frame=0;Frame<6000&&C->TaskProgress().TargetHp[0]==1500;++Frame)
        if(!SoraFoundryTest::Tick(W,1,TEXT("grenadier"))) return false;
    TestTrue(TEXT("An authored grenadier fires a real shell at the furnace"),Shots>0&&!WrongTarget);
    TestTrue(TEXT("The real projectile/blast damages the furnace actor and counter"),C->TaskProgress().TargetHp[0]<1500&&C->FoundryFurnace()->Health==C->TaskProgress().TargetHp[0]);
    auto* Pawn=W.Hero();SoraFoundryTest::FBeatWorld::Hurt(*C->FoundryFurnace(),2000);
    TestTrue(TEXT("Actual furnace destruction fails immediately"),C->FoundryFurnace()->Health==0&&W.Mode()->bDefeated);
    if(!W.Tick(120)||!W.Press(EKeys::Enter)||!SoraFoundryTest::Tick(W,4)) return false;
    TestTrue(TEXT("Ordinary retry rebuilds a real intact furnace and retains pawn"),W.Hero()==Pawn&&C->FoundryFurnace()&&C->FoundryFurnace()->Health==1500&&!W.Mode()->bDefeated);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFoundryNetsTest,"SoraArena.Campaign.FoundryBellowsNets",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraFoundryNetsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;SoraFoundryTest::FBeatWorld W(*this,TEXT("FoundryBellowsNets"),4,6);
    if(!SoraFoundryTest::Ready(W)) return false;
    auto* C=W.Campaign();auto* Craft=W.Fieldcraft();
    // Free authored max_alive slots by actual damage; drones spawn only at
    // their real 90 s wave trigger and reach/lock their real crew themselves.
    for(int F=0;F<8000&&(Craft->NetOf(0)!=SoraFieldcraftRules::ENet::Netted||Craft->NetOf(1)!=SoraFieldcraftRules::ENet::Netted);++F)
        if(!SoraFoundryTest::Tick(W,1,TEXT("drone"),true)) return false;
    if(!TestTrue(TEXT("Both authored drones physically reach and net distinct workmates"),Craft->NetOf(0)==SoraFieldcraftRules::ENet::Netted&&Craft->NetOf(1)==SoraFieldcraftRules::ENet::Netted&&Craft->TetherOf(0)!=Craft->TetherOf(1))) return false;
    int Hp=C->TaskProgress().TargetHp[0];
    if(!SoraFoundryTest::Tick(W,120,TEXT("drone"),true)) return false;
    TestTrue(TEXT("Two nets produce 5 HP/s total, with integer-frame tolerance"),Hp-C->TaskProgress().TargetHp[0]>=9&&Hp-C->TaskProgress().TargetHp[0]<=11);
    if(!SoraFoundryTest::Walk(W,SoraFoundryTest::Work::Net,0)||!SoraFoundryTest::Hold(W,30,TEXT("drone"))) return false;
    TestTrue(TEXT("Partial net hold cannot free a workmate"),Craft->NetOf(0)==SoraFieldcraftRules::ENet::Netted);
    if(!SoraFoundryTest::Hold(W,65,TEXT("drone"))) return false;
    TestTrue(TEXT("Normal one-second held input frees the actual first net"),Craft->NetOf(0)==SoraFieldcraftRules::ENet::Free&&Craft->PeopleInPlay()[1]->Condition()==SoraFieldcraftRules::EState::Up);
    // Kill the freed drone through ordinary damage to prevent the authored
    // rearm clock renetting while the next hand interaction is measured.
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->ArchetypeId()==TEXT("drone")&&*It!=Craft->TetherOf(1)) SoraFoundryTest::FBeatWorld::Hurt(**It,10000);
    if(!SoraFoundryTest::Walk(W,SoraFoundryTest::Work::Net,1)||!SoraFoundryTest::Hold(W,65,TEXT("drone"))) return false;
    TestTrue(TEXT("The second crew member is genuinely free"),Craft->NetOf(1)==SoraFieldcraftRules::ENet::Free&&Craft->PeopleInPlay()[2]->Condition()==SoraFieldcraftRules::EState::Up);
    Hp=C->TaskProgress().TargetHp[0];
    if(!SoraFoundryTest::Tick(W,60,TEXT("drone"),true)) return false;
    TestEqual(TEXT("Furnace drain stops when no crew is netted"),C->TaskProgress().TargetHp[0],Hp);
    return !HasAnyErrors();
}
#endif
