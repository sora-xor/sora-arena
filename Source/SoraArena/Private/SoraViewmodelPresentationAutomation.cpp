#include "SoraViewmodelPresentation.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraArcheryAutomation.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraViewmodelComponent.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraViewmodelContractTest,"SoraArena.Presentation.ViewmodelContract",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraViewmodelContractTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraViewmodelPresentation;
    FString Text,Error; FContract Contract;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())||
       !TestTrue(TEXT("The staged contract is readable"),FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Data/viewmodels.json"))))||
       !TestTrue(TEXT("The runtime parses the complete authored table"),Parse(Text,Contract,Error))) return false;
    TestEqual(TEXT("All catalog weapons plus bokken"),Contract.Weapons.Num(),22);
    TestEqual(TEXT("All eight presentation states"),Contract.Poses.Num(),8);
    for(int32 Id=0;Id<=BokkenId;++Id)
    {
        const FWeapon* Weapon=Contract.Weapons.Find(Id);
        if(!TestNotNull(TEXT("Every weapon has one pose record"),Weapon)) return false;
        const FPose* Pose=Contract.Poses.Find(Weapon->Pose);
        if(!TestNotNull(TEXT("Every weapon resolves a finite pose"),Pose)) return false;
        TestTrue(TEXT("Every pose is finite and starts ahead of the eye"),!Pose->Location.ContainsNaN()&&Pose->Location.X>0&&!Pose->Rotation.ContainsNaN());
    }
    auto Reject=[&](const TCHAR* Label,TFunctionRef<void(TSharedPtr<FJsonObject>)> Mutate) {
        TSharedPtr<FJsonObject> Root; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root);
        Mutate(Root); FString Changed; FJsonSerializer::Serialize(Root.ToSharedRef(),TJsonWriterFactory<>::Create(&Changed));
        FContract Invalid; FString Why;
        TestFalse(Label,Parse(Changed,Invalid,Why));
        TestTrue(TEXT("Invalid contract never leaks a partial weapon table"),Invalid.Weapons.IsEmpty()&&!Why.IsEmpty());
    };
    Reject(TEXT("Unknown schema rejected"),[](auto Root){ Root->SetNumberField(TEXT("schema_version"),99); });
    Reject(TEXT("Missing weapon rejected"),[](auto Root){ auto Rows=Root->GetArrayField(TEXT("weapons")); Rows.Pop(); Root->SetArrayField(TEXT("weapons"),Rows); });
    Reject(TEXT("Duplicate weapon rejected"),[](auto Root){ auto Rows=Root->GetArrayField(TEXT("weapons")); Rows[3]=Rows[4]; Root->SetArrayField(TEXT("weapons"),Rows); });
    Reject(TEXT("Non-object weapon rejected"),[](auto Root){ auto Rows=Root->GetArrayField(TEXT("weapons")); Rows[3]=MakeShared<FJsonValueNumber>(2); Root->SetArrayField(TEXT("weapons"),Rows); });
    Reject(TEXT("Wrong generated mesh rejected"),[](auto Root){ Root->GetArrayField(TEXT("weapons"))[3]->AsObject()->SetStringField(TEXT("first_person_mesh"),TEXT("/Game/Generated/Meshes/SM_Weapon_99")); });
    Reject(TEXT("Approximate sockets cannot admit a different mesh"),[](auto Root){ Root->GetArrayField(TEXT("weapons"))[3]->AsObject()->SetObjectField(TEXT("sockets_m"),MakeShared<FJsonObject>()); });
    Reject(TEXT("Missing drawn state rejected"),[](auto Root){ Root->GetObjectField(TEXT("poses"))->RemoveField(TEXT("bow.drawn")); });
    Reject(TEXT("Legacy draw tilt cannot stack on the drawn pose"),[](auto Root){ Root->GetObjectField(TEXT("motion"))->GetObjectField(TEXT("pitch_deg"))->SetNumberField(TEXT("bow_drawing"),-15); });
    Reject(TEXT("Unsafe bow reload rejected"),[](auto Root){ Root->GetObjectField(TEXT("poses"))->GetObjectField(TEXT("bow"))->GetObjectField(TEXT("motion_overrides"))->GetObjectField(TEXT("reload"))->SetNumberField(TEXT("pitch"),-30); });
    Reject(TEXT("Draw cannot silently change grip pivot"),[](auto Root){ Root->GetObjectField(TEXT("poses"))->GetObjectField(TEXT("bow.drawn"))->SetStringField(TEXT("anchor"),TEXT("Grip_R")); });
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraViewmodelProjectionTest,"SoraArena.Presentation.ViewmodelProjection",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraViewmodelProjectionTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraViewmodelPresentation;
    const FQuat Rest=FRotator(24,4,-8).Quaternion(),Action=FRotator(-10,0,-15).Quaternion(),Aim=FRotator(.18,.28,0).Quaternion();
    const FVector Probe(34,-7,12);
    TestTrue(TEXT("Composition applies rest, eye action, then presentation aim"),Compose(Aim,Action,Rest).RotateVector(Probe).Equals(
        Aim.RotateVector(Action.RotateVector(Rest.RotateVector(Probe))),1e-6));
    TestFalse(TEXT("The swapped action/rest product is observably different"),Compose(Aim,Action,Rest).Equals(Aim*Rest*Action,1e-5));
    const float A=BlendAlpha(1.f/60.f,12.f),B=BlendAlpha(1.f/30.f,12.f);
    TestTrue(TEXT("State interpolation is stable across frame partitions"),FMath::IsNearlyEqual(1.f-(1.f-A)*(1.f-A),B,1e-6f));
    TestEqual(TEXT("No elapsed time cannot jump state"),BlendAlpha(0,12),0.f);
    auto* Camera=NewObject<UCameraComponent>();
    FTransform DefaultAdditive; float DefaultAdditiveFOV=-1;
    Camera->GetAdditiveOffset(DefaultAdditive,DefaultAdditiveFOV);
    const FMinimalViewInfo DefaultView=CameraView(*Camera);
    TestTrue(TEXT("Disabled default additive fields are identity/zero, and the camera is perspective"),
        DefaultAdditive.Equals(FTransform::Identity)&&DefaultAdditiveFOV==0&&
        DefaultView.ProjectionMode==ECameraProjectionMode::Perspective&&
        DefaultView.Location.Equals(Camera->GetComponentLocation())&&DefaultView.Rotation.Equals(Camera->GetComponentRotation())&&
        DefaultView.FOV==Camera->FieldOfView);
    Camera->SetWorldLocationAndRotation(FVector(71,-52,43),FRotator(31,73,0));
    Camera->FieldOfView=87.f; Camera->FirstPersonFieldOfView=62.f; Camera->FirstPersonScale=.53f;
    Camera->bEnableFirstPersonFieldOfView=true; Camera->bEnableFirstPersonScale=true;
    Camera->AddAdditiveOffset(FTransform(FRotator(2,3,0),FVector(4,5,6)),7.f);
    Camera->SetOverscan(.1f); Camera->SetAsymmetricOverscan(FVector4f(.01f,.02f,.03f,.04f));
    const FTransform CameraBefore=Camera->GetComponentTransform();
    const FMinimalViewInfo Snapshot=CameraView(*Camera); FMinimalViewInfo Native;
    Camera->GetCameraView(0,Native); // No pawn/controller/XR on this fixture.
    TestTrue(TEXT("Read-only projection matches UE's actual camera fields including additive FOV/overscan"),
        Camera->GetComponentTransform().Equals(CameraBefore)&&Snapshot.Location.Equals(Native.Location,1e-8)&&
        Snapshot.Rotation.Equals(Native.Rotation,1e-8)&&Snapshot.FOV==Native.FOV&&
        Snapshot.FirstPersonFOV==Native.FirstPersonFOV&&Snapshot.FirstPersonScale==Native.FirstPersonScale&&
        Snapshot.CalculateFirstPersonFOVCorrectionFactor()==Native.CalculateFirstPersonFOVCorrectionFactor());
    // The unadmitted path must still be the original local offset * action,
    // even when the presentation camera has an independently rotated offset.
    auto* Legacy=NewObject<USoraViewmodelComponent>(); Legacy->SetupAttachment(Camera);
    for(const FRotator Offset:{FRotator::ZeroRotator,FRotator(.18,.28,0),FRotator(-.18,-.28,0)})
        for(int32 ActionIndex=0;ActionIndex<3;++ActionIndex)
    {
        const FVector LiveRay=Camera->GetComponentQuat().RotateVector(Offset.Vector());
        Legacy->Sway(1.f/60.f,.137f,.5f,ActionIndex==1,ActionIndex==2,true,true,Snapshot,LiveRay);
        const float Pitch=ActionIndex==1?-30.f:ActionIndex==2?25.f:-15.f;
        TestTrue(TEXT("Additive camera rotation cannot counter-rotate an unadmitted weapon"),
            Legacy->GetRelativeRotation().Quaternion().Equals(Offset.Quaternion()*FRotator(Pitch,0,-15).Quaternion(),1e-6));
        TestFalse(TEXT("The prior view-space inverse would fail this rotated-offset regression"),
            Snapshot.Rotation.UnrotateVector(LiveRay).Rotation().Quaternion().Equals(Offset.Quaternion(),1e-4));
    }
    Camera->ClearAdditiveOffset(); Camera->GetAdditiveOffset(DefaultAdditive,DefaultAdditiveFOV);
    TestTrue(TEXT("Clearing an additive offset restores identity/zero fields"),DefaultAdditive.Equals(FTransform::Identity)&&DefaultAdditiveFOV==0);
    for(const float WorldFOV:{75.f,94.f,110.f}) for(const float FirstFOV:{55.f,70.f,90.f})
    {
        FMinimalViewInfo View; View.Location=FVector(517,-991,87); View.Rotation=FRotator(31,73,0);
        View.FOV=WorldFOV; View.FirstPersonFOV=FirstFOV; View.FirstPersonScale=.6f; View.bUseFirstPersonParameters=true;
        // Actual gameplay extrema plus a separately labelled large-angle stress case.
        for(const FRotator Offset:{FRotator(.18,.28,0),FRotator(-.18,-.28,0),FRotator(4,6,0)})
        {
            const FVector LiveRay=(View.Rotation.Quaternion()*Offset.Quaternion()).GetForwardVector();
            const FVector Before=LiveRay,Direction=CorrectedWorldDirection(View,LiveRay);
            const FVector Projected=(View.TransformWorldToFirstPerson(View.Location+Direction*10000.f,true)-View.Location).GetSafeNormal();
            TestTrue(TEXT("Actual native FP projection restores the unchanged live ray at each FOV"),Projected.Equals(LiveRay,1e-6)&&LiveRay==Before);
        }
        View.bUseFirstPersonParameters=false;
        const FVector Ray=FRotator(17,42,0).Vector();
        TestTrue(TEXT("Ordinary camera does not receive FP correction"),CorrectedWorldDirection(View,Ray).Equals(Ray,1e-8));
        View.bUseFirstPersonParameters=true; View.ProjectionMode=ECameraProjectionMode::Orthographic;
        TestTrue(TEXT("Perspective correction is never claimed for orthographic views"),CorrectedWorldDirection(View,Ray).Equals(Ray,1e-8));
    }
    // No world/actor is needed to exercise the exact old world-visible branch.
    auto* NPC=NewObject<USoraViewmodelComponent>();
    for(const float Windup:{0.f,.25f,1.f}) for(const bool Reload:{false,true})
    {
        NPC->KernelPose(Windup,Reload);
        TestTrue(TEXT("NPC/practice root remains the exact pre-contract transform"),
            NPC->GetRelativeLocation().Equals(FVector(40,18,-18+8.f*Windup),1e-8)&&
            NPC->GetRelativeRotation().Equals(FRotator(Reload?-30.f:28.f*Windup,0,0),1e-8)&&!NPC->HasPresentationPose());
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraViewmodelBowTransitionTest,"SoraArena.Presentation.ViewmodelBowTransitions",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraViewmodelBowTransitionTest::RunTest(const FString& Parameters)
{
    (void)Parameters; using namespace SoraViewmodelPresentation; using SoraFieldcraftAutomation::FBeatWorld;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FBeatWorld W(*this,TEXT("ViewmodelBowTransitions"),0,6);
    if(!W.Start()||!SoraArcheryAutomation::EnterLine(*W.World)) return false;
    auto* Hero=W.Hero(); auto* Kit=Hero->GetEquipment(); auto* Model=Hero->GetViewmodel();
    const auto* Contract=Get();
    if(!TestNotNull(TEXT("Validated contract is active"),Contract)||!TestTrue(TEXT("Current bow is explicitly the fallback"),
        Model->UsesFallbackBowPresentation()&&!Model->UsesAuthoredPresentation())) return false;
    FTransform Socket;
    TestFalse(TEXT("Proxy cannot pretend to provide an authored grip transform"),Model->PresentationSocketWorld(TEXT("Grip_L"),Socket));
    USceneComponent* Grip=nullptr; USceneComponent* Upper=nullptr;
    for(USceneComponent* Part:Model->GetAttachChildren())
    {
        if(Part->GetName().StartsWith(TEXT("YumiGrip"))) Grip=Part;
        if(Part->GetName().StartsWith(TEXT("YumiUpper"))) Upper=Part;
    }
    if(!TestNotNull(TEXT("The real proxy grip exists"),Grip)||!TestNotNull(TEXT("The real proxy limb exists"),Upper)) return false;
    TestTrue(TEXT("Recenter uses the actual proxy grip and preserves the rotated limb geometry"),
        Grip->GetRelativeLocation().IsNearlyZero(1e-8)&&Upper->GetRelativeLocation().Equals(FVector(5,0,77),1e-8)&&
        Upper->GetRelativeRotation().Equals(FRotator(5,0,0),1e-8));
    const FVector GameplayRay=Kit->BowAimDirection(); const int32 Ammo=Kit->Ammo;
    const FMinimalViewInfo View=CameraView(*Hero->GetCamera());
    const auto Rest=FallbackBowPose(false),Drawn=FallbackBowPose(true);
    // Direct visual state updates must not consume ammo, begin a draw, or rewrite its ray.
    Model->Sway(2,0,0,false,false,false,false,View,GameplayRay);
    const FVector Before=Model->GetRelativeLocation();
    Model->Sway(1.f/60.f,0,0,false,false,false,true,View,GameplayRay);
    TestTrue(TEXT("Draw state moves towards its own fallback anchor without snapping"),Model->PresentationPose()==Drawn.Name&&
        Model->GetRelativeLocation().Equals(FMath::Lerp(Before,Drawn.Location,BlendAlpha(1.f/60.f,Contract->BlendPerSecond)),1e-6));
    const FVector DrawDirection=(View.TransformWorldToFirstPerson(View.Location+Model->GetForwardVector()*10000.f,true)-View.Location).GetSafeNormal();
    TestTrue(TEXT("The first blend frame already follows the unsmoothed live ray"),DrawDirection.Equals(GameplayRay,1e-6));
    Model->Sway(2,0,0,true,false,false,false,View,GameplayRay);
    TestTrue(TEXT("Reload returns to fallback rest with the bow-specific -10 degree action"),Model->PresentationPose()==Rest.Name&&
        Model->GetRelativeLocation().Equals(Rest.Location,1e-5)&&Model->GetRelativeRotation().Quaternion().Equals(
            FRotator(-10,0,0).Quaternion()*Rest.Rotation,1e-5));
    Model->Sway(2,0,0,false,false,false,false,View,GameplayRay);
    Model->Sway(1.f/60.f,.137f,1,false,false,false,false,View,GameplayRay);
    TestTrue(TEXT("Bob translates in eye coordinates, independent of the rest roll"),Model->GetRelativeLocation().Equals(Rest.Location+
        FVector(0,FMath::Sin(.137f*Contract->BobYRate)*Contract->BobY,FMath::Cos(.137f*Contract->BobZRate)*Contract->BobZ),1e-5));
    const auto BoundsFit=[&]()
    {
        TArray<FPartBounds> Bounds;
        if(!Model->FallbackBowBounds(Bounds)) return false;
        const double Tan=FMath::Tan(FMath::DegreesToRadians(View.FOV*.5f));
        const FVector RayInView=View.Rotation.UnrotateVector(GameplayRay);
        const double Center=RayInView.Y/RayInView.X/Tan;
        bool GripVisible=false,StaveVisible=false;
        for(const auto& Part:Bounds)
        {
            FBox2D Projected(ForceInit);
            for(const FVector& Corner:Part.WorldCorners)
            {
                const FVector Point=View.Rotation.UnrotateVector(View.TransformWorldToFirstPerson(Corner,false)-View.Location);
                if(Point.X<View.GetFinalPerspectiveNearClipPlane()+2.f-.01f) return false;
                Projected+=FVector2D(Point.Y/Point.X/Tan,Point.Z/Point.X/Tan*View.AspectRatio);
            }
            if(!Part.bArrow&&Projected.Max.X>Center-.14+1e-4) return false;
            if(Part.Name==TEXT("YumiGrip"))
            {
                // Loaded geometry, not a remembered socket or a fabricated box.
                if(!FMath::IsNearlyEqual(FVector::Distance(Part.WorldCorners[0],Part.WorldCorners[1]),9.,1e-4)||
                   !FMath::IsNearlyEqual(FVector::Distance(Part.WorldCorners[0],Part.WorldCorners[2]),7.,1e-4)||
                   !FMath::IsNearlyEqual(FVector::Distance(Part.WorldCorners[0],Part.WorldCorners[4]),22.,1e-4)) return false;
                GripVisible=Projected.Min.X>=-.9&&Projected.Max.X<=.9&&Projected.Min.Y>=-.9&&Projected.Max.Y<=.9&&
                    Projected.GetSize().X>=.07&&Projected.GetSize().Y>=.30;
            }
            if(Part.Name==TEXT("YumiLower")||Part.Name==TEXT("YumiUpper"))
                StaveVisible|=FMath::Min(Projected.Max.Y,1.)-FMath::Max(Projected.Min.Y,-1.)>=.5&&
                    FMath::Min(Projected.Max.X,1.)-FMath::Max(Projected.Min.X,-1.)>=.006;
        }
        return GripVisible&&StaveVisible;
    };
    Model->SetRelativeLocation(FVector(60,-3,-9.5)); Model->SetRelativeRotation(FQuat::Identity);
    TestFalse(TEXT("Previous authored anchor fails the actual proxy volume regression"),BoundsFit());
    Model->Sway(2,0,0,false,false,false,false,View,GameplayRay);
    struct FState { bool Draw,Reload,Strike,Sprint; };
    const FState States[]={{false,false,false,false},{true,false,false,false},{false,false,false,false},
        {false,true,false,false},{false,false,false,true},{true,false,false,true},{false,false,true,true}};
    for(const auto& State:States) for(int32 Frame=0;Frame<90;++Frame)
    {
        Model->Sway(1.f/60.f,Frame/60.f,1.f,State.Reload,State.Strike,State.Sprint,State.Draw,View,GameplayRay);
        if(!TestTrue(TEXT("Actual proxy bounds clear aim and retain visible grip/stave throughout draw/rest/reload/sprint blends"),BoundsFit())) return false;
        if(State.Draw)
        {
            const FVector Direction=(View.TransformWorldToFirstPerson(View.Location+Model->GetForwardVector()*10000.f,true)-View.Location).GetSafeNormal();
            if(!TestTrue(TEXT("Clearance leaves live native presentation direction unchanged"),Direction.Equals(GameplayRay,1e-6))) return false;
        }
    }
    TestTrue(TEXT("Presentation state never changes live equipment state"),Kit->Ammo==Ammo&&!Kit->IsBowDrawing()&&Kit->BowAimDirection().Equals(GameplayRay,1e-8));
    return !HasAnyErrors();
}
#endif
