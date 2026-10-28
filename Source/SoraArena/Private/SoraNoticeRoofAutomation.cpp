#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraWorldBuilder.h"
#include "SoraEnemy.h"
#include "SoraNoticeSquareRules.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "ProceduralMeshComponent.h"

namespace SoraNoticeRoofTest
{
using SoraFieldcraftAutomation::FBeatWorld;
bool Controls(FBeatWorld& W)
{
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    return W.Test.TestTrue(TEXT("The authored introduction releases controls"),W.Mode()->IsPlaying());
}
UStaticMeshComponent* Part(FBeatWorld& W,const TCHAR* Name)
{
    TArray<UStaticMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
    for(auto* P:Parts)if(P->GetName().StartsWith(Name))return P;
    return nullptr;
}
int Bodies(FBeatWorld& W)
{
    TArray<UProceduralMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
    int Count=0;for(auto* P:Parts)if(P->GetName().StartsWith(TEXT("NoticeMoneyChangerBody")))++Count;
    return Count;
}
ASoraEnemy* Marksman(FBeatWorld& W,bool RemoveOthers)
{
    ASoraEnemy* Mark=nullptr;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        if(It->ArchetypeId()==TEXT("marksman"))Mark=*It;
        else if(RemoveOthers)It->Destroy();
    }
    return Mark;
}
FVector Feet(FBeatWorld& W)
{
    return W.Hero()->GetActorLocation()-FVector(0,0,W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}
bool Walk(FBeatWorld& W,FVector2D Point,bool Controller)
{
    bool Grounded=true;float Largest=0;
    for(int I=0;I<1800&&FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),Point)>12;++I)
    {
        W.Look((FVector(Point,0)-W.Hero()->GetActorLocation()).GetSafeNormal2D().Rotation());
        const FVector Before=W.Hero()->GetActorLocation();
        if(!(Controller?W.World->InjectAxis(EKeys::Gamepad_LeftY,.6f):W.World->InjectKey(EKeys::W,IE_Pressed))||!W.Tick(1))return false;
        Grounded&=W.Hero()->GetCharacterMovement()->IsMovingOnGround();
        Largest=FMath::Max(Largest,float(FVector::Dist(Before,W.Hero()->GetActorLocation())));
    }
    if(!(Controller?W.World->InjectAxis(EKeys::Gamepad_LeftY,0):W.World->InjectKey(EKeys::W,IE_Released))||!W.Tick(4))return false;
    W.Test.AddInfo(FString::Printf(TEXT("Walk toward %s: feet %s, maximum step %.3f cm, grounded %d"),*Point.ToString(),*Feet(W).ToString(),Largest,Grounded));
    return W.Test.TestTrue(TEXT("The route segment uses continuous grounded movement"),Grounded&&Largest<15&&
        FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),Point)<30);
}
bool Flight(FBeatWorld& W,const FSoraLadder& L,bool Up,bool Controller,bool Pause=false)
{
    W.Look(FRotator(0,L.Yaw+(Up?0:180),0));
    if(!W.Test.TestTrue(TEXT("The physical ladder end is usable"),W.Fieldcraft()->Readout(*W.Hero()).bAtLadder)||
       !W.Press(Controller?EKeys::Gamepad_FaceButton_Bottom:EKeys::J)||
       !W.Test.TestTrue(TEXT("Mapped jump takes the ladder"),W.Fieldcraft()->IsOnLadder()))return false;
    float Largest=0;
    for(int I=0;I<600&&W.Fieldcraft()->IsOnLadder();++I)
    {
        const FVector Before=W.Hero()->GetActorLocation();
        if(!W.Tick(1))return false;
        Largest=FMath::Max(Largest,float(FVector::Dist(Before,W.Hero()->GetActorLocation())));
        if(Pause&&I==40)
        {
            if(!W.Press(EKeys::Escape))return false;
            const FVector Held=W.Hero()->GetActorLocation();
            if(!W.Tick(120)||!W.Test.TestTrue(TEXT("Pause holds the real ladder position"),Held.Equals(W.Hero()->GetActorLocation(),.01f))||!W.Press(EKeys::Escape))return false;
        }
    }
    W.Test.AddInfo(FString::Printf(TEXT("%s %s: feet %s, maximum step %.3f cm"),*L.Id,Up?TEXT("up"):TEXT("down"),*Feet(W).ToString(),Largest));
    return W.Test.TestTrue(TEXT("Ladder movement respects its 150 cm/s limit"),Largest<=2.6f);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNoticeRoofSolidsTest,"SoraArena.Campaign.NoticeSquare.RoofSolids",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraNoticeRoofSolidsTest::RunTest(const FString&)
{
    using namespace SoraNoticeRoofTest;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("NoticeRoofSolids"),2,9);
    if(!W.Start()||!Controls(W))return false;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)It->Destroy();
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(NoticeRoofSolids),false,W.Hero());
    for(const FVector P:{FVector(900,800,750),FVector(960,400,560),FVector(600,350,536.25),
        FVector(650,1250,536.25),FVector(650,1350,488.75),FVector(500,1200,320)})
    {
        FHitResult Hit;
        const bool Found=W.World->GetTestWorld()->LineTraceSingleByChannel(Hit,P+FVector(0,0,500),P-FVector(0,0,100),ECC_Visibility,Query);
        AddInfo(FString::Printf(TEXT("Roof probe %s hit %s at %s"),*P.ToString(),*GetNameSafe(Hit.GetComponent()),*Hit.ImpactPoint.ToString()));
        TestTrue(TEXT("The visible roof has the specified physical surface"),Found&&FMath::Abs(Hit.ImpactPoint.Z-P.Z)<.2);
    }
    FHitResult Wall;
    TestTrue(TEXT("The gabled building is closed to street movement"),W.World->GetTestWorld()->LineTraceSingleByChannel(
        Wall,FVector(500,1000,100),FVector(700,1000,100),ECC_Visibility,Query)&&FMath::Abs(Wall.ImpactPoint.X-600)<.2);
    const auto* Capsule=W.Hero()->GetCapsuleComponent();
    for(const auto& L:W.Craft().Ladders)
    {
        const FVector Foot(L.Foot,L.BaseHeightCm+Capsule->GetScaledCapsuleHalfHeight()+2.15f);
        const FVector Above=Foot+FVector(0,0,L.RiseCm()),Top=Above+FRotator(0,L.Yaw,0).Vector()*150;
        for(const auto Segment:{TPair<FVector,FVector>(Foot,Above),TPair<FVector,FVector>(Above,Top)})
        {
            FHitResult Hit;
            const bool Blocked=W.World->GetTestWorld()->SweepSingleByObjectType(Hit,Segment.Key,Segment.Value,FQuat::Identity,
                FCollisionObjectQueryParams(FCollisionObjectQueryParams::AllStaticObjects),
                FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),Query);
            if(Blocked)AddInfo(FString::Printf(TEXT("%s blocked by %s at %s"),*L.Id,*GetNameSafe(Hit.GetComponent()),*Hit.Location.ToString()));
            TestFalse(TEXT("A full standing capsule clears the authored ladder segments"),Blocked);
        }
    }
    TestEqual(TEXT("Only the board canopy amplifies steps"),W.Stealth()->SurfaceAt(FVector(500,1200,322)).StepPermille,1500);
    TestEqual(TEXT("Kawara does not inherit board noise"),W.Stealth()->SurfaceAt(FVector(900,800,752)).StepPermille,1000);
    TestEqual(TEXT("The building consists of two closed convex halves"),Bodies(W),2);
    TestNull(TEXT("The world roof does not stage the old floating slab"),Part(W,TEXT("Roof_ladder_b10")));
    return !HasAnyErrors();
}

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FSoraNoticeRoofRouteTest,"SoraArena.Campaign.NoticeSquare.RoofRoute",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
void FSoraNoticeRoofRouteTest::GetTests(TArray<FString>& Names,TArray<FString>& Commands)const
{
    Names.Add(TEXT("Keyboard"));Commands.Add(TEXT("Keyboard"));
    Names.Add(TEXT("Controller"));Commands.Add(TEXT("Controller"));
}
bool FSoraNoticeRoofRouteTest::RunTest(const FString& Parameters)
{
    using namespace SoraNoticeRoofTest;
    const bool Controller=Parameters==TEXT("Controller");
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,Controller?TEXT("NoticeRoofPad"):TEXT("NoticeRoofKeys"),2,9);
    if(!W.Start()||!Controls(W))return false;
    ASoraEnemy* Mark=Marksman(W,true);
    if(!TestNotNull(TEXT("The actual ridge marksman is live"),Mark))return false;
    AddInfo(TEXT("Only the initial street fixture is placed. Six other guards are removed; the marksman's normal senses and scan remain active. This qualifies traversal and rear takedown, not seven-guard stealth difficulty."));
    W.Harden();W.Stand(FVector(500,1750,0),-90);
    if(!W.Tick(10))return false;
    if(!Controller&&(!W.Press(EKeys::Escape)||!TestTrue(TEXT("The menu permits rebinding Jump"),W.Hero()->RemapCombatAction(TEXT("Jump"),EKeys::J))||!W.Press(EKeys::Escape)))return false;
    const auto A=W.Craft().Ladders[0],B=W.Craft().Ladders[1];
    if(!Walk(W,A.Foot,Controller)||!Flight(W,A,true,Controller,true)||!W.Tick(5)||
       !TestTrue(TEXT("The first flight ends on its supported canopy"),!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet(W).Z-322.15)<1)||
       !Walk(W,B.Foot,Controller))return false;
    auto* Roof=Part(W,TEXT("NoticeMoneyChangerRoofNorth"));
    if(!TestNotNull(TEXT("The second flight uses the real pitched roof"),Roof))return false;
    const auto Collision=Roof->GetCollisionEnabled();
    if(!Controller)Roof->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(!Flight(W,B,true,Controller))return false;
    if(!Controller)
    {
        TestTrue(TEXT("The missing roof cannot award arrival"),W.Fieldcraft()->IsOnLadder()&&!W.Raised(TEXT("roof_reached:")+B.Id));
        Roof->SetCollisionEnabled(Collision);
        if(!W.Tick(10))return false;
    }
    if(!TestTrue(TEXT("The second flight finishes on the real roof"),!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround())||
       !W.Press(Controller?EKeys::Gamepad_RightThumbstick:EKeys::C)||!W.Tick(3))return false;
    for(const FVector2D Point:{FVector2D(1100,1000),FVector2D(1100,800),FVector2D(1010,800)})if(!Walk(W,Point,Controller))return false;
    W.LookAt(Mark->GetActorLocation());
    if(!TestTrue(TEXT("The east approach offers a rear takedown on the live scanning marksman"),W.Stealth()->TakedownTarget(*W.Hero())==Mark)||
       !W.Press(Controller?EKeys::Gamepad_FaceButton_Right:EKeys::RightMouseButton)||!W.Tick(180)||
       !TestTrue(TEXT("The mapped melee input completes the lethal takedown"),Mark->IsBody()&&!Mark->IsUnconscious()))return false;
    for(const FVector2D Point:{FVector2D(1100,800),FVector2D(1100,1000),FVector2D(650,1250)})if(!Walk(W,Point,Controller))return false;
    if(!W.Press(Controller?EKeys::Gamepad_RightThumbstick:EKeys::C)||!W.Tick(3)||!Flight(W,B,false,Controller)||!W.Tick(5)||
       !TestTrue(TEXT("The upper descent returns to the supported canopy"),!W.Fieldcraft()->IsOnLadder()&&FMath::Abs(Feet(W).Z-322.15)<1)||
       !Walk(W,FVector2D(500,1450),Controller)||!Flight(W,A,false,Controller)||!W.Tick(5)||!Walk(W,FVector2D(500,1750),Controller))return false;
    TestTrue(TEXT("Both return flights end at street level"),!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet(W).Z-2.15)<1);
    TestEqual(TEXT("Each roof arrival is emitted once"),W.Count(*(TEXT("roof_reached:")+B.Id)),1);
    FBeatWorld::Hurt(*W.Hero(),W.Hero()->Health+1000);
    if(!W.Tick(2)||!TestTrue(TEXT("Death offers checkpoint retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!Controls(W))return false;
    auto* Fresh=Marksman(W,false);
    TestTrue(TEXT("Retry replaces the defeated rooftop guard at the actual ridge"),Fresh&&Fresh!=Mark&&!Fresh->IsBody()&&
        FVector::Dist2D(Fresh->GetActorLocation(),FVector(900,800,0))<10&&Fresh->GetActorLocation().Z>830);
    TestTrue(TEXT("Retry restores both flights without duplicate building bodies or a held ladder"),W.Craft().Ladders.Num()==2&&Bodies(W)==2&&!W.Fieldcraft()->IsOnLadder());
    return !HasAnyErrors();
}
#endif
