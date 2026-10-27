#include "SoraCampaignDirector.h"
#include "SoraArchiveRules.h"
#include "SoraBoss.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

void USoraCampaignDirector::ResetArchiveReveal(float BlendSeconds)
{
    if(!bArchiveRevealPending&&!bArchiveReveal) return;
    const bool WasActive=bArchiveReveal;
    bArchiveRevealPending=false;bArchiveReveal=false;ArchiveRevealSeconds=0;
    if(WasActive)
    {
        if(auto* Rival=ArchiveRevealRival.Get()) Rival->SetActorRotation(FRotator(0,Rival->GetActorRotation().Yaw,0));
        EndCinematicCamera(BlendSeconds);
    }
    ArchiveRevealRival.Reset();
    if(IsValid(Mode().Arena())) Mode().Arena()->StageArchiveReveal(-1.f);
    RefreshDialogueHold();
}

bool USoraCampaignDirector::TickArchiveReveal(float DeltaSeconds)
{
    namespace R=SoraArchiveRules;
    const FSoraBeat* Beat=ActiveBeatData();
    if(!bArchiveRevealPending&&!bArchiveReveal) return false;
    auto* Hero=Mode().Hero();
    if(bArchiveRevealPending&&!ArchiveRevealRival.IsValid())
        for(const auto& Enemy:Enemies)
            if(auto* Candidate=Cast<ASoraBoss>(Enemy.Get());Candidate&&Candidate->IsAlive()) { ArchiveRevealRival=Candidate;break; }
    auto* Rival=ArchiveRevealRival.Get();
    if(!Beat||Beat->Id!=TEXT("ch06.b09")||!Hero||!Rival||!Rival->IsAlive())
    { ResetArchiveReveal();return false; }
    if(!bArchiveReveal)
    {
        // A combat bark already at the head keeps its complete duration.
        // The visual prologue begins only when the family exchange owns it.
        if(Queue.IsEmpty()||ActiveChapter()->Dialogue[Queue[0].Line].Id!=TEXT("ch06.b09.toranosuke.005")) return false;
        bArchiveReveal=true;bArchiveRevealPending=false;ArchiveRevealSeconds=0;
        ArchiveRevealOrigin=FVector(ActiveChapter()->Space.Zones[Beat->Space.Zone].Rect.Min,R::FloorCm);
        Hero->GetCharacterMovement()->StopMovementImmediately();
        Rival->GetCharacterMovement()->StopMovementImmediately();
        // A cinematic cut establishes clear marks in the east aisle. The
        // subsequent impact path never crosses the four duel posts.
        Hero->SetActorLocation(ArchiveRevealOrigin+FVector(2070,900,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),false,nullptr,ETeleportType::TeleportPhysics);
        Hero->SetActorRotation(FRotator::ZeroRotator);
        if(Hero->GetController()) Hero->GetController()->SetControlRotation(FRotator::ZeroRotator);
        if(!IsValid(ShotCamera))
        {
            FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            ShotCamera=GetWorld()->SpawnActor<ACameraActor>(ArchiveRevealOrigin,FRotator::ZeroRotator,Params);
        }
        if(IsValid(ShotCamera))
        {
            ShotCamera->GetCameraComponent()->SetFieldOfView(58.f);
            ShotCamera->GetCameraComponent()->SetConstraintAspectRatio(false);
            if(auto* PC=UGameplayStatics::GetPlayerController(this,0);PC&&PC->IsLocalController()) PC->SetViewTarget(ShotCamera);
        }
        RefreshDialogueHold();
    }
    const double Before=ArchiveRevealSeconds;
    ArchiveRevealSeconds=FMath::Min(R::RevealSeconds,Before+FMath::Max(0.f,DeltaSeconds));
    const double T=ArchiveRevealSeconds;
    const double Slam=FMath::SmoothStep(0.,1.,FMath::Clamp((T-.25)/(R::ImpactSeconds-.25),0.,1.));
    const double Recover=FMath::SmoothStep(0.,1.,FMath::Clamp((T-18.8)/1.2,0.,1.));
    const double X=FMath::Lerp(FMath::Lerp(2200.,2444.,Slam),1800.,Recover);
    // Recoil to the side before the record close-up. The old mark left the
    // rival's head and back-mounted equipment directly over the family page.
    const double Recoil=FMath::SmoothStep(0.,1.,FMath::Clamp((T-R::ImpactSeconds)/1.8,0.,1.));
    const double Y=FMath::Lerp(FMath::Lerp(900.,1080.,Recoil),900.,Recover);
    const double Lean=T<R::ImpactSeconds?Slam*18.:18.*FMath::Exp(-(T-R::ImpactSeconds)*2.);
    // The final reaction releases both characters back inside the authored
    // duel ring, along its clear central aisle between the four posts.
    Hero->SetActorLocation(ArchiveRevealOrigin+FVector(FMath::Lerp(2070.,1400.,Recover),900,
        Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),false,nullptr,ETeleportType::TeleportPhysics);
    Rival->SetActorLocationAndRotation(ArchiveRevealOrigin+FVector(X,Y,Rival->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),
        FRotator(-Lean,180,0),false,nullptr,ETeleportType::TeleportPhysics);
    if(Mode().Arena()) Mode().Arena()->StageArchiveReveal(T);
    if(IsValid(ShotCamera))
    {
        FVector At,Look;
        if(T<3.2)
        { At=FVector(1940,500,250);Look=FVector(2260,900,125); }
        else if(T<18.)
        {
            const double Dolly=FMath::SmoothStep(0.,1.,(T-3.2)/(18.-3.2));
            // Leave the full slate above the bilingual subtitle safe area.
            At=FMath::Lerp(FVector(2150,810,156),FVector(2170,825,153),Dolly);Look=FVector(2474,900,150);
        }
        else { At=FVector(2200,640,160);Look=FVector(X,Y,145); }
        ShotCamera->SetActorLocationAndRotation(ArchiveRevealOrigin+At,(Look-At).Rotation());
    }
    // The 4.6-second physical prologue and 15.4 seconds of authored speech
    // share one active-time clock. Pause never reaches this function.
    const double Speech=FMath::Max(0.,T-R::SpeechStartSeconds)-FMath::Max(0.,Before-R::SpeechStartSeconds);
    if(Speech>0) TickDialogue(Speech);
    if(!bArchiveReveal) return true; // A dialogue callback reset the encounter.
    const int32 Last=ActiveChapter()->LineIndex(TEXT("ch06.b09.toranosuke.006"));
    // Float subtitle countdowns can leave a sub-millisecond tail after an
    // exact 20-second interval. Consume only that tail, never a following cue.
    if(T>=R::RevealSeconds&&!FinishedLines.Contains(Last)&&!Queue.IsEmpty()&&Queue[0].Line==Last&&LineRemaining<.001f)
        TickDialogue(LineRemaining);
    if(T>=R::RevealSeconds&&FinishedLines.Contains(Last)) ResetArchiveReveal(.35f);
    return true;
}
