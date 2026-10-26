#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraTenementDefenseRules.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
bool InKitchen(const ASoraCharacterBase& Body)
{
    const FVector P=Body.GetActorLocation();const auto* C=Body.GetCapsuleComponent();
    return SoraTenementDefenseRules::InKitchen(P.X,P.Y,P.Z,C->GetScaledCapsuleRadius(),C->GetScaledCapsuleHalfHeight());
}
}
bool USoraCampaignDirector::HeroAtTenementKitchen() const
{
    const auto* Hero=Mode().Hero();
    return Hero&&Hero->GetCharacterMovement()->IsMovingOnGround()&&InKitchen(*Hero);
}
bool USoraCampaignDirector::TenementKitchenContested() const
{
    for(const auto& Enemy:Enemies)
        if(IsValid(Enemy)&&Enemy->IsEnemy()&&Enemy->IsAlive()&&InKitchen(*Enemy))return true;
    return false;
}
ASoraEnemy* USoraCampaignDirector::SpawnTenementDefender(int32 Wave,int32 Group,int32 Member,int32 Slot)
{
    const auto* Beat=ActiveBeatData();SoraTenementDefenseRules::FPoint P;
    if(!Beat||!Beat->Space.bTenementDefense||!GetWorld()||!Beat->Waves.IsValidIndex(Wave)||
       !Beat->Waves[Wave].Groups.IsValidIndex(Group)||!SoraTenementDefenseRules::Spawn(Wave,Group,Member,P))return nullptr;
    const auto& Entry=Beat->Waves[Wave].Groups[Group];
    auto* Enemy=ASoraEnemy::SpawnArchetype(*GetWorld(),Entry.Type,Slot,FVector(P.X,P.Y,P.Z),FRotator(0,90,0));
    if(Enemy)
    {
        Enemy->Tags.Add(TEXT("TenementDefender"));Enemy->Tags.Add(Entry.Spawn);
        Enemy->Tags.Add(FName(*FString::Printf(TEXT("TenementWave%d"),Wave+1)));
        if(Wave==1)
            if(auto* Brain=Cast<ASoraEnemyController>(Enemy->GetController()))Brain->AssignTenementDefense(Member);
    }
    return Enemy;
}
