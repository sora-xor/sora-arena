#include "SoraWorldBuilder.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraDamage.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "World/SoraNavigation.h"
#include <limits>

namespace Margin=SoraMarginRules;

void ASoraWorldBuilder::CancelMargin()
{
    for(UStaticMeshComponent* Mark:MarginMarks) if(IsValid(Mark)) Mark->DestroyComponent();
    MarginMarks.Reset(); MarginIds.Reset(); MarginPoints.Reset(); MarginBoss.Reset();
    MarginElapsedMs=-1; MarginAttack=INDEX_NONE; bMarginReleased=false;
}
void ASoraWorldBuilder::StageMargin(bool Restore)
{
    CancelMargin(); MarginState.LeavePhase(); MarginClockCarry=0;
    if(!Restore) return;
    MarginState={}; MarginSerial=0;
    if(MarginConsoles.Num()!=Margin::Consoles)
        UE_LOG(LogTemp,Error,TEXT("SORA margin call requires fifteen physical bridge consoles"));
    for(UStaticMeshComponent* Console:MarginConsoles) if(IsValid(Console))
    {
        Console->SetVisibility(true); Console->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Console->SetCanEverAffectNavigation(true); Tint(Console,FLinearColor(.23f,.27f,.28f));
    }
}
void ASoraWorldBuilder::SelectMarginTargets(const ASoraPlayerCharacter& Hero,TArray<int32>& Ids,TArray<FVector>& LocalPoints) const
{
    Ids.Reset(); LocalPoints.Reset();
    if(!BridgeRoot||MarginConsoles.Num()!=Margin::Consoles) return;
    const FTransform Deck=BridgeRoot->GetComponentTransform();
    const FVector Feet=Hero.GetActorLocation()-FVector(0,0,Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    std::array<double,Margin::Consoles> Distances;
    Distances.fill(std::numeric_limits<double>::infinity());
    for(int32 Id=0;Id<MarginConsoles.Num();++Id)
        if(const auto* Console=MarginConsoles[Id].Get();IsValid(Console)&&Console->IsCollisionEnabled())
        {
            const FVector Local=Console->GetRelativeLocation()-FVector(0,0,Margin::ConsoleHeightCm*.5f);
            Distances[Id]=FVector::DistSquared(Feet,Deck.TransformPosition(Local));
        }
    for(int32 Id:MarginState.Select(Distances))
    {
        Ids.Add(Id);
        LocalPoints.Add(MarginConsoles[Id]->GetRelativeLocation()-FVector(0,0,Margin::ConsoleHeightCm*.5f));
    }
    // No padding with invented extra rings when fewer than three covers exist.
    if(Ids.IsEmpty())
    {
        Ids.Add(INDEX_NONE);
        FVector Local=Deck.InverseTransformPosition(Feet); Local.Z=0;
        LocalPoints.Add(Local);
    }
}
bool ASoraWorldBuilder::BridgeMarginPoints(const ASoraPlayerCharacter& Hero,TArray<FVector>& Points) const
{
    if(!HasBridgeDeck()||MarginIsPending()||MarginConsoles.Num()!=Margin::Consoles) return false;
    TArray<int32> Ids; TArray<FVector> LocalPoints;
    SelectMarginTargets(Hero,Ids,LocalPoints);
    for(const auto& Local:LocalPoints) Points.Add(BridgeRoot->GetComponentTransform().TransformPosition(Local));
    return !LocalPoints.IsEmpty();
}
bool ASoraWorldBuilder::BeginBridgeMargin(ASoraBoss& Boss,int32 Attack,int32 Serial)
{
    auto* Mode=GetWorld()->GetAuthGameMode<ASoraGameMode>();
    if(!Mode||!Mode->Hero()||Mode->Campaign()->CampaignBoss()!=&Boss||!HasBridgeDeck()||MarginIsPending()||
        MarginConsoles.Num()!=Margin::Consoles||Serial<=MarginSerial||Boss.BossId()!=TEXT("boss_collatera")||Boss.PhaseIndex()!=1||Boss.IsDefeated()||
        !Boss.Data()||!Boss.Data()->Attacks.IsValidIndex(Attack)||Boss.Data()->Attacks[Attack].Id!=TEXT("margin_call")) return false;
    SelectMarginTargets(*Mode->Hero(),MarginIds,MarginPoints);
    if(MarginPoints.IsEmpty()) return false;
    MarginState.ConsumePin();
    MarginBoss=&Boss; MarginAttack=Attack; MarginSerial=Serial; MarginElapsedMs=0;
    MarginWarningMs=Boss.WindupFor(Attack); bMarginReleased=false;
    const FLinearColor Amber=SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Cleave);
    for(const auto& Local:MarginPoints)
    {
        auto* Fill=Shape(this,BridgeRoot,TEXT("MarginFill"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
            Local+FVector(0,0,2),FVector(Margin::RadiusCm/50.f,Margin::RadiusCm/50.f,.02f),Amber);
        MarginMarks.Add(Fill);
        for(int32 Segment=0;Segment<16;++Segment)
        {
            const FVector A=Local+FVector(Margin::RadiusCm,0,3).RotateAngleAxis(Segment*22.5f,FVector::UpVector);
            const FVector B=Local+FVector(Margin::RadiusCm,0,3).RotateAngleAxis((Segment+1)*22.5f,FVector::UpVector);
            auto* Edge=Shape(this,BridgeRoot,TEXT("MarginRing"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
                (A+B)*.5f,FVector(.05f,.05f,FVector::Dist(A,B)/100.f),Amber);
            Edge->SetRelativeRotation(FRotationMatrix::MakeFromZ(B-A).Rotator()); MarginMarks.Add(Edge);
        }
    }
    return true;
}
void ASoraWorldBuilder::TickMargin(float DeltaSeconds,const ASoraBoss* CurrentBoss)
{
    if(!CurrentBoss||CurrentBoss->BossId()!=TEXT("boss_collatera")||CurrentBoss->PhaseIndex()!=1||CurrentBoss->IsDefeated())
    { CancelMargin(); MarginState.LeavePhase(); MarginClockCarry=0; return; }
    auto* Mode=GetWorld()->GetAuthGameMode<ASoraGameMode>();
    auto* Hero=Mode?Mode->Hero():nullptr;
    if(!Hero) { CancelMargin(); MarginState.LeavePhase(); return; }
    MarginClockCarry+=FMath::Max(0.f,DeltaSeconds)*1000.0;
    const int32 Elapsed=FMath::FloorToInt(MarginClockCarry); MarginClockCarry-=Elapsed;
    int32 Sheltering=INDEX_NONE;
    if(Hero->GetCharacterMovement()->IsMovingOnGround())
    {
        const FHitResult Aim=CurrentBoss->RangedAimTrace(*Hero);
        if(Aim.bBlockingHit) Sheltering=MarginConsoles.IndexOfByPredicate([&](const auto& Console) { return Console.Get()==Aim.GetComponent(); });
    }
    if(MarginState.Observe(Sheltering,Elapsed)) Mode->Campaign()->RaiseBeatEvent(TEXT("idle_in_cover_s:6"));
    if(!MarginIsPending()) return;
    ASoraBoss* Boss=MarginBoss.Get();
    if(!Boss||Boss!=CurrentBoss) { CancelMargin(); return; }
    const double Before=MarginElapsedMs;
    MarginElapsedMs+=FMath::Max(0.f,DeltaSeconds)*1000.0;
    if(Margin::Release(Before,MarginElapsedMs,MarginWarningMs,bMarginReleased))
    {
        bMarginReleased=true;
        Boss->AnnounceStrike(MarginAttack,MarginSerial);
        const FTransform Deck=BridgeRoot->GetComponentTransform();
        const FVector Up=Deck.TransformVectorNoScale(FVector::UpVector);
        const FVector HeroLocal=Deck.InverseTransformPosition(Hero->GetActorLocation());
        const float Radius=Margin::RadiusCm+Hero->GetCapsuleComponent()->GetScaledCapsuleRadius();
        bool NavigationChanged=false;
        for(int32 N=0;N<MarginPoints.Num();++N)
        {
            const FVector Impact=Deck.TransformPosition(MarginPoints[N]);
            SoraDamage::Beam(GetWorld(),Impact+Up*BridgeCeilingCm,Impact,FLinearColor(1,.65f,.1f),2.f,.16f);
            // Cover takes the announced strike even when its sheltering hero
            // leaves the ring. A serial can hit each physical console once.
            const int32 Id=MarginIds[N];
            if(MarginConsoles.IsValidIndex(Id)&&IsValid(MarginConsoles[Id])&&MarginConsoles[Id]->IsCollisionEnabled()&&MarginState.Strike(Id,MarginSerial))
            {
                auto* Console=MarginConsoles[Id].Get();
                Console->SetCollisionEnabled(ECollisionEnabled::NoCollision); Console->SetCanEverAffectNavigation(false);
                Console->SetVisibility(false); NavigationChanged=true;
            }
            if(FVector::DistSquared2D(HeroLocal,MarginPoints[N])<=Radius*Radius&&
                HeroLocal.Z>=0&&HeroLocal.Z<=BridgeCeilingCm+Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())
            {
                FHitResult Contact; Contact.Location=Hero->GetActorLocation(); Contact.ImpactPoint=Contact.Location;
                FSoraHit Hit=FSoraHit::Hazard(Impact); Hit.AttackId=TEXT("margin_call");
                SoraDamage::Strike(Hero,Margin::Damage,Hit,(Hero->GetActorLocation()-Impact).GetSafeNormal2D(),Contact,Boss->GetController(),Boss);
            }
        }
        for(int32 Id=0;Id<MarginConsoles.Num();++Id)
            if(MarginState.Live(Id)) Tint(MarginConsoles[Id],MarginState.Reinforced()?FLinearColor(.5f,.42f,.2f):
                MarginState.Hits[Id]?FLinearColor(.38f,.17f,.12f):FLinearColor(.23f,.27f,.28f));
        if(NavigationChanged)
            if(auto* Nav=USoraNavigation::Get(this);Nav&&!Nav->Settle())
                UE_LOG(LogTemp,Error,TEXT("SORA margin call navigation did not settle after console destruction"));
    }
    if(bMarginReleased&&MarginElapsedMs>=MarginWarningMs+200) CancelMargin();
}
