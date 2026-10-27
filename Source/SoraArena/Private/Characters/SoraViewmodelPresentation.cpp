#include "SoraViewmodelPresentation.h"
#include "SoraCatalog.h"
#include "Camera/CameraComponent.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace SoraViewmodelPresentation
{
namespace
{
using FObject=TSharedPtr<FJsonObject>;
bool Number(const FObject& Object,const TCHAR* Key,float& Out)
{
    double Value=0;
    if(!Object.IsValid()||!Object->TryGetNumberField(Key,Value)||!FMath::IsFinite(Value)||FMath::Abs(Value)>100000.) return false;
    Out=static_cast<float>(Value); return true;
}
bool Vector(const FObject& Object,const TCHAR* Key,FVector& Out)
{
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    if(!Object.IsValid()||!Object->TryGetArrayField(Key,Values)||Values->Num()!=3) return false;
    double XYZ[3]={};
    for(int32 Index=0;Index<3;++Index)
        if(!(*Values)[Index]->TryGetNumber(XYZ[Index])||!FMath::IsFinite(XYZ[Index])||FMath::Abs(XYZ[Index])>10000.) return false;
    Out=FVector(XYZ[0],XYZ[1],XYZ[2]); return true;
}
FObject Object(const FObject& Parent,const TCHAR* Key)
{
    const FObject* Value=nullptr;
    return Parent.IsValid()&&Parent->TryGetObjectField(Key,Value)?*Value:nullptr;
}
bool String(const FObject& Parent,const TCHAR* Key,FString& Out)
{
    return Parent.IsValid()&&Parent->TryGetStringField(Key,Out)&&!Out.IsEmpty();
}
}
bool Parse(const FString& Text,FContract& Out,FString& Error)
{
    Out=FContract(); Error.Reset(); FContract Candidate;
    auto Fail=[&Error](const FString& Why) { Error=Why; return false; };
    FObject Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root.IsValid()) return Fail(TEXT("viewmodels: invalid JSON"));
    float Version=0; FString Kind;
    if(!Number(Root,TEXT("schema_version"),Version)||Version!=2||!String(Root,TEXT("kind"),Kind)||Kind!=TEXT("sora-first-person-viewmodels"))
        return Fail(TEXT("viewmodels: unknown schema"));
    if(!Number(Root,TEXT("mesh_scale"),Candidate.MeshScale)||Candidate.MeshScale<=0||Candidate.MeshScale>2)
        return Fail(TEXT("viewmodels: invalid mesh scale"));
    const auto Motion=Object(Root,TEXT("motion")),Bob=Object(Motion,TEXT("bob_cm")),Pitch=Object(Motion,TEXT("pitch_deg")),Windup=Object(Motion,TEXT("kernel_windup"));
    if(!Number(Motion,TEXT("blend_per_s"),Candidate.BlendPerSecond)||Candidate.BlendPerSecond<=0||Candidate.BlendPerSecond>60||
       !Number(Bob,TEXT("y"),Candidate.BobY)||!Number(Bob,TEXT("z"),Candidate.BobZ)||
       !Number(Bob,TEXT("y_rad_per_s"),Candidate.BobYRate)||!Number(Bob,TEXT("z_rad_per_s"),Candidate.BobZRate)||
       !Number(Pitch,TEXT("reload"),Candidate.ReloadPitch)||!Number(Pitch,TEXT("committed_strike"),Candidate.StrikePitch)||
       !Number(Motion,TEXT("sprint_roll_deg"),Candidate.SprintRoll)||!Number(Windup,TEXT("lift_cm"),Candidate.WindupLift)||
       !Number(Windup,TEXT("pitch_deg"),Candidate.WindupPitch)||Pitch->HasField(TEXT("bow_drawing")))
        return Fail(TEXT("viewmodels: invalid motion or stacked legacy bow tilt"));
    const auto Poses=Object(Root,TEXT("poses"));
    const TSet<FString> ExpectedPoses={TEXT("sword"),TEXT("dagger"),TEXT("gun"),TEXT("polearm"),TEXT("heavy"),TEXT("kama"),TEXT("bow"),TEXT("bow.drawn")};
    if(!Poses.IsValid()||Poses->Values.Num()!=ExpectedPoses.Num()) return Fail(TEXT("viewmodels: incomplete pose table"));
    for(const FString& Name:ExpectedPoses)
    {
        const auto Pose=Object(Poses,*Name),Rest=Object(Pose,TEXT("rest"));
        FString Anchor; FVector Rotation; FPose Entry; Entry.Name=Name; Entry.ReloadPitch=Candidate.ReloadPitch;
        if(!String(Pose,TEXT("anchor"),Anchor)||(Anchor!=TEXT("Grip_R")&&Anchor!=TEXT("Grip_L"))||
           !Vector(Rest,TEXT("anchor_cm"),Entry.Location)||Entry.Location.X<=0||!Vector(Rest,TEXT("rotation_deg"),Rotation))
            return Fail(TEXT("viewmodels: invalid pose ")+Name);
        Entry.Anchor=FName(*Anchor); Entry.Rotation=FRotator(Rotation.X,Rotation.Y,Rotation.Z).Quaternion();
        const auto Reload=Object(Object(Pose,TEXT("motion_overrides")),TEXT("reload"));
        if(Reload.IsValid()&&!Number(Reload,TEXT("pitch"),Entry.ReloadPitch)) return Fail(TEXT("viewmodels: invalid reload override"));
        Candidate.Poses.Add(Name,Entry);
    }
    if(Candidate.Poses.FindChecked(TEXT("bow")).ReloadPitch!=-10.f||
       Candidate.Poses.FindChecked(TEXT("bow")).Anchor!=FName(TEXT("Grip_L"))||Candidate.Poses.FindChecked(TEXT("bow.drawn")).Anchor!=FName(TEXT("Grip_L")))
        return Fail(TEXT("viewmodels: bow requires its left grip and admitted -10 degree reload limit"));
    const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
    if(!Root->TryGetArrayField(TEXT("weapons"),Entries)||Entries->Num()!=22||!FSoraCatalog::Get().IsReady())
        return Fail(TEXT("viewmodels: expected catalog-ready 22 weapon entries"));
    TSet<FString> Keys;
    for(const auto& Value:*Entries)
    {
        const FObject* EntryPointer=nullptr;
        if(!Value.IsValid()||!Value->TryGetObject(EntryPointer)||!EntryPointer->IsValid()) return Fail(TEXT("viewmodels: invalid weapon object"));
        const auto& Entry=*EntryPointer; FWeapon Weapon; double NumberId=0; FString StringId;
        if(Entry->TryGetNumberField(TEXT("id"),NumberId))
        {
            if(!FMath::IsFinite(NumberId)||NumberId<0||NumberId>20||FMath::FloorToDouble(NumberId)!=NumberId) return Fail(TEXT("viewmodels: invalid weapon id"));
            Weapon.Id=static_cast<int32>(NumberId);
        }
        else if(Entry->TryGetStringField(TEXT("id"),StringId)&&StringId==TEXT("bokken")) Weapon.Id=BokkenId;
        else return Fail(TEXT("viewmodels: invalid weapon id"));
        if(Candidate.Weapons.Contains(Weapon.Id)||!String(Entry,TEXT("key"),Weapon.Key)||Keys.Contains(Weapon.Key)||
           !String(Entry,TEXT("en"),Weapon.Name)||!String(Entry,TEXT("pose"),Weapon.Pose)||!Candidate.Poses.Contains(Weapon.Pose)||
           !String(Entry,TEXT("first_person_mesh"),Weapon.Mesh)||!Weapon.Mesh.StartsWith(TEXT("/Game/Generated/Meshes/SM_"))||
           Weapon.Mesh.Contains(TEXT(".."))||Weapon.Mesh.Contains(TEXT("."))) return Fail(TEXT("viewmodels: duplicate/invalid weapon entry"));
        if(Weapon.Id==BokkenId)
        {
            if(Weapon.Key!=TEXT("DojoBokken")||Weapon.Name!=TEXT("Dojo bokken")||Weapon.Pose!=TEXT("sword")) return Fail(TEXT("viewmodels: wrong bokken identity"));
        }
        else if(Weapon.Name!=FSoraCatalog::Get().Weapon(Weapon.Id).NameEnglish||!Weapon.Key.StartsWith(FString::Printf(TEXT("W%02d_"),Weapon.Id)))
            return Fail(TEXT("viewmodels: weapon identity differs from catalog"));
        Weapon.bApproximateSockets=Entry->HasField(TEXT("sockets_m"));
        const FString ExpectedMesh=Weapon.Id==BokkenId?TEXT("SM_Nyaagyu_DojoBokken"):Weapon.Id==0?TEXT("SM_Nyaagyu_HeroKatana"):
            Weapon.Id==1?TEXT("SM_Nyaagyu_ArcCarbine"):FString::Printf(TEXT("SM_Weapon_%02d"),Weapon.Id);
        if(Weapon.Mesh!=TEXT("/Game/Generated/Meshes/")+ExpectedMesh||
           Weapon.bApproximateSockets!=(Weapon.Id==0||Weapon.Id==1||Weapon.Id==BokkenId))
            return Fail(TEXT("viewmodels: wrong mesh identity or approximate socket admission"));
        if(!Weapon.bApproximateSockets)
        {
            FString Record;
            if(!String(Entry,TEXT("sockets_from"),Record)||Record!=TEXT("Content/SourceArt/Weapons/Runtime/")+Weapon.Key+TEXT("/build_record.json"))
                return Fail(TEXT("viewmodels: invalid socket record reference"));
        }
        if(Weapon.Id==18)
        {
            const TArray<TSharedPtr<FJsonValue>>* States=nullptr;
            if(Weapon.Pose!=TEXT("bow")||!Entry->TryGetArrayField(TEXT("states"),States)||States->Num()!=2||
               (*States)[0]->AsString()!=TEXT("rest")||(*States)[1]->AsString()!=TEXT("drawn")||!Object(Entry,TEXT("package")).IsValid())
                return Fail(TEXT("viewmodels: incomplete bow states/package"));
        }
        Keys.Add(Weapon.Key); Candidate.Weapons.Add(Weapon.Id,MoveTemp(Weapon));
    }
    Out=MoveTemp(Candidate); return true;
}
const FContract* Get()
{
    static FContract Contract;
    static bool Attempted=false,Valid=false;
    if(!Attempted)
    {
        Attempted=true; FString Text,Error;
        Valid=FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Data/viewmodels.json")))&&Parse(Text,Contract,Error);
        if(!Valid) UE_LOG(LogTemp,Warning,TEXT("First-person presentation remains legacy: %s"),*Error);
    }
    return Valid?&Contract:nullptr;
}
FMinimalViewInfo CameraView(const UCameraComponent& Camera)
{
    // UE 5.8 CameraComponent.cpp projection fields, read without GetCameraView's
    // SetWorldRotation/HandleXRCamera side effects. Cleared additive offsets are
    // identity/zero (FTransform's default constructor plus UObject zeroed
    // allocation, and ClearAdditiveOffset); supported setters retain this.
    // This snapshot covers the game's perspective component, not XR or a
    // custom camera manager's post-component modifications.
    FMinimalViewInfo View; FTransform Additive; float AdditiveFOV=0;
    Camera.GetAdditiveOffset(Additive,AdditiveFOV);
    const FTransform Transform=Additive*Camera.GetComponentTransform();
    View.Location=Transform.GetLocation(); View.Rotation=Transform.Rotator();
    View.FOV=Camera.FieldOfView+AdditiveFOV; View.AspectRatio=Camera.AspectRatio;
    View.bConstrainAspectRatio=Camera.bConstrainAspectRatio; View.ProjectionMode=Camera.ProjectionMode;
    View.FirstPersonFOV=Camera.bEnableFirstPersonFieldOfView?Camera.FirstPersonFieldOfView:View.FOV;
    View.FirstPersonScale=Camera.bEnableFirstPersonScale?Camera.FirstPersonScale:1.f;
    View.bUseFirstPersonParameters=Camera.bEnableFirstPersonFieldOfView||Camera.bEnableFirstPersonScale;
    View.ApplyOverscan(Camera.Overscan,Camera.bScaleResolutionWithOverscan,Camera.bCropOverscan);
    View.ApplyAsymmetricOverscan(Camera.AsymmetricOverscan,Camera.bScaleResolutionWithOverscan,Camera.bCropOverscan);
    if(Camera.bOverrideAspectRatioAxisConstraint) View.AspectRatioAxisConstraint=Camera.AspectRatioAxisConstraint;
    return View;
}
FVector CorrectedWorldDirection(const FMinimalViewInfo& View,const FVector& GameplayDirection)
{
    const FVector Direction=GameplayDirection.GetSafeNormal();
    if(View.ProjectionMode!=ECameraProjectionMode::Perspective||!View.bUseFirstPersonParameters) return Direction;
    const float Factor=View.CalculateFirstPersonFOVCorrectionFactor();
    if(!FMath::IsFinite(Factor)||Factor<=UE_SMALL_NUMBER) return Direction;
    return (View.TransformFirstPersonToWorld(View.Location+Direction*10000.f,true)-View.Location).GetSafeNormal();
}
FQuat Compose(const FQuat& Aim,const FQuat& Action,const FQuat& Rest) { return (Aim*Action*Rest).GetNormalized(); }
FPose FallbackBowPose(bool bDrawn)
{
    // Fixed framing chosen from all corners of the actual seven cube
    // components, including the 22 cm grip and 13x15x13 cm paw. Do not use
    // the authored bow's socket-point framing for these different volumes.
    // No automatic offscreen translation can conceal a failed bounds check.
    FPose Pose; Pose.Name=bDrawn?TEXT("fallback.bow.drawn"):TEXT("fallback.bow");
    Pose.Anchor=TEXT("YumiGrip"); Pose.ReloadPitch=-10.f;
    Pose.Location=bDrawn?FVector(120,-36,-12):FVector(120,-48,-15);
    Pose.Rotation=bDrawn?FQuat::Identity:FRotator(0,6,-8).Quaternion();
    return Pose;
}
float BlendAlpha(float DeltaSeconds,float PerSecond) { return 1.f-FMath::Exp(-FMath::Max(0.f,DeltaSeconds)*PerSecond); }
}
