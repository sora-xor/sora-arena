#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraEquipmentComponent.h"
#include "SoraHistoricalArms.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraSpireSupplyTest,"SoraArena.Campaign.SpireSupply",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraSpireSupplyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    const auto& Catalog=FSoraCatalog::Get();
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    TestEqual(TEXT("The existing object-form supply keeps its identity"),
        Catalog.Chapter(2).Beats[13].SupplyPoint,FString(TEXT("vol_b14_supply")));
    // RemapCombatAction changes this pawn's PlayerInput and isolated control
    // slot only. Declare this guard before W so it checks after world teardown
    // and deletion of the fixture's save/profile, including on early returns.
    const auto GlobalActions=GetDefault<UInputSettings>()->GetActionMappings();
    const auto GlobalAxes=GetDefault<UInputSettings>()->GetAxisMappings();
    FString ControlSlot;
    ON_SCOPE_EXIT
    {
        TestTrue(TEXT("Fixture teardown preserves global action mappings"),
            GetDefault<UInputSettings>()->GetActionMappings()==GlobalActions);
        TestTrue(TEXT("Fixture teardown preserves global axis mappings"),
            GetDefault<UInputSettings>()->GetAxisMappings()==GlobalAxes);
        if(!ControlSlot.IsEmpty())
            TestFalse(TEXT("Fixture teardown removes its isolated rebound profile"),
                UGameplayStatics::DoesSaveGameExist(ControlSlot,0));
    };
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("SpireSupply"),7,9);
    ControlSlot=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!W.Start()||!W.Tick(30)) return false;
    const auto Freeze=[&]()
    {
        SoraLiftAutomation::HoldThreats(*W.World);
        for(ASoraCompanion* Ally:W.Fieldcraft()->AlliesInPlay())
        {
            Ally->SetActorTickEnabled(false); Ally->SetActorEnableCollision(false);
            Ally->GetCharacterMovement()->StopMovementImmediately();
            Ally->GetCharacterMovement()->SetComponentTickEnabled(false);
        }
    };
    Freeze();
    auto* Arena=W.Mode()->Arena();
    auto* Kit=W.Hero()->GetEquipment();
    const FString Id=TEXT("sp_spire_base");
    FVector Cache;
    if(!TestTrue(TEXT("The authored named L1 cache is staged"),Arena->SupplyFloor(Id,Cache))) return false;
    TestEqual(TEXT("The cache stands on the actual L1 floor"),Cache.Z,0.0);
    FVector Other;
    TestFalse(TEXT("A different supply identity cannot activate this cache"),Arena->SupplyFloor(TEXT("sp_nokaji"),Other));
    if(!Kit->EquipCampaignWeapon(18)||!W.Tick(30)) return false;
    // Spent inventory setup. The live held count deliberately differs from
    // its stored copy, exactly as it does after normal firing.
    for(int32 N=0;N<SoraBeatRules::WeaponCount;++N)
        if(!SoraHistoricalArms::IsMelee(N)) Kit->AmmoByWeapon[N]=0;
    Kit->Ammo=0; Kit->AmmoByWeapon[18]=12;
    const auto* Before=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("The ordinary spire checkpoint exists"),Before)) return false;
    const int32 WeaponsBefore=Before->CheckpointWeapons,BeatsBefore=Before->CheckpointBeatsMask;
    W.Hero()->Health=FMath::Max(1.f,W.Hero()->Health-25.f);
    const float HealthBefore=W.Hero()->Health;
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("Distant input never replenishes the quiver"),Kit->Ammo,0);
    const FVector Approach=Cache+FVector(-140,0,0);
    if(!TestTrue(TEXT("Normal movement reaches the supply crate"),SoraLiftAutomation::Walk(*W.World,Approach))) return false;
    if(!TestTrue(TEXT("Actual grounded arrival can reach the crate"),Arena->CanReachSupply(Id,*W.Hero()))) return false;
    TestEqual(TEXT("Walking into reach does not refill automatically"),Kit->Ammo,0);
    TestTrue(TEXT("The nearby hint identifies the cache and the live action key"),
        W.Mode()->NoticeEnglish.Contains(TEXT("League supply cache: E")));
    const FVector Ground=W.Hero()->GetActorLocation();
    W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->SetActorLocation(Ground+FVector(0,0,900),false,nullptr,ETeleportType::TeleportPhysics);
    W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    TestFalse(TEXT("Matching XY on another floor cannot reach the cache"),Arena->CanReachSupply(Id,*W.Hero()));
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("Wrong-floor input cannot refill"),Kit->Ammo,0);
    W.Hero()->SetActorLocation(Ground,false,nullptr,ETeleportType::TeleportPhysics);
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    auto* Movement=W.Hero()->GetCharacterMovement();
    // The wrong-floor setup has entered falling. Teleporting the capsule
    // back does not reset its cached floor: wait for an actual landing before
    // pressing Jump, and face away so low-cover vaulting cannot consume it.
    for(int32 Frame=0;Frame<120&&(!Movement->IsMovingOnGround()||!W.Hero()->CanJump());++Frame)
        if(!W.Tick(1)) return false;
    W.Look((W.Hero()->GetActorLocation()-Cache).GetSafeNormal2D().Rotation());
    const FVector JumpStart=W.Hero()->GetActorLocation();
    AddInfo(FString::Printf(TEXT("Supply jump setup: at=%s mode=%d can_jump=%d vault=%d base=%s"),
        *JumpStart.ToString(),int32(Movement->MovementMode),W.Hero()->CanJump(),W.Hero()->IsVaulting(),
        *GetNameSafe(W.Hero()->GetMovementBaseObject())));
    if(!TestTrue(TEXT("The jump begins on a real grounded floor"),Movement->IsMovingOnGround()&&W.Hero()->CanJump())||
        !TestTrue(TEXT("Space is the live mapped Jump key"),W.Hero()->GetActionKeys(TEXT("Jump")).Contains(EKeys::SpaceBar))||
        !W.World->InjectKey(EKeys::SpaceBar,IE_Pressed)) return false;
    for(int32 Frame=0;Frame<12&&!(Movement->IsFalling()&&W.Hero()->GetActorLocation().Z>JumpStart.Z+5);++Frame)
        if(!W.Tick(1)) return false;
    const bool Airborne=Movement->IsFalling()&&Movement->Velocity.Z>0&&W.Hero()->GetActorLocation().Z>JumpStart.Z+5;
    AddInfo(FString::Printf(TEXT("Supply jump result: at=%s rise=%.2f mode=%d velocity=%s held=%d vault=%d reach=%d"),
        *W.Hero()->GetActorLocation().ToString(),W.Hero()->GetActorLocation().Z-JumpStart.Z,int32(Movement->MovementMode),
        *Movement->Velocity.ToString(),W.Hero()->IsActionHeld(TEXT("Jump")),W.Hero()->IsVaulting(),
        Arena->CanReachSupply(Id,*W.Hero())));
    if(!TestTrue(TEXT("Mapped Jump actually raises the falling capsule"),Airborne)||
        !TestFalse(TEXT("A jumping hero cannot use supplies"),Arena->CanReachSupply(Id,*W.Hero()))||
        !W.Press(EKeys::E)||!TestEqual(TEXT("Airborne input cannot refill"),Kit->Ammo,0)) return false;
    if(!W.World->InjectKey(EKeys::SpaceBar,IE_Released)) return false;
    for(int32 Frame=0;Frame<180&&!Movement->IsMovingOnGround();++Frame) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("The jump lands naturally before the wall test"),Movement->IsMovingOnGround())||
        !TestEqual(TEXT("Landing alone never replenishes ammunition"),Kit->Ammo,0)) return false;
    auto* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Wall);
    Wall->SetRootComponent(Box); Box->SetBoxExtent(FVector(10,100,100));
    Box->SetCollisionProfileName(TEXT("BlockAll")); Box->RegisterComponent(); Wall->AddInstanceComponent(Box);
    Wall->SetActorLocation(Cache+FVector(-85,0,100));
    TestFalse(TEXT("A solid obstruction blocks the actual supply crate"),Arena->CanReachSupply(Id,*W.Hero()));
    if(!W.Press(EKeys::E)) return false;
    if(!TestEqual(TEXT("Input through a wall cannot refill"),Kit->Ammo,0)) return false;
    Wall->Destroy();
    if(!W.Tick(3)||!TestTrue(TEXT("Removing the obstruction restores reach"),Arena->CanReachSupply(Id,*W.Hero()))) return false;
    // Reload remains a real action. Supply cannot finish it or replenish
    // another weapon while it is still in progress.
    if(!W.Press(EKeys::R)||!TestTrue(TEXT("Mapped Reload begins normally"),Kit->bReloading)||!W.Press(EKeys::E)) return false;
    TestTrue(TEXT("Supply does not cancel or finish an active reload"),Kit->bReloading&&Kit->Ammo==0&&Kit->AmmoByWeapon[1]==0);
    for(int32 N=0;N<600&&Kit->bReloading;++N) if(!W.Tick(1)) return false;
    if(!TestFalse(TEXT("The ordinary reload finishes itself"),Kit->bReloading)) return false;
    Kit->Ammo=1;
    if(!W.World->InjectKey(EKeys::LeftMouseButton,IE_Pressed)||!W.Tick(10)||
        !TestTrue(TEXT("Mapped Fire starts a real bow draw"),Kit->IsBowDrawing())||!W.Press(EKeys::E)) return false;
    TestTrue(TEXT("Supply preserves the in-progress draw and its spent inventory"),Kit->IsBowDrawing()&&Kit->Ammo==1&&Kit->AmmoByWeapon[1]==0);
    if(!W.World->InjectKey(EKeys::LeftMouseButton,IE_Released)||!W.Tick(90)||!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("Explicit Interact fills the held quiver to twelve"),Kit->Ammo,12);
    for(int32 N=0;N<SoraBeatRules::WeaponCount;++N)
        if(!SoraHistoricalArms::IsMelee(N))
            TestEqual(FString::Printf(TEXT("Unlocked magazine %d has its catalog cap"),N),Kit->AmmoByWeapon[N],Catalog.Weapon(N).Magazine);
    TestEqual(TEXT("Restocking keeps the held weapon"),W.Hero()->WeaponId,18);
    TestEqual(TEXT("Restocking grants no healing"),W.Hero()->Health,HealthBefore);
    const auto Full=Kit->AmmoByWeapon;
    if(!W.Press(EKeys::E)||!W.Press(EKeys::E)) return false;
    TestTrue(TEXT("Repeated full use is idempotent"),Kit->AmmoByWeapon==Full&&Kit->Ammo==12);
    TestEqual(TEXT("Supply does not advance combat"),W.Campaign()->ActiveBeat(),9);
    TestEqual(TEXT("Supply does not defeat an enemy"),W.Campaign()->Kills,0);

    if(!Kit->EquipCampaignWeapon(0)||!W.Tick(30)||!W.Press(EKeys::V)||!W.Tick(50)) return false;
    TestTrue(TEXT("The blade is fully sheathed before supply"),Kit->IsSheathed());
    Kit->AmmoByWeapon[18]=0;
    if(!W.World->InjectKey(EKeys::LeftControl,IE_Pressed)||!W.Tick(1)||
        !TestTrue(TEXT("Mapped guard raises the sheathed hand"),Kit->IsGuardHeld())||!W.Press(EKeys::E)) return false;
    TestTrue(TEXT("Supply cannot lower a guard or fill while it is held"),Kit->IsGuardHeld()&&Kit->AmmoByWeapon[18]==0);
    if(!W.World->InjectKey(EKeys::LeftControl,IE_Released)||!W.Tick(2)) return false;
    if(!W.Press(EKeys::E)) return false;
    TestTrue(TEXT("Supply preserves the equipped sheathed blade"),W.Hero()->WeaponId==0&&Kit->IsSheathed()&&Kit->AmmoByWeapon[18]==12);
    if(!Kit->EquipCampaignWeapon(18)||!W.Tick(30)) return false;
    W.Look(FRotator(45,0,0));
    if(!W.Hold(EKeys::LeftMouseButton,45)) return false;
    TestEqual(TEXT("An actual bow shot spends one of the supplied arrows"),Kit->Ammo,11);
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("Supply cannot bypass the real post-shot cooldown"),Kit->Ammo,11);
    if(!W.Tick(90)||!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("Spending allows another explicit refill"),Kit->Ammo,12);

    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("Interact can be rebound in the ordinary menu"),
        W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G))) return false;
    W.Mode()->ResumePlay();
    if(!W.Tick(3)) return false;
    Kit->Ammo=0;
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("The former key no longer replenishes"),Kit->Ammo,0);
    if(!W.Press(EKeys::G)) return false;
    TestEqual(TEXT("The live mapped Interact key replenishes"),Kit->Ammo,12);
    const auto* After=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Cache use changes no saved unlock or checkpoint progress"),After&&After->CheckpointBeat==9&&
        After->CheckpointWeapons==WeaponsBefore&&After->CheckpointBeatsMask==BeatsBefore);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Death enters the ordinary retry flow"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    Freeze(); Arena=W.Mode()->Arena(); Kit=W.Hero()->GetEquipment();
    if(!TestTrue(TEXT("Retry rebuilds the named supply point"),Arena->SupplyFloor(Id,Cache))) return false;
    TestEqual(TEXT("Retry returns to the spire checkpoint"),W.Campaign()->ActiveBeat(),9);
    if(!Kit->EquipCampaignWeapon(18)||!W.Tick(30)) return false;
    Kit->Ammo=0;
    if(!TestTrue(TEXT("The rebuilt crate remains reachable through normal movement"),
        SoraLiftAutomation::Walk(*W.World,Cache+FVector(-140,0,0)))||!W.Press(EKeys::G)) return false;
    TestEqual(TEXT("Rebound interaction still restocks after retry"),Kit->Ammo,12);
    return !HasAnyErrors();
}
#endif
