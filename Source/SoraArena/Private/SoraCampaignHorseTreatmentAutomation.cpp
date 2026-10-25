#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraHorse.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"

namespace SoraTreatmentTest
{
using SoraFieldcraftAutomation::FBeatWorld;
void Isolate(FBeatWorld& W)
{
    // Isolate treatment from combat difficulty; existing siege damage still
    // goes through the normal defended-target API used by these tests.
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        It->SetActorTickEnabled(false); It->GetCharacterMovement()->StopMovementImmediately();
        It->GetCharacterMovement()->SetComponentTickEnabled(false);
        if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
    }
}
bool Tick(FBeatWorld& W,int Frames,float Dt=1.f/60.f)
{ for(int I=0;I<Frames;++I) { Isolate(W); if(!W.Tick(1,Dt)) return false; } return true; }
FKey Action(FBeatWorld& W,const TCHAR* Name)
{ for(const auto& Key:W.Hero()->GetActionKeys(Name)) if(!Key.IsGamepadKey()) return Key; return FKey(); }
bool Ready(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start()) return false;
    W.Harden();
    for(int I=0;I<1800&&!W.Mode()->IsPlaying();++I) if(!Tick(W,1)) return false;
    return W.Test.TestTrue(TEXT("Both indexed real horses are present in the treatment beat"),W.Mode()->IsPlaying()&&W.Campaign()->IsHorseTreatment()&&
        W.Campaign()->TreatmentHorse(0)&&W.Campaign()->TreatmentHorse(1));
}
bool WalkTo(FBeatWorld& W,FVector At)
{
    At.Z=0; auto* Hero=W.Hero(); auto* Nav=USoraNavigation::Get(Hero); TArray<FVector> Path;
    if(!Nav||!Nav->Settle()||!Nav->FindPath(Hero->GetActorLocation(),At,*Hero,Path)||Path.IsEmpty()) return false;
    Path.Add(At);
    for(const FVector& Point:Path)
    {
        for(int Frame=0;Frame<1200&&FVector::Dist2D(Hero->GetActorLocation(),Point)>20;++Frame)
        {
            const FRotator Facing=(Point-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
            Hero->GetController()->SetControlRotation(Facing); Hero->FaceRotation(Facing,0);
            if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,1)) return false;
        }
        if(FVector::Dist2D(Hero->GetActorLocation(),Point)>30) { W.World->InjectKey(EKeys::W,IE_Released); return false; }
    }
    return W.World->InjectKey(EKeys::W,IE_Released)&&Tick(W,4);
}
bool Walk(FBeatWorld& W,int Index)
{ return WalkTo(W,W.Campaign()->TreatmentHorse(Index)->GetActorLocation()+FVector(-180,0,0)); }
bool Hold(FBeatWorld& W,int Frames)
{ const FKey Key=Action(W,TEXT("Interact")); return W.World->InjectKey(Key,IE_Pressed)&&Tick(W,Frames)&&W.World->InjectKey(Key,IE_Released)&&Tick(W,1); }
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true); W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.World->Tick(1)||!W.World->EnableKeyInput()) return false;
    for(int N=0;N<3&&!W.Mode()->IsPlaying();++N) if(!W.Press(EKeys::Enter)) return false;
    W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName E) { W.Events.Add(E.ToString()); });
    W.Harden(); return Tick(W,4)&&W.Mode()->IsPlaying();
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHorseTreatmentHoldTest,"SoraArena.Campaign.HorseTreatmentHold",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraHorseTreatmentHoldTest::RunTest(const FString& Parameters)
{
    (void)Parameters; SoraTreatmentTest::FBeatWorld W(*this,TEXT("HorseTreatmentHold"),1,5);
    if(!SoraTreatmentTest::Ready(W)) return false;
    auto* C=W.Campaign(); const auto Use=SoraTreatmentTest::Action(W,TEXT("Interact"));
    for(int Index=0;Index<2;++Index)
    {
        if(!SoraTreatmentTest::Walk(W,Index)||!SoraTreatmentTest::Hold(W,125)) return false;
        TestTrue(TEXT("A full horse consumes no treatment or cooldown"),C->TaskProgress().TargetHp[Index]==400&&C->HorseTreatmentState().Cooldown[Index]==0);
        C->DamageDefendedTarget(Index,200);
        for(int Attempt=0;Attempt<2;++Attempt)
        {
            if(!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,60)) return false;
            TestTrue(TEXT("Mapped hold reserves hands and earns partial progress"),C->HorseTreatmentOccupiesHands()&&C->HorseTreatmentState().Index==Index&&C->HorseTreatmentState().HeldMs>=900&&W.Hero()->GetViewmodel()->bHiddenInGame);
            if(!W.World->InjectKey(Use,IE_Released)) return false;
            TestTrue(TEXT("Release discards partial treatment immediately"),C->HorseTreatmentState().Index==INDEX_NONE&&C->HorseTreatmentState().HeldMs==0);
        }
        TestEqual(TEXT("Separate short holds cannot heal"),C->TaskProgress().TargetHp[Index],200);
        if(!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,30)) return false;
        const int32 Weapon=W.Hero()->WeaponId,Ammo=W.Hero()->GetEquipment()->Ammo;
        for(const TCHAR* Name:{TEXT("Fire"),TEXT("Melee"),TEXT("Reload"),TEXT("Block"),TEXT("WeaponThree")})
            if(!W.Press(SoraTreatmentTest::Action(W,Name))) return false;
        TestTrue(TEXT("Treatment occupies hands throughout weapon input"),C->HorseTreatmentOccupiesHands()&&!W.Hero()->GetEquipment()->IsCommittedStrike()&&
            !W.Hero()->GetEquipment()->IsGuardHeld()&&!W.Hero()->GetEquipment()->bReloading&&W.Hero()->WeaponId==Weapon&&W.Hero()->GetEquipment()->Ammo==Ammo);
        SoraTreatmentTest::FBeatWorld::Hurt(*W.Hero(),1);
        TestFalse(TEXT("Real hero damage immediately cancels treatment"),C->HorseTreatmentOccupiesHands());
        if(!SoraTreatmentTest::Tick(W,125)||!W.World->InjectKey(Use,IE_Released)) return false;
        TestEqual(TEXT("Still-held input after damage cannot restart treatment"),C->TaskProgress().TargetHp[Index],200);
        if(!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,20)) return false;
        const FVector At=C->TreatmentHorse(Index)->GetActorLocation();
        auto* Arena=W.Mode()->Arena(); const FVector Mid=(W.Hero()->GetEye()->GetComponentLocation()+At)*.5;
        auto* Wall=ASoraWorldBuilder::Shape(Arena,Arena->GetRootComponent(),TEXT("TreatmentLosBlocker"),TEXT("/Engine/BasicShapes/Cube.Cube"),
            Arena->GetRootComponent()->GetComponentTransform().InverseTransformPosition(Mid),FVector(.1f,1.f,2.f),FLinearColor::Gray,true);
        if(!SoraTreatmentTest::Tick(W,2)) return false;
        TestFalse(TEXT("An intervening physical blocker cancels treatment"),C->HorseTreatmentOccupiesHands());
        Wall->DestroyComponent(); if(!W.World->InjectKey(Use,IE_Released)) return false;
        if(!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,20)||
            !SoraTreatmentTest::WalkTo(W,At+FVector(-500,0,0))||!W.World->InjectKey(Use,IE_Released)) return false;
        TestTrue(TEXT("Walking out of reach cancels without cooldown"),!C->HorseTreatmentOccupiesHands()&&C->HorseTreatmentState().Cooldown[Index]==0);
        if(!SoraTreatmentTest::Walk(W,Index)) return false;
        W.Look(FRotator(0,180,0));
        if(!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,20)||!W.Press(SoraTreatmentTest::Action(W,TEXT("Jump")))||!SoraTreatmentTest::Tick(W,2)) return false;
        TestTrue(TEXT("Jump cancels before landing or leaving horizontal reach"),!W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&!C->HorseTreatmentOccupiesHands());
        if(!W.World->InjectKey(Use,IE_Released)||!SoraTreatmentTest::Tick(W,90)||!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,20)||!W.Press(EKeys::Escape)) return false;
        TestTrue(TEXT("Menu opening cancels the hold"),W.Mode()->bMenu&&!C->HorseTreatmentOccupiesHands());
        if(!W.World->InjectKey(Use,IE_Released)||!W.Press(EKeys::Escape)||!SoraTreatmentTest::Tick(W,2)) return false;
        // Even a blocking target collider is ignored by the destination trace.
        auto* Body=Cast<UPrimitiveComponent>(C->TreatmentHorse(Index)->GetRootComponent());
        const auto Prior=Body->GetCollisionResponseToChannel(ECC_Visibility); Body->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
        if(!W.World->InjectKey(Use,IE_Pressed)) return false;
        for(int Frame=0;Frame<2200&&C->HorseTreatmentState().HeldMs<1990&&C->HorseTreatmentOccupiesHands();++Frame)
            if(!SoraTreatmentTest::Tick(W,1,.001f)) return false;
        TestTrue(TEXT("The target's own blocking collider permits treatment up to the deadline"),C->HorseTreatmentOccupiesHands()&&C->HorseTreatmentState().HeldMs>=1990);
        TestEqual(TEXT("No health is awarded before two seconds"),C->TaskProgress().TargetHp[Index],200);
        if(!SoraTreatmentTest::Tick(W,1,.025f)||!SoraTreatmentTest::Tick(W,120)||!W.World->InjectKey(Use,IE_Released)) return false;
        Body->SetCollisionResponseToChannel(ECC_Visibility,Prior);
        TestEqual(TEXT("Crossing two seconds heals exactly sixty once despite continued held input"),C->TaskProgress().TargetHp[Index],260);
        TestTrue(TEXT("Both localized objectives explain held treatment and target HP"),C->ObjectiveText().Contains(TEXT("2秒"))&&C->ObjectiveTextEnglish().Contains(TEXT("2 s"))&&C->ObjectiveTextEnglish().Contains(TEXT("260/400")));
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraHorseTreatmentCooldownTest,"SoraArena.Campaign.HorseTreatmentCooldownRetry",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraHorseTreatmentCooldownTest::RunTest(const FString& Parameters)
{
    (void)Parameters; SoraTreatmentTest::FBeatWorld W(*this,TEXT("HorseTreatmentCooldownRetry"),1,5);
    if(!SoraTreatmentTest::Ready(W)) return false;
    auto* C=W.Campaign(); const auto Use=SoraTreatmentTest::Action(W,TEXT("Interact"));
    C->DamageDefendedTarget(0,10); C->DamageDefendedTarget(1,150);
    if(!SoraTreatmentTest::WalkTo(W,FVector(W.BeatData().Space.Anchor,0))||!SoraTreatmentTest::Hold(W,125)) return false;
    TestTrue(TEXT("The generic work anchor cannot repair either horse"),C->TaskProgress().TargetHp[0]==390&&C->TaskProgress().TargetHp[1]==250);
    for(int Index=0;Index<2;++Index)
    {
        if(!SoraTreatmentTest::Walk(W,Index)||!SoraTreatmentTest::Hold(W,125)) return false;
        TestEqual(TEXT("Each target heals independently, capped at its four hundred HP"),C->TaskProgress().TargetHp[Index],Index==0?400:310);
    }
    TestTrue(TEXT("Treating the second horse does not reset the first cooldown"),C->HorseTreatmentState().Cooldown[0]>0&&C->HorseTreatmentState().Cooldown[1]>C->HorseTreatmentState().Cooldown[0]);
    if(!W.Press(EKeys::Escape)) return false;
    const auto Paused=C->HorseTreatmentState(); if(!W.Tick(180)) return false;
    TestTrue(TEXT("Both per-horse cooldowns pause with the menu"),C->HorseTreatmentState().Cooldown[0]==Paused.Cooldown[0]&&C->HorseTreatmentState().Cooldown[1]==Paused.Cooldown[1]);
    if(!W.Press(EKeys::Escape)) return false;
    C->DamageDefendedTarget(0,100);
    if(!SoraTreatmentTest::Walk(W,0)||!SoraTreatmentTest::Hold(W,125)) return false;
    TestEqual(TEXT("An injured horse on cooldown refuses a full new hold"),C->TaskProgress().TargetHp[0],300);
    for(int Frame=0;Frame<1500&&C->HorseTreatmentState().Cooldown[0]>0;++Frame) if(!SoraTreatmentTest::Tick(W,1)) return false;
    TestTrue(TEXT("Horse A becomes available while horse B has its own later deadline"),C->HorseTreatmentState().Cooldown[0]==0&&C->HorseTreatmentState().Cooldown[1]>0);
    if(!SoraTreatmentTest::Hold(W,125)) return false;
    TestEqual(TEXT("A fresh hold after its cooldown heals the first horse"),C->TaskProgress().TargetHp[0],360);
    TWeakObjectPtr<ASoraHorse> OldA=C->TreatmentHorse(0),OldB=C->TreatmentHorse(1);
    C->DamageDefendedTarget(1,400);
    TestTrue(TEXT("Losing either horse enters ordinary checkpoint failure and cancels work"),W.Mode()->bDefeated&&!C->HorseTreatmentOccupiesHands());
    if(!W.Press(EKeys::Enter)||!SoraTreatmentTest::Tick(W,4)) return false;
    TestTrue(TEXT("Retry clears old indexed actors, damage and both cooldowns"),!OldA.IsValid()&&!OldB.IsValid()&&C->TreatmentHorse(0)&&C->TreatmentHorse(1)&&
        C->TaskProgress().TargetHp[0]==400&&C->TaskProgress().TargetHp[1]==400&&C->HorseTreatmentState().Cooldown[0]==0&&C->HorseTreatmentState().Cooldown[1]==0);
    C->DamageDefendedTarget(1,100);
    if(!SoraTreatmentTest::Walk(W,1)||!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,30)) return false;
    TestTrue(TEXT("The second attempt has active treatment before failure"),C->HorseTreatmentOccupiesHands());
    C->DamageDefendedTarget(0,400);
    TestTrue(TEXT("The other horse's destruction immediately cancels active treatment"),W.Mode()->bDefeated&&!C->HorseTreatmentOccupiesHands()&&C->HorseTreatmentState().HeldMs==0);
    if(!W.World->InjectKey(Use,IE_Released)||!W.Press(EKeys::Enter)||!SoraTreatmentTest::Tick(W,4)) return false;
    C->DamageDefendedTarget(0,100);
    if(!SoraTreatmentTest::Walk(W,0)||!W.World->InjectKey(Use,IE_Pressed)||!SoraTreatmentTest::Tick(W,30)||!SoraTreatmentTest::Reload(W)) return false;
    C=W.Campaign();
    TestTrue(TEXT("Loading the canonical checkpoint restores targets with no partial hold or cooldown"),C->IsHorseTreatment()&&C->TreatmentHorse(0)&&C->TreatmentHorse(1)&&
        C->TaskProgress().TargetHp[0]==400&&C->TaskProgress().TargetHp[1]==400&&C->HorseTreatmentState().Index==INDEX_NONE&&
        C->HorseTreatmentState().Cooldown[0]==0&&C->HorseTreatmentState().Cooldown[1]==0);
    return !HasAnyErrors();
}
#endif
