#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraBoss.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraInputStates.h"
#include "Combat/SoraBossCatalog.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignCaneThrustTest,"SoraArena.Campaign.CollectorCaneThrust",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignCaneThrustTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(int32 InputMode=0;InputMode<3;++InputMode) // keyboard, rebound keyboard, pad
    {
        // Directed setup: seed the real P3 checkpoint, raise health, and place
        // both bodies on a clear summit tile. Only attack selection is forced;
        // its clock, lock, collision, damage and mapped defenses run normally.
        SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("CollectorCaneThrust"),7,13);
        if(!W.Start(0,INDEX_NONE,2)) return false;
        W.Harden();
        auto* Hero=W.Hero(); auto* Kit=Hero->GetEquipment();
        auto* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
        if(!TestNotNull(TEXT("The actual summit cane-phase Collector is present"),Boss)||
            !TestEqual(TEXT("The fixture begins in P3"),Boss->PhaseIndex(),2)) return false;
        Boss->Hold(120000);
        if(!W.World->TakeUpArm(0)) return false;
        const bool Pad=InputMode==2;
        const auto Key=[&](const TCHAR* Action)
        {
            for(const FKey& Bound:Hero->GetActionKeys(Action)) if(Bound.IsGamepadKey()==Pad) return Bound;
            return FKey();
        };
        const int32 RightControl=SoraInput::FindRemappable(TEXT("MoveRight"),1);
        if(InputMode==1)
        {
            if(!W.Press(EKeys::Escape)||!Hero->RemapCombatAction(TEXT("Block"),EKeys::G)||
                !Hero->RemapCombatAction(TEXT("Jump"),EKeys::J)||
                Hero->RemapControl(RightControl,EKeys::L)!=ESoraRemapResult::Done) return false;
            W.Mode()->ResumePlay();
            if(!W.Tick(2)||!TestTrue(TEXT("Rebound defense and movement replace the old keyboard slots"),
                Key(TEXT("Block"))==EKeys::G&&Key(TEXT("Jump"))==EKeys::J&&Hero->ControlKey(RightControl,false)==EKeys::L)) return false;
        }
        const FKey Guard=Key(TEXT("Block")),Jump=Key(TEXT("Jump"));
        const FKey Right=Pad?EKeys::Gamepad_LeftX:Hero->ControlKey(RightControl,false);
        if(!TestTrue(TEXT("The active guard, jump and side controls exist"),Guard.IsValid()&&Jump.IsValid()&&Right.IsValid())) return false;
        if(Pad)
        {
            const auto* PC=Cast<APlayerController>(Hero->GetController());
            if(!TestTrue(TEXT("The pad stick drives the actual MoveRight axis"),PC&&PC->PlayerInput&&
                PC->PlayerInput->AxisMappings.ContainsByPredicate([](const FInputAxisKeyMapping& Map)
                { return Map.AxisName==TEXT("MoveRight")&&Map.Key==EKeys::Gamepad_LeftX&&Map.Scale==1.f; }))) return false;
        }
        const auto Side=[&](bool Down)
        { return Pad?W.World->InjectAxis(Right,Down?1.f:0.f):W.World->InjectKey(Right,Down?IE_Pressed:IE_Released); };
        auto* Bus=USoraGameEvents::Get(W.World->GetTestWorld());
        if(!TestNotNull(TEXT("Actual damage, defense and attack events are observable"),Bus)) return false;
        float Damage=0.f; int32 Guards=0,Parries=0,Rolls=0,Windups=0,Strikes=0,WindupMs=0;
        int32 WindupAt=-1,StrikeAt=-1; bool AfterAwase=false;
        const auto Damaged=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
        { if(E.Victim==Hero&&E.Causer==Boss) Damage+=E.Amount; });
        const auto Guarded=Bus->OnGuarded.AddLambda([&](const FSoraDefenseEvent& E)
        { if(E.Defender==Hero&&E.Attacker==Boss) ++Guards; });
        const auto Parried=Bus->OnParried.AddLambda([&](const FSoraDefenseEvent& E)
        { if(E.Defender==Hero&&E.Attacker==Boss) ++Parries; });
        const auto Rolled=Bus->OnMarobashi.AddLambda([&](const FSoraMarobashiEvent& E)
        { if(E.Hero==Hero&&E.Opponent==Boss) { ++Rolls; AfterAwase=E.bAfterAwase; } });
        const auto Phased=Bus->OnBossPhase.AddLambda([&](const FSoraBossPhaseEvent& E)
        {
            if(E.Boss!=Boss||E.Detail!=TEXT("amort_cane_thrust")) return;
            const int32 Now=FMath::FloorToInt(W.World->GetTestWorld()->GetTimeSeconds()*1000);
            if(E.Phase==ESoraBossPhase::Windup) { ++Windups; WindupMs=E.WindupMs; WindupAt=Now; }
            if(E.Phase==ESoraBossPhase::Strike) { ++Strikes; StrikeAt=Now; }
        });
        ON_SCOPE_EXIT
        {
            W.World->InjectKey(Guard,IE_Released); W.World->InjectKey(Jump,IE_Released); Side(false);
            Bus->OnDamaged.Remove(Damaged); Bus->OnGuarded.Remove(Guarded); Bus->OnParried.Remove(Parried);
            Bus->OnMarobashi.Remove(Rolled); Bus->OnBossPhase.Remove(Phased);
        };
        const auto Until=[&](const auto& Predicate,int32 Frames=180)
        {
            for(int32 Frame=0;Frame<Frames&&!Predicate();++Frame) if(!W.Tick(1)) return false;
            return TestTrue(TEXT("The bounded real thrust reaches the requested state"),Predicate());
        };
        for(int32 Response=0;Response<3;++Response) // none, fresh frontal guard, late side+Jump
        {
            if(!Until([&]() { return Boss->BossAttackIndex()==INDEX_NONE&&!Boss->IsStaggered()&&!Boss->IsInvulnerable()&&!Kit->IsStepping(); })) return false;
            const FVector Floor(W.BeatData().Space.Summit.Center+FVector2D(900,0),16000);
            for(ACharacter* Body:{static_cast<ACharacter*>(Boss),static_cast<ACharacter*>(Hero)})
            {
                Body->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
                Body->GetCharacterMovement()->StopMovementImmediately();
                const FVector Offset(Body==Hero?220:0,0,Body->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2);
                Body->SetActorLocation(Floor+Offset,false,nullptr,ETeleportType::TeleportPhysics);
            }
            W.LookAt(Boss->GetActorLocation());
            if(!W.Tick(3)||!Until([&]() { return Hero->GetCharacterMovement()->IsMovingOnGround(); },60)) return false;
            if(!TestTrue(TEXT("The drawn katana starts without a held guard"),Hero->WeaponId==0&&!Kit->IsSheathing()&&!Kit->IsGuardHeld())) return false;
            FHitResult Line;
            FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraCaneThrustTest),false,Hero);
            if(!TestTrue(TEXT("The real summit geometry leaves a clear line to the Collector"),
                W.World->GetTestWorld()->LineTraceSingleByChannel(Line,Hero->GetActorLocation(),Boss->GetActorLocation(),ECC_Visibility,Query)&&Line.GetActor()==Boss)) return false;
            Damage=0; Guards=0; Parries=0; Rolls=0; Windups=0; Strikes=0; WindupAt=-1; StrikeAt=-1; AfterAwase=false;
            if(!Boss->ForceAttack(TEXT("amort_cane_thrust"))||!Until([&]() { return Boss->IsBossTelegraphing(); })) return false;
            if(!TestTrue(TEXT("The real cyan thrust retains its original 600 ms warning"),Windups==1&&WindupMs==600&&
                Boss->BossAttack()&&Boss->BossAttack()->Telegraph==ESoraBossTelegraph::Cyan)) return false;
            FVector RollFrom=Hero->GetActorLocation();
            if(Response==1)
            {
                if(!Until([&]() { return Boss->BossWarningSeconds()<=.10f; })||
                    !W.World->InjectKey(Guard,IE_Pressed)||!TestTrue(TEXT("The fresh mapped guard is actually held"),Kit->IsGuardHeld())) return false;
            }
            else if(Response==2)
            {
                if(!Until([&]() { return Boss->BossWarningSeconds()<=.25f; })||!Side(true)) return false;
                RollFrom=Hero->GetActorLocation();
                if(!W.World->InjectKey(Jump,IE_Pressed)||!W.Tick(1)||
                    !W.World->InjectKey(Jump,IE_Released)||!Side(false)) return false;
                if(!TestTrue(TEXT("Mapped side plus Jump enters the live marobashi window"),Rolls==1&&!AfterAwase&&Kit->IsStepping()&&Boss->IsTurnLocked())) return false;
            }
            if(!Until([&]() { return Boss->IsRecovering(); })||!W.World->InjectKey(Guard,IE_Released)||!W.Tick(1)) return false;
            TestTrue(TEXT("The strike observes the original warning on the advancing world clock"),
                Strikes==1&&StrikeAt-WindupAt>=600&&StrikeAt-WindupAt<=650);
            TestEqual(TEXT("The cyan cane thrust never produces a parry"),Parries,0);
            TestEqual(TEXT("The real thrust applies its authored damage or guard chip"),Damage,Response==0?28.f:Response==1?14.f:0.f);
            TestEqual(TEXT("Only the fresh frontal guard emits a guard event"),Guards,Response==1?1:0);
            TestEqual(TEXT("Only side plus Jump emits marobashi"),Rolls,Response==2?1:0);
            if(Response==2)
            {
                TestTrue(TEXT("The step moves the capsule off the locked line on the solid summit floor"),
                    FMath::Abs(Hero->GetActorLocation().Y-RollFrom.Y)>100&&Hero->GetCharacterMovement()->IsMovingOnGround());
                FCollisionQueryParams SolidQuery(SCENE_QUERY_STAT(SoraCaneThrustRoll),false,Hero);
                TestFalse(TEXT("The resulting capsule does not penetrate summit collision"),
                    W.World->GetTestWorld()->OverlapBlockingTestByChannel(Hero->GetActorLocation(),FQuat::Identity,ECC_Pawn,
                        FCollisionShape::MakeCapsule(Hero->GetCapsuleComponent()->GetScaledCapsuleRadius(),
                            Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-.5f),SolidQuery));
            }
            TestTrue(TEXT("A normal cane defense neither captures nor changes the phase"),Boss->IsAlive()&&Boss->PhaseIndex()==2&&!W.Campaign()->AwaitingCapture());
            AddInfo(FString::Printf(TEXT("Collector cane thrust: input=%d response=%d windup=%d elapsed=%d damage=%.1f guard=%d parry=%d marobashi=%d displacement=%.1f"),
                InputMode,Response,WindupMs,StrikeAt-WindupAt,Damage,Guards,Parries,Rolls,FVector::Dist2D(RollFrom,Hero->GetActorLocation())));
            if(HasAnyErrors()) return false;
        }
    }
    return !HasAnyErrors();
}
#endif
