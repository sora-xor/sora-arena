#pragma once

// The b08 groups enter through authored openings. Coordinates are feet in cm;
// movement uses the real CharacterMovement capsule, never timed teleports.
namespace SoraWorkshopEncounterRules
{
enum class EEntry { None,Street,Vault,Canal,Roof };
struct FPoint { double X=0,Y=0,Z=0; };
struct FSpawn { FPoint Floor;EEntry Entry;int Member; };
constexpr FSpawn Spawns[]={
    {{3480,-250,0},EEntry::Street,0},{{3480,-110,0},EEntry::Street,1},{{3480,30,0},EEntry::Street,2},
    {{3480,-1270,0},EEntry::Vault,0},{{3480,-1490,0},EEntry::Vault,1},
    {{1960,-2450,0},EEntry::Canal,0},{{2040,-2450,0},EEntry::Canal,1},
    {{2750,-1650,650},EEntry::Roof,0}};
constexpr int SpawnIndex(int Wave,int Group,int Member)
{
    if(Wave==0&&Group==0&&Member>=0&&Member<3)return Member;
    if(Wave==1&&Group>=0&&Group<2&&Member>=0&&Member<2)return 3+Group*2+Member;
    if(Wave==2&&Group==0&&Member==0)return 7;
    return -1;
}
constexpr const char* Kind(int Index)
{return Index==3||Index==4?"blade_retainer":Index==7?"grenadier":"enforcer_rifle";}
constexpr FPoint WalkPoint(EEntry Entry,int Member,int Leg)
{
    if(Entry==EEntry::Street)return Leg==0?FPoint{3480,-1030,0}:FPoint{3280.-140*Member,-1080,0};
    if(Entry==EEntry::Canal)return Leg==0?FPoint{1960.+80*Member,-2140,0}:FPoint{1850.+300*Member,-1850,0};
    return {};
}
constexpr int WalkLegs=2;
constexpr double VaultXSpeed=-200,VaultZSpeed=850;
constexpr bool VaultLanded(double X,double Feet,bool Grounded)
{return Grounded&&X<=3350&&Feet>=-4&&Feet<=8;}
// Fixed perch on the supported north-west eave, facing the open yard. Normal
// ranged retreat must not walk a roof defender into unsupported space.
constexpr FPoint Roof=Spawns[7].Floor;
}
