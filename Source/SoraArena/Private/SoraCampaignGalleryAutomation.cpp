#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraGalleryRules.h"
#include "SoraLiftAutomation.h"
#include "SoraEquipmentComponent.h"
#include "Components/BoxComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraGalleryPoisTest,"SoraArena.Campaign.GalleryPois",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraGalleryPoisTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const auto& Authored=FSoraCatalog::Get().Chapter(7).Beats[11];
    TestEqual(TEXT("All six authored gallery identities reach the catalog"),Authored.Pois.Num(),6);
    TestTrue(TEXT("The covered mon retains its authored interaction"),Authored.Pois.ContainsByPredicate(
        [](const FSoraExplorePoi& Poi) { return Poi.Id==TEXT("poi_covered_mon")&&
            Poi.Interaction==TEXT("tear the seizure label off the Nyaagyu 陣羽織"); }));
    const auto Actions=GetDefault<UInputSettings>()->GetActionMappings();
    FString Controls;
    ON_SCOPE_EXIT
    {
        TestTrue(TEXT("Gallery input fixture preserves global action mappings"),GetDefault<UInputSettings>()->GetActionMappings()==Actions);
        if(!Controls.IsEmpty()) TestFalse(TEXT("Gallery fixture deletes its rebound controls"),UGameplayStatics::DoesSaveGameExist(Controls,0));
    };
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("GalleryPois"),7,10);
    Controls=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!W.Start()||!W.Tick(30)) return false;
    W.Harden();
    auto* Arena=W.Mode()->Arena();
    const FName Toy=TEXT("poi_child_toy"),Mon=TEXT("poi_covered_mon");
    const FString ToyLine=TEXT("ch08.b12.nyaakoto.002");
    const auto ToyLines=[&]() { return W.Campaign()->QueuedSubtitles().FilterByPredicate(
        [&](const FSoraSubtitle& Line) { return Line.LineId==ToyLine; }).Num(); };
    FVector ToyAt,MonAt;
    if(!TestTrue(TEXT("Both lore objects stand in the physical gallery"),
        Arena->GalleryPoiFloor(Toy,ToyAt)&&Arena->GalleryPoiFloor(Mon,MonAt))) return false;
    TestEqual(TEXT("Toy is on the 142 metre gallery floor"),ToyAt.Z,14200.0);
    TestEqual(TEXT("Jinbaori shares the actual gallery floor"),MonAt.Z,ToyAt.Z);
    TestTrue(TEXT("The alien seizure label initially covers the mon"),Arena->GalleryLabelVisible()&&!Arena->GalleryMonVisible());
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("Input from the lower lift landing discovers nothing"),W.Campaign()->GalleryPoiMask(),0);
    if(!TestTrue(TEXT("Normal capstan input and walking enter the gallery"),
        SoraLiftAutomation::Ride(*W.World)&&SoraLiftAutomation::GalleryFloor(*W.World))) return false;
    const uint64 FindsBefore=W.Campaign()->CollectedMask();
    const auto ProgressBefore=W.Campaign()->Progress();
    auto* Kit=W.Hero()->GetEquipment();
    const int32 WeaponBefore=W.Hero()->WeaponId,AmmoBefore=Kit->Ammo;
    const auto InventoryBefore=Kit->AmmoByWeapon;
    if(!TestTrue(TEXT("Walking reaches the lit toy plinth"),SoraLiftAutomation::Walk(*W.World,ToyAt-FVector(190,0,0)))||
        !TestTrue(TEXT("A grounded player has direct reach to the toy"),Arena->CanReachGalleryPoi(Toy,*W.Hero()))) return false;
    TestEqual(TEXT("Arrival alone does not inspect the toy"),W.Campaign()->GalleryPoiMask(),0);
    const FVector Ground=W.Hero()->GetActorLocation();
    auto* Movement=W.Hero()->GetCharacterMovement();
    W.Hero()->SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr));
    Movement->StopMovementImmediately();
    W.Hero()->SetActorLocation(Ground-FVector(0,0,900),false,nullptr,ETeleportType::TeleportPhysics);
    Movement->SetMovementMode(MOVE_Walking);
    if(!TestFalse(TEXT("Matching XY on a lower floor cannot inspect the toy"),Arena->CanReachGalleryPoi(Toy,*W.Hero()))||
        !W.Press(EKeys::E)||!TestEqual(TEXT("Wrong-floor mapped input discovers nothing"),W.Campaign()->GalleryPoiMask(),0)) return false;
    W.Hero()->SetActorLocation(Ground,false,nullptr,ETeleportType::TeleportPhysics);
    Movement->StopMovementImmediately();
    for(int32 Frame=0;Frame<120&&(!Movement->IsMovingOnGround()||!W.Hero()->CanJump());++Frame)
        if(!W.Tick(1)) return false;
    W.Look((Ground-ToyAt).GetSafeNormal2D().Rotation());
    const float StartZ=W.Hero()->GetActorLocation().Z;
    if(!TestTrue(TEXT("The gallery jump starts grounded and eligible"),Movement->IsMovingOnGround()&&W.Hero()->CanJump())||
        !W.World->InjectKey(EKeys::SpaceBar,IE_Pressed)) return false;
    for(int32 Frame=0;Frame<12&&W.Hero()->GetActorLocation().Z<StartZ+5;++Frame) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("Mapped Jump establishes actual upward flight"),Movement->IsFalling()&&Movement->Velocity.Z>0&&
        W.Hero()->GetActorLocation().Z>StartZ+5)||!W.Press(EKeys::E)||
        !TestEqual(TEXT("Airborne input discovers nothing"),W.Campaign()->GalleryPoiMask(),0)) return false;
    if(!W.World->InjectKey(EKeys::SpaceBar,IE_Released)) return false;
    for(int32 Frame=0;Frame<180&&!Movement->IsMovingOnGround();++Frame) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("The hero naturally lands"),Movement->IsMovingOnGround())) return false;
    auto* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Wall);
    Wall->SetRootComponent(Box); Box->SetBoxExtent(FVector(10,110,130));
    Box->SetCollisionProfileName(TEXT("BlockAll")); Box->RegisterComponent(); Wall->AddInstanceComponent(Box);
    Wall->SetActorLocation(ToyAt+FVector(-100,0,125));
    if(!TestFalse(TEXT("A real wall blocks the toy's visibility trace"),Arena->CanReachGalleryPoi(Toy,*W.Hero()))||
        !W.Press(EKeys::E)||!TestEqual(TEXT("Input cannot inspect through the wall"),W.Campaign()->GalleryPoiMask(),0)) return false;
    Wall->Destroy();
    if(!W.Tick(3)||!TestTrue(TEXT("Removing the wall restores direct reach"),Arena->CanReachGalleryPoi(Toy,*W.Hero()))) return false;
    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("The ordinary menu rebinds Interact"),W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G))||
        !W.Press(EKeys::G)||!TestEqual(TEXT("Menu input does not inspect an object"),W.Campaign()->GalleryPoiMask(),0)) return false;
    W.Mode()->ResumePlay();
    if(!W.Tick(3)||!W.Press(EKeys::E)||!TestEqual(TEXT("The former key cannot inspect"),W.Campaign()->GalleryPoiMask(),0)||
        !W.Press(EKeys::G)) return false;
    TestTrue(TEXT("Mapped interaction records the toy only"),W.Campaign()->HasGalleryPoi(Toy)&&!W.Campaign()->HasGalleryPoi(Mon));
    TestEqual(TEXT("The exact authored toy line is queued once"),ToyLines(),1);
    if(!W.Press(EKeys::G)) return false;
    TestEqual(TEXT("Repeated inspection never duplicates the authored line"),ToyLines(),1);
    TestEqual(TEXT("Lore discovery awards no collectibles"),W.Campaign()->CollectedMask(),FindsBefore);
    TestEqual(TEXT("Lore discovery does not complete the optional cache"),W.Campaign()->Progress().CompletedMask,ProgressBefore.CompletedMask);
    TestTrue(TEXT("Lore discovery changes no weapon or ammunition state"),W.Hero()->WeaponId==WeaponBefore&&Kit->Ammo==AmmoBefore&&
        Kit->AmmoByWeapon==InventoryBefore&&W.Campaign()->Progress().WeaponsMask==ProgressBefore.WeaponsMask);
    auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("The toy flag is immediately saved"),Saved)) return false;
    TestTrue(TEXT("Only lore is added to the existing lift-start save"),Saved->GalleryPoiMask==1&&Saved->CheckpointBeat==10&&
        (Saved->CheckpointBeatsMask&SoraBeatRules::BeatBit(11))==0&&static_cast<uint64>(Saved->Collectibles)==FindsBefore);
    auto* Lift=Arena->CampaignLift();
    if(!SoraLiftAutomation::Walk(*W.World,Lift->GalleryCache()+FVector(-150,0,0))||!W.Press(EKeys::G)) return false;
    const uint64 Finds=W.Campaign()->CollectedMask();
    const uint64 Expected=FindsBefore|(7ull<<(7*6+2));
    TestEqual(TEXT("The unchanged cache awards exactly the three authored collectibles"),Finds,Expected);
    TestTrue(TEXT("The cache retains its optional completion"),(W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(11))!=0);
    const auto AfterCache=W.Campaign()->Progress();
    if(!TestTrue(TEXT("Normal walking reaches the jinbaori after searching the cache"),
        SoraLiftAutomation::Walk(*W.World,MonAt-FVector(190,0,0)))||
        !TestTrue(TEXT("The seizure label is physically reachable"),Arena->CanReachGalleryPoi(Mon,*W.Hero()))||!W.Press(EKeys::G)) return false;
    TestTrue(TEXT("Mapped interaction tears the cover and reveals the mon"),W.Campaign()->HasGalleryPoi(Mon)&&
        !Arena->GalleryLabelVisible()&&Arena->GalleryMonVisible());
    if(!W.Press(EKeys::G)) return false;
    TestEqual(TEXT("Repeated tearing is idempotent"),W.Campaign()->GalleryPoiMask(),SoraGalleryRules::All);
    TestEqual(TEXT("Tearing leaves collectibles unchanged"),W.Campaign()->CollectedMask(),Finds);
    TestEqual(TEXT("Tearing leaves optional completion unchanged"),W.Campaign()->Progress().CompletedMask,AfterCache.CompletedMask);
    Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("Both discoveries reach disk before the summit"),Saved)) return false;
    TestTrue(TEXT("Discovery saving never moves the lift checkpoint"),Saved->GalleryPoiMask==3&&Saved->CheckpointBeat==10);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Gallery death enters ordinary retry"),W.Mode()->bDefeated)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    TestTrue(TEXT("Retry keeps lore while restoring the lift start"),W.Campaign()->GalleryPoiMask()==3&&W.Campaign()->ActiveBeat()==10&&
        !W.Campaign()->InLiftGallery()&&W.Mode()->Arena()->CampaignLift()->Height()==2700.f);
    TestEqual(TEXT("Retry retains all three existing finds"),W.Campaign()->CollectedMask(),Finds);
    TestTrue(TEXT("The rebuilt jinbaori retains the torn state"),!W.Mode()->Arena()->GalleryLabelVisible()&&W.Mode()->Arena()->GalleryMonVisible());
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(this); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    W.Harden(); Arena=W.Mode()->Arena();
    TestTrue(TEXT("A fresh world loads lore without inventing gallery progress"),W.Campaign()->GalleryPoiMask()==3&&
        W.Campaign()->ActiveBeat()==10&&!W.Campaign()->InLiftGallery()&&
        (W.Campaign()->Progress().CompletedMask&SoraBeatRules::BeatBit(11))==0);
    if(!SoraLiftAutomation::Ride(*W.World,EKeys::G)||!SoraLiftAutomation::GalleryFloor(*W.World)) return false;
    if(!SoraLiftAutomation::Walk(*W.World,ToyAt-FVector(190,0,0))||!W.Press(EKeys::G)) return false;
    TestEqual(TEXT("A saved toy does not replay its line in a fresh world"),ToyLines(),0);
    if(!SoraLiftAutomation::Walk(*W.World,MonAt-FVector(190,0,0))||!W.Press(EKeys::G)) return false;
    TestTrue(TEXT("A saved label stays torn on repeat input"),W.Campaign()->GalleryPoiMask()==3&&
        !Arena->GalleryLabelVisible()&&Arena->GalleryMonVisible());
    if(!SoraLiftAutomation::Walk(*W.World,Arena->CampaignLift()->GetActorLocation()+FVector(500,0,14200))) return false;
    if(!TestTrue(TEXT("The normal north stair remains usable without reopening the cache"),
        SoraLiftAutomation::Gallery(*W.World,false))) return false;
    TestEqual(TEXT("The stair alone starts the summit"),W.Campaign()->ActiveBeat(),12);
    Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("The summit checkpoint is saved"),Saved)) return false;
    TestTrue(TEXT("The summit retains finds and lore without forcing optional completion"),Saved->CheckpointBeat==12&&
        Saved->GalleryPoiMask==3&&static_cast<uint64>(Saved->Collectibles)==Finds&&
        (Saved->CheckpointBeatsMask&SoraBeatRules::BeatBit(11))==0);
    if(!TestTrue(TEXT("Chapter replay remains available"),W.Campaign()->SelectChapter(0))) return false;
    TestEqual(TEXT("Chapter replay preserves gallery lore"),W.Campaign()->GalleryPoiMask(),3);
    W.Campaign()->StartOver();
    TestEqual(TEXT("A genuinely new campaign clears gallery lore"),W.Campaign()->GalleryPoiMask(),0);
    return !HasAnyErrors();
}
#endif
