#include "SoraWorldBuilder.h"
#include "SoraSummitRules.h"
#include "SoraBoss.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "Combat/SoraDamage.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "PhysicsEngine/BodySetup.h"
#include "ProceduralMeshComponent.h"

namespace Summit=SoraSummitRules;

void ASoraWorldBuilder::BuildSummitTiles()
{
    const FLinearColor Metal(.12f,.16f,.20f);
    auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Materials/M_ArenaSurface.M_ArenaSurface"),nullptr,LOAD_NoWarn);
    if(!Base) Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    for(int32 X=-Summit::GridRadius;X<Summit::GridRadius;++X)
        for(int32 Y=-Summit::GridRadius;Y<Summit::GridRadius;++Y)
        {
            const auto Poly=Summit::Tile(X,Y);
            if(Poly.empty()) continue;
            auto& Tile=SummitTiles.AddDefaulted_GetRef(); Tile.X=X; Tile.Y=Y;
            const FString Name=FString::Printf(TEXT("SummitTile_%d_%d"),X,Y);
            auto* Mesh=NewObject<UProceduralMeshComponent>(this,MakeUniqueObjectName(this,UProceduralMeshComponent::StaticClass(),FName(*Name)));
            Tile.Mesh=Mesh;
            Mesh->SetupAttachment(RootComponent); Mesh->SetRelativeLocation(SummitCenter);
            Mesh->SetMobility(EComponentMobility::Movable);
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Mesh->SetCollisionObjectType(ECC_WorldStatic); Mesh->SetCollisionResponseToAllChannels(ECR_Block);
            Mesh->SetCanEverAffectNavigation(false); Mesh->SetGenerateOverlapEvents(false);
            Mesh->bUseComplexAsSimpleCollision=false; Mesh->bUseAsyncCooking=false;
            TArray<FVector> Vertices,Normals,Convex;
            TArray<int32> Indices; TArray<FVector2D> UV;
            const auto Triangle=[&](FVector A,FVector B,FVector C)
            {
                const FVector Normal=FVector::CrossProduct(B-A,C-A).GetSafeNormal();
                // ProceduralMesh uses clockwise front faces; normals face outward.
                for(const FVector P:{A,C,B}) { Indices.Add(Vertices.Num()); Vertices.Add(P); Normals.Add(Normal); UV.Add(FVector2D(P)/300.f); }
            };
            for(const auto P:Poly)
            {
                Tile.Outline.Add(FVector2D(P.X,P.Y)); Tile.Stand+=FVector2D(P.X,P.Y);
                Convex.Add(FVector(P.X,P.Y,0)); Convex.Add(FVector(P.X,P.Y,-40));
            }
            Tile.Stand/=Poly.size();
            for(int32 N=1;N<int32(Poly.size())-1;++N)
            {
                Triangle(FVector(Tile.Outline[0],0),FVector(Tile.Outline[N],0),FVector(Tile.Outline[N+1],0));
                Triangle(FVector(Tile.Outline[0],-40),FVector(Tile.Outline[N+1],-40),FVector(Tile.Outline[N],-40));
            }
            for(int32 N=0;N<Tile.Outline.Num();++N)
            {
                const FVector A(Tile.Outline[N],0),B(Tile.Outline[(N+1)%Tile.Outline.Num()],0),Down(0,0,-40);
                Triangle(A,A+Down,B); Triangle(B,A+Down,B+Down);
                auto* Edge=Box(Name+TEXT("Edge"),SummitCenter+(A+B)*.5f+FVector(0,0,2),
                    FVector((B-A).Size(),5,3),Metal,false,(B-A).Rotation());
                Edge->SetVisibility(false); Tile.Edges.Add(Edge);
            }
            const TArray<FLinearColor> Colors; const TArray<FProcMeshTangent> Tangents;
            Mesh->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,UV,Colors,Tangents,false);
            Mesh->AddCollisionConvexMesh(Convex);
            // This convex prism exactly matches the rendered tile. Use it
            // for both movement and complex traces: UWorld's default trace
            // params request complex collision, but this mesh has no cooked
            // triangle section. Set the flag after AddCollisionConvexMesh
            // (which resets it) and before registration creates its shapes.
            Mesh->GetBodySetup()->CollisionTraceFlag=CTF_UseSimpleAsComplex;
            if(Base)
            {
                auto* Material=UMaterialInstanceDynamic::Create(Base,Mesh);
                Material->SetVectorParameterValue(TEXT("BaseColor"),Metal); Material->SetVectorParameterValue(TEXT("Color"),Metal);
                Material->SetScalarParameterValue(TEXT("Roughness"),.72f); Mesh->SetMaterial(0,Material);
            }
            Mesh->RegisterComponent(); AddInstanceComponent(Mesh);
            Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Mesh->SetCanEverAffectNavigation(true);
        }
}

void ASoraWorldBuilder::ResetSeizure()
{
    SummitBoss.Reset(); SummitFieldStarted=-1; SummitPattern=-1; bSummitStrikeAnnounced=false;
    for(auto& Tile:SummitTiles)
    {
        Tile.bSelected=false; Tile.State=int32(Summit::EStage::Intact);
        if(Tile.Mesh)
        {
            Tile.Mesh->SetRelativeLocation(SummitCenter); Tile.Mesh->SetVisibility(true);
            Tile.Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Tile.Mesh->SetCanEverAffectNavigation(true);
        }
        for(UStaticMeshComponent* Edge:Tile.Edges) if(Edge) Edge->SetVisibility(false);
    }
}
void ASoraWorldBuilder::ClearSummitTiles()
{
    for(auto& Tile:SummitTiles) if(Tile.Mesh) Tile.Mesh->DestroyComponent();
    SummitTiles.Reset();
}

bool ASoraWorldBuilder::BeginSeizure(ASoraBoss& Boss,int32 Attack,int32 Serial,int32 WarningMs)
{
    if(!bSummitActive||SummitTiles.IsEmpty()||Boss.BossId()!=TEXT("boss_val_amort")||Boss.PhaseIndex()!=1) return false;
    SummitBoss=&Boss; SummitPattern=(SummitPattern+1)%3;
    SummitFieldStarted=FMath::FloorToInt(GetWorld()->GetTimeSeconds()*1000);
    SummitWarningMs=WarningMs; SummitFieldSerial=Serial; SummitAttackIndex=Attack; bSummitStrikeAnnounced=false;
    const auto* Mode=GetWorld()->GetAuthGameMode<ASoraGameMode>();
    const FVector Hero=Mode&&Mode->Hero()?Mode->Hero()->GetActorLocation()-SummitCenter:FVector::ZeroVector;
    const int32 HX=FMath::FloorToInt(Hero.X/Summit::TileCm),HY=FMath::FloorToInt(Hero.Y/Summit::TileCm);
    for(auto& Tile:SummitTiles) Tile.bSelected=Summit::Selected(SummitPattern,Tile.X,Tile.Y,HX,HY);
    return true;
}

bool ASoraWorldBuilder::SummitSafePoint(const FVector& From,const ACharacter& Body,FVector& Out) const
{
    const auto* Capsule=Body.GetCapsuleComponent();
    const float Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
    double Best=MAX_dbl;
    for(const auto& Tile:SummitTiles)
    {
        if(!Summit::Solid(static_cast<Summit::EStage>(Tile.State))) continue;
        bool EdgeTile=false;
        for(const FIntPoint D:{FIntPoint(1,0),FIntPoint(-1,0),FIntPoint(0,1),FIntPoint(0,-1)})
        {
            const auto* Other=SummitTiles.FindByPredicate([&](const FSoraSummitTile& T) { return T.X==Tile.X+D.X&&T.Y==Tile.Y+D.Y; });
            EdgeTile|=!Other||!Summit::Solid(static_cast<Summit::EStage>(Other->State));
        }
        if(!EdgeTile) continue;
        bool Fits=true;
        for(int32 N=0;N<Tile.Outline.Num();++N)
        {
            const FVector2D A=Tile.Outline[N],D=Tile.Outline[(N+1)%Tile.Outline.Num()]-A,P=Tile.Stand-A;
            if((D.X*P.Y-D.Y*P.X)/D.Size()<Radius+6) Fits=false;
        }
        if(!Fits) continue;
        const FVector Spot=SummitCenter+FVector(Tile.Stand,Half+4);
        const double Distance=FVector::DistSquared2D(Spot,From);
        if(Distance>=Best) continue;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSummitRecovery),false,&Body);
        if(GetWorld()->OverlapBlockingTestByChannel(Spot,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(Radius,Half),Query)) continue;
        Best=Distance; Out=Spot;
    }
    return Best<MAX_dbl;
}

void ASoraWorldBuilder::TickSeizure()
{
    const auto* Mode=GetWorld()?GetWorld()->GetAuthGameMode<ASoraGameMode>():nullptr;
    auto* Hero=Mode?Mode->Hero():nullptr;
    if(!bSummitActive||!Mode||!Mode->IsPlaying()||Mode->bDefeated||!Hero) return;
    auto* Boss=SummitBoss.Get();
    if(SummitFieldStarted>=0&&(!Boss||Boss->IsDefeated()||Boss->PhaseIndex()!=1)) { ResetSeizure(); Boss=nullptr; }
    const int32 Now=FMath::FloorToInt(GetWorld()->GetTimeSeconds()*1000),Elapsed=Now-SummitFieldStarted;
    const auto Stage=SummitFieldStarted<0?Summit::EStage::Intact:Summit::Stage(Elapsed,SummitWarningMs);
    if(Boss&&!bSummitStrikeAnnounced&&Elapsed>=SummitWarningMs)
    { Boss->AnnounceStrike(SummitAttackIndex,SummitFieldSerial); bSummitStrikeAnnounced=true; }
    const FLinearColor Amber=SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Cleave);
    for(auto& Tile:SummitTiles)
    {
        const auto State=Tile.bSelected?Stage:Summit::EStage::Intact;
        if(Tile.State!=int32(State))
        {
            Tile.State=int32(State);
            Tile.Mesh->SetCollisionEnabled(Summit::Solid(State)?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
            Tile.Mesh->SetCanEverAffectNavigation(Summit::Solid(State));
        }
        const double Offset=Tile.bSelected?Summit::Offset(Elapsed,SummitWarningMs):0;
        const FVector Position=SummitCenter+FVector(0,0,Offset);
        if(!Tile.Mesh->GetRelativeLocation().Equals(Position,.01f)) Tile.Mesh->SetRelativeLocation(Position);
        Tile.Mesh->SetVisibility(State!=Summit::EStage::Void||Elapsed-SummitWarningMs<1500);
        const bool Mark=State==Summit::EStage::Marked||State==Summit::EStage::Restoring;
        const FLinearColor Color=Amber*(.65f+.35f*FMath::Sin(Elapsed*.0062831853f));
        for(UStaticMeshComponent* Edge:Tile.Edges)
        {
            Edge->SetVisibility(Mark);
            if(Mark)
                if(auto* Mat=Cast<UMaterialInstanceDynamic>(Edge->GetMaterial(0)))
                { Mat->SetVectorParameterValue(TEXT("BaseColor"),Color); Mat->SetVectorParameterValue(TEXT("Color"),Color); }
        }
    }
    const auto Recover=[&](ACharacter& Body)
    {
        FVector Spot;
        if(!SummitSafePoint(Body.GetActorLocation(),Body,Spot))
            Spot=SummitCenter+FVector(0,-320,120+Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+4);
        Body.SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        Body.GetCharacterMovement()->StopMovementImmediately();
        Body.SetActorLocation(Spot,false,nullptr,ETeleportType::TeleportPhysics);
    };
    if(Hero->GetActorLocation().Z<SummitCenter.Z-100)
    {
        FHitResult Hit; Hit.ImpactPoint=Hero->GetActorLocation();
        auto Fall=FSoraHit::Hazard(Hero->GetActorLocation()); Fall.AttackId=TEXT("amort_seizure_field");
        SoraDamage::Strike(Hero,25.f,Fall,FVector::UpVector,Hit,nullptr,this);
        if(Mode->bDefeated) return;
        Recover(*Hero); Hero->ProtectAfterSummitFall();
    }
    // A falling construct must not remain alive on a lower, unreachable
    // floor and hold the seizure shield forever. Recovery preserves health.
    // Keep this recovery available through a phase change: a body can already
    // be below the floor when P3 restores the tiles and clears SummitBoss.
    ASoraBoss* Occupant=Boss;
    if(!Occupant)
        for(TActorIterator<ASoraBoss> It(GetWorld());It;++It)
            if(It->BossId()==TEXT("boss_val_amort")&&FVector::DistSquared2D(It->ArenaCenter(),SummitCenter)<1) { Occupant=*It; break; }
    if(Occupant)
        for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
            if(It->IsAlive()&&!It->IsFlying()&&(*It==Occupant||It->Summoner()==Occupant)&&It->GetActorLocation().Z<SummitCenter.Z-100) Recover(**It);
}
