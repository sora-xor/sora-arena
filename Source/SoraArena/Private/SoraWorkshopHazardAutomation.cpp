#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraProjectile.h"
#include "SoraWorkshopProp.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"
#include "Misc/ScopeExit.h"

namespace SoraWorkshopHazardTest
{
using SoraFieldcraftAutomation::FBeatWorld;
namespace R=SoraWorkshopHazardRules;
TArray<ASoraWorkshopProp*> Props(FBeatWorld& W)
{
    TArray<ASoraWorkshopProp*> Found;
    for(TActorIterator<ASoraWorkshopProp> It(W.World->GetTestWorld());It;++It)
        if(!It->IsActorBeingDestroyed())Found.Add(*It);
    Found.Sort([](const ASoraWorkshopProp& A,const ASoraWorkshopProp& B){return A.GetActorLocation().X<B.GetActorLocation().X;});
    return Found;
}
void FreezeWorkshopHazard(FBeatWorld& W)
{
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
    {
        It->SetActorTickEnabled(false);It->GetCharacterMovement()->StopMovementImmediately();
        It->GetCharacterMovement()->SetComponentTickEnabled(false);
        if(auto* Brain=It->GetController())Brain->SetActorTickEnabled(false);
    }
}
bool Tick(FBeatWorld& W,int Frames)
{for(int I=0;I<Frames;++I){FreezeWorkshopHazard(W);if(!W.Tick(1))return false;}return true;}
bool WorkshopHazardReady(FBeatWorld& W)
{
    if(!FSoraCatalog::Get().Load()||!W.Start())return false;
    W.Harden();for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!Tick(W,1))return false;
    return W.Test.TestTrue(TEXT("The defense stages one oil stack and three soft covers"),W.Mode()->IsPlaying()&&Props(W).Num()==4);
}
void Place(ASoraCharacterBase& Body,FVector Feet)
{
    Body.GetCharacterMovement()->StopMovementImmediately();
    Body.SetActorLocation(Feet+FVector(0,0,Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.15),false,nullptr,ETeleportType::TeleportPhysics);
}
ASoraProjectile* Shell(FBeatWorld& W,FVector From,FVector Velocity,float Radius=100,float Damage=1,bool Arrow=false)
{
    const FTransform At(Velocity.Rotation(),From);
    auto* P=W.World->GetTestWorld()->SpawnActorDeferred<ASoraProjectile>(ASoraProjectile::StaticClass(),At,
        W.Hero(),W.Hero(),ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!P)return nullptr;
    P->Velocity=Velocity;P->Radius=Radius;P->Damage=Damage;P->Gravity=0;P->ArmingCm=0;P->WeaponId=7;P->bArrow=Arrow;
    P->FinishSpawning(At);return P;
}
bool Ignite(FBeatWorld& W,ASoraWorkshopProp& Oil)
{
    if(!W.Test.TestNotNull(TEXT("A real explosive projectile is launched"),Shell(W,FVector(2600,-1200,55),FVector(-1500,0,0))))return false;
    for(int I=0;I<120&&!Oil.IsSpent();++I)if(!Tick(W,1))return false;
    return W.Test.TestTrue(TEXT("Actual projectile contact ignites the oil"),Oil.IsSpent()&&Oil.FireLeftMs()>0);
}
void Hit(FBeatWorld& W,ASoraWorkshopProp& P,int Amount,bool Ranged)
{
    FHitResult Contact;Contact.ImpactPoint=P.GetActorLocation();
    const auto H=Ranged?FSoraHit::Ranged(W.Hero()->GetActorLocation(),3):FSoraHit::Melee(W.Hero()->GetActorLocation(),0);
    SoraDamage::Strike(&P,Amount,H,FVector::ForwardVector,Contact,W.Hero()->GetController(),W.Hero());
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopOilIgnitionTest,"SoraArena.Campaign.LanternWorkshop.OilIgnition",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopOilIgnitionTest::RunTest(const FString&)
{
    using namespace SoraWorkshopHazardTest;
    FBeatWorld W(*this,TEXT("WorkshopOilIgnition"),2,7);if(!WorkshopHazardReady(W))return false;
    auto* Oil=Props(W)[0];auto* Bus=USoraGameEvents::Get(W.Hero());
    Hit(W,*Oil,1000,false);Hit(W,*Oil,1000,true);
    Shell(W,FVector(2600,-1200,55),FVector(-1500,0,0),100,1000,true);
    if(!Tick(W,30))return false;
    TestFalse(TEXT("Melee, round damage and an actual arrow leave the oil intact"),Oil->IsSpent());
    // A real shell hits the inside of the house wall. Its radius covers the
    // jars, but the wall must stop ignition on its opposite face.
    Shell(W,FVector(2200,-1200,100),FVector(1500,0,0),320,10);
    if(!Tick(W,30))return false;
    TestFalse(TEXT("The house wall stops a real shell blast from igniting oil through it"),Oil->IsSpent());
    FSoraDetonatedEvent E;E.Location=FVector(3000,-1200,55);E.Radius=100;E.Damage=100;
    Bus->OnDetonated.Broadcast(E);TestFalse(TEXT("Out-of-radius detonation cannot ignite oil"),Oil->IsSpent());
    if(!W.Press(EKeys::Escape))return false;
    E.Location=FVector(2400,-1200,55);Bus->OnDetonated.Broadcast(E);
    if(!Tick(W,30))return false;
    TestFalse(TEXT("An event while paused cannot ignite the stack"),Oil->IsSpent());W.Mode()->ResumePlay();
    if(!Ignite(W,*Oil))return false;
    const int Left=Oil->FireLeftMs();Bus->OnDetonated.Broadcast(E);
    TestEqual(TEXT("Repeated blasts cannot extend a burning patch"),Oil->FireLeftMs(),Left);
    TestFalse(TEXT("Ignited oil no longer supplies hard collision"),Oil->GetActorEnableCollision()&&
        Cast<UPrimitiveComponent>(Oil->GetRootComponent())->IsCollisionEnabled());
    if(!Tick(W,400))return false;
    TestEqual(TEXT("Six active seconds extinguish the patch"),Oil->FireLeftMs(),0);
    Bus->OnDetonated.Broadcast(E);TestEqual(TEXT("The consumed jars cannot relight"),Oil->FireLeftMs(),0);
    AddInfo(TEXT("Seeded b08 and launched real projectiles; synthetic out-of-range/pause events isolate guards. This is not ordinary combat or visual acceptance."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopOilDamageTest,"SoraArena.Campaign.LanternWorkshop.OilDamageRetry",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopOilDamageTest::RunTest(const FString&)
{
    using namespace SoraWorkshopHazardTest;
    FBeatWorld W(*this,TEXT("WorkshopOilDamage"),2,7);if(!WorkshopHazardReady(W))return false;
    Place(*W.Hero(),FVector(1900,-1660,0));if(!Tick(W,10)||!W.Hold(EKeys::E,125))return false;
    FreezeWorkshopHazard(W);TArray<ASoraEnemy*> Enemies;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)if(It->IsAlive())Enemies.Add(*It);
    if(!TestEqual(TEXT("Seal releases three registered opponents"),Enemies.Num(),3))return false;
    auto Found=Props(W);TArray<TWeakObjectPtr<ASoraWorkshopProp>> Old;for(auto* P:Found)Old.Add(P);
    auto* Oil=Found[0];auto* Bus=USoraGameEvents::Get(W.Hero());
    if(!Ignite(W,*Oil))return false;
    const int Left=Oil->FireLeftMs(),Expected=Left*R::DamagePerSecond/1000;
    Place(*W.Hero(),FVector(2440,-1200,0));
    Place(*Enemies[0],FVector(2400,-1300,0));Enemies[0]->Health=10;
    Place(*Enemies[1],FVector(2460,-1100,0));Enemies[1]->Health=500;
    // Deliberate same-height placement behind the real wall isolates the
    // obstruction check independently of the interior's raised floor.
    Place(*Enemies[2],FVector(2260,-1200,0));Enemies[2]->Health=500;
    const auto Before=W.Campaign()->TaskProgress();
    int Deaths=0;float HeroDamage=0,EnemyDamage=0;
    const auto Hurt=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
    {if(E.Causer==Oil){if(E.Victim==W.Hero())HeroDamage+=E.Amount;if(E.Victim==Enemies[1])EnemyDamage+=E.Amount;}});
    const auto Death=Bus->OnDied.AddLambda([&](const FSoraDiedEvent& E){if(E.Victim==Enemies[0]&&E.Killer==Oil)++Deaths;});
    ON_SCOPE_EXIT{Bus->OnDamaged.Remove(Hurt);Bus->OnDied.Remove(Death);};
    if(!Tick(W,60)||!W.Press(EKeys::Escape))return false;
    const int PausedLeft=Oil->FireLeftMs();const float PausedDamage=HeroDamage;
    if(!Tick(W,120))return false;
    TestEqual(TEXT("Pause preserves the remaining active fire clock"),Oil->FireLeftMs(),PausedLeft);
    TestEqual(TEXT("Pause applies no fire damage"),HeroDamage,PausedDamage);W.Mode()->ResumePlay();
    if(!Tick(W,400))return false;
    TestEqual(TEXT("Exposed hero receives the remaining authored 12 DPS"),HeroDamage,float(Expected));
    TestEqual(TEXT("Exposed enemy receives the same rate without rear/stagger bonuses"),EnemyDamage,float(Expected));
    TestEqual(TEXT("Real wall blocks same-height fire exposure"),Enemies[2]->Health,500.f);
    TestEqual(TEXT("Oil records exactly one ordinary opponent death"),Deaths,1);
    TestEqual(TEXT("Normal damage credits the registered wave"),
        SoraBeatRules::Defeated(W.Campaign()->TaskProgress(),W.BeatData().Task),SoraBeatRules::Defeated(Before,W.BeatData().Task)+1);
    for(const auto& P:W.Fieldcraft()->WorkshopCraftspeople())TestEqual(TEXT("Sheltered craftspeople remain unharmed"),P->Health,100.f);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health,nullptr,nullptr,UDamageType::StaticClass());
    if(!TestTrue(TEXT("Fire fixture enters real defeat"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter))return false;
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!Tick(W,1))return false;
    const auto Fresh=Props(W);if(!TestEqual(TEXT("Retry recreates exactly four props"),Fresh.Num(),4))return false;
    for(const auto& P:Old)TestFalse(TEXT("Retry destroys each old prop"),P.IsValid());
    TestTrue(TEXT("Retry restores sealed waves and unlit oil"),W.Fieldcraft()->NeedsWorkshopSeal()&&!Fresh[0]->IsSpent()&&Fresh[0]->FireLeftMs()==0);
    // Clear synchronously from the normal damage event while a fire tick has
    // queued victims: no old-stage hits may run after that callback.
    if(!Ignite(W,*Fresh[0]))return false;
    Place(*W.Hero(),FVector(2440,-1200,0));bool Cleared=false;
    const auto Clear=Bus->OnDamaged.AddLambda([&](const FSoraDamagedEvent& E)
    {if(E.Victim==W.Hero()&&E.Causer==Fresh[0]){Cleared=true;W.Fieldcraft()->Clear();}});
    const bool Ran=Tick(W,30);Bus->OnDamaged.Remove(Clear);
    TestTrue(TEXT("Damage callback can clear its own fire without stale-stage access"),Ran&&Cleared&&Props(W).IsEmpty());
    AddInfo(TEXT("Registered enemies frozen and positioned, hero health hardened; real fire damage, death credit, pause, mapped retry and synchronous cleanup. Ordinary encounter balance remains untested."));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWorkshopCoverTest,"SoraArena.Campaign.LanternWorkshop.DestructibleCover",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraWorkshopCoverTest::RunTest(const FString&)
{
    using namespace SoraWorkshopHazardTest;
    FBeatWorld W(*this,TEXT("WorkshopCover"),2,7);if(!WorkshopHazardReady(W))return false;
    auto Found=Props(W);auto* Rack=Found[1];
    Place(*W.Hero(),FVector(2770,-1100,0));W.Look(FRotator(0,90,0));
    if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,60)||!W.World->InjectKey(EKeys::W,IE_Released))return false;
    TestTrue(TEXT("Intact rack blocks real mapped walking"),W.Hero()->GetActorLocation().Y<=-1008);
    Hit(W,*Rack,10,false);Hit(W,*Rack,10,true);
    TestEqual(TEXT("Normal melee and ranged hits reduce soft cover health"),Rack->CoverHealth(),20);
    if(!W.Press(EKeys::Escape))return false;Hit(W,*Rack,1000,true);
    TestEqual(TEXT("Paused hits cannot destroy cover"),Rack->CoverHealth(),20);W.Mode()->ResumePlay();
    Place(*W.Hero(),FVector(2600,-1800,0));
    Shell(W,FVector(2770,-1200,70),FVector(0,1500,0),100,100);
    if(!Tick(W,30))return false;
    TestTrue(TEXT("A real blast destroys the damaged bamboo rack"),Rack->IsSpent());
    Place(*W.Hero(),FVector(2770,-1100,0));W.Look(FRotator(0,90,0));
    if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!Tick(W,60)||!W.World->InjectKey(EKeys::W,IE_Released))return false;
    TestTrue(TEXT("Broken rack releases collision up to the hard building wall"),W.Hero()->GetActorLocation().Y>-975);
    Hit(W,*Found[2],1000,false);TestTrue(TEXT("Drying board is also destructible"),Found[2]->IsSpent());
    FHitResult Well;FCollisionQueryParams Query;Query.AddIgnoredActor(W.Hero());
    const auto Hard=[&]{return W.World->GetTestWorld()->LineTraceSingleByChannel(Well,FVector(2600,-1550,40),FVector(2600,-1250,40),ECC_Visibility,Query);};
    if(!TestTrue(TEXT("Well curb remains real hard cover"),Hard()))return false;
    const FVector At=Well.ImpactPoint;
    SoraDamage::Strike(Well.GetActor(),1000,FSoraHit::Melee(At,0),FVector::ForwardVector,Well,W.Hero()->GetController(),W.Hero());
    TestTrue(TEXT("Attacking hard cover does not remove it"),Hard()&&Well.ImpactPoint.Equals(At,.01));
    TestFalse(TEXT("Distant rack destruction does not ignite the oil"),Found[0]->IsSpent());
    AddInfo(TEXT("Seeded defense with mapped collision movement, typed melee/round damage and actual shell impact. Provisional cover geometry and art remain WIP."));
    return !HasAnyErrors();
}
#endif
