#include "SoraLanternWorkshopRules.h"
#include "SoraFieldcraftRules.h"
#include "SoraWorkshopHazardRules.h"
#include "SoraWorkshopEncounterRules.h"
#include <limits>
#include <cassert>
#include <iomanip>
#include <iostream>

int main()
{
    namespace R=SoraLanternWorkshopRules;
    std::cout<<std::setprecision(15)<<"{\"solids\":[";
    bool Comma=false;
    for(const auto& B:R::Solids())
    {
        if(Comma)std::cout<<',';
        Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<",0,"<<int(B.Surface)<<']';
    }
    std::cout<<"],\"stations\":[";Comma=false;
    for(const auto& P:R::Stations)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<P.X<<','<<P.Y<<','<<R::FloorAt(P.X,P.Y)<<']';
    }
    std::cout<<"],\"floor_samples\":[";Comma=false;
    for(const auto& P:{R::FPoint{1655,-950},{1745,-950},{1900,-1535},{1900,-1490},{3150,-1900},{3150,-2000}})
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<P.X<<','<<P.Y<<','<<R::FloorAt(P.X,P.Y)<<']';
    }
    std::cout<<"],\"craft_routes\":[";Comma=false;
    for(int I=0;I<R::CraftspersonCount;++I)
    {
        if(Comma)std::cout<<',';Comma=true;
        const auto A=R::CraftStart(I),B=R::CraftShelter(I);
        std::cout<<"[["<<A.X<<','<<A.Y<<",47.15],["<<B.X<<','<<B.Y<<",47.15]]";
    }
    std::cout<<"],\"seal_reach\":[";
    std::cout<<R::CanCutSeal(1900,-1660,0,true)<<','<<R::CanCutSeal(1900,-1540,22.5,true)<<','
        <<R::CanCutSeal(1900,-1450,45,true)<<','<<R::CanCutSeal(1900,-1660,450,true)<<','
        <<R::CanCutSeal(1900,-1700,0,true)<<','<<R::CanCutSeal(2120,-1550,0,true)<<','
        <<R::CanCutSeal(1900,-1660,0,false);
    int Hold=0;
    assert(!SoraFieldcraftRules::Hold(Hold,true,1999,R::SealHoldMs));
    assert(Hold==1999);
    assert(!SoraFieldcraftRules::Hold(Hold,false,1,R::SealHoldMs));
    assert(Hold==0);
    assert(!SoraFieldcraftRules::Hold(Hold,true,1999,R::SealHoldMs));
    assert(SoraFieldcraftRules::Hold(Hold,true,1,R::SealHoldMs));
    std::cout<<"],\"hold_ms\":"<<Hold;
    namespace H=SoraWorkshopHazardRules;
    std::cout<<",\"hazard_solids\":[["<<H::OilX<<','<<H::OilY<<','<<H::OilHalfHeightCm<<','
        <<H::OilRadiusCm*2<<','<<H::OilRadiusCm*2<<','<<H::OilHalfHeightCm*2<<",0,1]";
    for(const auto& C:H::Covers)std::cout<<",["<<C.X<<','<<C.Y<<','<<C.Height*.5<<','<<C.SX<<','<<C.SY<<','<<C.Height<<",0,1]";
    std::cout<<"],\"burn_partitions\":[";Comma=false;
    for(int Step:{1,7,16,17,33,100,1000,5999,6000,7000,std::numeric_limits<int>::max()})
    {
        H::FFire Fire;int Carry=0,Damage=0;
        assert(Fire.Ignite());assert(Fire.Advance(-1)==0&&Fire.Advance(0)==0&&Fire.LeftMs==6000);
        while(Fire.LeftMs)Damage+=H::Burn(Carry,Fire.Advance(Step));
        assert(!Fire.Ignite()&&Fire.Advance(1)==0&&Carry==0);
        if(Comma)std::cout<<',';Comma=true;std::cout<<'['<<Step<<','<<Damage<<']';
    }
    H::FFire F;assert(F.Ignite());int Carry=0;
    assert(H::Burn(Carry,F.Advance(5999))==71&&Carry==988&&F.LeftMs==1);
    assert(!F.Ignite()&&F.LeftMs==1);
    assert(H::Burn(Carry,F.Advance(20))==1&&Carry==0&&F.LeftMs==0);
    assert(H::FloorContact(H::OilX+180,H::OilY,8));
    assert(!H::FloorContact(H::OilX+180.01,H::OilY,0));
    assert(!H::FloorContact(H::OilX,H::OilY,45)&&!H::FloorContact(H::OilX,H::OilY,450));
    assert(!H::FloorContact(H::OilX,H::OilY,-4.01));
    assert(H::BlastReaches(320,320,1,true));
    assert(!H::BlastReaches(320.01,320,1,true)&&!H::BlastReaches(1,320,1,false));
    assert(!H::BlastReaches(1,320,0,true)&&!H::BlastReaches(1,0,1,true));
    assert(!H::BlastReaches(1,std::numeric_limits<double>::infinity(),1,true));
    assert(!H::BlastReaches(std::numeric_limits<double>::quiet_NaN(),320,1,true));
    int Health=40;using Hit=SoraCombatRules::EHit;
    assert(H::BreakCover(Health,Hit::Melee,20,false)==0&&Health==40);
    assert(H::BreakCover(Health,Hit::Hazard,100,true)==0&&Health==40);
    assert(H::BreakCover(Health,Hit::Ranged,-1,true)==0&&Health==40);
    assert(H::BreakCover(Health,Hit::Ranged,std::numeric_limits<float>::infinity(),true)==0);
    assert(H::BreakCover(Health,Hit::Melee,15,true)==15&&Health==25);
    assert(H::BreakCover(Health,Hit::Ranged,10,true)==10&&Health==15);
    assert(H::BreakCover(Health,Hit::Blast,100,true)==15&&Health==0);
    assert(H::BreakCover(Health,Hit::Blast,100,true)==0);
    using Rate=SoraCombatRules::EEnvironmentalRate;
    assert(SoraCombatRules::EnemyVulnerabilityDamage(12,Hit::Hazard,Rate::WorkshopOil,true,-1000,2000)==12);
    assert(SoraCombatRules::EnemyVulnerabilityDamage(12,Hit::Melee,Rate::WorkshopOil,true,-1000,2000)>12);
    std::cout<<"],\"hazard_boundary_assertions\":true";
    namespace E=SoraWorkshopEncounterRules;
    std::cout<<",\"combat_spawns\":[";Comma=false;
    for(const auto& S:E::Spawns)
    {if(Comma)std::cout<<',';Comma=true;std::cout<<'['<<S.Floor.X<<','<<S.Floor.Y<<','<<S.Floor.Z<<']';}
    std::cout<<"],\"entry_routes\":[";Comma=false;
    for(const auto& S:E::Spawns)
    {
        if(S.Entry!=E::EEntry::Street&&S.Entry!=E::EEntry::Canal)continue;
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<"[["<<S.Floor.X<<','<<S.Floor.Y<<",2.15]";
        for(int L=0;L<E::WalkLegs;++L){const auto P=E::WalkPoint(S.Entry,S.Member,L);std::cout<<",["<<P.X<<','<<P.Y<<",2.15]";}
        std::cout<<']';
    }
    std::cout<<"],\"vault_speed\":["<<E::VaultXSpeed<<','<<E::VaultZSpeed<<']';
    int Expected=0;
    for(int W=0;W<3;++W)for(int G=0;G<(W==1?2:1);++G)for(int M=0;M<(W==0?3:W==1?2:1);++M)
        assert(E::SpawnIndex(W,G,M)==Expected++);
    assert(Expected==8&&E::SpawnIndex(-1,0,0)==-1&&E::SpawnIndex(3,0,0)==-1&&E::SpawnIndex(1,2,0)==-1);
    assert(E::SpawnIndex(0,0,3)==-1&&E::SpawnIndex(2,0,1)==-1&&E::SpawnIndex(0,0,-1)==-1);
    assert(E::VaultLanded(3350,8,true)&&!E::VaultLanded(3351,0,true)&&!E::VaultLanded(3300,160,true));
    assert(!E::VaultLanded(3300,0,false));
    std::cout<<",\"entry_boundary_assertions\":true}\n";
}
