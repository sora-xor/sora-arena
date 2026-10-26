#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraWorkshopEncounterRules.h"

ASoraEnemy* USoraCampaignDirector::SpawnWorkshopDefender(int32 Wave,int32 Group,int32 Member,int32 Slot)
{
    namespace R=SoraWorkshopEncounterRules;
    const auto* Beat=ActiveBeatData();const int Index=R::SpawnIndex(Wave,Group,Member);
    if(!Beat||Beat->Id!=TEXT("ch03.b08")||Index<0||!Beat->Waves.IsValidIndex(Wave)||
       !Beat->Waves[Wave].Groups.IsValidIndex(Group))return nullptr;
    const auto& Entry=Beat->Waves[Wave].Groups[Group];const auto& Spawn=R::Spawns[Index];
    if(Entry.Type!=FName(UTF8_TO_TCHAR(R::Kind(Index))))return nullptr;
    const FVector At(Spawn.Floor.X,Spawn.Floor.Y,Spawn.Floor.Z+90.15);
    auto* Enemy=SpawnWaveOpponent(Entry.Type,false,Slot,Entry.bInvulnerable,&At);
    if(Enemy)
    {
        Enemy->Tags.Add(TEXT("WorkshopDefender"));Enemy->Tags.Add(FName(*FString::Printf(TEXT("WorkshopEntry%d"),Index)));
        if(Spawn.Entry==R::EEntry::Roof)Enemy->Tags.Add(TEXT("WorkshopRooftop"));
        if(auto* Brain=Cast<ASoraEnemyController>(Enemy->GetController()))Brain->AssignWorkshopDefense(Index);
    }
    return Enemy;
}
