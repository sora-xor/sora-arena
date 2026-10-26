#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraProjectile.h"
#include "SoraWorkshopEncounterRules.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"

namespace SoraWorkshopEntryTest
{
using SoraFieldcraftAutomation::FBeatWorld;
namespace R=SoraWorkshopEncounterRules;
ASoraEnemy* Member(FBeatWorld& W,int Index)
{
    const FName Tag(*FString::Printf(TEXT("WorkshopEntry%d"),Index));
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->IsAlive()&&It->ActorHasTag(Tag))return *It;
    return nullptr;
}
bool EntryReady(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    W.Harden();for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    W.Stand(FVector(1900,-1660,0));if(!W.Tick(10)||!W.Hold(EKeys::E,125))return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    return W.Test.TestFalse(TEXT("The real seal hold releases the encounter"),W.Fieldcraft()->NeedsWorkshopSeal());
}
void Defeat(FBeatWorld& W,ASoraEnemy* E)
{if(E)UGameplayStatics::ApplyDamage(E,E->Health+1000,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());}
bool Entered(FBeatWorld& W,int Begin,int End)
{
    for(int I=Begin;I<End;++I){auto* E=Member(W,I);if(!E||E->IsWorkshopArriving())return false;}
    return true;
}
ASoraEnemy* ReachRoof(FBeatWorld& W)
{
    for(int F=0;F<1000&&!Member(W,7);++F)
    {for(int I=0;I<7;++I)Defeat(W,Member(W,I));if(!W.Tick(1))return nullptr;}
    return Member(W,7);
}
ASoraProjectile* WarnedShell(FBeatWorld& W)
{
    for(TActorIterator<ASoraProjectile> It(W.World->GetTestWorld());It;++It)
        if(!It->IsActorBeingDestroyed()&&IsValid(It->ArcWarningActor()))return *It;
    return nullptr;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopEntriesTest,"SoraArena.Campaign.LanternWorkshop.AuthoredArrivals",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopEntriesTest::RunTest(const FString&)
{
    using namespace SoraWorkshopEntryTest;
    FBeatWorld W(*this,TEXT("WorkshopEntries"),2,7);if(!EntryReady(W))return false;
    TestEqual(TEXT("Only the street wave is released initially"),W.Campaign()->TaskProgress().Released,1u);
    for(int I=0;I<3;++I)
    {
        auto* E=Member(W,I);if(!TestNotNull(TEXT("Each street member has its authored identity"),E))return false;
        TestTrue(TEXT("Street members begin in the north-east passage"),E->GetActorLocation().X>3440&&E->GetActorLocation().Y>-1030);
    }
    for(int F=0;F<600&&!Entered(W,0,3);++F)if(!W.Tick(1))return false;
    if(!TestTrue(TEXT("All three rifles physically enter through the street passage"),Entered(W,0,3)))return false;
    Defeat(W,Member(W,0));if(!W.Tick(10))return false;
    TestEqual(TEXT("Two survivors hold back wave two"),W.Campaign()->TaskProgress().Released,1u);
    Defeat(W,Member(W,1));
    TMap<int,FVector> Last;TSet<int> Seen;bool PausedVault=false;
    for(int F=0;F<600&&!Entered(W,3,7);++F)
    {
        if(!W.Tick(1))return false;
        for(int I=3;I<7;++I)if(auto* E=Member(W,I))
        {
            const FVector At=E->GetActorLocation();const auto P=R::Spawns[I].Floor;
            if(!Seen.Contains(I))
            {Seen.Add(I);TestTrue(TEXT("Each second-wave member spawns at its assigned entrance"),FVector::Dist2D(At,FVector(P.X,P.Y,0))<20);}
            if(const auto* Before=Last.Find(I))TestTrue(TEXT("Entry movement uses continuous capsule motion"),FVector::Dist(*Before,At)<25);
            Last.Add(I,At);
            if(I<5&&At.Z>200&&!PausedVault)
            {
                if(!W.Press(EKeys::Escape))return false;const FVector Held=E->GetActorLocation();
                if(!W.Tick(60))return false;
                TestTrue(TEXT("Menu pause freezes the airborne vault"),E->GetActorLocation().Equals(Held,.01));
                W.Mode()->ResumePlay();Last.Add(I,Held);PausedVault=true;
            }
        }
    }
    TestEqual(TEXT("All four second-wave entrances were observed"),Seen.Num(),4);
    TestTrue(TEXT("Both real fence vaults and both canal entries finish"),Entered(W,3,7));
    TestTrue(TEXT("A physical vault was exercised across pause"),PausedVault);
    for(int I=3;I<5;++I)
    {
        auto* E=Member(W,I);if(!E)return false;
        auto* Brain=Cast<ASoraEnemyController>(E->GetController());
        TestTrue(TEXT("Vault uses LaunchCharacter and ends on the yard floor"),Brain&&Brain->WorkshopVaultLaunched()&&
            E->GetActorLocation().X<3350&&E->GetCharacterMovement()->IsMovingOnGround()&&E->GetActorLocation().Z<100);
    }
    AddInfo(TEXT("Seeded checkpoint, hardened hero and scripted defeats release waves; movement and pause are real. Ordinary combat balance and visual acceptance are not established."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopBlockedEntryTest,"SoraArena.Campaign.LanternWorkshop.BlockedArrival",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopBlockedEntryTest::RunTest(const FString&)
{
    using namespace SoraWorkshopEntryTest;
    FBeatWorld W(*this,TEXT("WorkshopBlockedEntry"),2,7);if(!EntryReady(W))return false;
    auto* Barrier=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Mesh=ASoraWorldBuilder::Shape(Barrier,nullptr,TEXT("EntryBarrier"),TEXT("/Engine/BasicShapes/Cube.Cube"),
        FVector::ZeroVector,FVector(2,.4,2),FLinearColor::Gray,true);
    Barrier->SetRootComponent(Mesh);Barrier->SetActorLocation(FVector(3480,-600,100));
    if(!W.Tick(420))return false;
    for(int I=0;I<3;++I)
    {
        auto* E=Member(W,I);if(!TestNotNull(TEXT("Blocked rifle remains alive"),E))return false;
        TestTrue(TEXT("A collision stop cannot count as completed arrival"),E->IsWorkshopArriving()&&E->GetActorLocation().Y>-580);
    }
    Barrier->Destroy();for(int F=0;F<600&&!Entered(W,0,3);++F)if(!W.Tick(1))return false;
    TestTrue(TEXT("Removing the obstruction lets the real routes finish"),Entered(W,0,3));
    AddInfo(TEXT("An injected physical barrier isolates blocked-route handling; no production collision is changed."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopRoofShellTest,"SoraArena.Campaign.LanternWorkshop.RooftopWarningRetry",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopRoofShellTest::RunTest(const FString&)
{
    using namespace SoraWorkshopEntryTest;
    FBeatWorld W(*this,TEXT("WorkshopRoofShell"),2,7);if(!EntryReady(W))return false;
    auto* Roof=ReachRoof(W);if(!TestNotNull(TEXT("Normal wave accounting releases the rooftop grenadier"),Roof))return false;
    TestTrue(TEXT("The grenadier spawns on its supported eave"),Roof->GetActorLocation().Equals(FVector(R::Roof.X,R::Roof.Y,R::Roof.Z+90.15),5));
    for(int F=0;F<600&&!WarnedShell(W);++F)if(!W.Tick(1))return false;
    auto* Shell=WarnedShell(W);if(!TestNotNull(TEXT("Normal grenadier AI launches a warned shell"),Shell))return false;
    TWeakObjectPtr<AActor> Warning=Shell->ArcWarningActor();TWeakObjectPtr<ASoraProjectile> WeakShell=Shell;
    TArray<UStaticMeshComponent*> Parts;Warning->GetComponents(Parts);
    TestEqual(TEXT("The warning contains a trajectory and closed landing ring"),Parts.Num(),56);
    for(auto* P:Parts)TestEqual(TEXT("Warning geometry cannot block movement or projectiles"),P->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
    if(!W.Press(EKeys::Escape))return false;const FVector Held=Shell->GetActorLocation();
    if(!W.Tick(120))return false;
    TestTrue(TEXT("Pause preserves both projectile and its warning"),WeakShell.IsValid()&&Warning.IsValid()&&Shell->GetActorLocation().Equals(Held,.01));
    W.Mode()->ResumePlay();for(int F=0;F<300&&WeakShell.IsValid();++F)if(!W.Tick(1))return false;
    TestFalse(TEXT("Actual impact removes the projectile-owned warning"),Warning.IsValid());
    for(int F=0;F<600&&!WarnedShell(W);++F)
    {
        if(!W.Tick(1))return false;
        TestTrue(TEXT("Ranged retreat never walks the roof post off its eave"),FVector::Dist2D(Roof->GetActorLocation(),FVector(R::Roof.X,R::Roof.Y,0))<3&&
            Roof->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Roof->GetActorLocation().Z-740.15)<3);
    }
    Shell=WarnedShell(W);if(!TestNotNull(TEXT("Normal recovery permits a second warned shell"),Shell))return false;
    WeakShell=Shell;Warning=Shell->ArcWarningActor();TWeakObjectPtr<ASoraEnemy> OldRoof=Roof;
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health,nullptr,nullptr,UDamageType::StaticClass());
    if(!TestTrue(TEXT("Real defeat opens retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter))return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    TestTrue(TEXT("Retry destroys the old roof actor, shell and warning"),!OldRoof.IsValid()&&!WeakShell.IsValid()&&!Warning.IsValid());
    TestTrue(TEXT("Retry restores the uncut seal and unreleased waves"),W.Fieldcraft()->NeedsWorkshopSeal()&&W.Campaign()->TaskProgress().Released==0);
    AddInfo(TEXT("Wave defeats are scripted; roof AI, windup, shell flight, collision, pause and retry run normally. Warning art and ordinary encounter play still need review."));
    return !HasAnyErrors();
}
#endif
