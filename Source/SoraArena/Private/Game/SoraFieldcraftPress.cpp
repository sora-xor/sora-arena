#include "SoraFieldcraft.h"
#include "SoraPressRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraGameMode.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Game/SoraCampaignReach.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace Press=SoraPressRules;

FVector USoraFieldcraft::PressCenter(int32 Index) const
{
    return PressHall&&Index>=0&&Index<Press::Count
        ?FVector(PressHall->Origin+FVector2D(Press::Centers[Index].X,Press::Centers[Index].Y),0):FVector::ZeroVector;
}
bool USoraFieldcraft::PressRunning(int32 Index) const
{ return PressHall&&Press::Running(JammedPresses,Index); }
bool USoraFieldcraft::NearRunningPress(const FVector& Origin) const
{
    if(!PressHall) return false;
    // The impact is 80 cm above the floor. Distance is from the sound's
    // source, not its listener; a catwalk outside this sphere stays exposed.
    for(int32 I=0;I<Press::Count;++I)
        if(PressRunning(I)&&FVector::DistSquared(Origin,PressCenter(I)+FVector(0,0,80))<=FMath::Square(float(Press::RadiusCm)))
            return true;
    return false;
}
int32 USoraFieldcraft::PressNoisePermille(const FVector& Origin) const
{ return NearRunningPress(Origin)&&Press::Masking(PressClockMs)?Press::NoisePermille:1000; }
int32 USoraFieldcraft::PressMaskedMs(const FVector& Origin,int32 IntervalMs) const
{
    return IntervalMs>0&&NearRunningPress(Origin)
        ?int32(Press::MaskedBetween(FMath::Max<int64>(0,PressClockMs-IntervalMs),PressClockMs)):0;
}
bool USoraFieldcraft::CanWorkPress(int32 Objective) const
{
    if(!PressHall||Objective==3) return true;
    ASoraPlayerCharacter* Player=Hero();
    if(Objective<0||Objective>=3||!Player||!Player->GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Center=PressCenter(Press::Master[Objective]);
    if(FVector::Dist2D(Player->GetActorLocation(),Center+FVector(0,-240,0))>SoraCampaignReach::Interact) return false;
    const float FeetZ=Player->GetActorLocation().Z-Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(FeetZ-Center.Z)>120.f) return false;
    const FVector Handle=Center+FVector(0,-170,110);
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(PressWork),false,Player);
    return !GetWorld()->LineTraceSingleByChannel(Hit,Player->GetEye()->GetComponentLocation(),Handle,ECC_Visibility,Query);
}
void USoraFieldcraft::AdvancePressClock(UWorld* World,ELevelTick TickType,float DeltaSeconds)
{
    (void)TickType;
    const auto* Mode=World?Cast<ASoraGameMode>(World->GetAuthGameMode()):nullptr;
    if(World!=GetWorld()||!PressHall||!Mode||!Mode->IsPlaying()||Mode->bDeterministicPractice||DeltaSeconds<=0) return;
    // Publish this frame's phase before actor perception and weapon events.
    // The subsystem's later visual/inspection tick consumes the same phase.
    PressCarryMs+=double(DeltaSeconds)*1000.0;
    const int64 Whole=FMath::FloorToInt64(PressCarryMs);
    PressCarryMs-=Whole; PressClockMs+=Whole;
}
void USoraFieldcraft::ClearPressHall()
{
    if(PressClockHandle.IsValid()) FWorldDelegates::OnWorldPreActorTick.Remove(PressClockHandle);
    PressClockHandle.Reset(); PressCarryMs=0;
    for(auto& Inspection:PressInspections)
    {
        if(auto* Guard=Inspection.Guard.Get())
            if(auto* Brain=Cast<ASoraEnemyController>(Guard->GetController())) Brain->ClearErrand();
        Inspection=FPressInspection{};
    }
    PressHall=nullptr; PressClockMs=0; JammedPresses=0; PressPlatens.Reset();
}
void USoraFieldcraft::StagePressHall(const FSoraBeat& Beat)
{
    if(!Beat.Space.PressHall.bEnabled) return;
    PressHall=&Beat.Space.PressHall;
    PressClockHandle=FWorldDelegates::OnWorldPreActorTick.AddUObject(this,&USoraFieldcraft::AdvancePressClock);
    const FLinearColor Metal(.055f,.07f,.075f),Die(.2f,.3f,.31f);
    for(int32 I=0;I<Press::Count;++I)
    {
        const FVector At=PressCenter(I);
        const auto Part=[&](const FString& Name,const FVector& Offset,const FVector& Size,bool Collision)
        {
            auto* P=Piece(FString::Printf(TEXT("Press%d_%s"),I,*Name),SoraFieldcraftLayout::Cube,
                At+Offset,Size/100.f,Metal,Collision,SoraFieldcraftLayout::Metal);
            P->ComponentTags.Add(TEXT("PressMachine")); return P;
        };
        Part(TEXT("Base"),FVector(0,0,30),FVector(400,300,60),true);
        Part(TEXT("Crown"),FVector(0,0,330),FVector(400,300,40),true);
        for(int X:{-1,1}) for(int Y:{-1,1})
            Part(FString::Printf(TEXT("Post%d%d"),X,Y),FVector(175*X,125*Y,180),FVector(30,30,300),true);
        auto* Platen=Part(TEXT("Platen"),FVector(0,0,80),FVector(320,220,30),false);
        Platen->SetMobility(EComponentMobility::Movable);
        Platen->ComponentTags.Add(TEXT("PressPlaten")); PressPlatens.Add(Platen);
        if(Press::Objective(I)>=0)
        {
            auto* Handle=Piece(FString::Printf(TEXT("Press%d_MasterHandle"),I),SoraFieldcraftLayout::Cube,
                At+FVector(0,-165,110),FVector(.5f,.1f,.2f),Die,false,SoraFieldcraftLayout::Metal);
            Handle->ComponentTags.Add(TEXT("PressMaster"));
        }
    }
}
void USoraFieldcraft::JamPress(int32 Objective)
{
    if(!PressHall||!Press::Jam(JammedPresses,Objective)) return;
    auto& Inspection=PressInspections[Objective]; Inspection.RequestedMs=PressClockMs;
    // Removing a masking source is immediate, before dialogue callbacks or
    // another noise in this frame. Only the first wedge gives this line.
    if(JammedPresses==(1u<<Press::Master[Objective])) Raise(TEXT("interact:press_any_first"));
}
bool USoraFieldcraft::PressInspectionArrived(int32 Objective) const
{ return PressHall&&Objective>=0&&Objective<3&&PressInspections[Objective].ArrivedMs>=0; }
bool USoraFieldcraft::PressInspectionOverdue(int32 Objective) const
{ return PressHall&&Objective>=0&&Objective<3&&PressInspections[Objective].bOverdue; }
ASoraEnemy* USoraFieldcraft::PressInspector(int32 Objective) const
{ return PressHall&&Objective>=0&&Objective<3?PressInspections[Objective].Guard.Get():nullptr; }

void USoraFieldcraft::TickPressHall(int32 DeltaMs)
{
    if(!PressHall||DeltaMs<=0) return;
    const int32 Phase=Press::Phase(PressClockMs);
    // Stamp/dwell, return, then drop. The same clock gates noise and motion.
    const float Z=Phase<150?80.f:Phase<500?FMath::Lerp(80.f,250.f,(Phase-150)/350.f):
        Phase<1400?250.f:FMath::Lerp(250.f,80.f,(Phase-1400)/200.f);
    for(int32 I=0;I<PressPlatens.Num();++I)
        if(auto* Platen=PressPlatens[I].Get()) Platen->SetWorldLocation(PressCenter(I)+FVector(0,0,PressRunning(I)?Z:80.f));
    for(int32 Objective=0;Objective<3;++Objective)
    {
        auto& Work=PressInspections[Objective];
        if(Work.RequestedMs<0||Work.bFinished) continue;
        const FVector Center=PressCenter(Press::Master[Objective]);
        const FVector Feet=Center+FVector(0,-240,0);
        ASoraEnemy* Guard=Work.Guard.Get();
        auto* Brain=Guard?Cast<ASoraEnemyController>(Guard->GetController()):nullptr;
        if(Guard&&(!Guard->IsAlive()||!Brain||!Brain->HasErrand()))
        {
            Work.Guard.Reset(); Guard=nullptr; Brain=nullptr;
            if(Work.ArrivedMs>=0) { Work.bFinished=true; continue; }
        }
        if(Guard&&Brain&&Brain->ErrandReached())
        {
            // Strict 3D errand mode never calls a failed path an arrival.
            if(Work.ArrivedMs<0)
            {
                Work.ArrivedMs=PressClockMs;
                Work.bOverdue|=Work.ArrivedMs-Work.RequestedMs>Press::InspectionMs;
            }
            if(PressClockMs-Work.ArrivedMs>=2000)
            { Brain->ClearErrand(); Work.bFinished=true; }
            continue;
        }
        if(PressClockMs-Work.RequestedMs>Press::InspectionMs) Work.bOverdue=true;
        if(Guard) continue;
        float Distance=MAX_flt;
        for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
        {
            auto* Candidate=Cast<ASoraEnemyController>(It->GetController());
            if(!It->IsAlive()||It->ArchetypeId()!=TEXT("auditor")||!Candidate||!Candidate->IsGuard()||
                Candidate->HasErrand()||!SoraStealthRules::IsCalm(Candidate->State())) continue;
            const float D=FVector::DistSquared(It->GetActorLocation(),Feet);
            if(D<Distance) { Distance=D; Guard=*It; Brain=Candidate; }
        }
        if(!Guard||!Brain) continue;
        Work.Guard=Guard;
        const FVector Goal=Feet+FVector(0,0,Guard->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        Brain->SetErrand(Goal,Center-Feet,1.f,0,true,true,70.f);
        Raise(TEXT("ai_event:press_silent"));
        if(!PressHall) return;
    }
}
