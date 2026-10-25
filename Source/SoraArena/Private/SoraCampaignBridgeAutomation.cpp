#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "SoraBridgeProp.h"
#include "SoraBridgeRules.h"
#include "SoraBoss.h"
#include "SoraEquipmentComponent.h"
#include "Combat/SoraBossCatalog.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"
#include "World/SoraNavigation.h"

namespace SoraBridgeTest
{
using SoraFieldcraftAutomation::FBeatWorld;
FVector Feet(const ACharacter& Body)
{ return Body.GetActorLocation()-FVector(0,0,Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); }
ASoraBoss* Boss(FBeatWorld& W) { return const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss()); }
void StopIntent(ASoraBoss& Body)
{
    Body.Hold(60000);
    if(auto* Controller=Body.GetController()) Controller->SetActorTickEnabled(false);
    Body.GetCharacterMovement()->StopMovementImmediately();
    // Keep CharacterMovement enabled: moving-base transport is under test.
}
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    W.World->DestroyTestWorld(true); W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()) return false;
    for(int32 N=0;N<3&&!W.Mode()->IsPlaying();++N) if(!W.Press(EKeys::Enter)) return false;
    W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName Event) { W.Events.Add(Event.ToString()); });
    W.Harden(); return W.Mode()->IsPlaying();
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBridgeDeckTest,"SoraArena.Campaign.BridgeDeck",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBridgeDeckTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!FSoraCatalog::Get().Load()) return false;
    SoraBridgeTest::FBeatWorld W(*this,TEXT("BridgeDeck"),6,12);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden(); auto* Boss=SoraBridgeTest::Boss(W); auto* Arena=W.Mode()->Arena();
    if(!TestNotNull(TEXT("Collatera is present"),Boss)||!TestNotNull(TEXT("Dedicated bridge pivot"),Arena->BridgeDeckRoot())) return false;
    SoraBridgeTest::StopIntent(*Boss);
    TestEqual(TEXT("Phase one starts level"),Arena->BridgeListDegrees(),0.f);
    TestEqual(TEXT("Six chairs and four pods"),Arena->BridgeLooseProps().Num(),10);
    TArray<UStaticMeshComponent*> Pieces; Arena->GetComponents(Pieces);
    int32 AttachedFloors=0;
    for(auto* Piece:Pieces)
    {
        if(Piece->GetName().StartsWith(TEXT("Zone7Floor")))
        { TestTrue(TEXT("Actual bridge floor is movable and attached"),Piece->Mobility==EComponentMobility::Movable&&Piece->IsAttachedTo(Arena->BridgeDeckRoot())); ++AttachedFloors; }
        if(Piece->GetName().StartsWith(TEXT("Zone6")))
            TestFalse(TEXT("Bridge approach stays outside the moving base"),Piece->IsAttachedTo(Arena->BridgeDeckRoot()));
    }
    TestEqual(TEXT("One real bridge floor, no hidden flat duplicate"),AttachedFloors,1);
    const FVector WalkTo=W.Hero()->GetActorLocation()+FVector(0,500,0);
    if(!TestTrue(TEXT("Mapped W walks onto the off-centre deck"),SoraLiftAutomation::Walk(*W.World,WalkTo))) return false;
    const float BasePace=W.Hero()->GetCharacterMovement()->MaxWalkSpeed;
    const FTransform Level=Arena->BridgeDeckRoot()->GetComponentTransform();
    const FVector HeroLocal=Level.InverseTransformPosition(SoraBridgeTest::Feet(*W.Hero()));
    const FVector BossLocal=Level.InverseTransformPosition(SoraBridgeTest::Feet(*Boss));
    const float HeroZ=W.Hero()->GetActorLocation().Z,BossZ=Boss->GetActorLocation().Z;
    // Health setup selects the production phase transition. Combat damage and
    // the barrier are covered by Boss.Collatera; no pawn/base transform is set.
    Boss->Health=Boss->MaxHealth*.6f;
    if(!W.Tick(90)) return false;
    const FTransform Listed=Arena->BridgeDeckRoot()->GetComponentTransform();
    TestEqual(TEXT("Phase two lists ten degrees"),Arena->BridgeListDegrees(),10.f);
    TestTrue(TEXT("Hero rides the base through ordinary swept CharacterMovement"),W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&
        FVector::Dist(Listed.InverseTransformPosition(SoraBridgeTest::Feet(*W.Hero())),HeroLocal)<20&&W.Hero()->GetActorLocation().Z>HeroZ+50);
    TestTrue(TEXT("NPC rides the same moving base"),Boss->GetCharacterMovement()->IsMovingOnGround()&&
        FVector::Dist(Listed.InverseTransformPosition(SoraBridgeTest::Feet(*Boss)),BossLocal)<20&&FMath::Abs(Boss->GetActorLocation().Z-BossZ)>100);
    const auto Floor=W.Hero()->GetCharacterMovement()->CurrentFloor.HitResult;
    TestTrue(TEXT("Actual collision normal is tilted"),FMath::IsNearlyEqual(Floor.ImpactNormal.Z,FMath::Cos(FMath::DegreesToRadians(10.f)),.002f)&&Floor.ImpactNormal.Y<-.16f);
    for(const auto Direction:{TPair<float,float>(-90,1.1f),TPair<float,float>(90,.85f)})
    {
        W.Look(FRotator(0,Direction.Key,0));
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.Tick(12)) return false;
        TestTrue(TEXT("Mapped uphill/downhill input applies authored pace"),FMath::IsNearlyEqual(W.Hero()->GetCharacterMovement()->MaxWalkSpeed,BasePace*Direction.Value,.1f));
        if(!W.World->InjectKey(EKeys::W,IE_Released)||!W.Tick(2)) return false;
    }
    if(!W.Press(EKeys::SpaceBar)||!W.Tick(4)) return false;
    TestTrue(TEXT("Airborne input receives no deck pace modifier"),W.Hero()->GetCharacterMovement()->IsFalling()&&
        Arena->BridgeMoveScale(*W.Hero(),FVector(0,-1,0))==1.f);
    if(!W.Tick(90)) return false;
    TestTrue(TEXT("Navigation projects onto the listed collision"),USoraNavigation::Get(Arena)&&USoraNavigation::Get(Arena)->Settle());
    FVector OnMesh;
    TestTrue(TEXT("Listed deck remains navigable"),USoraNavigation::Get(Arena)->Project(SoraBridgeTest::Feet(*W.Hero()),OnMesh)&&
        FMath::Abs(OnMesh.Z-SoraBridgeTest::Feet(*W.Hero()).Z)<20);
    auto* Prop=Arena->BridgeLooseProps()[0].Get();
    double First=-1,Second=-1,Previous=Prop->WarningElapsedMs();
    for(int32 Frame=0;Frame<900&&Second<0;++Frame)
    {
        if(!W.Tick(1)) return false;
        const double Current=Prop->WarningElapsedMs();
        if(Current>=0&&(Previous<0||Current<Previous))
        { if(First<0) First=W.World->GetTestWorld()->GetTimeSeconds(); else Second=W.World->GetTestWorld()->GetTimeSeconds(); }
        Previous=Current;
    }
    TestTrue(TEXT("Production concurrent scheduler repeats the real slide every six seconds"),First>=0&&Second>First&&FMath::Abs((Second-First)-6)<.04);
    if(!W.Press(EKeys::Escape)) return false;
    const double Paused=Prop->WarningElapsedMs(); const FVector Stopped=Prop->GetActorLocation();
    if(!W.Tick(90)) return false;
    TestTrue(TEXT("Menu pause freezes slide and deck"),Prop->WarningElapsedMs()==Paused&&Prop->GetActorLocation().Equals(Stopped,.01)&&Arena->BridgeListDegrees()==10);
    W.Mode()->ResumePlay(); Boss->Health=Boss->MaxHealth*.3f;
    if(!W.Tick(3)) return false;
    TestTrue(TEXT("Phase three retains tilt and cancels sliding"),Boss->PhaseIndex()==2&&Arena->BridgeListDegrees()==10&&Prop->WarningElapsedMs()<0);
    if(!SoraBridgeTest::Reload(W)||!W.Tick(90)) return false;
    TestTrue(TEXT("Loading the saved third phase rebuilds a listed bridge"),SoraBridgeTest::Boss(W)&&SoraBridgeTest::Boss(W)->PhaseIndex()==2&&
        W.Mode()->Arena()->BridgeListDegrees()==10&&W.Mode()->Arena()->BridgeLooseProps().Num()==10);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Death offers normal checkpoint retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(90)) return false;
    TestTrue(TEXT("Retry preserves the saved phase and real deck"),SoraBridgeTest::Boss(W)&&SoraBridgeTest::Boss(W)->PhaseIndex()==2&&W.Mode()->Arena()->BridgeListDegrees()==10);
    // Exercise the same kit boundary used by campaign advance. Full mission
    // advance and the wheel remain covered by Playthrough and HelmHandsAndFloor.
    Arena=W.Mode()->Arena(); Arena->StageKit(*W.Campaign()->ActiveChapter(),13);
    TestTrue(TEXT("The following helm kit has a level floor and no loose attack bodies"),!Arena->HasBridgeDeck()&&Arena->BridgeListDegrees()==0&&Arena->BridgeLooseProps().IsEmpty());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBridgePropsTest,"SoraArena.Campaign.BridgeProps",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBridgePropsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!FSoraCatalog::Get().Load()) return false;
    SoraBridgeTest::FBeatWorld W(*this,TEXT("BridgeProps"),6,12);
    if(!W.Start(0,INDEX_NONE,1)) return false;
    W.Harden(); auto* Boss=SoraBridgeTest::Boss(W); auto* Arena=W.Mode()->Arena();
    if(!Boss||Arena->BridgeLooseProps().Num()!=10) return false;
    SoraBridgeTest::StopIntent(*Boss); Boss->SetActorTickEnabled(false); // Isolate one real prop pulse from other attacks.
    if(!W.Tick(90)) return false;
    const auto Local=[&](FVector P) { return Arena->BridgeDeckRoot()->GetComponentTransform().TransformPosition(P); };
    for(FVector Point:{FVector(-1800,0,0),FVector(-1800,-900,0),FVector(-1600,-900,0)})
        if(!TestTrue(TEXT("Mapped movement reaches the real downhill contact lane"),SoraLiftAutomation::Walk(*W.World,Local(Point)))) return false;
    auto* Front=Arena->BridgeLooseProps()[0].Get(); auto* Rear=Arena->BridgeLooseProps()[1].Get();
    const FVector Before=Front->GetActorLocation(); const float Health=W.Hero()->Health;
    const int32 Attack=Boss->Data()->AttackIndex(TEXT("slide_props"));
    if(!TestTrue(TEXT("Production slide admission accepts phase two"),Arena->BeginBridgeSlide(*Boss,Attack,7001))) return false;
    const int32 Windup=Boss->WindupFor(Attack);
    if(!W.Tick(1,(Windup-1)/1000.f)) return false;
    TestTrue(TEXT("Warning moves visuals only and deals no early damage"),Front->GetActorLocation().Equals(Before,.01)&&W.Hero()->Health==Health);
    for(int32 Frame=0;Frame<600&&W.Hero()->Health==Health;++Frame) if(!W.Tick(1,1.f/120)) return false;
    TestEqual(TEXT("Swept body contact deals thirty damage"),Health-W.Hero()->Health,30.f);
    TestTrue(TEXT("A real contact blocks the body and knocks down the hero"),Front->IsBlocked()&&W.Hero()->GetEquipment()->IsStaggered());
    const FVector Contact=Front->GetActorLocation();
    if(!W.Tick(60,1.f/120)) return false;
    TestTrue(TEXT("Knockdown remains inside its six-hundred-ms window"),W.Hero()->GetEquipment()->IsStaggered());
    if(!W.Tick(16,1.f/120)) return false;
    TestFalse(TEXT("Knockdown ends after six hundred ms"),W.Hero()->GetEquipment()->IsStaggered());
    TestTrue(TEXT("Blocked prop stays at contact without repeated damage"),Front->GetActorLocation().Equals(Contact,.01)&&Health-W.Hero()->Health==30);
    if(!SoraLiftAutomation::Walk(*W.World,Local(FVector(-1850,-900,0)))) return false;
    const float MissHealth=W.Hero()->Health;
    if(!Arena->BeginBridgeSlide(*Boss,Attack,7002)) return false;
    TestTrue(TEXT("Next cue preserves the contact position"),Front->GetActorLocation().Equals(Contact,.01));
    if(!W.Tick(720)) return false;
    TestEqual(TEXT("A hero beside the swept lane takes no radius damage"),W.Hero()->Health,MissHealth);
    if(!Arena->BeginBridgeSlide(*Boss,Attack,7003)||!W.Tick(360)) return false;
    TestTrue(TEXT("Walls and other props stop both bodies"),Front->IsBlocked()&&Rear->IsBlocked());
    const FTransform Deck=Arena->BridgeDeckRoot()->GetComponentTransform();
    const FVector A=Deck.InverseTransformPosition(Front->GetActorLocation()),B=Deck.InverseTransformPosition(Rear->GetActorLocation());
    TestTrue(TEXT("Props stop inside the port wall and pile without overlap"),A.Y>=-2065.1&&B.Y>=A.Y+69.9&&B.Y<=A.Y+72);
    const FVector Piled=Rear->GetActorLocation();
    if(!W.Tick(120)) return false;
    TestTrue(TEXT("Piled bodies are not reset between pulses"),Rear->GetActorLocation().Equals(Piled,.01));
    return !HasAnyErrors();
}
#endif
