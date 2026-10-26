#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraAudio.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraWardGateRules.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"

namespace SoraWardGateTest
{
using SoraFieldcraftAutomation::FBeatWorld;
void HoldGuards(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)
    {
        I->GetCharacterMovement()->StopMovementImmediately();
        I->GetCharacterMovement()->SetComponentTickEnabled(false);
        if(auto* C=I->GetController())C->SetActorTickEnabled(false);
    }
}
bool WaitForControl(FBeatWorld& W)
{
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1,.02f))return false;
    return W.Test.TestTrue(TEXT("Ward dialogue releases control"),W.Mode()->IsPlaying());
}
bool StartWard(FBeatWorld& W,bool Patrol=false)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    W.Harden();
    if(Patrol)
    {
        // A hidden, stationary observer leaves the real guard routes active.
        W.Stand(FVector(-6620,-565,0));
        W.Hero()->GetCharacterMovement()->StopMovementImmediately();
        W.Hero()->GetCharacterMovement()->SetComponentTickEnabled(false);
    }
    else HoldGuards(W);
    return WaitForControl(W);
}
ASoraEnemy* GuardAt(FBeatWorld& W,int Index)
{
    const auto P=SoraWardGateRules::Posts[Index];
    for(TActorIterator<ASoraEnemy> I(W.World->GetTestWorld());I;++I)
        if(FVector2D::Distance(FVector2D(I->GetActorLocation()),FVector2D(P.X,P.Y))<45)return *I;
    W.Test.AddError(FString::Printf(TEXT("Ward guard %d is absent from its initial post"),Index));return nullptr;
}
bool WalkWard(FBeatWorld& W,FVector2D Point,bool Exit=false)
{
    for(int Frame=0;Frame<2400&&FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),Point)>15.f;++Frame)
    {
        if(W.Campaign()->ActiveBeat()!=2)break;
        W.Look(FVector(Point-FVector2D(W.Hero()->GetActorLocation()),0).Rotation());
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1))return false;
    }
    W.World->InjectKey(EKeys::W,IE_Released);
    if(!W.Tick(4))return false;
    if(Exit)return W.Test.TestEqual(TEXT("Mapped movement through the ward exit advances the campaign"),W.Campaign()->ActiveBeat(),3);
    W.Test.AddInfo(FString::Printf(TEXT("Ward walk toward %s ends at %s, crouched=%d"),
        *Point.ToString(),*W.Hero()->GetActorLocation().ToString(),W.Hero()->IsCrouched()));
    return W.Test.TestTrue(TEXT("Mapped movement reaches its ward waypoint"),W.Campaign()->ActiveBeat()==2&&
        FVector2D::Distance(FVector2D(W.Hero()->GetActorLocation()),Point)<30.f);
}
bool Cut(FBeatWorld& W,ASoraEnemy& E,bool PlaceHero)
{
    if(PlaceHero)W.Stand(E.GetActorLocation()+FVector(-80,0,0));
    UGameplayStatics::ApplyDamage(&E,E.Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!W.Test.TestTrue(TEXT("A lethal-sized blow subdues the bound guard"),E.IsSubdued()&&!E.IsAlive()))return false;
    W.LookAt(E.GetActorLocation());
    if(!W.Hold(EKeys::E,95)||!WaitForControl(W))return false;
    return W.Test.TestTrue(TEXT("Mapped interaction cuts the downed guard's seal"),E.IsFreed());
}
FCollisionObjectQueryParams Objects()
{ FCollisionObjectQueryParams Q;Q.AddObjectTypesToQuery(ECC_WorldStatic);Q.AddObjectTypesToQuery(ECC_WorldDynamic);return Q; }
bool Trace(FBeatWorld& W,FVector A,FVector B,FHitResult& Hit)
{
    return W.World->GetTestWorld()->LineTraceSingleByObjectType(Hit,A,B,Objects(),
        FCollisionQueryParams(SCENE_QUERY_STAT(WardGeometry),false,W.Hero()));
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWardGateSolidsTest,"SoraArena.Campaign.WardGate.Solids",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWardGateSolidsTest::RunTest(const FString&)
{
    using namespace SoraWardGateTest;
    FBeatWorld W(*this,TEXT("WardSolids"),2,2);if(!StartWard(W))return false;
    for(const FVector P:{FVector(-7820,-850,0),FVector(-7820,-630,0),FVector(-7300,-900,-40),
        FVector(-6390,-825,-30),FVector(-6390,-775,-60),FVector(-6390,-725,-90),
        FVector(-6200,-650,-90),FVector(-5975,-650,-60),FVector(-5925,-650,-30)})
    {
        FHitResult H;
        const bool Hit=Trace(W,FVector(P.X,P.Y,P.Z+25),FVector(P.X,P.Y,P.Z-80),H);
        TestTrue(FString::Printf(TEXT("Real floor at %s (component %s, Z %.2f)"),*P.ToString(),*GetNameSafe(H.GetComponent()),H.ImpactPoint.Z),
            Hit&&!H.bStartPenetrating&&FMath::IsNearlyEqual(H.ImpactPoint.Z,P.Z,1.f));
    }
    FHitResult H;
    TestTrue(TEXT("Culvert ceiling is exactly 90 cm above its floor"),
        Trace(W,FVector(-6200,-650,-80),FVector(-6200,-650,50),H)&&FMath::Abs(H.ImpactPoint.Z)<1.f);
    TestTrue(TEXT("The wicket begins physically barred"),Trace(W,FVector(-6280,135,60),FVector(-6100,135,60),H));
    TestTrue(TEXT("The shop has its real walkable roof at 320 cm"),
        Trace(W,FVector(-6400,900,400),FVector(-6400,900,250),H)&&FMath::IsNearlyEqual(H.ImpactPoint.Z,320.,1.));
    TestEqual(TEXT("Only the below-ground culvert surface halves noise"),W.Stealth()->SurfaceAt(FVector(-6200,-650,-89)).StepPermille,500);
    TestTrue(TEXT("The ground above it does not inherit submerged noise suppression"),W.Stealth()->SurfaceAt(FVector(-6200,-650,2)).StepPermille!=500);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWardGateAmbienceTest,"SoraArena.Campaign.WardGate.Ambience",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWardGateAmbienceTest::RunTest(const FString&)
{
    using namespace SoraWardGateTest;
    FBeatWorld W(*this,TEXT("WardAmbience"),2,2);if(!StartWard(W))return false;
    auto* Audio=USoraAudioSubsystem::Get(W.World->GetTestWorld());
    if(!TestNotNull(TEXT("Ward audio subsystem"),Audio))return false;
    const FSoraAudioPlay* Stream=nullptr;
    for(const auto& Play:Audio->Plays())if(Play.Cue==TEXT("amb.stream"))Stream=&Play;
    TestTrue(TEXT("Staging the actual ward starts its positioned culvert loop"),Stream&&Stream->IsVoiced()&&
        Stream->bSpatial&&Stream->bLoop&&Stream->Location.Equals(FVector(-6200,-650,-85))&&
        Audio->LiveLoops().Contains(TEXT("amb.stream")));
    const FSoraBeat* Beat=W.Campaign()->ActiveBeatData();
    if(!TestNotNull(TEXT("Current ward beat"),Beat))return false;
    W.Fieldcraft()->Clear();
    TestFalse(TEXT("Clearing the ward stops its stream"),Audio->LiveLoops().Contains(TEXT("amb.stream")));
    W.Fieldcraft()->Stage(*Beat);
    const auto Streams=Audio->LiveLoops().FilterByPredicate([](FName Cue){return Cue==TEXT("amb.stream");});
    TestEqual(TEXT("Restaging leaves exactly one stream"),Streams.Num(),1);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWardGateScannerTest,"SoraArena.Campaign.WardGate.Scanner",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWardGateScannerTest::RunTest(const FString&)
{
    using namespace SoraWardGateTest;
    FBeatWorld W(*this,TEXT("WardScanner"),2,2);if(!StartWard(W))return false;
    TestFalse(TEXT("Frozen guards do not detect the hero before sensor contact"),W.Stealth()->IsDetected());
    W.Stand(FVector(-6400,-100,0),0);
    if(!W.Hold(EKeys::W,120)||!WaitForControl(W))return false;
    TestTrue(TEXT("Mapped walk into the closed gate contacts the independent scanner"),
        W.Count(TEXT("scanner_enter:scan_arch_b03"))==1&&W.Stealth()->IsDetected()&&W.Hero()->GetActorLocation().X<-6208);
    if(!W.Tick(120))return false;
    TestEqual(TEXT("Remaining in the sheet does not repeat entry"),W.Count(TEXT("scanner_enter:scan_arch_b03")),1);
    W.Stand(FVector(-6400,-100,0));if(!W.Tick(2)||!W.Press(EKeys::Escape))return false;
    W.Stand(FVector(-6245,-100,0));if(!W.Tick(120))return false;
    TestEqual(TEXT("The menu pauses scanner evaluation"),W.Count(TEXT("scanner_enter:scan_arch_b03")),1);
    if(!W.Press(EKeys::Escape)||!W.Tick(3))return false;
    TestEqual(TEXT("Resuming observes the new contact exactly once"),W.Count(TEXT("scanner_enter:scan_arch_b03")),2);
    AddInfo(TEXT("Directed sensor test: AI controllers are held. The first contact uses mapped walking; pause/re-entry uses explicit placement."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWardGateWicketTest,"SoraArena.Campaign.WardGate.Wicket",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWardGateWicketTest::RunTest(const FString&)
{
    using namespace SoraWardGateTest;
    FBeatWorld W(*this,TEXT("WardWicket"),2,2);if(!StartWard(W))return false;
    ASoraEnemy* Other=GuardAt(W,2);ASoraEnemy* Kidoban=GuardAt(W,0);ASoraEnemy* Enforcer=GuardAt(W,3);
    if(!Other||!Kidoban||!Enforcer||!Cut(W,*Other,true))return false;
    TestFalse(TEXT("Freeing another conscript cannot unbar the wicket"),W.Fieldcraft()->IsWardWicketOpen());
    if(!Cut(W,*Kidoban,true))return false;
    TestTrue(TEXT("The freed named kidoban opens the wicket once"),W.Fieldcraft()->IsWardWicketOpen()&&W.Count(TEXT("wicket_open:kidoban"))==1);
    TestFalse(TEXT("The same guard cannot open it again"),W.Fieldcraft()->FreeWardKidoban(Kidoban));
    FHitResult H;
    TestFalse(TEXT("The swung leaf leaves the crouched passage clear"),Trace(W,FVector(-6280,135,60),FVector(-6100,135,60),H));
    TestTrue(TEXT("Opening the wicket preserves its low lintel"),Trace(W,FVector(-6280,135,170),FVector(-6100,135,170),H));
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health,nullptr,Enforcer,UDamageType::StaticClass());
    if(!TestTrue(TEXT("Lethal damage presents the real retry screen"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter))return false;
    HoldGuards(W);if(!WaitForControl(W))return false;
    TestEqual(TEXT("Retry restores the ward checkpoint"),W.Campaign()->ActiveBeat(),2);
    TestFalse(TEXT("Retry restores a barred wicket"),W.Fieldcraft()->IsWardWicketOpen());
    TestFalse(TEXT("Retry resets the sensor's detection state"),W.Stealth()->IsDetected());
    TestTrue(TEXT("Retry restores the closed leaf's physical collision"),Trace(W,FVector(-6280,135,60),FVector(-6100,135,60),H));
    AddInfo(TEXT("Directed named-guard, interaction and checkpoint test. Knockdowns use the damage interface; AI and movement are held."));
    return !HasAnyErrors();
}

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FSoraWardGateRoutesTest,"SoraArena.Campaign.WardGate.Routes",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
void FSoraWardGateRoutesTest::GetTests(TArray<FString>& Names,TArray<FString>& Commands) const
{ for(const TCHAR* Name:{TEXT("Culvert"),TEXT("Roof"),TEXT("Wicket")}){Names.Add(Name);Commands.Add(Name);} }
bool FSoraWardGateRoutesTest::RunTest(const FString& Route)
{
    using namespace SoraWardGateTest;
    FBeatWorld W(*this,*(TEXT("WardRoute")+Route),2,2);if(!StartWard(W))return false;
    if(Route==TEXT("Culvert"))
    {
        if(!W.Press(EKeys::C)||!W.Tick(10)||!TestTrue(TEXT("Mapped crouch changes the real capsule"),W.Hero()->IsCrouched())||
           !WalkWard(W,{-7300,-550})||!WalkWard(W,{-7000,-800})||!WalkWard(W,{-6390,-900})||
           !WalkWard(W,{-6390,-650})||!WalkWard(W,{-6200,-650}))return false;
        TestTrue(TEXT("Crouched movement reaches the physical underground culvert"),W.Hero()->GetActorLocation().Z<0);
        if(!WalkWard(W,{-5850,-650})||!WalkWard(W,{-5800,-400}))return false;
    }
    else if(Route==TEXT("Roof"))
    {
        if(!WalkWard(W,{-7400,400})||!WalkWard(W,{-6400,600}))return false;
        W.Look(FRotator(0,90,0));if(!W.Press(EKeys::SpaceBar)||!W.Tick(240))return false;
        if(!TestTrue(TEXT("Mapped jump climbs the authored ladder onto its roof"),
            W.Raised(TEXT("ladder_up:ladder_b03_shop"))&&!W.Fieldcraft()->IsOnLadder()&&W.Hero()->GetActorLocation().Z>400)||
           !WalkWard(W,{-6400,930})||!WalkWard(W,{-6000,930})||!WalkWard(W,{-6000,500})||!W.Tick(90)||
           !WalkWard(W,{-5800,400}))return false;
    }
    else if(Route==TEXT("Wicket"))
    {
        auto* Kidoban=GuardAt(W,0);if(!Kidoban||!WalkWard(W,{-6700,350})||!WalkWard(W,{-6380,150})||!Cut(W,*Kidoban,false)||
           !W.Press(EKeys::C)||!W.Tick(10)||!WalkWard(W,{-6300,135})||!WalkWard(W,{-6100,135}))return false;
    }
    else return false;
    TestFalse(TEXT("The alternate route avoids the scanner"),W.Raised(TEXT("scanner_enter:scan_arch_b03")));
    if(!WalkWard(W,{-5800,0},true))return false;
    AddInfo(TEXT("Directed traversal from the ward spawn with mapped movement, crouch and ladder input; no hero position warps. AI is held, and the wicket fixture supplies a nonlethal damage hit. This is not ordinary stealth acceptance."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWardGatePatrolsTest,"SoraArena.Campaign.WardGate.Patrols",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWardGatePatrolsTest::RunTest(const FString&)
{
    using namespace SoraWardGateTest;
    FBeatWorld W(*this,TEXT("WardPatrols"),2,2);if(!StartWard(W,true))return false;
    ASoraEnemy* Guards[2]={GuardAt(W,1),GuardAt(W,4)};if(!Guards[0]||!Guards[1])return false;
    for(int I=0;I<3100;++I)
    {
        if(!W.Tick(1,.02f))return false;
        for(auto* E:Guards)
        {
            const auto* Brain=Cast<ASoraEnemyController>(E->GetController());
            if(!TestTrue(TEXT("The observed guard remains on its unaware patrol"),Brain&&Brain->State()==SoraStealthRules::EState::Unaware))return false;
        }
    }
    for(int G=0;G<2;++G)
    {
        const auto& T=Cast<ASoraEnemyController>(Guards[G]->GetController())->PatrolTiming();
        const int Period=G?50000:40000;
        TestTrue(TEXT("Real waypoint arrivals complete the authored circuit on time"),T.Cycles>=1&&!T.Overdue&&FMath::Abs(T.LastCycleMs-Period)<=50&&T.Visited==63);
        AddInfo(FString::Printf(TEXT("Ward patrol %d: cycles=%d last_ms=%lld visited=%u overdue=%d"),G,T.Cycles,T.LastCycleMs,T.Visited,T.Overdue));
    }
    if(!W.Press(EKeys::Escape))return false;
    const FVector Before[]={Guards[0]->GetActorLocation(),Guards[1]->GetActorLocation()};
    const long long Clocks[]={Cast<ASoraEnemyController>(Guards[0]->GetController())->PatrolTiming().ElapsedMs,
        Cast<ASoraEnemyController>(Guards[1]->GetController())->PatrolTiming().ElapsedMs};
    if(!W.Tick(180))return false;
    for(int G=0;G<2;++G)
    {
        TestTrue(TEXT("Menu holds the physical ward patrol"),Guards[G]->GetActorLocation().Equals(Before[G],1.f));
        TestEqual(TEXT("Menu holds its circuit clock"),Cast<ASoraEnemyController>(Guards[G]->GetController())->PatrolTiming().ElapsedMs,Clocks[G]);
    }
    AddInfo(TEXT("Live patrol test with the observer held inside the hut. This does not establish ordinary stealth difficulty."));
    return !HasAnyErrors();
}
#endif
