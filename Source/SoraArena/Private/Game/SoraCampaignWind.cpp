#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraRidgeRules.h"
#include "SoraEquipmentComponent.h"
#include "SoraEnemy.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Combat/SoraCombatEffects.h"
#include "SoraGameMode.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"

void USoraCampaignDirector::ResetWind()
{
    // Terminal falls keep the existing pawn still on the result screen. The
    // ordinary checkpoint reset can then put that pawn back onto its floor.
    if(bWindFallHeld)
        if(auto* Hero=Mode().Hero()) Hero->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    bWindFallHeld=false;
    WindMs=0; WindWarningSerial=0; WindGustSerial=0; WindAnchor=INDEX_NONE;
    RidgeFalls=0; LastBraceAnchor=0; bWindLee=false; bWindHint=false;
    if(WindStrip) WindStrip->DestroyComponent();
    WindStrip=nullptr;
}
void USoraCampaignDirector::FinishWindFall(ASoraPlayerCharacter& Hero)
{
    ReleaseWindBrace();
    Hero.ResetDialogueInput();
    Hero.SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
    Hero.GetCharacterMovement()->DisableMovement();
    bWindFallHeld=true;
    Hero.Health=0;
    PlayerKilled();
}
void USoraCampaignDirector::ReleaseWindBrace() { WindAnchor=INDEX_NONE; }
bool USoraCampaignDirector::WindAt(const FVector& Point) const
{
    const auto* S=ActiveSpace();
    if(!S||!S->Wind.Enabled()||!Mode().bCampaign||Mode().bDeterministicPractice) return false;
    const FVector P=Point-FVector(S->Wind.Origin,0);
    if(S->Wind.Ridge()) return P.X>=0&&P.X<=18000&&FMath::Abs(P.Y)<=3000&&P.Z>=-800&&P.Z<=2200;
    return P.X>=2000&&P.X<=6000&&P.Y>=3300&&P.Y<=4500&&P.Z>=-500&&P.Z<=1400;
}
FVector USoraCampaignDirector::ProjectileWind(const FVector& Point,bool Arrow,int32 Weapon) const
{
    // Only real arrows and grenade/enemy shells opt in. Hitscan has no call
    // to this path. No hidden aim offset is applied when firing.
    if(!Mode().IsPlaying()||!WindAt(Point)||(!Arrow&&Weapon!=7&&Weapon!=INDEX_NONE)) return FVector::ZeroVector;
    if(ActiveSpace()->Wind.Ridge()&&Mode().Arena()&&Mode().Arena()->WindShelteredPoint(Point)) return FVector::ZeroVector;
    return FVector(0,SoraRidgeRules::Acceleration(SoraRidgeRules::At(WindMs).Speed),0);
}
bool USoraCampaignDirector::InteractWind(ASoraPlayerCharacter& Hero)
{
    const auto* S=ActiveSpace(); auto* World=Mode().Arena(); const auto* Kit=Hero.GetEquipment();
    if(!S||!S->Wind.Ridge()||!Mode().IsPlaying()||!Hero.CanPlay()||!World||!Hero.IsActionHeld(TEXT("Interact"))||
        Kit->IsCommittedStrike()||Kit->IsTriggerHeld()||Kit->IsBowDrawing()||Kit->IsStepping()||Kit->bReloading) return false;
    const int Anchor=World->ReachRidgeCable(Hero);
    if(Anchor==INDEX_NONE) return false;
    WindAnchor=Anchor; LastBraceAnchor=Anchor;
    Hero.GetCharacterMovement()->StopMovementImmediately(); Hero.ConsumeMovementInputVector();
    Fire(TEXT("wind_brace")); return true;
}
bool USoraCampaignDirector::RidgeReadyToComplete() const
{
    const auto* S=ActiveSpace(); const auto* Hero=Mode().Hero();
    return !S||!S->Wind.Ridge()||(Hero&&Hero->GetCharacterMovement()->IsMovingOnGround()&&S->Exit.Contains(Hero->GetActorLocation()));
}
void USoraCampaignDirector::TickWind(int32 DeltaMs)
{
    const auto* S=ActiveSpace(); auto* Hero=Mode().Hero(); auto* World=Mode().Arena();
    if(!S||!S->Wind.Enabled()||!Hero||!World||!Mode().IsPlaying()||!Hero->CanPlay()) { ReleaseWindBrace(); return; }
    WindMs+=DeltaMs;
    const auto Wind=SoraRidgeRules::At(WindMs);
    if(Wind.Warning&&Wind.Serial!=WindWarningSerial)
    {
        WindWarningSerial=Wind.Serial;
        Fire(TEXT("gust_warning")); // Fire also emits the authored :first row.
        // Text stays available without sound/color/flash perception; source
        // contains no synthetic voice or claim to the missing roar recording.
        if(S->Wind.Ridge())
            Notify(TEXT("突風が来る。綱を掴むか、肋材や鰭の陰へ。"),
                TEXT("Gust incoming. Brace on a cable or shelter behind a rib or fin."),3.5f);
        else
            Notify(TEXT("突風が来る。開口部から離れろ。"),
                TEXT("Gust incoming. Move back from the open hangar mouth."),3.5f);
    }
    if(WindAnchor!=INDEX_NONE&&(!Hero->IsActionHeld(TEXT("Interact"))||World->ReachRidgeCable(*Hero)==INDEX_NONE)) ReleaseWindBrace();
    const FVector P=Hero->GetActorLocation()-FVector(S->Wind.Origin,0);
    bWindLee=S->Wind.Ridge()&&World->WindLee(*Hero);
    if(S->Wind.Ridge()&&!bWindHint&&World->ReachRidgeCable(*Hero)!=INDEX_NONE)
    {
        bWindHint=true; const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
        Notify(FString::Printf(TEXT("%s を押している間、綱を掴む。"),*Key.Japanese),
            FString::Printf(TEXT("Hold %s to brace on the cable."),*Key.English),6.f);
    }
    const auto* Effects=USoraCombatEffects::Get(this);
    if(WindAt(Hero->GetActorLocation())&&!Hero->IsVaulting()&&!(Effects&&Effects->IsRooted(Hero)))
    {
        float Push=SoraRidgeRules::Push(Hero->IsCrouched(),IsWindBraced(),bWindLee)*DeltaMs/1000.f;
        const float Radius=Hero->GetCapsuleComponent()->GetScaledCapsuleRadius()+2;
        if(S->Wind.Ridge()) Push=SoraRidgeRules::GuardedPush(P.X,P.Y,Radius,Push);
        else Push=FMath::Max(0.f,FMath::Min(Push,4500.f-Radius-static_cast<float>(P.Y)));
        // Swept external displacement is not velocity. It cannot leave
        // residual drift on release, pause, a root/net or a cable anchor.
        if(Push>0) { FHitResult Hit; Hero->AddActorWorldOffset(FVector(0,Push,0),true,&Hit); }
    }
    // Beyond the open hangar mouth, a deliberate walk/jump falls to the
    // checkpoint defeat. It never receives the ridge's cable recovery.
    if(S->Wind.Kind==TEXT("hangar")&&P.Z<-550)
    { FinishWindFall(*Hero); return; }
    if(S->Wind.Ridge()&&P.Z<SoraRidgeRules::Height(FMath::Clamp(P.X,0.,18000.))-550)
    {
        ReleaseWindBrace();
        if(RidgeFalls>=SoraRidgeRules::Recoveries||Hero->Health<=SoraRidgeRules::FallCost)
        { FinishWindFall(*Hero); return; }
        ++RidgeFalls; Hero->Health-=SoraRidgeRules::FallCost;
        Hero->ResetDialogueInput();
        Hero->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        Hero->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
        const FVector At=World->RidgeAnchorFloor(LastBraceAnchor)+FVector(0,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3);
        Hero->SetActorLocation(At,false,nullptr,ETeleportType::TeleportPhysics);
        Fire(TEXT("ridge_fall_recovered"));
    }
    const bool GustBegan=Wind.Gust&&Wind.Serial!=WindGustSerial;
    if(GustBegan) WindGustSerial=Wind.Serial;
    for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
        if(It->IsAlive()&&It->Archetype()&&It->Archetype()->Behavior==ESoraEnemyBehavior::Drone&&WindAt(It->GetActorLocation()))
        {
            if(GustBegan) It->DisruptWindAim(SoraRidgeRules::DroneDisruptionMs);
            // Authored drone drift has no speed; use the same exposed-body
            // 120 cm/s only during gusts (explicit provisional choice).
            if(Wind.Gust) { FHitResult Hit; It->AddActorWorldOffset(FVector(0,SoraRidgeRules::DroneDriftCmS*DeltaMs/1000.f,0),true,&Hit); }
        }
    // A functional indigo strip on the actual upper yumi limb, not a HUD
    // decoration or fabricated wind meter. Final cloth/material is art work.
    if(!WindStrip&&Hero->WeaponId==18)
    {
        WindStrip=ASoraWorldBuilder::Shape(Hero,Hero->GetViewmodel(),TEXT("WindTenuguiProxy"),
            TEXT("/Engine/BasicShapes/Cube.Cube"),FVector(18,0,140),FVector(.035,.32,.004),FLinearColor(.08,.10,.24));
        WindStrip->SetOnlyOwnerSee(true); WindStrip->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
    }
    if(WindStrip)
    {
        WindStrip->SetVisibility(Hero->WeaponId==18&&!Hero->GetEquipment()->IsSheathing());
        const FVector Dir=Hero->GetViewmodel()->GetComponentTransform().InverseTransformVectorNoScale(FVector(0,1,0));
        const float Lift=Wind.Warning?.9f:Wind.Gust?1.f:.45f;
        WindStrip->SetRelativeLocation(FVector(18,0,140)+Dir*16*Lift-FVector(0,0,(1-Lift)*10));
        WindStrip->SetRelativeRotation(FRotationMatrix::MakeFromY(Dir*Lift-FVector(0,0,(1-Lift)*.6f)).Rotator());
        WindStrip->SetRelativeScale3D(FVector(.035,.32,.004));
    }
}
