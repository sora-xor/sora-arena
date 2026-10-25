#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraArcheryAutomation.h"
#include "SoraBowRules.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraFrontEnd.h"
#include "SoraGameEvents.h"
#include "SoraSettings.h"
#include "SoraViewmodelComponent.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

namespace SoraBowAimAutomation
{
using SoraFieldcraftAutomation::FBeatWorld;
bool BeginDraw(FBeatWorld& W,const FKey& Key)
{
    return W.World->InjectKey(Key,IE_Pressed)&&
        W.Test.TestTrue(TEXT("Mapped Attack begins a real yumi draw"),W.Hero()->GetEquipment()->IsBowDrawing());
}
bool SwayingDraw(FBeatWorld& W,const FKey& Key)
{
    return BeginDraw(W,Key)&&W.Tick(342)&&W.Test.TestFalse(TEXT("A normal 5.7 s held draw has visible sway"),
        W.Hero()->GetEquipment()->BowAimOffset().IsNearlyZero(.001));
}
bool Cancelled(FBeatWorld& W)
{
    const auto* Kit=W.Hero()->GetEquipment();
    return W.Test.TestTrue(TEXT("Cancellation drops both the draw and its visible aim offset"),
        !Kit->IsBowDrawing()&&Kit->BowAimOffset().IsZero())&&
        W.Test.TestEqual(TEXT("Cancelled draws issue no arrow identity"),W.Campaign()->ArcheryProgress().Issued,0)&&
        W.Test.TestEqual(TEXT("Cancelled draws retain all twelve finite arrows"),
            W.Hero()->WeaponId==18?Kit->Ammo:Kit->AmmoByWeapon[18],12);
}
bool MenuAction(FBeatWorld& W,SoraUI::EAction Action)
{
    auto* Menu=W.Mode()->FrontEnd();
    for(int32 I=0;I<12;++I)
    {
        const auto& Rows=Menu->Rows();
        if(Rows.IsValidIndex(Menu->Focus())&&Rows[Menu->Focus()].Action==Action) return W.Press(EKeys::Enter);
        if(!W.Press(EKeys::Down)) return false;
    }
    return false;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBowAimSwayTest,"SoraArena.Campaign.BowAimSway",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBowAimSwayTest::RunTest(const FString& Parameters)
{
    using namespace SoraBowAimAutomation;
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(int32 Difficulty=0;Difficulty<3;++Difficulty)
    {
        FBeatWorld W(*this,TEXT("BowAimSway"),0,6);
        if(!W.Start()||!SoraArcheryAutomation::EnterLine(*W.World)) return false;
        W.Mode()->Settings()->SetCampaignDifficulty(static_cast<SoraAccessibility::EDifficulty>(Difficulty));
        auto* Hero=W.Hero(); auto* Kit=Hero->GetEquipment();
        // A rotated camera also checks that sway is camera-local, rather than
        // a fixed world-axis offset. The shot deliberately goes above the range.
        SoraArcheryAutomation::Look(*W.World,FRotator(75,37,0));
        const FQuat Camera=Hero->GetCamera()->GetComponentQuat();
        const FRotator Control=Hero->GetControlRotation();
        auto* Events=USoraGameEvents::Get(Hero);
        if(!TestNotNull(TEXT("The ordinary shot event bus exists"),Events)) return false;
        TArray<FSoraWeaponFiredEvent> Fired;
        const auto Handle=Events->OnWeaponFired.AddLambda([&](const FSoraWeaponFiredEvent& E) {
            if(E.Shooter==Hero&&E.WeaponId==18) Fired.Add(E);
        });
        ON_SCOPE_EXIT { Events->OnWeaponFired.Remove(Handle); };
        const double Started=W.World->GetTestWorld()->GetTimeSeconds();
        if(!BeginDraw(W,EKeys::LeftMouseButton)) return false;
        double FullAt=-1,SwayAt=-1;
        for(int32 Frame=0;Frame<342;++Frame)
        {
            if(!W.Tick(1)) return false;
            const double Age=W.World->GetTestWorld()->GetTimeSeconds()-Started;
            const FRotator Offset=Kit->BowAimOffset();
            const auto Expected=SoraBowRules::AimSway(Age);
            if(FullAt<0&&Kit->BowDrawProgress()>=1.f) FullAt=Age;
            if(SwayAt<0&&!Offset.IsNearlyZero(1e-8)) SwayAt=Age;
            if(Age<4.65-1e-5&&!TestTrue(TEXT("No aim movement during draw or four full-draw seconds"),Offset.IsZero())) return false;
            if(!TestTrue(TEXT("The observed ray follows the same provisional profile on all difficulties"),
                FMath::IsNearlyEqual(Offset.Pitch,Expected.Pitch,1e-5)&&FMath::IsNearlyEqual(Offset.Yaw,Expected.Yaw,1e-5))) return false;
            const FMinimalViewInfo View=SoraViewmodelPresentation::CameraView(*Hero->GetCamera());
            const FVector BowDirection=Hero->GetViewmodel()->GetForwardVector();
            const FVector ProjectedDirection=(View.TransformWorldToFirstPerson(View.Location+BowDirection*10000.f,true)-View.Location).GetSafeNormal();
            if(!TestTrue(TEXT("Fallback draw uses the drawn pose and native FP direction follows the current gameplay ray without lag"),
                Hero->GetViewmodel()->UsesFallbackBowPresentation()&&Hero->GetViewmodel()->PresentationPose()==TEXT("bow.drawn")&&
                ProjectedDirection.Equals(Kit->BowAimDirection(),1e-5))) return false;
        }
        UE_LOG(LogTemp,Display,TEXT("Bow actual hold difficulty=%d full_at=%.6f sway_at=%.6f offset=%s input=%d ammo=%d"),
            Difficulty,FullAt,SwayAt,*Kit->BowAimOffset().ToString(),int32(W.Mode()->InputState()),Kit->Ammo);
        TestTrue(TEXT("Actual mapped draw still completes after 650 ms"),FullAt>=.65-1e-5&&FullAt<=.65+1.f/60.f+1e-5);
        TestTrue(TEXT("Visible sway begins on the first normal frame after 4.65 s"),SwayAt>=4.65-1e-5&&SwayAt<=4.65+1.f/60.f+1e-5);
        TestTrue(TEXT("Sway does not mutate camera or player control rotation"),
            Hero->GetCamera()->GetComponentQuat().Equals(Camera,1e-6)&&Hero->GetControlRotation().Equals(Control,1e-6));
        const FVector VisibleRay=Kit->BowAimDirection();
        const FVector VisibleOrigin=Hero->GetCamera()->GetComponentLocation()+VisibleRay*65.f;
        TestTrue(TEXT("The visible aim ray actually moves off the centerline"),!VisibleRay.Equals(Camera.GetForwardVector(),1e-5));
        // No tick between observation and release: the release must sample the
        // ray the HUD projects, before its drawing flag is cleared.
        if(!W.World->InjectKey(EKeys::LeftMouseButton,IE_Released)||
            !TestEqual(TEXT("One real release emits one shot event"),Fired.Num(),1)) return false;
        TestTrue(TEXT("The shot event retains the exact visible aim and origin"),
            Fired[0].Direction.Equals(VisibleRay,1e-8)&&Fired[0].Origin.Equals(VisibleOrigin,1e-6));
        ASoraProjectile* Arrow=nullptr;
        for(TActorIterator<ASoraProjectile> It(W.World->GetTestWorld());It;++It)
            if(It->GetOwner()==Hero&&It->ArcheryShotId) Arrow=*It;
        if(!TestNotNull(TEXT("The release creates an actual lesson arrow"),Arrow)) return false;
        TestTrue(TEXT("Actual initial velocity and transform use the visible aim ray"),
            Arrow->Velocity.Equals(VisibleRay*6500.f,.001)&&Arrow->GetActorLocation().Equals(VisibleOrigin,1e-6)&&
            Arrow->GetActorForwardVector().Equals(VisibleRay,1e-6));
        TestEqual(TEXT("One held release spends just one finite arrow"),Kit->Ammo,11);
        TestTrue(TEXT("Ending the draw immediately recenters subsequent aim"),!Kit->IsBowDrawing()&&Kit->BowAimOffset().IsZero());
        if(!W.Tick(130)) return false;
        TestEqual(TEXT("The real flight expiry resolves the intended miss once"),W.Campaign()->ArcheryProgress().Resolved,1);
        TestEqual(TEXT("Visible sway does not award lesson progress"),W.Campaign()->ArcheryProgress().Hits,0);
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBowAimCancellationTest,"SoraArena.Campaign.BowAimCancellation",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBowAimCancellationTest::RunTest(const FString& Parameters)
{
    using namespace SoraBowAimAutomation;
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const auto Actions=GetDefault<UInputSettings>()->GetActionMappings();
    FString ControlSlot;
    ON_SCOPE_EXIT {
        TestTrue(TEXT("The fixture restores global input mappings"),Actions==GetDefault<UInputSettings>()->GetActionMappings());
        if(!ControlSlot.IsEmpty()) TestFalse(TEXT("The remapped control profile is removed on teardown"),UGameplayStatics::DoesSaveGameExist(ControlSlot,0));
    };
    FBeatWorld W(*this,TEXT("BowAimCancellation"),0,6);
    ControlSlot=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!W.Start()||!SoraArcheryAutomation::EnterLine(*W.World)||!SwayingDraw(W,EKeys::LeftMouseButton)) return false;
    if(!W.Press(EKeys::Escape)||!Cancelled(W)||!W.Hero()->RemapCombatAction(TEXT("Fire"),EKeys::G)) return false;
    if(!W.World->InjectKeyPastFrontEnd(EKeys::G,IE_Pressed)||!W.Tick(120)||!Cancelled(W)) return false;
    W.Mode()->ResumePlay();
    if(!W.Tick(1)||!W.World->InjectKey(EKeys::G,IE_Released)||!W.Tick(1)||!Cancelled(W)) return false;
    if(!BeginDraw(W,EKeys::G)||!W.Tick(120)) return false;
    TestTrue(TEXT("Remapped fresh draw cannot inherit the old sway phase"),W.Hero()->GetEquipment()->BowAimOffset().IsZero());
    if(!W.Press(EKeys::One)||!W.World->InjectKey(EKeys::G,IE_Released)||!Cancelled(W)||
        !W.Press(EKeys::Three)||!W.Tick(20)||!SwayingDraw(W,EKeys::G)) return false;
    // The real dialogue boundary flushes input and actions before playback.
    W.Hero()->ResetDialogueInput();
    if(!Cancelled(W)||!W.Tick(1)||!W.World->InjectKey(EKeys::G,IE_Released)||!SwayingDraw(W,EKeys::G)) return false;
    // Exercise the actual stagger response without introducing a hostile
    // actor into the authored no-combat range or fabricating an arrow event.
    W.Hero()->GetEquipment()->Stagger(.5f);
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!Cancelled(W)||!W.Tick(35)||!SwayingDraw(W,EKeys::G)) return false;
    if(!W.Press(EKeys::Escape)||!MenuAction(W,SoraUI::EAction::Restart)||
        !MenuAction(W,SoraUI::EAction::ConfirmYes)||!W.Tick(30)||!Cancelled(W)) return false;
    if(!SoraArcheryAutomation::EnterLine(*W.World)||!SwayingDraw(W,EKeys::G)) return false;
    W.Campaign()->SaveProgress();
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(this); W.World.Reset(); W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Tick(30)||!Cancelled(W)) return false;
    if(!SoraArcheryAutomation::EnterLine(*W.World)||!BeginDraw(W,EKeys::G)||!W.Tick(120)) return false;
    TestTrue(TEXT("Fresh-world load retains the mapping and starts a new steady draw"),
        W.Hero()->GetEquipment()->IsBowDrawing()&&W.Hero()->GetEquipment()->BowAimOffset().IsZero());
    if(!W.Press(EKeys::Escape)||!W.World->InjectKey(EKeys::G,IE_Released)||!Cancelled(W)) return false;
    return !HasAnyErrors();
}
#endif
