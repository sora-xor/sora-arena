#include "SoraLanternWorkshopRules.h"
#include "SoraFieldcraftRules.h"
#include "SoraWorkshopHazardRules.h"
#include "SoraWorkshopEncounterRules.h"
#include "SoraWorkshopCraftRules.h"
#include "SoraBeatRules.h"
#include <limits>
#include <cassert>
#include <iomanip>
#include <iostream>

void CraftChecks()
{
    namespace C=SoraWorkshopCraftRules;namespace B=SoraBeatRules;
    // The authored release window includes both endpoints. Holding past it
    // fails once and cannot roll into a new attempt without a release.
    for(int Ms:{0,639,640,800,960,961,2000,std::numeric_limits<int>::max()})
    {
        C::FState S;assert(C::Begin(S,0));
        const auto Tick=C::Tick(S,Ms,true),Release=C::Release(S,true);
        if(Ms>960)assert(Tick==C::EResult::Missed&&Release==C::EResult::None);
        else assert(Tick==C::EResult::None&&Release==(Ms>=640?C::EResult::Passed:C::EResult::Missed));
        assert(C::Begin(S,0));
        assert(C::Tick(S,961,true)==C::EResult::Missed);
        assert(C::Tick(S,10000,true)==C::EResult::None&&!C::Begin(S,0));
        assert(C::Release(S,true)==C::EResult::None&&C::Begin(S,0));
    }
    for(int Step:{1,3})for(int Partition:{1,7,16,17,33,100,1499,1500,2000,std::numeric_limits<int>::max()})
    {
        C::FState S;assert(C::Begin(S,Step));
        int Held=0;while(Held<1499)
        {const int Delta=std::min(Partition,1499-Held);assert(C::Tick(S,Delta,true)==C::EResult::None);Held+=Delta;}
        assert(S.ElapsedMs==1499&&C::Tick(S,-1,true)==C::EResult::None&&S.ElapsedMs==1499);
        assert(C::Release(S,true)==C::EResult::Cancelled);
        assert(C::Begin(S,Step)&&C::Tick(S,1,true)==C::EResult::None&&S.ElapsedMs==1);
        assert(C::Tick(S,1498,true)==C::EResult::None);
        assert(C::Tick(S,Partition,true)==C::EResult::Passed);
        assert(!C::Begin(S,Step)&&C::Tick(S,10000,true)==C::EResult::None);
        assert(C::Release(S,true)==C::EResult::None&&C::Begin(S,Step));
        assert(C::Tick(S,1499,true)==C::EResult::None);
        assert(C::Tick(S,1,false)==C::EResult::Cancelled&&!C::Begin(S,Step));
        assert(C::Release(S,true)==C::EResult::None&&C::Begin(S,Step));
        assert(C::Tick(S,1,true)==C::EResult::None&&S.ElapsedMs==1);
    }
    for(int Partition:{1,7,16,17,33,100,799,800,1000,std::numeric_limits<int>::max()})
    {
        C::FState S;assert(C::Begin(S,0));int Held=0;
        while(Held<799){const int D=std::min(Partition,799-Held);assert(C::Tick(S,D,true,true)==C::EResult::None);Held+=D;}
        assert(C::Tick(S,Partition,true,true)==C::EResult::Passed);
        assert(!C::Begin(S,0)&&C::Release(S,true)==C::EResult::None);
    }
    for(int Step:{-1,2,4,5,6}){C::FState S;assert(!C::Begin(S,Step));}
    C::FState S;assert(C::Begin(S,0)&&C::Tick(S,800,true)==C::EResult::None);
    assert(C::Release(S,false)==C::EResult::Cancelled);
    assert(C::Begin(S,0)&&C::Tick(S,800,true)==C::EResult::None);
    C::Cancel(S);assert(C::Release(S,true)==C::EResult::None);
    // A failed replacement strip must not erase finished hoops. Use the
    // common production accounting, including recipe advancement.
    B::FTask Task{};Task.Goal=B::EGoal::Steps;Task.StepCount=6;
    const int Counts[]={6,4,1,1,3,1};
    for(int I=0;I<6;++I)Task.Steps[I].Count=Counts[I];
    auto State=B::StartTask(Task,0);
    for(int I=0;I<2;++I)assert(B::CreditStroke(State,Task)==B::EStroke::Counted);
    assert(C::Begin(S,0)&&C::Tick(S,600,true)==C::EResult::None&&C::Release(S,true)==C::EResult::Missed);
    assert(State.Done==2&&State.StepDone==2);
    for(int I=2;I<6;++I)B::CreditStroke(State,Task);
    assert(State.Done==6&&State.Step==1&&State.StepDone==0);
    for(int I=1;I<6;++I)for(int N=0;N<Counts[I];++N)B::CreditStroke(State,Task);
    assert(State.Done==16&&State.Step==6&&B::CreditStroke(State,Task)==B::EStroke::Refused&&State.Done==16);
}

int main()
{
    CraftChecks();
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
    std::cout<<",\"entry_boundary_assertions\":true,\"craft_boundary_assertions\":true}\n";
}
