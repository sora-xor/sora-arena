#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraMaaiAutomation.h"
#include "SoraCatalog.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/ScopeExit.h"
#include "Templates/UniquePtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignMaaiTest,"SoraArena.Campaign.Maai",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignMaaiTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const FString Slot=FSoraAutomationWorld::UniqueSaveSlot(TEXT("CampaignMaai"));
    FSoraAutomationWorld::IgnoreMissingGeneratedArt(*this);
    FSoraAutomationWorld::IgnoreAbsentSaveSlot(*this,Slot);
    TUniquePtr<FSoraAutomationWorld> World;
    const auto Destroy=[&]() {
        if(World) { World->DestroyTestWorld(true); World->ForwardErrorMessages(this); World.Reset(); }
    };
    ON_SCOPE_EXIT { Destroy(); FSoraAutomationWorld::DeleteSaveSlot(Slot); };
    USoraSaveGame* Seed=NewObject<USoraSaveGame>();
    if(!TestTrue(TEXT("Opening lesson checkpoint seeded"),USoraCampaignDirector::SeedCheckpoint(*Seed,0,1)&&
        UGameplayStatics::SaveGameToSlot(Seed,Slot,0))) return false;
    const auto Start=[&]() {
        World=MakeUnique<FSoraAutomationWorld>();
        return World->Start(Slot)&&World->Tick(1)&&World->EnableKeyInput()&&
            World->PressKey(EKeys::Enter)&&World->PressKey(EKeys::Enter)&&World->Mode()->IsPlaying();
    };
    if(!TestTrue(TEXT("Distance lesson starts"),Start())) return false;
    auto* Campaign=World->Mode()->Campaign();
    ASoraPlayerCharacter* Hero=World->Player();
    ASoraEnemy* Mentor=Campaign->MaaiMentor();
    if(!TestNotNull(TEXT("Sekireisai is present"),Mentor)) return false;
    const FVector OriginalMentor=Mentor->GetActorLocation();
    const float OriginalHealth=Hero->Health;
    if(!World->Tick(120)) return false;
    TestTrue(TEXT("Mentor stands on the same clear floor as the hero"),Mentor->GetCharacterMovement()->IsMovingOnGround()&&
        FMath::Abs(Mentor->GetActorLocation().Z-Hero->GetActorLocation().Z)<3.f);
    TestEqual(TEXT("Waiting cannot bypass stance"),Campaign->DojoLessonStage(),0);
    TestFalse(TEXT("Mentor does not attack during his distance lesson"),Mentor->IsPupilWindup());
    TestEqual(TEXT("Hero is unharmed"),Hero->Health,OriginalHealth);
    if(!World->InjectKey(EKeys::LeftControl,IE_Pressed)||!World->Tick(45)||!World->InjectKey(EKeys::LeftControl,IE_Released)) return false;
    TestEqual(TEXT("Stance leaves the distance lesson active"),Campaign->ActiveBeat(),1);
    TestTrue(TEXT("Distance gate opens after stance"),Campaign->MaaiReady());
    if(!World->Tick(361)) return false;
    TestTrue(TEXT("Six idle seconds show the floor band"),Campaign->MaaiNeedsHelp());
    TestTrue(TEXT("Mentor waits at his mark"),FVector::Dist2D(Mentor->GetActorLocation(),OriginalMentor)<1.f);
    const FVector StartPosition=Hero->GetActorLocation();
    const auto Stand=[&](float Distance) {
        Hero->GetCharacterMovement()->StopMovementImmediately();
        const FVector Center=Mentor->GetActorLocation();
        Hero->SetActorLocation(FVector(Center.X-Distance,Center.Y,Hero->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
    };
    Stand(195.f);
    Hero->GetController()->SetControlRotation(FRotator(0,180,0));
    if(!World->Tick(40)) return false;
    TestFalse(TEXT("Correct distance while facing away shows no ring"),Campaign->MaaiInBand());
    TestFalse(TEXT("Facing away cannot acquire the band"),Campaign->TaskProgress().Maai.Acquired);
    Hero->GetController()->SetControlRotation(FRotator::ZeroRotator);
    if(!World->Tick(20)) return false;
    TestFalse(TEXT("A third of a second does not confirm the band"),Campaign->TaskProgress().Maai.Acquired);
    for(const auto Difficulty:{SoraAccessibility::EDifficulty::Easy,SoraAccessibility::EDifficulty::Normal,SoraAccessibility::EDifficulty::Hard})
    {
        World->Mode()->Settings()->SetCampaignDifficulty(Difficulty);
        if(!World->Tick(1)) return false;
        TestTrue(TEXT("The moon ring is present at every difficulty"),Campaign->MaaiInBand());
    }
    Hero->GetController()->SetControlRotation(FRotator(0,180,0));
    if(!World->Tick(1)) return false;
    TestEqual(TEXT("Turning away resets the continuous hold"),Campaign->TaskProgress().Maai.HeldMs,0);
    Stand(165.f); Hero->GetController()->SetControlRotation(FRotator::ZeroRotator);
    if(!World->Tick(1)) return false;
    TestFalse(TEXT("Too close shows no moon ring"),Campaign->MaaiInBand());
    TestTrue(TEXT("Too close raises the authored hint"),Campaign->QueuedSubtitles().ContainsByPredicate(
        [](const FSoraSubtitle& Line) { return Line.LineId==TEXT("ch01.b02.sekireisai.009"); }));
    Stand(225.f);
    if(!World->Tick(40)) return false;
    TestFalse(TEXT("Too far cannot acquire the band"),Campaign->TaskProgress().Maai.Acquired);
    TestFalse(TEXT("Too far shows no moon ring"),Campaign->MaaiInBand());
    Hero->SetActorLocation(StartPosition,false,nullptr,ETeleportType::TeleportPhysics);
    if(!TestTrue(TEXT("W/S movement recovers the first authored step"),SoraMaaiAutomation::Walk(*World,1))) return false;
    TestTrue(TEXT("The hero actually walked"),FVector::Dist2D(StartPosition,Hero->GetActorLocation())>50.f);
    TestEqual(TEXT("One recovered step cannot finish the lesson"),Campaign->ActiveBeat(),1);
    TestEqual(TEXT("Only one step is counted"),Campaign->TaskProgress().Maai.Done,1);
    TestTrue(TEXT("Mentor's first step is 120 cm"),FMath::IsNearlyEqual(FVector::Dist2D(OriginalMentor,Mentor->GetActorLocation()),120.f,2.f));
    TestFalse(TEXT("Confirmed step clears floor help"),Campaign->MaaiNeedsHelp());
    const auto HasLine=[&](const TCHAR* Id) { return Campaign->QueuedSubtitles().ContainsByPredicate(
        [Id](const FSoraSubtitle& Line) { return Line.LineId==Id; }); };
    TestTrue(TEXT("First recovered step raises its voiced acknowledgement"),HasLine(TEXT("ch01.b02.sekireisai.007")));
    // No partial lesson is a checkpoint: recreate the entire world from the
    // real saved beat start, then earn every gate again through player input.
    Destroy();
    if(!TestTrue(TEXT("Checkpoint reloads in a fresh world"),Start())) return false;
    Campaign=World->Mode()->Campaign(); Hero=World->Player();
    TestEqual(TEXT("Reload returns to opening lesson"),Campaign->ActiveBeat(),1);
    TestEqual(TEXT("Reload must relearn stance"),Campaign->DojoLessonStage(),0);
    TestEqual(TEXT("Reload grants no maai steps"),Campaign->TaskProgress().Maai.Done,0);
    TestFalse(TEXT("Reload retains no range acquisition"),Campaign->TaskProgress().Maai.Acquired);
    if(!World->InjectKey(EKeys::LeftControl,IE_Pressed)||!World->Tick(45)||!World->InjectKey(EKeys::LeftControl,IE_Released)) return false;
    Mentor=Campaign->MaaiMentor();
    const FVector RestoredMark=Mentor->GetActorLocation();
    if(!TestTrue(TEXT("First step is earned again after reload"),SoraMaaiAutomation::Walk(*World,1))) return false;
    const FVector FirstStep=Mentor->GetActorLocation();
    if(!TestTrue(TEXT("Left step requires a fresh recovered band"),SoraMaaiAutomation::Walk(*World,2))) return false;
    const FVector SecondStep=Mentor->GetActorLocation();
    const FVector Back=(FirstStep-RestoredMark).GetSafeNormal2D();
    const FVector Left=(SecondStep-FirstStep).GetSafeNormal2D();
    TestTrue(TEXT("Second mentor step is 150 cm"),FMath::IsNearlyEqual(FVector::Dist2D(FirstStep,SecondStep),150.f,2.f));
    TestTrue(TEXT("The second step is to the mentor's left"),FVector::DotProduct(Left,FVector::CrossProduct(FVector::UpVector,Back))>.99f);
    FVector LastMark=SecondStep;
    for(int32 Frame=0;Frame<600&&Campaign->IsMaaiLesson();++Frame)
    {
        LastMark=Mentor->GetActorLocation();
        if(!SoraMaaiAutomation::Steer(*World)||!World->Tick(1)) return false;
    }
    if(!World->InjectKey(EKeys::W,IE_Released)||!World->InjectKey(EKeys::S,IE_Released)) return false;
    TestTrue(TEXT("Third mentor step is 80 cm forward"),FMath::IsNearlyEqual(FVector::Dist2D(SecondStep,LastMark),80.f,2.f)&&
        FVector::DotProduct((LastMark-SecondStep).GetSafeNormal2D(),Back)<-.99f);
    TestEqual(TEXT("Third confirmation opens the next lesson"),Campaign->ActiveBeat(),2);
    TestTrue(TEXT("Distance lesson restores site zero"),(Campaign->Progress().SitesMask&1u)!=0);
    TestTrue(TEXT("Completed distance gate raises its final line"),HasLine(TEXT("ch01.b02.sekireisai.008")));
    auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!TestNotNull(TEXT("Next lesson writes checkpoint"),Saved)) return false;
    TestEqual(TEXT("Saved checkpoint is the next lesson"),Saved->CheckpointBeat,2);
    Destroy();
    if(!TestTrue(TEXT("Completed lesson reloads"),Start())) return false;
    TestEqual(TEXT("Completed maai is not replayed after checkpoint"),World->Mode()->Campaign()->ActiveBeat(),2);
    return !HasAnyErrors();
}
#endif
