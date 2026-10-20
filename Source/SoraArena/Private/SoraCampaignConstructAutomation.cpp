#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraBoss.h"
#include "SoraConstructRules.h"
#include "SoraEquipmentComponent.h"
#include "SoraSettings.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignConstructTest,"SoraArena.Campaign.CollateralConstruct",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignConstructTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("CollateralConstruct"),7,13);
    if(!W.Start(0,INDEX_NONE,1)) return false;
    W.Harden();
    W.Mode()->Settings()->SetCampaignDifficulty(SoraAccessibility::EDifficulty::Normal);
    ASoraBoss* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    if(!TestNotNull(TEXT("P2 summit boss exists"),Boss)) return false;
    Boss->Hold(120000);
    for(int32 Frame=0;Frame<180&&Boss->LiveAdds()<2;++Frame) if(!W.Tick(1)) return false;
    if(!TestEqual(TEXT("The existing summon contract produces two adds"),Boss->LiveAdds(),2)) return false;
    // Isolate each add, without changing its attack clock or damage paths.
    // Boss phase/seizure behavior is covered by the summit fixtures.
    Boss->SetActorTickEnabled(false);
    if(auto* Brain=Boss->GetController()) Brain->SetActorTickEnabled(false);
    TArray<ASoraEnemy*> Constructs;
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        if(It->Summoner()==Boss)
        {
            Constructs.Add(*It); It->Seize(true); It->Seize(false);
            It->GetCharacterMovement()->StopMovementImmediately();
            It->GetCharacterMovement()->SetComponentTickEnabled(false);
            if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
        }
    if(!TestEqual(TEXT("Both live adds are discoverable"),Constructs.Num(),2)) return false;
    ASoraEnemy* Seal=Constructs[0]; ASoraEnemy* Heavy=Constructs[1];
    TestTrue(TEXT("Only the summit collateral variant receives the new core"),Seal->IsCollateralConstruct()&&Heavy->IsCollateralConstruct());
    TestEqual(TEXT("The construct has one authored 25-damage slam"),Seal->AttackDamage(0),25);
    TestEqual(TEXT("It has no inherited shuttle thrust"),Seal->AttackDamage(1),0);
    TestEqual(TEXT("The core hold lasts one second"),Seal->SealCutHoldMs(),1000);
    const FVector Floor(W.BeatData().Space.Summit.Center+FVector2D(1000,0),16000);
    const auto Place=[&](ASoraEnemy& Enemy)
    {
        Enemy.SetActorLocation(Floor+FVector(0,0,Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),false,nullptr,ETeleportType::TeleportPhysics);
        Enemy.SetActorRotation(FRotator::ZeroRotator);
        W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
        W.Hero()->GetCharacterMovement()->StopMovementImmediately();
        W.Hero()->SetActorLocation(Floor+FVector(165,0,90),false,nullptr,ETeleportType::TeleportPhysics);
        W.Look((Enemy.ConstructCorePoint()-W.Hero()->GetCamera()->GetComponentLocation()).Rotation());
    };
    // Keep the second add clear of the selected construct and all its traces.
    Heavy->SetActorLocation(Floor+FVector(-500,450,Heavy->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2));
    Place(*Seal);
    W.Hero()->SetActorLocation(Floor+FVector(245,0,90));
    W.Look((Seal->ConstructCorePoint()-W.Hero()->GetCamera()->GetComponentLocation()).Rotation());
    if(!W.Tick(3)) return false;
    const auto Open=[&](ASoraEnemy& Enemy)
    {
        if(!TestTrue(TEXT("A live construct can commit its slam"),Enemy.TryAttack(*W.Hero(),FVector::Dist2D(Enemy.GetActorLocation(),W.Hero()->GetActorLocation())))) return false;
        for(int32 Frame=0;Frame<80&&!Enemy.IsConstructCoreOpen();++Frame) if(!W.Tick(1)) return false;
        if(!Enemy.IsConstructCoreOpen())
            AddError(FString::Printf(TEXT("Slam never exposed its core: enemy=%s hero=%s attack=%s input=%d"),
                *Enemy.GetActorLocation().ToString(),*W.Hero()->GetActorLocation().ToString(),
                Enemy.CurrentAttack()?*Enemy.CurrentAttack()->Id.ToString():TEXT("none"),int32(W.Mode()->InputState())));
        return Enemy.IsConstructCoreOpen();
    };
    const float Before=W.Hero()->Health;
    if(!TestTrue(TEXT("The initial slam commits near the authored radius"),Seal->TryAttack(*W.Hero(),245))||!W.Tick(51)) return false;
    TestTrue(TEXT("At 850 ms the amber windup still protects its core"),Seal->IsWindingUp()&&!Seal->CanCutSeal());
    TestEqual(TEXT("No damage arrives before the authored windup"),W.Hero()->Health,Before);
    for(int32 Frame=0;Frame<12&&!Seal->IsConstructCoreOpen();++Frame) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("The released slam exposes the recovery core"),Seal->IsConstructCoreOpen())) return false;
    TestEqual(TEXT("The actual on-floor slam deals 25 damage at 245 cm"),Before-W.Hero()->Health,25.f);
    Place(*Seal);
    TestTrue(TEXT("The physical core is reachable from its front"),Seal->CanReachConstructCore(*W.Hero()));
    const FVector At=W.Hero()->GetActorLocation();
    W.Hero()->SetActorLocation(At-FVector(0,0,400));
    TestFalse(TEXT("Matching XY on a different floor cannot cut the core"),Seal->CanReachConstructCore(*W.Hero()));
    W.Hero()->SetActorLocation(At);
    W.Look(FRotator::ZeroRotator);
    TestFalse(TEXT("Facing away cannot cut the core"),Seal->CanReachConstructCore(*W.Hero()));
    W.Look((Seal->ConstructCorePoint()-W.Hero()->GetCamera()->GetComponentLocation()).Rotation());
    auto* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Wall); Wall->SetRootComponent(Box); Box->SetBoxExtent(FVector(5,100,120));
    Box->SetCollisionProfileName(TEXT("BlockAll")); Box->SetCanEverAffectNavigation(false);
    Box->RegisterComponent(); Wall->AddInstanceComponent(Box);
    Wall->SetActorLocation((W.Hero()->GetCamera()->GetComponentLocation()+Seal->ConstructCorePoint())*.5f);
    TestFalse(TEXT("A real blocker prevents core contact"),Seal->CanReachConstructCore(*W.Hero()));
    Wall->Destroy();
    // Release/repress between ticks must discard partial work. The second
    // hold begins too late to finish before this recovery window closes.
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(20)) return false;
    if(!TestTrue(TEXT("Mapped E input begins the exposed core cut"),W.Campaign()->SealBeingCut()==Seal)) return false;
    if(!W.World->InjectKey(EKeys::E,IE_Released)||!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(40)) return false;
    TestTrue(TEXT("Release discards earlier time instead of banking a completed seal cut"),Seal->IsAlive()&&W.Campaign()->SealCutProgress()<.8f);
    if(!W.Tick(30)||!W.World->InjectKey(EKeys::E,IE_Released)) return false;
    TestTrue(TEXT("Recovery expiry cancels a late cut"),Seal->IsAlive()&&!Seal->CanCutSeal()&&!W.Campaign()->SealBeingCut());
    if(!Open(*Seal)) return false;
    if(!W.World->InjectKey(EKeys::E,IE_Pressed)||!W.Tick(55)) return false;
    TestTrue(TEXT("A fresh core cut requires the full second"),Seal->IsAlive()&&W.Campaign()->SealBeingCut()==Seal);
    if(!W.Tick(10)||!W.World->InjectKey(EKeys::E,IE_Released)) return false;
    if(!TestTrue(TEXT("The held seal releases intact goods"),!Seal->IsAlive()&&Seal->HasReleasedGoods())) return false;
    TestEqual(TEXT("The boss removes exactly one live add"),Boss->LiveAdds(),1);
    TestTrue(TEXT("One remaining construct keeps the seizure shield up"),Boss->IsShieldUp());
    TArray<UStaticMeshComponent*> Parts; Seal->GetComponents(Parts);
    TMap<UStaticMeshComponent*,FVector> From;
    for(auto* Part:Parts) if(Part->GetName().Contains(TEXT("Proxy"))&&!Part->GetName().Contains(TEXT("Core"))) From.Add(Part,Part->GetComponentLocation());
    TestEqual(TEXT("All five functional goods proxies remain"),From.Num(),5);
    if(!W.Tick(105)) return false;
    bool Settled=true,Travelled=false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ConstructReleaseFixture),false,Seal);
    for(TActorIterator<ASoraCharacterBase> It(W.World->GetTestWorld());It;++It) Query.AddIgnoredActor(*It);
    for(const auto& Entry:From)
    {
        FHitResult Ground; const FVector P=Entry.Key->GetComponentLocation();
        const bool Hit=W.World->GetTestWorld()->LineTraceSingleByChannel(Ground,P+FVector(0,0,10),P-FVector(0,0,250),ECC_Visibility,Query);
        Settled&=Hit&&FMath::Abs(P.Z-Entry.Key->Bounds.BoxExtent.Z-Ground.ImpactPoint.Z-2)<3;
        Travelled|=FVector::Dist(P,Entry.Value)>20;
    }
    TestTrue(TEXT("Released goods settle gently onto actual solid floor"),Settled&&Travelled&&IsValid(Seal)&&Seal->GetLifeSpan()==0);
    TestTrue(TEXT("The released assembly never rolls onto its side"),FMath::Abs(Seal->GetActorRotation().Roll)<1);
    Place(*Heavy);
    if(!W.Tick(3)) return false;
    const float OutsideHealth=W.Hero()->Health;
    if(!TestTrue(TEXT("The escape fixture commits a slam"),Heavy->TryAttack(*W.Hero(),165))) return false;
    W.Hero()->SetActorLocation(Floor+FVector(260,0,90));
    for(int32 Frame=0;Frame<80&&!Heavy->IsConstructCoreOpen();++Frame) if(!W.Tick(1)) return false;
    TestTrue(TEXT("A missed slam still opens its recovery core"),Heavy->IsConstructCoreOpen());
    TestEqual(TEXT("Leaving the 250 cm radius prevents slam damage"),W.Hero()->Health,OutsideHealth);
    if(!W.Tick(90)) return false;
    Place(*Heavy);
    if(!W.Tick(2)) return false;
    auto* Kit=W.Hero()->GetEquipment();
    if(!TestTrue(TEXT("The chapter has unlocked the heavy forge hammer"),Kit->EquipCampaignWeapon(8))) return false;
    Kit->Sheathe(false);
    // Closed core, then two real committed heavy sweeps into the exposed
    // component. No direct damage call supplies the gameplay heavy contacts.
    if(!W.Press(EKeys::LeftMouseButton)||!W.Tick(55)) return false;
    TestEqual(TEXT("A closed core rejects a heavy swing"),Heavy->Health,260.f);
    if(!Open(*Heavy)||!W.Press(EKeys::LeftMouseButton)||!W.Tick(17)) return false;
    if(!TestEqual(TEXT("The first physical heavy contact removes half the core"),Heavy->Health,130.f)) return false;
    if(!W.Tick(35)||!W.Press(EKeys::LeftMouseButton)||!W.Tick(17)) return false;
    TestTrue(TEXT("Exactly two heavy contacts release the second assembly"),!Heavy->IsAlive()&&Heavy->HasReleasedGoods());
    TestEqual(TEXT("Both release routes preserve add accounting"),Boss->LiveAdds(),0);
    TestFalse(TEXT("The existing shield drops when the last construct releases"),Boss->IsShieldUp());
    TestFalse(TEXT("The released core cannot be credited twice"),Heavy->CutSeal(W.Hero()));
    // A normal loom still exposes its own authored attack and takes ordinary
    // body damage. It never receives the summit core or collateral release.
    ASoraEnemy* Loom=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("loom_automaton"),20,Floor+FVector(-400,-450,115),FRotator::ZeroRotator);
    if(!TestNotNull(TEXT("An ordinary loom spawns"),Loom)) return false;
    TestTrue(TEXT("Ordinary loom behavior is untouched"),!Loom->IsCollateralConstruct()&&Loom->AttackDamage(0)==45&&Loom->AttackDamage(1)==35&&Loom->Health==420);
    TestFalse(TEXT("Ordinary looms cannot expose collateral seals"),Loom->CanCutSeal());
    TestEqual(TEXT("The encounter stays in the same boss beat"),W.Campaign()->ActiveBeat(),13);
    TWeakObjectPtr<ASoraEnemy> Released=Seal;
    Boss->Destroy();
    if(!W.Tick(1)) return false;
    TestTrue(TEXT("Encounter removal cleans up its released goods"),!Released.IsValid()||Released->IsActorBeingDestroyed());
    return !HasAnyErrors();
}
#endif
