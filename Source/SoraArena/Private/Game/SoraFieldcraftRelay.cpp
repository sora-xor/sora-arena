#include "SoraFieldcraft.h"
#include "SoraCampaignDirector.h"
#include "SoraGameMode.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Components/PointLightComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"

void USoraFieldcraft::ClearRelayRoom()
{
    if(auto* Auditor=RelayAuditor.Get())
        if(auto* Brain=Cast<ASoraEnemyController>(Auditor->GetController())) Brain->ClearErrand();
    RelayAuditor.Reset();RelayInspecting=INDEX_NONE;RelayInspected=0;RelayArrivedMs=-1;
    RelayInspectionPath.Reset();RelayInspectionLeg=0;RelayInspectionAtLeg=0;
    if(auto* Glow=RelayGlow.Get()) Glow->Destroy();
    RelayGlow.Reset();RelayRoom=nullptr;RelayRoomMs=0;RelayNodes.Reset();RelayFan.Reset();
    for(int I=0;I<2;++I) { RelayLampOutMs[I]=-1;RelayLampNoticed[I]=false; }
}
void USoraFieldcraft::StageRelayRoom(const FSoraBeat& Beat)
{
    if(!Beat.Space.RelayRoom.bEnabled) return;
    RelayRoom=&Beat.Space.RelayRoom;
    const FVector Origin(RelayRoom->Origin,0);
    const FLinearColor Wood(.22f,.14f,.075f),Metal(.025f,.045f,.055f),Cyan(.1f,.8f,.9f);
    const auto Box=[&](const TCHAR* Name,const FVector& Center,const FVector& Size,bool Collision=true)
    {
        auto* P=Piece(Name,SoraFieldcraftLayout::Cube,Origin+Center,Size/100.f,Wood,Collision,SoraFieldcraftLayout::Timber);
        P->ComponentTags.Add(TEXT("RelayStructure"));return P;
    };
    // 1.8 m gallery around the authored 8 x 5 m void; ordinary walkable
    // treads connect it to the floor. No teleport or floor-only interaction.
    Box(TEXT("RelaySouthGallery"),FVector(1000,160,390),FVector(1160,180,20));
    Box(TEXT("RelayNorthGallery"),FVector(1040,840,390),FVector(1080,180,20));
    Box(TEXT("RelayStairSouthEdge"),FVector(460,770,390),FVector(80,40,20));
    Box(TEXT("RelayStairNorthEdge"),FVector(460,920,390),FVector(80,20,20));
    Box(TEXT("RelayWestGallery"),FVector(510,500,390),FVector(180,500,20));
    Box(TEXT("RelayEastGallery"),FVector(1490,500,390),FVector(180,500,20));
    // A short maintenance approach from the north gallery reaches the
    // authored node inside the void without increasing the player's reach.
    // End beyond the grounded work position (y=690), leaving the drone's
    // five-metre orbit clear of the approach and its side railings.
    Box(TEXT("RelayNodeApproach"),FVector(1000,730,390),FVector(120,160,20));
    for(int I=0;I<25;++I)
        Box(*FString::Printf(TEXT("RelayStair%d"),I),FVector(108+16*I,850,8*(I+1)),FVector(16,120,16*(I+1)));
    const auto Rail=[&](const FVector& Center,const FVector& Size) { Box(TEXT("RelayRail"),Center,Size); };
    Rail(FVector(1000,250,450),FVector(800,10,100));
    Rail(FVector(600,500,450),FVector(10,500,100));Rail(FVector(1400,500,450),FVector(10,500,100));
    Rail(FVector(770,750,450),FVector(340,10,100));Rail(FVector(1230,750,450),FVector(340,10,100));
    Rail(FVector(940,700,450),FVector(10,100,100));Rail(FVector(1060,700,450),FVector(10,100,100));
    Rail(FVector(1000,70,450),FVector(1160,10,100));Rail(FVector(1000,930,450),FVector(1160,10,100));
    Rail(FVector(420,430,450),FVector(10,720,100));Rail(FVector(1580,500,450),FVector(10,860,100));
    for(const FVector2D At:{FVector2D(440,90),FVector2D(1000,90),FVector2D(1560,90),
        FVector2D(440,910),FVector2D(1000,910),FVector2D(1560,910),FVector2D(440,500),FVector2D(1560,500)})
        Box(TEXT("RelayPost"),FVector(At,200),FVector(30,30,400));
    for(const FVector2D At:{FVector2D(280,250),FVector2D(280,650),FVector2D(1750,650),FVector2D(1750,200)})
        Box(TEXT("RelayNagamochi"),FVector(At,45),FVector(180,90,90));
    for(const FVector2D At:{FVector2D(1750,830),FVector2D(1650,330),FVector2D(650,80)})
        for(int I=0;I<3;++I)
            Piece(TEXT("RelayAlarmBell"),SoraFieldcraftLayout::Cylinder,Origin+FVector(At,30+45*I),
                FVector(1.f-I*.18f,1.f-I*.18f,.6f),Metal,true,SoraFieldcraftLayout::Metal);
    for(const auto& Patch:Beat.Space.Fieldcraft.Floors)
        for(int I=0;I<12;++I)
        {
            auto* Clapper=Piece(TEXT("RelayClapper"),SoraFieldcraftLayout::Cylinder,
                FVector(Patch.Area.Center,5)+FVector((I%4-1.5f)*55.f,(I/4-1)*45.f,0),
                FVector(.08f,.08f,.45f),Metal,false,SoraFieldcraftLayout::Metal);
            Clapper->SetWorldRotation(FRotator(90,27*I,0));
        }
    Piece(TEXT("RelayColumn"),SoraFieldcraftLayout::Cylinder,Origin+FVector(1000,500,375),FVector(1.6f,1.6f,7.5f),Metal,true);
    for(int I=0;I<3;++I)
    {
        const auto N=SoraRelayRules::Nodes[I];
        const FVector Out=I==0?FVector(-1,0,0):I==1?FVector(1,0,0):FVector(0,1,0);
        auto* Node=Piece(*FString::Printf(TEXT("RelayNode%d"),I),SoraFieldcraftLayout::Sphere,
            Origin+FVector(N.X,N.Y,N.Z)+Out*3.f,FVector(.2f,.2f,.3f),Cyan,false);
        Node->ComponentTags.Add(TEXT("RelayNode"));RelayNodes.Add(Node);
    }
    for(int I=0;I<16;++I)
    {
        auto* Ray=Piece(TEXT("RelayScanRay"),SoraFieldcraftLayout::Cube,Origin+FVector(1000,500,122),
            FVector(2.f,.025f,.025f),Cyan,false);
        Ray->SetMobility(EComponentMobility::Movable);RelayFan.Add(Ray);
    }
    auto* Light=GetWorld()->SpawnActor<APointLight>(Origin+FVector(1000,500,350),FRotator::ZeroRotator);
    if(Light)
    {
        Light->SetMobility(EComponentMobility::Movable);
        Light->PointLightComponent->SetAttenuationRadius(600.f);
        Light->PointLightComponent->SetIntensity(4500.f);
        Light->PointLightComponent->SetLightColor(Cyan);
        Light->PointLightComponent->SetCastShadows(true);
        RelayGlow=Light;
    }
}
void USoraFieldcraft::RelayLampExtinguished(int32 Index)
{
    if(RelayRoom&&Index>=0&&Index<2&&RelayLampOutMs[Index]<0) RelayLampOutMs[Index]=RelayRoomMs;
}
void USoraFieldcraft::TickRelayRoom(int32 DeltaMs)
{
    if(!RelayRoom||DeltaMs<=0) return;
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const auto* Campaign=Mode?Mode->Campaign():nullptr;
    if(!Campaign||!Campaign->IsRelayRoom()) return;
    RelayRoomMs+=DeltaMs;
    const auto& State=Campaign->RelayState();
    for(int I=0;I<RelayNodes.Num();++I)
        if(auto* Node=RelayNodes[I].Get())
        {
            const FLinearColor Color=State.IsDisabled(I)?FLinearColor(.015f,.025f,.03f):
                State.NodesLockedMs>0?FLinearColor(.95f,.1f,.03f):State.Exposed(I)?FLinearColor(.1f,.8f,.9f):FLinearColor(.5f,.35f,.12f);
            if(auto* Material=Cast<UMaterialInstanceDynamic>(Node->GetMaterial(0)))
            { Material->SetVectorParameterValue(TEXT("BaseColor"),Color);Material->SetVectorParameterValue(TEXT("Color"),Color); }
        }
    for(int I=0;I<RelayFan.Num();++I) if(auto* Ray=RelayFan[I].Get())
    {
        const FRotator Angle(0,float(State.PhaseMs)*360.f/SoraRelayRules::PeriodMs-232.5f+15.f*I,0);
        Ray->SetWorldLocationAndRotation(FVector(RelayRoom->Origin,122)+FVector(1000,500,0)+Angle.Vector()*190.f,Angle);
        Ray->SetVisibility(!State.AllDisabled());
    }
    if(auto* Light=RelayGlow.Get()) Light->PointLightComponent->SetIntensity(State.AllDisabled()?0.f:4500.f);
    for(int I=0;I<2;++I)
        if(RelayLampOutMs[I]>=0&&!RelayLampNoticed[I]&&RelayRoomMs-RelayLampOutMs[I]>=SoraRelayRules::LampNoticeMs)
        {
            RelayLampNoticed[I]=true;
            const FVector At(Staged->Lamps[I].At,100);ASoraEnemyController* Nearest=nullptr;float Best=MAX_flt;
            for(TActorIterator<ASoraEnemyController> It(GetWorld());It;++It)
                if(const auto* Enemy=Cast<ASoraEnemy>(It->GetPawn());Enemy&&Enemy->IsAlive()&&It->IsGuard())
                {
                    const float D=FVector::DistSquared(Enemy->GetActorLocation(),At);
                    if(D<Best) { Best=D;Nearest=*It; }
                }
            if(Nearest) Nearest->NoticeTampering(At);
            if(!RelayRoom||!Staged) return;
        }
    TickRelayInspection();
}

bool USoraFieldcraft::RelayInspectionArrived(int32 Node) const
{ return RelayRoom&&SoraRelayRules::ValidNode(Node)&&(RelayInspected&(1u<<Node))!=0; }
ASoraEnemy* USoraFieldcraft::RelayInspector() const { return RelayAuditor.Get(); }

void USoraFieldcraft::TickRelayInspection()
{
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const auto* Campaign=Mode?Mode->Campaign():nullptr;
    if(!RelayRoom||!Campaign||!Campaign->IsRelayRoom()) return;
    auto* Guard=RelayAuditor.Get();
    auto* Brain=Guard?Cast<ASoraEnemyController>(Guard->GetController()):nullptr;
    if(Guard&&(!Guard->IsAlive()||!Brain||!Brain->HasErrand()||Brain->State()!=SoraStealthRules::EState::Unaware))
    {
        if(Brain) Brain->ClearErrand();
        Guard=nullptr;Brain=nullptr;RelayAuditor.Reset();RelayInspecting=INDEX_NONE;
        RelayInspectionPath.Reset();RelayArrivedMs=-1;
    }
    if(Guard&&Brain)
    {
        if(!Brain->ErrandReached()) return; // A blocked path never becomes an inspection.
        if(RelayInspectionLeg==RelayInspectionAtLeg)
        {
            if(RelayArrivedMs<0)
            { RelayArrivedMs=RelayRoomMs;RelayInspected|=1u<<RelayInspecting; }
            if(RelayRoomMs-RelayArrivedMs<2000) return;
        }
        if(++RelayInspectionLeg>=RelayInspectionPath.Num())
        {
            Brain->ClearErrand();RelayAuditor.Reset();RelayInspecting=INDEX_NONE;
            RelayInspectionPath.Reset();RelayArrivedMs=-1;
            return;
        }
    }
    else
    {
        RelayInspecting=INDEX_NONE;
        for(int Node=0;Node<3;++Node)
            if(Campaign->RelayState().IsDisabled(Node)&&!(RelayInspected&(1u<<Node)))
            { RelayInspecting=Node;break; }
        if(RelayInspecting==INDEX_NONE) return;
        for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
        {
            auto* Candidate=Cast<ASoraEnemyController>(It->GetController());
            if(It->IsAlive()&&It->ArchetypeId()==TEXT("auditor")&&Candidate&&Candidate->IsGuard()&&
                !Candidate->HasErrand()&&Candidate->State()==SoraStealthRules::EState::Unaware)
            { Guard=*It;Brain=Candidate;break; }
        }
        if(!Brain) return;
        RelayAuditor=Guard;RelayInspectionPath.Reset();RelayInspectionLeg=0;RelayArrivedMs=-1;
        const FVector Origin(RelayRoom->Origin,0);
        if(RelayInspecting==2)
        {
            // The upper control is reached by the actual stair and gallery.
            RelayInspectionPath.Add(Origin+FVector(110,750,0));
            for(int I=0;I<5;++I) RelayInspectionPath.Add(Origin+FVector(110+80*I,850,16+80*I));
            RelayInspectionPath.Add(Origin+FVector(510,850,400));
            RelayInspectionPath.Add(Origin+FVector(800,840,400));
            RelayInspectionPath.Add(Origin+FVector(1000,840,400));
        }
        RelayInspectionPath.Add(Campaign->RelayWorkLocation(RelayInspecting));
        RelayInspectionAtLeg=RelayInspectionPath.Num()-1;
        if(RelayInspecting==2)
            for(int I=RelayInspectionAtLeg-1;I>=0;--I)
            { const FVector ReturnPoint=RelayInspectionPath[I];RelayInspectionPath.Add(ReturnPoint); }
        RelayInspectionPath.Add(Origin+FVector(300,500,0));
    }
    const FVector Feet=RelayInspectionPath[RelayInspectionLeg];
    const FVector Facing=RelayInspectionLeg==RelayInspectionAtLeg?Campaign->RelayNodeLocation(RelayInspecting)-Feet:FVector(1,0,0);
    // The mesh's upper stair connection is missing at the default nav
    // resolution. Follow these authored, supported legs with the actual
    // walking capsule; ground-floor approaches still use navigation.
    const bool Steps=RelayInspecting==2&&RelayInspectionLeg>0&&RelayInspectionLeg<RelayInspectionPath.Num()-1;
    Brain->SetErrand(Feet+FVector(0,0,Guard->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),Facing,.6f,0,true,true,Steps?20.f:45.f,Steps);
}
