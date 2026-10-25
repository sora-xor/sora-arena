#include "SoraViewmodelComponent.h"
#include "SoraCatalog.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "Misc/Paths.h"

namespace
{
bool AdmittedSocketsAndMaterials(UStaticMesh* Mesh,const SoraViewmodelPresentation::FWeapon& Entry)
{
    // Approximate hero sockets are not admission. The static yumi alone is
    // also insufficient: its authored arrow plus string/draw package is pending.
    // Yari/naginata await separate import/original-capture qualification too.
    if(!Mesh||Entry.bApproximateSockets||Entry.Id>=18||Mesh->GetPathName()!=Entry.Mesh+TEXT(".")+FPaths::GetCleanFilename(Entry.Mesh)||
       Mesh->GetNumLODs()<1||Mesh->GetNumVertices(0)<=0||Mesh->GetStaticMaterials().IsEmpty()) return false;
    for(const auto& Material:Mesh->GetStaticMaterials())
        if(!Material.MaterialInterface||!Material.MaterialInterface->GetPathName().StartsWith(TEXT("/Game/Generated/"))) return false;
    for(const FName SocketName:{FName(TEXT("Grip_R")),FName(TEXT("Grip_L")),FName(TEXT("Muzzle"))})
    {
        const UStaticMeshSocket* Socket=Mesh->FindSocket(SocketName);
        if(!Socket||Socket->RelativeLocation.ContainsNaN()||Socket->RelativeRotation.ContainsNaN()||Socket->RelativeScale.ContainsNaN()||
           !Socket->RelativeScale.Equals(FVector::OneVector,1e-4)) return false;
    }
    return true;
}
}

void USoraViewmodelComponent::Build(int32 WeaponId,bool bDojoBokken,bool bFirstPerson)
{
    for(const auto& P:Parts) if(P) P->DestroyComponent(); Parts.Reset();
    PrimaryMesh=nullptr; bFirstPersonMode=bFirstPerson; bPresentationReady=false;
    bAuthoredPresentation=false; bFallbackBowPresentation=false; ActivePose.Reset();
    if(bFirstPerson) { SetRelativeLocation(RestLocation()); SetRelativeRotation(FQuat::Identity); }
    PresentationWeapon=bDojoBokken?SoraViewmodelPresentation::BokkenId:WeaponId;
    if(!FSoraCatalog::Get().IsReady()) return;
    AActor* Owner=GetOwner();
    const auto& W=FSoraCatalog::Get().Weapon(WeaponId);
    // Chapter-one sparring uses the original bokken. The first two ordinary
    // weapons use authored meshes; all of these change presentation only.
    UStaticMesh* AuthoredMesh=nullptr;
    if(bDojoBokken)
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Generated/Meshes/SM_Nyaagyu_DojoBokken.SM_Nyaagyu_DojoBokken"));
    else if(WeaponId==0&&bFirstPerson)
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Generated/Meshes/SM_Nyaagyu_HeroKatana.SM_Nyaagyu_HeroKatana"));
    else if(WeaponId==1)
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Generated/Meshes/SM_Nyaagyu_ArcCarbine.SM_Nyaagyu_ArcCarbine"));
    if(!AuthoredMesh&&!bDojoBokken&&WeaponId<18)
    {
        const FString Asset=FString::Printf(TEXT("/Game/Generated/Meshes/SM_Weapon_%02d.SM_Weapon_%02d"),WeaponId,WeaponId);
        AuthoredMesh=LoadObject<UStaticMesh>(nullptr,*Asset);
    }
    const auto* Contract=bFirstPerson?SoraViewmodelPresentation::Get():nullptr;
    const auto* Presentation=Contract?Contract->Weapons.Find(PresentationWeapon):nullptr;
    if(AuthoredMesh)
    {
        auto* Mesh=NewObject<UStaticMeshComponent>(Owner,MakeUniqueObjectName(Owner,UStaticMeshComponent::StaticClass(),TEXT("OriginalWeaponMesh")));
        // Visual only, so never in the navigation octree (ASoraWorldBuilder::Shape).
        Mesh->SetCanEverAffectNavigation(false); Mesh->SetStaticMesh(AuthoredMesh);
        Mesh->SetupAttachment(this); Mesh->SetRelativeScale3D(FVector(.75)); Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if(bFirstPerson&&Presentation&&AdmittedSocketsAndMaterials(AuthoredMesh,*Presentation))
        {
            const auto& Pose=Contract->Poses.FindChecked(Presentation->Pose);
            const UStaticMeshSocket* Anchor=AuthoredMesh->FindSocket(Pose.Anchor);
            // Qrest is in mesh axes. Recenter at the socket's position; do not
            // undo its rotation (W15's grip axes intentionally rotate 90 degrees).
            Mesh->SetRelativeScale3D(FVector(Contract->MeshScale));
            Mesh->SetRelativeLocation(-Anchor->RelativeLocation*Contract->MeshScale);
            bAuthoredPresentation=true;
        }
        if(bFirstPerson) Mesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
        Mesh->SetOnlyOwnerSee(bFirstPerson); Mesh->SetVisibility(true); Mesh->RegisterComponent(); Owner->AddInstanceComponent(Mesh); Parts.Add(Mesh);
        PrimaryMesh=Mesh;
        if(bAuthoredPresentation) BeginPresentation(false);
        return;
    }
    auto Add=[&](FString N,FVector L,FVector S,FLinearColor C)
    {
        auto* M=ASoraWorldBuilder::Shape(Owner,this,N,TEXT("/Engine/BasicShapes/Cube.Cube"),L,S,C);
        if(bFirstPerson) M->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
        M->SetOnlyOwnerSee(bFirstPerson); M->SetVisibility(true); Parts.Add(M); return M;
    };
    if(WeaponId==18)
    {
        // Yumi: an asymmetric stave, with the grip below its midpoint. This
        // source-only silhouette is awaiting a rigged, material-finished bow.
        const FLinearColor Wood(.31f,.14f,.055f), String(.79f,.72f,.55f);
        Add(TEXT("YumiLower"),FVector(5,0,-39),FVector(.045,.045,.75),Wood)->SetRelativeRotation(FRotator(-6,0,0));
        Add(TEXT("YumiUpper"),FVector(12,0,72),FVector(.045,.045,1.45),Wood)->SetRelativeRotation(FRotator(5,0,0));
        Add(TEXT("YumiGrip"),FVector(7,0,-5),FVector(.09,.07,.22),FLinearColor(.09f,.055f,.03f));
        Add(TEXT("YumiString"),FVector(-13,0,34),FVector(.008,.008,2.15),String);
        Add(TEXT("NockedArrow"),FVector(34,0,2),FVector(.48,.012,.012),FLinearColor(.64f,.38f,.13f));
        Add(TEXT("Arrowhead"),FVector(83,0,2),FVector(.055,.025,.025),FLinearColor(.66f,.70f,.74f));
    }
    else if(WeaponId==19 || WeaponId==20)
    {
        const bool bYari=WeaponId==19;
        Add(TEXT("LacqueredShaft"),FVector(50,0,2),FVector(2.f,.035f,.035f),FLinearColor(.19f,.095f,.035f));
        Add(TEXT("IronFerrule"),FVector(145,0,2),FVector(.085f,.045f,.045f),FLinearColor(.35f,.38f,.40f));
        auto* Blade=Add(bYari?TEXT("StraightSpearhead"):TEXT("CurvedNaginataBlade"),
            FVector(bYari?172:178,0,bYari?2:7),FVector(bYari?.30f:.42f,.02f,bYari?.035f:.065f),
            FLinearColor(.68f,.75f,.79f));
        if(!bYari) Blade->SetRelativeRotation(FRotator(0,-10.f,0));
    }
    else if(W.Kind==TEXT("melee"))
    {
        Add(TEXT("Blade"),FVector(30,0,10),FVector(.9,.025,.07),bDojoBokken?FLinearColor(.46,.27,.11):FLinearColor(.72,.80,.84));
        Add(TEXT("Tsuka"),FVector(-24,0,10),FVector(.22,.055,.075),FLinearColor(.15,.06,.025));
        Add(TEXT("Tsuba"),FVector(-10,0,10),FVector(.025,.16,.20),bDojoBokken?FLinearColor(.31,.16,.06):FLinearColor(.52,.32,.08));
    }
    else
    {
        Add(TEXT("Receiver"),FVector(5,0,0),FVector(.5,.1,.14),FLinearColor(.14,.16,.18));
        Add(TEXT("Barrel"),FVector(43,0,1),FVector(.42,.045,.045),W.Special?FLinearColor(.07,.67,.67):FLinearColor(.20,.23,.25));
        Add(TEXT("Stock"),FVector(-26,0,-1),FVector(.3,.08,.13),FLinearColor(.29,.13,.035));
        Add(TEXT("Magazine"),FVector(3,0,-12),FVector(.1,.08,.22),FLinearColor(.25,.25,.23));
        Add(TEXT("Sight"),FVector(22,0,10),FVector(.08,.065,.06),FLinearColor(.65,.39,.08));
    }
    Add(TEXT("FurPaw"),FVector(-13,-2,-10),FVector(.13,.15,.13),FLinearColor(.69,.47,.25));
    if(bFirstPerson&&WeaponId==18&&Presentation)
    {
        // This is the existing proxy's actual grip, not an authored socket.
        // Recenter the unchanged proxy geometry as a group, and label it fallback.
        const FVector ProxyGrip(7,0,-5);
        for(const auto& Part:Parts) if(Part) Part->SetRelativeLocation(Part->GetRelativeLocation()-ProxyGrip);
        BeginPresentation(true);
    }
}
void USoraViewmodelComponent::BeginPresentation(bool bFallbackBow)
{
    const auto* Contract=SoraViewmodelPresentation::Get();
    const auto* Entry=Contract?Contract->Weapons.Find(PresentationWeapon):nullptr;
    if(!Entry) return;
    const auto& Pose=Contract->Poses.FindChecked(Entry->Pose);
    bPresentationReady=true; bFallbackBowPresentation=bFallbackBow;
    SmoothedAnchor=Pose.Location; SmoothedRest=Pose.Rotation; ActivePose=Pose.Name;
    SmoothedPitch=SmoothedRoll=SmoothedLift=0;
    SetRelativeLocation(SmoothedAnchor); SetRelativeRotation(SmoothedRest);
}
void USoraViewmodelComponent::Present(float DeltaSeconds,float LifeTime,float Moving,float Pitch,float Roll,float Lift,
    bool bDrawn,const FMinimalViewInfo* View,const FVector& GameplayRay)
{
    const auto* Contract=SoraViewmodelPresentation::Get();
    const auto& Entry=Contract->Weapons.FindChecked(PresentationWeapon);
    const auto& Pose=Contract->Poses.FindChecked(bDrawn?TEXT("bow.drawn"):Entry.Pose);
    ActivePose=Pose.Name;
    const float Alpha=SoraViewmodelPresentation::BlendAlpha(DeltaSeconds,Contract->BlendPerSecond);
    SmoothedAnchor=FMath::Lerp(SmoothedAnchor,Pose.Location,Alpha);
    SmoothedRest=FQuat::Slerp(SmoothedRest,Pose.Rotation,Alpha).GetNormalized();
    SmoothedPitch=FMath::Lerp(SmoothedPitch,Pitch,Alpha); SmoothedRoll=FMath::Lerp(SmoothedRoll,Roll,Alpha);
    SmoothedLift=FMath::Lerp(SmoothedLift,Lift,Alpha);
    const FQuat Action=FRotator(SmoothedPitch,0,SmoothedRoll).Quaternion();
    FQuat Aim=FQuat::Identity;
    if(bDrawn&&View&&GetAttachParent())
    {
        const FVector Desired=GetAttachParent()->GetComponentQuat().UnrotateVector(
            SoraViewmodelPresentation::CorrectedWorldDirection(*View,GameplayRay));
        // Keep the current live ray outside every state/rest interpolation.
        Aim=FQuat::FindBetweenNormals((Action*SmoothedRest).GetForwardVector(),Desired);
    }
    SetRelativeLocation(SmoothedAnchor+FVector(0,FMath::Sin(LifeTime*Contract->BobYRate)*Moving*Contract->BobY,
        FMath::Cos(LifeTime*Contract->BobZRate)*Moving*Contract->BobZ+SmoothedLift));
    SetRelativeRotation(SoraViewmodelPresentation::Compose(Aim,Action,SmoothedRest));
}
void USoraViewmodelComponent::Sway(float DeltaSeconds,float LifeTime,float Moving,bool bReloading,bool bStrike,
    bool bSprint,bool bBowDrawing,const FMinimalViewInfo& View,const FVector& GameplayRay)
{
    if(bFirstPersonMode&&bPresentationReady)
    {
        const auto* Contract=SoraViewmodelPresentation::Get();
        const auto& Pose=Contract->Poses.FindChecked(Contract->Weapons.FindChecked(PresentationWeapon).Pose);
        Present(DeltaSeconds,LifeTime,Moving,bReloading?Pose.ReloadPitch:bStrike?Contract->StrikePitch:0.f,
            bSprint?Contract->SprintRoll:0.f,0.f,PresentationWeapon==18&&bBowDrawing,&View,GameplayRay);
        return;
    }
    // Unadmitted meshes retain their prior framing. No authored paw is invented.
    const float Pitch=bReloading?-30.f:bStrike?25.f:bBowDrawing?-15.f:0.f,Roll=bSprint?-15.f:0.f;
    SetRelativeLocation(FVector(40,18+FMath::Sin(LifeTime*8)*Moving*.7,-18+FMath::Cos(LifeTime*16)*Moving*.6));
    // Gameplay offset is camera-component-local. The presentation view can
    // include an additive camera rotation, which must not counter-rotate this
    // legacy branch (or change the old BowAimOffset * action composition).
    const FVector EyeRay=GetAttachParent()?GetAttachParent()->GetComponentQuat().UnrotateVector(GameplayRay):GameplayRay;
    SetRelativeRotation(EyeRay.Rotation().Quaternion()*FRotator(Pitch,0,Roll).Quaternion());
}
void USoraViewmodelComponent::KernelPose(float Windup,bool bReloading)
{
    if(bFirstPersonMode&&bPresentationReady)
    {
        const auto* Contract=SoraViewmodelPresentation::Get();
        const auto& Pose=Contract->Poses.FindChecked(Contract->Weapons.FindChecked(PresentationWeapon).Pose);
        Present(GetWorld()?GetWorld()->GetDeltaSeconds():0.f,0,0,bReloading?Pose.ReloadPitch:Contract->WindupPitch*Windup,
            0,Contract->WindupLift*Windup,false,nullptr,FVector::ForwardVector);
        return;
    }
    // World-visible NPC/practice transforms intentionally remain exact.
    SetRelativeLocation(FVector(40,18,-18+8.f*Windup));
    SetRelativeRotation(FRotator(bReloading?-30.f:28.f*Windup,0,0));
}
bool USoraViewmodelComponent::PresentationSocketWorld(FName Socket,FTransform& Transform) const
{
    if(!bAuthoredPresentation||!PrimaryMesh||!PrimaryMesh->DoesSocketExist(Socket)) return false;
    Transform=PrimaryMesh->GetSocketTransform(Socket,RTS_World);
    return !Transform.ContainsNaN();
}
