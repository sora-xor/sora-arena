#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraProjectile.h"
#include "Engine/World.h"

bool USoraCampaignDirector::IsHorseShellDefense() const
{ return Mode().bCampaign&&ActiveSpace()&&ActiveSpace()->bHorseShell; }
bool USoraCampaignDirector::HorseShellSession(uint64 Generation) const
{
    return Generation==HorseShellGeneration&&IsHorseShellDefense()&&!Mode().bDefeated&&
        IsValid(GetOwner())&&!GetOwner()->IsActorBeingDestroyed();
}
void USoraCampaignDirector::BindHorseGrenadier(ASoraEnemy& Enemy,int32 Wave)
{
    if(!IsHorseShellDefense()||Wave!=SoraHorseShellRules::Wave||Enemy.ArchetypeId()!=TEXT("grenadier")) return;
    check(!HorseGrenadier.IsValid());
    HorseGrenadier=&Enemy; Enemy.BindHorseShell(*this,HorseShellGeneration);
}
void USoraCampaignDirector::ResetHorseShells()
{
    ++HorseShellGeneration;
    const auto Grenadier=HorseGrenadier; HorseGrenadier.Reset();
    // Detach every old reference before warning or projectile Destroy callbacks.
    const auto Shots=MoveTemp(HorseShells); HorseShells.Reset();
    if(Grenadier.IsValid()) Grenadier->CancelHorseShell();
    for(const auto& Shot:Shots) if(Shot.IsValid()) Shot->Destroy();
}
AActor* USoraCampaignDirector::HorseShellQuarry(const ASoraEnemy& Enemy,FVector& Landing) const
{
    if(!IsHorseShellDefense()||Mode().bDefeated||HorseGrenadier.Get()!=&Enemy||!Enemy.IsAlive()) return nullptr;
    ASoraHorse* Nearest=nullptr; double Best=TNumericLimits<double>::Max();
    for(int I=0;I<2;++I)
    {
        auto* Candidate=TreatmentHorse(I);
        if(!IsValid(Candidate)||Candidate->IsActorBeingDestroyed()||TaskState.TargetHp[I]<=0) continue;
        const double Distance=FVector::DistSquared2D(Enemy.GetActorLocation(),Candidate->GetActorLocation());
        if(Distance<Best) { Best=Distance; Nearest=Candidate; }
    }
    if(Nearest) Landing=Nearest->GetActorLocation()-FVector(0,0,90);
    return Nearest;
}
bool USoraCampaignDirector::RegisterHorseShell(ASoraProjectile& Projectile,uint64 Generation)
{
    if(!HorseShellSession(Generation)||Projectile.GetOwner()!=HorseGrenadier.Get()) return false;
    HorseShells.RemoveAll([](const auto& Shot) { return !Shot.IsValid(); });
    HorseShells.Add(&Projectile); return true;
}
void USoraCampaignDirector::ResolveHorseShell(ASoraProjectile& Projectile,uint64 Generation)
{
    const auto Current=[&] { return HorseShellSession(Generation)&&Projectile.HorseShellCurrent()&&
        HorseShells.Contains(TWeakObjectPtr<ASoraProjectile>(&Projectile)); };
    if(!Current()) return;
    const FVector At=Projectile.GetActorLocation();
    FCollisionObjectQueryParams Solid;
    Solid.AddObjectTypesToQuery(ECC_WorldStatic); Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    for(int I=0;I<2;++I)
    {
        if(!Current()) return;
        auto* Target=TreatmentHorse(I);
        if(!IsValid(Target)||Target->IsActorBeingDestroyed()||TaskState.TargetHp[I]<=0||
           FVector::DistSquared(At,Target->GetActorLocation())>FMath::Square(double(SoraHorseShellRules::RadiusCm))) continue;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraHorseShellBlast),false,&Projectile);
        Query.AddIgnoredActor(Target);
        if(GetWorld()->LineTraceTestByObjectType(At,Target->GetActorLocation(),Solid,Query)) continue;
        DamageDefendedTarget(I,SoraHorseShellRules::Damage);
    }
}
