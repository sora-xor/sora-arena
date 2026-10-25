#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraArchiveRules.h"
#include "SoraEnemy.h"
#include "SoraWorldBuilder.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"

namespace
{
FVector ArchiveFeet(const ASoraPlayerCharacter& Hero)
{ return Hero.GetActorLocation()-FVector(0,0,Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()); }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArchiveExitTest,"SoraArena.Campaign.ArchiveExit",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraArchiveExitTest::RunTest(const FString&)
{
    using SoraFieldcraftAutomation::FBeatWorld;
    namespace R=SoraArchiveRules;
    if(!FSoraCatalog::Get().Load()) return false;
    // The duel's actual door blocks the capsule-sized opening.
    {
        FBeatWorld Duel(*this,TEXT("ArchiveLockedExit"),5,8);if(!Duel.Start()) return false;
        const auto& Z=Duel.Campaign()->ActiveChapter()->Space.Zones[Duel.BeatData().Space.Zone];
        const FVector A(Z.Rect.Min.X+1300,Z.Rect.Max.Y-120,R::FloorCm+90),B=A+FVector(0,260,0);
        FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(ArchiveLockedExit),false,Duel.Hero());
        TestTrue(TEXT("The duel's north door blocks a standing capsule sweep"),
            Duel.World->GetTestWorld()->SweepSingleByChannel(Hit,A,B,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(34,88),Q)&&
            Hit.GetComponent()&&Hit.GetComponent()->ComponentHasTag(TEXT("ArchiveNorthGate")));
    }
    FBeatWorld W(*this,TEXT("ArchiveExit"),5,9);if(!W.Start()) return false;
    W.Harden();auto* Hero=W.Hero();
    const auto& Chapter=*W.Campaign()->ActiveChapter();
    const auto& Z=Chapter.Space.Zones[W.BeatData().Space.Zone];
    const auto& Press=Chapter.Beats[10].Space;
    const double X=Z.Rect.Min.X+R::DoorX,Y=Z.Rect.Max.Y,PX=Press.Entry.X,WalkY=Y+R::WalkNorth;
    for(int I=0;I<6000&&!W.Campaign()->TaskProgress().LinesDone;++I) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("The whole pledge finishes without skipping its dialogue"),W.Campaign()->TaskProgress().LinesDone)||
        !TestEqual(TEXT("Lines alone do not cut to the press hall"),W.Campaign()->ActiveBeat(),9)||
        !TestTrue(TEXT("The archive entry has real support six metres up"),FMath::Abs(ArchiveFeet(*Hero).Z-R::FloorCm)<4.f)) return false;
    float LargestMove=0;
    const auto Walk=[&](FVector2D Goal,int MaxFrames=2400)
    {
        bool Good=true;
        for(int Frame=0;Frame<MaxFrames&&FVector2D::Distance(FVector2D(Hero->GetActorLocation()),Goal)>12.f;++Frame)
        {
            W.Look(FRotator(0,(FVector(Goal,0)-Hero->GetActorLocation()).GetSafeNormal2D().Rotation().Yaw,0));
            const FVector Before=Hero->GetActorLocation();
            if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) {Good=false;break;}
            LargestMove=FMath::Max(LargestMove,float(FVector::Distance(Before,Hero->GetActorLocation())));
            if(W.Campaign()->ActiveBeat()==10)
                for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
                {
                    It->SetActorTickEnabled(false);It->GetCharacterMovement()->DisableMovement();
                    if(It->GetController()) It->GetController()->SetActorTickEnabled(false);
                }
        }
        Good=W.World->InjectKey(EKeys::W,IE_Released)&&W.Tick(1)&&Good;
        return Good&&FVector2D::Distance(FVector2D(Hero->GetActorLocation()),Goal)<=25.f;
    };
    if(!TestTrue(TEXT("Mapped forward input reaches the north door"),Walk({X,Y-100}))||
        !TestTrue(TEXT("The unlocked door and first five treads are walkable"),Walk({X,Y+R::StairStart+5*R::TreadCm}))) return false;
    const FVector Paused=Hero->GetActorLocation();
    if(!W.Press(EKeys::Escape)||!W.Tick(120)) return false;
    TestTrue(TEXT("Pause holds the actual stair position"),Hero->GetActorLocation().Equals(Paused,.1f));
    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("The remaining treads descend to the landing"),Walk({X,WalkY}))||
        !TestTrue(TEXT("The stairs reach the four-metre catwalk level"),FMath::Abs(ArchiveFeet(*Hero).Z-R::CatwalkCm)<4.f)) return false;
    // A real temporary obstacle must stop ordinary movement on the connector.
    auto* Barrier=W.World->GetTestWorld()->SpawnActor<AActor>();
    if(!TestNotNull(TEXT("The connector obstruction spawns"),Barrier)) return false;
    auto* Box=NewObject<UBoxComponent>(Barrier);Barrier->SetRootComponent(Box);Box->SetBoxExtent({10,100,120});
    Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();
    const double BlockX=X+400;Barrier->SetActorLocation({BlockX,WalkY,520});
    const bool Blocked=!Walk({X+800,WalkY},180);
    TestTrue(TEXT("A solid obstacle prevents passage and premature completion"),Blocked&&Hero->GetActorLocation().X<BlockX&&W.Campaign()->ActiveBeat()==9);
    Barrier->Destroy();
    const double MidX=(X+PX)*.5;
    if(!TestTrue(TEXT("Removing the obstacle allows walking along the same landing"),Walk({MidX,WalkY}))) return false;
    // Ordinary jump/vault input must not escape the provisional connector
    // into the unbuilt gap. Test both edges with the actual moving capsule.
    for(int Side:{-1,1})
    {
        W.Look(FRotator(0,Side*90,0));
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.World->InjectKey(EKeys::SpaceBar,IE_Pressed)||!W.Tick(120)||
            !W.World->InjectKey(EKeys::SpaceBar,IE_Released)||!W.World->InjectKey(EKeys::W,IE_Released)||!W.Tick(30)) return false;
        if(!TestTrue(TEXT("Jumping toward either bridge screen retains supported play"),
            FMath::Abs(Hero->GetActorLocation().Y-WalkY)<R::WalkHalfWidth&&
            Hero->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(ArchiveFeet(*Hero).Z-R::CatwalkCm)<4.f&&
            W.Campaign()->ActiveBeat()==9)||!Walk({MidX,WalkY})) return false;
    }
    if(!TestTrue(TEXT("The guarded connector reaches the press approach"),Walk({PX,WalkY}))||
        !TestEqual(TEXT("The hall does not start before the press landing"),W.Campaign()->ActiveBeat(),9)||
        !TestTrue(TEXT("The north press doorway reaches the actual NW catwalk"),Walk(Press.Entry))) return false;
    TestEqual(TEXT("Physical arrival after the pledge starts the press hall"),W.Campaign()->ActiveBeat(),10);
    TestTrue(TEXT("The transition retains a grounded capsule on the catwalk"),Hero->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(ArchiveFeet(*Hero).Z-400)<4.f);
    TestTrue(TEXT("Walking and the beat transition never teleport the capsule"),LargestMove<30.f);
    const auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Only arrival records the press checkpoint"),Save&&Save->CheckpointChapter==5&&Save->CheckpointBeat==10);
    AddInfo(FString::Printf(TEXT("Actual mapped movement across ten treads and the connector; maximum displacement %.3f cm. Press guards frozen after arrival. Provisional collision geometry, not final architecture or ordinary combat qualification."),LargestMove));
    return !HasAnyErrors();
}
#endif
