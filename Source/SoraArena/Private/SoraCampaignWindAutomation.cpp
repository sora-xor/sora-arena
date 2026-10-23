#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRidgeAutomation.h"
#include "SoraEquipmentComponent.h"
#include "SoraProjectile.h"
#include "SoraViewmodelComponent.h"
#include "SoraGameEvents.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Combat/SoraCombatEffects.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/InputSettings.h"
#include "GameFramework/DamageType.h"
#include "Misc/ScopeExit.h"

namespace SoraWindAutomation
{
void Freeze(SoraFieldcraftAutomation::FBeatWorld& W) { SoraLiftAutomation::HoldThreats(*W.World); }
bool Ready(SoraFieldcraftAutomation::FBeatWorld& W)
{
    if(!W.Start()) return false;
    Freeze(W);
    for(int F=0;F<1200&&!W.Hero()->CanPlay();++F) if(!W.Tick(1)) return false;
    return W.Tick(30)&&W.Hero()->CanPlay()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround();
}
// Setup a distinct real supported floor for isolated force/reach samples.
// Traversal/fall tests below never use this to claim a walked route or jump.
bool Stand(SoraFieldcraftAutomation::FBeatWorld& W,double X,double Y)
{
    const FVector O(W.BeatData().Space.Wind.Origin,0);
    auto* H=W.Hero(); H->GetCharacterMovement()->StopMovementImmediately();
    H->SetActorLocation(O+FVector(X,Y,(W.BeatData().Space.Wind.Ridge()?SoraRidgeRules::Height(X,Y):0)+H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+4),false,nullptr,ETeleportType::TeleportPhysics);
    H->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    return W.Tick(12)&&H->GetCharacterMovement()->IsMovingOnGround();
}
bool Reload(SoraFieldcraftAutomation::FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true);W.World->ForwardErrorMessages(&W.Test);W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.World->Tick(1)||!W.World->EnableKeyInput()) return false;
    for(int N=0;N<3;++N) if(!W.World->PressKey(EKeys::Enter)) return false;
    Freeze(W);return W.Tick(30)&&W.Campaign()->ActiveBeat()==9;
}
bool WaitOnDefeatAndRetry(SoraFieldcraftAutomation::FBeatWorld& W,int CheckpointBeat)
{
    auto* Hero=W.Hero();
    if(!W.Test.TestTrue(TEXT("A terminal fall offers the ordinary checkpoint result"),
        IsValid(Hero)&&W.Mode()->bDefeated&&Hero->Health==0&&Hero->GetCharacterMovement()->MovementMode==MOVE_None)) return false;
    const FVector Stopped=Hero->GetActorLocation();
    const int Clock=W.Campaign()->WindClockMs();
    // Waiting at the result must not let gravity carry this pawn to KillZ.
    if(!W.Tick(1200)||!W.Test.TestTrue(TEXT("Waiting on defeat preserves the controlled pawn"),
        IsValid(Hero)&&W.Hero()==Hero&&!Hero->IsActorBeingDestroyed())) return false;
    W.Test.TestTrue(TEXT("The falling body stays stopped for twenty seconds on the result screen"),
        Hero->GetActorLocation().Equals(Stopped,1.f)&&Hero->GetCharacterMovement()->Velocity.IsZero());
    W.Test.TestEqual(TEXT("The result screen does not advance wind"),W.Campaign()->WindClockMs(),Clock);
    if(!W.Press(EKeys::Enter)) return false;
    Freeze(W);
    if(!W.Tick(30)) return false;
    return W.Test.TestTrue(TEXT("The real retry key restores that pawn and its grounded checkpoint"),
        W.Hero()==Hero&&Hero->IsAlive()&&!W.Mode()->bDefeated&&W.Campaign()->ActiveBeat()==CheckpointBeat&&
        Hero->GetCharacterMovement()->IsMovingOnGround());
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRidgeWindTest,"SoraArena.Campaign.RidgeWind",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRidgeWindTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraWindAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    const auto Actions=GetDefault<UInputSettings>()->GetActionMappings();
    const auto Axes=GetDefault<UInputSettings>()->GetAxisMappings();FString Control;
    ON_SCOPE_EXIT { TestTrue(TEXT("Global action map restored"),Actions==GetDefault<UInputSettings>()->GetActionMappings());
        TestTrue(TEXT("Global axes restored"),Axes==GetDefault<UInputSettings>()->GetAxisMappings());
        if(!Control.IsEmpty()) TestFalse(TEXT("Isolated remapping profile removed"),UGameplayStatics::DoesSaveGameExist(Control,0)); };
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("RidgeWind"),6,9);Control=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!Ready(W)) return false;
    auto* C=W.Campaign();auto* H=W.Hero();const FVector O(W.BeatData().Space.Wind.Origin,0);
    if(!Stand(W,500,-200)) return false;
    double Y=H->GetActorLocation().Y;
    if(!W.Tick(60)) return false;
    TestTrue(TEXT("Exposed standing hero moves 120 cm per second"),FMath::Abs(H->GetActorLocation().Y-Y-120)<3);
    if(!W.Press(EKeys::C)||!W.Tick(5)||!TestTrue(TEXT("Mapped C establishes actual crouch"),H->IsCrouched())) return false;
    Y=H->GetActorLocation().Y;
    if(!W.Tick(60)) return false;
    TestTrue(TEXT("Crouch halves external push"),FMath::Abs(H->GetActorLocation().Y-Y-60)<3);
    // Isolate the existing root service here; the combat fixture separately
    // proves the enemy net's delivery. Wind must not translate a rooted body.
    auto* Effects=USoraCombatEffects::Get(H);
    if(!TestNotNull(TEXT("Actual root service is present"),Effects)) return false;
    Effects->Root(*H,1200);const FVector Netted=H->GetActorLocation();
    if(!W.Tick(45)) return false;
    TestTrue(TEXT("Rooted hero is not displaced by external wind"),Effects->IsRooted(H)&&FVector::Dist(H->GetActorLocation(),Netted)<3);
    if(!W.Tick(40)) return false;
    TestFalse(TEXT("Existing net root expires normally"),Effects->IsRooted(H));
    if(!W.Press(EKeys::C)||!Stand(W,700,-300)) return false;
    W.LookAt(O+FVector(700,-400,SoraRidgeRules::Height(700,400)+90));
    if(!TestTrue(TEXT("Actual cable is grounded and visible"),W.Mode()->Arena()->ReachRidgeCable(*H)!=INDEX_NONE)||
       !W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(3)||!TestTrue(TEXT("Mapped held Interact braces"),C->IsWindBraced())) return false;
    const FVector Braced=H->GetActorLocation();
    if(!W.Hold(EKeys::W,90)) return false;
    TestTrue(TEXT("Cable brace stops external push and walking"),FVector::Dist(H->GetActorLocation(),Braced)<3);
    if(!W.Press(EKeys::Escape)) return false;
    TestFalse(TEXT("Pause releases the brace immediately"),C->IsWindBraced());
    const int Clock=C->WindClockMs(); if(!W.Tick(300)) return false;
    TestEqual(TEXT("Paused world does not advance the gust clock"),C->WindClockMs(),Clock);
    if(!H->RemapCombatAction(TEXT("Interact"),EKeys::G)) return false;
    W.Mode()->ResumePlay();if(!W.Tick(2)||!W.Press(EKeys::E)) return false;
    TestFalse(TEXT("Old key cannot brace after remapping"),C->IsWindBraced());
    if(!Stand(W,700,-300)) return false;W.LookAt(O+FVector(700,-400,SoraRidgeRules::Height(700,400)+90));
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(2)||!TestTrue(TEXT("New mapped key braces"),C->IsWindBraced())||
        !W.World->InjectKey(EKeys::G,IE_Released)||!W.Tick(1)) return false;
    TestFalse(TEXT("Release clears brace without delayed ticks"),C->IsWindBraced());
    // All three missing downwind cable runs must refuse the real action.
    for(int X:{5000,10000,14000})
    {
        if(!Stand(W,X,300)||!W.Press(EKeys::G)) return false;
        TestFalse(FString::Printf(TEXT("Cable gap %d cannot brace"),X),C->IsWindBraced());
    }
    if(!W.Press(EKeys::C)||!Stand(W,1225,500)||!TestTrue(TEXT("Crouched rib creates actual downstream lee"),C->InWindLee())) return false;
    Y=H->GetActorLocation().Y;if(!W.Tick(60)) return false;
    TestTrue(TEXT("Crouched rib lee stops external wind"),FMath::Abs(H->GetActorLocation().Y-Y)<3);
    if(!W.Press(EKeys::C)||!W.Tick(4)) return false;
    TestFalse(TEXT("Rib lee does not grant standing shelter"),C->InWindLee());
    if(!Stand(W,3100,0)||!W.Tick(3)||!TestTrue(TEXT("Sensor fin provides actual traced lee"),C->InWindLee())) return false;
    Y=H->GetActorLocation().Y;if(!W.Tick(120)) return false;
    TestTrue(TEXT("Full lee removes standing external push"),FMath::Abs(H->GetActorLocation().Y-Y)<3);
    // Read the production schedule through ordinary ticks, including its
    // first warning, rather than setting a wind timestamp in the fixture.
    while(C->WindClockMs()<10000) if(!W.Tick(1)) return false;
    // If earlier reach cases crossed the first warning, inspect a subsequent
    // full warning boundary while retaining the first dialogue in Heard.
    int Next=C->WindClockMs()+100;
    while(!SoraRidgeRules::At(Next).Warning||SoraRidgeRules::At(Next-1).Warning) ++Next;
    while(C->WindClockMs()<Next) if(!W.Tick(1)) return false;
    TestTrue(TEXT("Accessible warning is emitted by the production gust clock"),W.Mode()->NoticeEnglish.Contains(TEXT("Gust incoming")));
    TestTrue(TEXT("One-second pre-gust warning has steady drift"),C->ProjectileWind(O+FVector(1000,0,200),true,18)==FVector(0,280,0));
    if(!W.Tick(60)) return false;
    TestTrue(TEXT("Gust uses authored 18 m/s acceleration"),C->ProjectileWind(O+FVector(1000,0,200),true,18)==FVector(0,630,0));
    if(!W.Tick(150)) return false;
    TestTrue(TEXT("Gust expires after its 2.5-second hold"),C->ProjectileWind(O+FVector(1000,0,200),true,18)==FVector(0,280,0));
    C->SaveProgress();
    if(!Reload(W)) return false;
    TestFalse(TEXT("Fresh-world checkpoint never restores a held brace"),W.Campaign()->IsWindBraced());
    TestTrue(TEXT("Fresh checkpoint starts a new deterministic wind cycle"),W.Campaign()->WindClockMs()<1000);
    TestEqual(TEXT("Checkpoint retry grants its own three fall recoveries"),W.Campaign()->RidgeRecoveries(),0);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRidgeTraversalTest,"SoraArena.Campaign.RidgeTraversal",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRidgeTraversalTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraWindAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("RidgeTraversal"),6,9);
    if(!Ready(W)) return false;
    const auto Space=W.BeatData().Space;const FVector O(Space.Wind.Origin,0);
    // World geometry itself, not just the source dimensions, must retain
    // the complete crown and slope and expose real void at each lip.
    for(int X:{300,6300,11700,12300,17700}) for(int Side:{-1,1})
    {
        const double Half=SoraRidgeRules::CrownHalf(X);
        FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(RidgeFloorFixture),false,W.Hero());
        for(double Y:{0.,Side*(Half+200)})
        {
            const FVector P=O+FVector(X,Y,0);
            TestTrue(TEXT("Ridge floor is actual collision"),W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,P+FVector(0,0,400),P-FVector(0,0,500),ECC_Visibility,Q));
            TestTrue(TEXT("Actual plate follows authored grade"),FMath::Abs(Hit.ImpactPoint.Z-SoraRidgeRules::Height(X,Y))<3);
        }
        const FVector Beyond=O+FVector(X,Side*(Half+500),0);
        TestFalse(TEXT("There is no hidden floor beyond the exposed lip"),W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,Beyond+FVector(0,0,400),Beyond-FVector(0,0,900),ECC_Visibility,Q));
    }
    // Follow the full route with live mapped movement and low-cover vaults.
    // Freeze combat only; newly released groups remain pending combat and
    // the beat cannot finish until every authored wave is cleared.
    for(int X:{5900,11900,17750})
    {
        if(!SoraRidgeAutomation::Walk(*W.World,Space,X,*this,true)) return false;
        Freeze(W);
    }
    TestTrue(TEXT("All three wave triggers require the actual ridge route"),(W.Campaign()->TaskProgress().Released&7u)==7u);
    TestEqual(TEXT("Arrival alone does not bypass the drone encounter"),W.Campaign()->ActiveBeat(),9);
    // A real held brace sets a non-default anchor before the fall cases.
    // This distinguishes last-anchor recovery from always returning to X0.
    if(!Stand(W,6500,-300)) return false;
    W.LookAt(O+FVector(6500,-400,SoraRidgeRules::Height(6500,400)+90));
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(2)||
        !TestTrue(TEXT("Mapped brace remembers a non-entry anchor"),W.Campaign()->IsWindBraced()&&W.Campaign()->RidgeLastAnchor()>0)||
        !W.World->InjectKey(EKeys::E,IE_Released)||!W.Tick(1)) return false;
    // Isolate deliberate fall recovery after the traversal. The relocation is
    // a supported setup; every fall below follows real held W input.
    for(int N=0;N<4;++N)
    {
        if(!Stand(W,700,600)) return false;
        const double Before=W.Hero()->Health;
        if(!W.Tick(180)||!TestTrue(TEXT("Wind alone cannot move a capsule off the lip"),W.Hero()->GetCharacterMovement()->IsMovingOnGround())) return false;
        W.Look(FRotator(0,90,0));if(!W.World->InjectKey(EKeys::W,IE_Pressed)) return false;
        for(int F=0;F<300&&!W.Mode()->bDefeated&&W.Campaign()->RidgeRecoveries()==N;++F) if(!W.Tick(1)) return false;
        if(!W.World->InjectKey(EKeys::W,IE_Released)||!W.Tick(15)) return false;
        if(N<3)
        {
            TestEqual(TEXT("Deliberate fall spends one recovery"),W.Campaign()->RidgeRecoveries(),N+1);
            TestEqual(TEXT("Recovery costs exactly 25 HP"),W.Hero()->Health,static_cast<float>(Before-25));
            TestTrue(TEXT("Recovery lands on last brace anchor support"),FVector::Dist2D(W.Hero()->GetActorLocation(),W.Mode()->Arena()->RidgeAnchorFloor(W.Campaign()->RidgeLastAnchor()))<100);
        }
        else TestTrue(TEXT("Fourth deliberate fall requests checkpoint retry"),W.Mode()->bDefeated);
    }
    if(!WaitOnDefeatAndRetry(W,9)) return false;
    TestEqual(TEXT("Actual retry restarts b10"),W.Campaign()->ActiveBeat(),9);
    TestEqual(TEXT("Retry resets its bounded recovery allowance"),W.Campaign()->RidgeRecoveries(),0);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHangarFallsTest,"SoraArena.Campaign.HangarFalls",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHangarFallsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraWindAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("HangarFalls"),6,7);
    if(!Ready(W)) return false;
    const FVector O(W.BeatData().Space.Wind.Origin,0);
    for(bool Jump:{false,true})
    {
        // Walk from the real checkpoint around the stairs and shuttle 1.
        // No relocation, movement-mode override or synthetic fall event.
        for(const FVector P:{FVector(400,1400,0),FVector(2500,1400,0),FVector(2500,4000,0)})
            if(!SoraLiftAutomation::Walk(*W.World,O+P)) return false;
        if(!W.Tick(720)) return false;
        auto* Hero=W.Hero();
        if(!TestTrue(TEXT("Passive hangar wind stops at the exposed lip without defeat"),
            Hero->GetCharacterMovement()->IsMovingOnGround()&&!W.Mode()->bDefeated&&
            Hero->GetActorLocation().Y-O.Y>4400&&Hero->GetActorLocation().Y-O.Y<4500)) return false;
        W.Look(FRotator(0,90,0));
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)) return false;
        if(Jump)
        {
            const double Z=Hero->GetActorLocation().Z;
            if(!W.Press(EKeys::SpaceBar)||!W.Tick(3)||
                !TestTrue(TEXT("The normal Jump key launches through the open mouth"),
                    Hero->GetCharacterMovement()->IsFalling()&&Hero->GetActorLocation().Z>Z)) return false;
        }
        bool CrossedMouth=false;
        for(int Frame=0;Frame<360&&!W.Mode()->bDefeated;++Frame)
        {
            if(!W.Tick(1)) return false;
            CrossedMouth|=Hero->GetActorLocation().Y-O.Y>4500;
        }
        if(!W.World->InjectKey(EKeys::W,IE_Released)) return false;
        TestTrue(Jump?TEXT("A deliberate jump exits real hangar collision"):TEXT("A deliberate walk exits real hangar collision"),CrossedMouth);
        TestEqual(TEXT("A hangar fall never spends or grants a ridge cable recovery"),W.Campaign()->RidgeRecoveries(),0);
        if(!WaitOnDefeatAndRetry(W,7)) return false;
        TestTrue(TEXT("Retry returns to the hangar checkpoint entry"),
            FVector::Dist2D(W.Hero()->GetActorLocation(),FVector(W.BeatData().Space.Entry,0))<100);
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHangarSpawnClearanceTest,"SoraArena.Campaign.HangarSpawnClearance",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraHangarSpawnClearanceTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraWindAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("HangarSpawnClearance"),6,7);
    if(!Ready(W)) return false;
    const FVector O(W.BeatData().Space.Wind.Origin,0);
    TSet<int32> Checked;int Rifles=0;
    // Isolate layout and the real wave queue: production damage defeats one
    // frozen opponent at a time. This is not an ordinary-combat acceptance.
    for(int Pass=0;Pass<12&&W.Campaign()->ActiveBeat()==7;++Pass)
    {
        Freeze(W);ASoraEnemy* Next=nullptr;
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        {
            if(!It->IsAlive()) continue;
            Next=*It;
            const int Slot=It->EnemySlot();if(Checked.Contains(Slot)) continue;
            Checked.Add(Slot);
            const FVector At=It->GetActorLocation();const auto* Capsule=It->GetCapsuleComponent();
            FCollisionQueryParams Q(SCENE_QUERY_STAT(HangarSpawnClearance),false,*It);
            TestFalse(FString::Printf(TEXT("Wave slot %d has a clear actual capsule"),Slot),
                W.World->GetTestWorld()->OverlapBlockingTestByChannel(At,Capsule->GetComponentQuat(),ECC_Pawn,
                    FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),Q));
            if(!It->IsFlying())
            {
                FHitResult Support;
                const FVector Feet=At-FVector(0,0,Capsule->GetScaledCapsuleHalfHeight());
                TestTrue(FString::Printf(TEXT("Grounded wave slot %d has real nearby deck/gallery support"),Slot),
                    W.World->GetTestWorld()->LineTraceSingleByChannel(Support,Feet+FVector(0,0,5),Feet-FVector(0,0,150),ECC_Visibility,Q)&&
                    Support.ImpactNormal.Z>.9f);
            }
            if(It->ArchetypeId()==TEXT("enforcer_rifle"))
            {
                ++Rifles;
                const FVector Planned=O+FVector(7600,1900+(Slot<3?Slot:Slot-3)*300,120);
                TestTrue(TEXT("The forward rifle spawns on its explicit clear aisle instead of an adjusted proxy face"),FVector::Dist2D(At,Planned)<10);
            }
        }
        if(!TestNotNull(TEXT("The real wave queue supplies its next opponent"),Next)) return false;
        UGameplayStatics::ApplyDamage(Next,100000.f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
        Freeze(W);if(!W.Tick(1)) return false;
    }
    TestEqual(TEXT("All eleven authored hangar wave members receive collision checks"),Checked.Num(),11);
    TestEqual(TEXT("Both waves contain the same five authored rifles"),Rifles,5);
    TestEqual(TEXT("Defeating the unchanged roster advances into the hangar radio beat"),W.Campaign()->ActiveBeat(),8);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWindProjectilesTest,"SoraArena.Campaign.WindProjectiles",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWindProjectilesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraWindAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    for(int Beat:{7,9})
    {
        SoraFieldcraftAutomation::FBeatWorld W(*this,Beat==7?TEXT("HangarDrift"):TEXT("RidgeDrift"),6,Beat);
        if(!Ready(W)) return false;
        const bool Ridge=Beat==9;const FVector O(W.BeatData().Space.Wind.Origin,0);
        const double X=Ridge?500:2200,Y=Ridge?-100:4000;
        if(!Stand(W,X,Y)) return false;
        if(!Ridge)
        {
            const double Before=W.Hero()->GetActorLocation().Y;
            if(!W.Tick(60)) return false;
            TestTrue(TEXT("Hangar mouth has actual outward body push"),FMath::Abs(W.Hero()->GetActorLocation().Y-Before-120)<3);
            if(!W.Tick(360)) return false;
            TestTrue(TEXT("Open hangar lip blocks wind but has no wall"),W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&
                W.Hero()->GetActorLocation().Y-O.Y<4500);
            TestTrue(TEXT("Outside the mouth volume has no projectile wind"),W.Campaign()->ProjectileWind(O+FVector(1000,1600,200),true,18).IsZero());
            TestTrue(TEXT("Wind volume ends at authored 45 m mouth lip"),W.Campaign()->ProjectileWind(O+FVector(4000,4501,200),true,18).IsZero());
        }
        for(int Weapon:{18,7})
        {
            if(!Stand(W,X,Y)||!W.World->TakeUpArm(Weapon)||!W.Tick(45)) return false;
            W.Look(FRotator(25,0,0));
            if(!W.World->InjectKey(EKeys::LeftMouseButton,IE_Pressed)) return false;
            if(Weapon==18)
            {
                if(!W.Tick(45)||!TestTrue(TEXT("Mapped fire holds the actual bow at full draw"),W.Hero()->GetEquipment()->IsBowDrawing())) return false;
            }
            else if(!W.Tick(1)) return false;
            if(!W.World->InjectKey(EKeys::LeftMouseButton,IE_Released)||!W.Tick(1)) return false;
            ASoraProjectile* Shot=nullptr;
            for(TActorIterator<ASoraProjectile> It(W.World->GetTestWorld());It;++It)
                if(It->GetOwner()==W.Hero()&&It->WeaponId==Weapon) Shot=*It;
            if(!TestNotNull(TEXT("Real mapped release creates the requested projectile"),Shot)) return false;
            const double Vy=Shot->Velocity.Y; double Expected=0;
            for(int F=0;F<12;++F)
            {
                if(!IsValid(Shot)) { AddError(TEXT("Projectile collided before its wind sample completed")); return false; }
                Expected+=W.Campaign()->ProjectileWind(Shot->GetActorLocation(),Shot->bArrow,Shot->WeaponId).Y/60.;
                if(!W.Tick(1)) return false;
            }
            if(!TestTrue(TEXT("Projectile stays live through its original flight"),IsValid(Shot))) return false;
            AddInfo(FString::Printf(TEXT("Wind projectile beat=%d weapon=%d delta_vy=%.3f expected=%.3f"),Beat+1,Weapon,Shot->Velocity.Y-Vy,Expected));
            TestTrue(TEXT("Actual arrow/shell velocity receives the sampled environmental acceleration"),Expected>0&&FMath::Abs(Shot->Velocity.Y-Vy-Expected)<7);
            Shot->Destroy();if(!W.Tick(120)) return false;
        }
        if(Ridge)
        {
            TestTrue(TEXT("Projectile under a physical fin receives no drift until leaving its lee"),W.Campaign()->ProjectileWind(O+FVector(3100,0,150),true,18).IsZero());
            TestTrue(TEXT("Projectile above that fin is exposed"),!W.Campaign()->ProjectileWind(O+FVector(3100,0,500),true,18).IsZero());
        }
        // The actual hitscan event retains its camera ray; the wind service
        // is never invoked by the beam implementation.
        if(!Stand(W,X,Y)||!W.World->TakeUpArm(1)||!W.Tick(45)) return false;
        W.Look(FRotator(25,0,0));
        FSoraWeaponFiredEvent Beam;bool Fired=false;
        auto* Events=USoraGameEvents::Get(W.Hero());
        const auto Handle=Events->OnWeaponFired.AddLambda([&](const FSoraWeaponFiredEvent& E){if(E.Shooter==W.Hero()&&E.WeaponId==1){Beam=E;Fired=true;}});
        const FVector Aim=W.Hero()->GetCamera()->GetForwardVector();
        const bool Pressed=W.Press(EKeys::LeftMouseButton);
        Events->OnWeaponFired.Remove(Handle);
        if(!Pressed||!TestTrue(TEXT("Mapped hitscan fires"),Fired)) return false;
        TestTrue(TEXT("Hitscan direction is unchanged by real wind"),Beam.Direction.Equals(Aim,1.e-6));
        TestTrue(TEXT("Unrelated projectile weapon does not opt into wind"),W.Campaign()->ProjectileWind(O+FVector(X,Y,200),false,14).IsZero());
        if(!Ridge)
        {
            // A live grenadier's ordinary brain/attack spawns the enemy
            // shell; no synthetic velocity or direct detonation fixture.
            if(!Stand(W,2200,3700)) return false;
            auto* Grenadier=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("grenadier"),99,O+FVector(4000,4100,120),FRotator(0,180,0));
            if(!TestNotNull(TEXT("Ordinary enemy grenadier spawns"),Grenadier)) return false;
            ASoraProjectile* Shell=nullptr;
            for(int F=0;F<1200&&!Shell&&!W.Mode()->bDefeated;++F)
            {
                if(!W.Tick(1)) return false;
                for(TActorIterator<ASoraProjectile> It(W.World->GetTestWorld());It;++It)
                    if(It->GetOwner()==Grenadier) { Shell=*It; break; }
            }
            if(!TestNotNull(TEXT("Live enemy attack releases its shell"),Shell)) return false;
            const double Before=Shell->Velocity.Y;double Expected=0;
            for(int F=0;F<8;++F)
            {
                if(!IsValid(Shell)) { AddError(TEXT("Enemy shell ended before drift sample"));return false; }
                Expected+=W.Campaign()->ProjectileWind(Shell->GetActorLocation(),false,INDEX_NONE).Y/60.;
                if(!W.Tick(1)) return false;
            }
            TestTrue(TEXT("Actual enemy shell receives the same environmental acceleration"),IsValid(Shell)&&Expected>0&&FMath::Abs(Shell->Velocity.Y-Before-Expected)<7);
        }
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRidgeDroneWindTest,"SoraArena.Campaign.RidgeDroneWind",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRidgeDroneWindTest::RunTest(const FString& Parameters)
{
    (void)Parameters;using namespace SoraWindAutomation;
    if(!FSoraCatalog::Get().Load()) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("RidgeDroneWind"),6,9);
    if(!Ready(W)||!Stand(W,500,-200)) return false;
    auto* C=W.Campaign();auto* H=W.Hero();auto* Effects=USoraCombatEffects::Get(H);
    const FVector O(W.BeatData().Space.Wind.Origin,0);
    ASoraEnemy* Drone=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&It->ArchetypeId()==TEXT("drone")) { Drone=*It;break; }
    if(!TestNotNull(TEXT("Authored wave supplies the drone and its beat tuning"),Drone)||!Effects) return false;
    // Isolate attack/force behavior: keep its brain and movement component
    // frozen, but let the actual pawn wind up, cast its net and recover.
    // This supported setup does not claim autonomous combat or flight QA.
    Drone->SetActorLocation(O+FVector(500,-1000,450),false,nullptr,ETeleportType::TeleportPhysics);
    Drone->SetActorRotation(FRotator(0,(H->GetActorLocation()-Drone->GetActorLocation()).Rotation().Yaw,0));
    Drone->SetActorTickEnabled(true);
    if(!TestTrue(TEXT("Production net attack commits"),Drone->TryAttack(*H,FVector::Dist2D(H->GetActorLocation(),Drone->GetActorLocation())))) return false;
    for(int F=0;F<120&&!Effects->IsRooted(H);++F) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("Real net delivery roots the exposed hero"),Effects->IsRooted(H))) return false;
    const FVector Netted=H->GetActorLocation();int HeldFrames=0;
    while(Effects->IsRooted(H)&&HeldFrames<120)
    {
        if(!W.Tick(1)) return false;
        ++HeldFrames;
        if(Effects->IsRooted(H)) TestTrue(TEXT("Delivered net does not translate the hero in wind"),FVector::Dist(H->GetActorLocation(),Netted)<3);
    }
    TestTrue(TEXT("Ridge wave's net releases after authored 1.2 s, not generic 1.5 s"),HeldFrames>=70&&HeldFrames<=73&&!Effects->IsRooted(H));
    // At the first gust the prior net has fully recovered. Begin another
    // real 800 ms windup shortly before onset and observe its interruption.
    while(C->WindClockMs()<10400) if(!W.Tick(1)) return false;
    if(!Stand(W,500,-200)) return false;
    Drone->SetActorRotation(FRotator(0,(H->GetActorLocation()-Drone->GetActorLocation()).Rotation().Yaw,0));
    if(!TestTrue(TEXT("Drone is aiming before gust onset"),Drone->TryAttack(*H,FVector::Dist2D(H->GetActorLocation(),Drone->GetActorLocation()))&&Drone->IsWindingUp())) return false;
    while(C->WindClockMs()<11000) if(!W.Tick(1)) return false;
    TestFalse(TEXT("Actual gust cancels the in-progress aim"),Drone->IsAttacking());
    const double Before=Drone->GetActorLocation().Y;
    if(!W.Tick(30)) return false;
    TestTrue(TEXT("Actual exposed drone drifts during gust"),FMath::Abs(Drone->GetActorLocation().Y-Before-60)<3);
    TestFalse(TEXT("Drone cannot reacquire in the first 0.5 s of disruption"),Drone->TryAttack(*H,FVector::Dist2D(H->GetActorLocation(),Drone->GetActorLocation())));
    if(!W.Tick(10)) return false;
    Drone->SetActorRotation(FRotator(0,(H->GetActorLocation()-Drone->GetActorLocation()).Rotation().Yaw,0));
    TestTrue(TEXT("Aim can resume after the authored 0.6 s disruption"),Drone->TryAttack(*H,FVector::Dist2D(H->GetActorLocation(),Drone->GetActorLocation())));
    return !HasAnyErrors();
}

#endif
