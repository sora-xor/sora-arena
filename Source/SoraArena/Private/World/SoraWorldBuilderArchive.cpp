#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraArchiveRules.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/WidgetComponent.h"
#include "Engine/Font.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/RectLight.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UI/SoraUIFont.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
// The authored household arithmetic is visible on the actual slate. Slate
// uses the game's shipped Japanese font, so this remains text at every
// viewport size rather than baked or generated lettering.
TSharedRef<SWidget> FamilyRecord(UFont* Font)
{
    const auto Face=[Font](int32 Size)
    { auto F=Font->GetLegacySlateFontInfo();F.Size=Size;return F; };
    const FLinearColor Cyan(.78f,.93f,1.f),Muted(.48f,.65f,.70f);
    auto Rows=SNew(SVerticalBox);
    Rows->AddSlot().AutoHeight().Padding(0,0,0,8)
        [SNew(STextBlock).Text(FText::FromString(TEXT("武家方記録"))).Font(Face(24)).ColorAndOpacity(Muted)];
    Rows->AddSlot().AutoHeight().Padding(0,0,0,30)
        [SNew(STextBlock).Text(FText::FromString(TEXT("鷲尾家"))).Font(Face(58)).ColorAndOpacity(Cyan)];
    const auto Row=[&](const TCHAR* Label,const TCHAR* Value,int32 Size,float Bottom,bool Purchase=false)
    {
        const FLinearColor Ink=Purchase?FLinearColor(1.f,.62f,.30f):Cyan;
        Rows->AddSlot().AutoHeight().Padding(0,0,0,Bottom)
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(Label)).Font(Face(Size)).ColorAndOpacity(Ink)]
            +SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text(FText::FromString(Value)).Font(Face(Size)).ColorAndOpacity(Ink)]];
    };
    Row(TEXT("元本"),TEXT("120"),36,8);
    Row(TEXT("利息"),TEXT("22"),36,8);
    Row(TEXT("延滞金"),TEXT("36"),36,8);
    Row(TEXT("手数料"),TEXT("52"),36,8);
    Row(TEXT("返済"),TEXT("△40"),36,24);
    Row(TEXT("残高"),TEXT("190"),60,18);
    Row(TEXT("買取価格"),TEXT("30"),36,10,true);
    Rows->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("単位：石"))).Font(Face(22)).ColorAndOpacity(Muted)];
    return SNew(SBorder).Padding(40).BorderBackgroundColor(FLinearColor(.0003f,.0008f,.001f,1.f))[Rows];
}
constexpr float FamilyPageLumens=220.f;
}

void ASoraWorldBuilder::BuildArchive(const FSoraZone& Zone,const FSoraZone& Press)
{
    namespace R=SoraArchiveRules;
    const FVector O(Zone.Rect.Min,R::FloorCm);
    const FLinearColor Timber(.16f,.11f,.065f),Plaster(.58f,.55f,.49f),Slate(.025f,.032f,.035f);
    const auto Part=[&](const TCHAR* Name,FVector At,FVector Size,FLinearColor Color,const TCHAR* Role,bool Solid=true)
    { return Box(Name,O+At,Size,Color,Solid,FRotator::ZeroRotator,Role); };
    Part(TEXT("ArchiveBoardFloor"),FVector(1300,900,-40),FVector(2760,1960,80),Timber,TEXT("Timber"));
    Part(TEXT("ArchiveRoof"),FVector(1300,900,620),FVector(2760,1960,40),Timber,TEXT("Timber"));
    for(const FSoraBox& Wall:Zone.Walls)
        Box(TEXT("ArchiveWall"),FVector(Wall.Center,R::FloorCm+Wall.Height*.5f),FVector(Wall.Size,Wall.Height),Plaster,true,FRotator::ZeroRotator,TEXT(""));
    for(int I=0;I<Zone.Cover.Num();++I)
    {
        const auto& Post=Zone.Cover[I];
        auto* P=Box(FString::Printf(TEXT("ArchiveDuelPost%d"),I),FVector(Post.Center,R::FloorCm+Post.Height*.5f),
            FVector(Post.Size,Post.Height),Timber,true,FRotator::ZeroRotator,TEXT("Timber"));
        P->ComponentTags.Add(TEXT("ArchiveDuelPost"));
    }
    // Preserve the tested rack collision. The visible shelves/slates live
    // inside that footprint and do not add hundreds of navigation obstacles.
    // These simple shapes establish Claude's bay/light direction; authored
    // timber and glass production assets still need their separate art pass.
    for(int Side:{0,1})
    {
        const float X=Side?2540.f:60.f,Front=Side?2480.f:120.f;
        auto* Rack=Part(TEXT("ArchiveSlateRackCollision"),FVector(X,900,180),FVector(120,1800,360),Slate,TEXT(""));
        Rack->SetVisibility(false);
        if(Side) { ArchiveEastRack=Rack;Rack->ComponentTags.Add(TEXT("ArchiveEastRack")); }
        const auto RackPart=[&](const TCHAR* Name,FVector At,FVector Size,FLinearColor Color,const TCHAR* Role)
        {
            auto* Piece=Part(Name,At,Size,Color,Role,false);
            Piece->AttachToComponent(Rack,FAttachmentTransformRules::KeepWorldTransform);
            return Piece;
        };
        const auto Batch=[&](const TCHAR* Name,FLinearColor Color,bool Glow)
        {
            auto* Mesh=NewObject<UInstancedStaticMeshComponent>(this,MakeUniqueObjectName(this,UInstancedStaticMeshComponent::StaticClass(),FName(Name)));
            Mesh->SetupAttachment(Rack);Mesh->SetAbsolute(false,false,true);
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);
            Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
            Mesh->SetCastShadow(!Glow);Mesh->RegisterComponent();AddInstanceComponent(Mesh);Pieces.Add(Mesh);
            Tint(Mesh,Color);
            if(Glow)
                if(auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Generated/Materials/M_ArenaGlow.M_ArenaGlow")))
                {
                    auto* Material=UMaterialInstanceDynamic::Create(Base,Mesh);
                    Material->SetVectorParameterValue(TEXT("Color"),Color);Mesh->SetMaterial(0,Material);
                }
            Mesh->ComponentTags.Add(Glow?TEXT("ArchiveSlateEdges"):TEXT("ArchiveSlateBodies"));
            return Mesh;
        };
        auto* Bodies=Batch(TEXT("ArchiveStoredSlates"),Slate,false);
        UInstancedStaticMeshComponent* Edges[4];
        for(int Level=0;Level<4;++Level) Edges[Level]=Batch(TEXT("ArchiveSlateEdgeGlow"),FLinearColor(.14f,.50f,.60f)*(.35f+.65f*Level/3.f),true);
        RackPart(TEXT("ArchiveRackBack"),FVector(Side?2592:8,900,160),FVector(8,1680,320),Timber,TEXT("Timber"));
        RackPart(TEXT("ArchiveRackPlinth"),FVector(X,900,15),FVector(116,1680,30),Timber,TEXT("Timber"));
        for(int Bay=0;Bay<9;++Bay)
        {
            const float Y=172.f+182.f*Bay;
            for(int Shelf=0;Shelf<6;++Shelf)
            {
                const float Z=30.f+44.f*Shelf;
                if(Side&&Bay==4&&Z>100.f&&Z<200.f)
                    for(float Offset:{-64.f,64.f})
                        RackPart(TEXT("ArchiveShelfNiche"),FVector(X,Y+Offset,Z),FVector(112,42,5),Timber,TEXT("Timber"));
                else RackPart(TEXT("ArchiveShelf"),FVector(X,Y,Z),FVector(112,170,5),Timber,TEXT("Timber"));
                for(int Book=0;Book<29;++Book)
                {
                    const int Seed=Side*1723+Bay*191+Shelf*43+Book*13;
                    FRandomStream Variation(Seed*7919+37);
                    const float BY=Y-76.f+Book*5.4f+Variation.FRandRange(-.7f,.7f);
                    const float Height=Variation.FRandRange(24.f,32.f),Thickness=Variation.FRandRange(1.8f,3.2f);
                    // Leave the readable 75x100 cm household plate's own bay
                    // clear. Its physical size/camera are unchanged this pass.
                    if(Side&&FMath::Abs(BY-900.f)<43.f&&Z+Height>98.f&&Z<202.f) continue;
                    const FVector At(Front+(Side?1.f:-1.f)*13.f,BY,Z+3.f+Height*.5f);
                    Bodies->AddInstance(FTransform(FQuat::Identity,O+At,FVector(.22f,Thickness/100.f,Height/100.f)),true);
                    if(Seed%17==0) continue; // stable, sparse unlit records
                    // Interrupted, uneven edge inscriptions avoid the former
                    // full-height repeated bars. Each record retains one body.
                    const int Level=Variation.RandRange(0,3);
                    const float Lower=Variation.FRandRange(4.f,7.f),Gap=Variation.FRandRange(2.f,5.f),Bottom=Z+5.f;
                    const float Upper=FMath::Min(Variation.FRandRange(8.f,14.f),Height-Lower-Gap-4.f);
                    for(const FVector2D Segment:{FVector2D(Bottom+Lower*.5f,Lower),FVector2D(Bottom+Lower+Gap+Upper*.5f,Upper)})
                    {
                        const FVector Edge(Front+(Side?-1.f:1.f)*.3f,BY,Segment.X);
                        Edges[Level]->AddInstance(FTransform(FQuat::Identity,O+Edge,FVector(.004f,.007f,Segment.Y/100.f)),true);
                    }
                }
            }
            if(auto* Lamp=GetWorld()->SpawnActor<ARectLight>(O+FVector(Front+(Side?-1.f:1.f)*3.f,Y,190),FRotator(0,Side?180:0,0)))
            {
                Lamp->SetMobility(EComponentMobility::Movable);
                auto* Light=Lamp->RectLightComponent.Get();
                Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(36.f);
                Light->SetLightColor(FLinearColor(.25f,.66f,.78f));Light->SetAttenuationRadius(250.f);
                Light->SetSourceWidth(150.f);Light->SetSourceHeight(70.f);
                Light->SetCastShadows(Side&&Bay>=3&&Bay<=5);
                Lamp->Tags.Add(TEXT("ArchiveRackLight"));DecorActors.Add(Lamp);
            }
        }
        for(int Post=0;Post<=9;++Post)
            RackPart(TEXT("ArchiveRackUpright"),FVector(Front+(Side?6.f:-6.f),81.f+182.f*Post,160),FVector(12,12,320),Timber,TEXT("Timber"));
    }
    // Exposed framing and plain plaster replace the archive's masonry look.
    for(float Y:{300.f,600.f,900.f,1200.f,1500.f})
        Part(TEXT("ArchiveCeilingBeam"),FVector(1300,Y,570),FVector(2600,24,40),Timber,TEXT("Timber"),false);
    for(int Side:{0,1})
    {
        for(float Y:{300.f,600.f,900.f,1200.f,1500.f})
            Part(TEXT("ArchiveWallPost"),FVector(Side?2592:8,Y,300),FVector(16,20,600),Timber,TEXT("Timber"),false);
        Part(TEXT("ArchiveWallTie"),FVector(Side?2590:10,900,370),FVector(16,1800,18),Timber,TEXT("Timber"),false);
    }
    ArchiveExposure=GetWorld()->SpawnActor<APostProcessVolume>();
    if(ArchiveExposure)
    {
        ArchiveExposure->bUnbound=true;ArchiveExposure->Priority=100.f;ArchiveExposure->BlendWeight=0.f;
        ArchiveExposure->Tags.Add(TEXT("ArchiveExposure"));DecorActors.Add(ArchiveExposure);
        auto& Grade=ArchiveExposure->Settings;
        Grade.bOverride_AutoExposureMethod=true;Grade.AutoExposureMethod=AEM_Manual;
        Grade.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Grade.AutoExposureApplyPhysicalCameraExposure=false;
        Grade.bOverride_AutoExposureBias=true;Grade.AutoExposureBias=-2.f;
    }
    ArchivePage=Part(TEXT("ArchiveWashioSlate"),FVector(2477,900,150),FVector(4,75,100),FLinearColor(.015f,.025f,.03f),TEXT(""),false);
    ArchivePage->ComponentTags.Add(TEXT("ArchiveFamilyPage"));
    ArchivePageFont=SoraUI::CreateUIFont(this);
    ArchivePageText=NewObject<UWidgetComponent>(this);
    ArchivePageText->SetupAttachment(RootComponent);
    ArchivePageText->SetWidgetSpace(EWidgetSpace::World);
    ArchivePageText->SetDrawSize(FVector2D(750,1000));ArchivePageText->SetPivot(FVector2D(.5f,.5f));
    ArchivePageText->SetBlendMode(EWidgetBlendMode::Opaque);
    ArchivePageText->SetBackgroundColor(FLinearColor(.0003f,.0008f,.001f,1.f));
    // The world widget shares the room's fixed exposure. Its independent
    // radiance restores the text hierarchy without lifting every shelf/wall.
    ArchivePageText->SetTintColorAndOpacity(FLinearColor(8.f,8.f,8.f,1.f));
    ArchivePageText->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    ArchivePageText->SetCanEverAffectNavigation(false);
    ArchivePageText->SetRelativeLocation(O+FVector(2474,900,150));
    ArchivePageText->SetRelativeRotation(FRotator(0,180,0));ArchivePageText->SetRelativeScale3D(FVector(.1f));
    ArchivePageText->SetSlateWidget(FamilyRecord(ArchivePageFont));
    ArchivePageText->SetVisibility(false);ArchivePageText->SetRedrawTime(1.f);
    ArchivePageText->RegisterComponent();AddInstanceComponent(ArchivePageText);
    ArchivePageText->ComponentTags.Add(TEXT("ArchiveFamilyRecord"));
    ArchivePageLight=GetWorld()->SpawnActor<ARectLight>(O+FVector(2470,900,150),FRotator(0,180,0));
    if(ArchivePageLight)
    {
        ArchivePageLight->SetMobility(EComponentMobility::Movable);
        ArchivePageLight->Tags.Add(TEXT("ArchiveFamilyPageLight"));
        auto* Light=ArchivePageLight->RectLightComponent.Get();
        Light->SetIntensityUnits(ELightUnits::Lumens);
        Light->SetIntensity(0.f); Light->SetVisibility(false);
        Light->SetLightColor(FLinearColor(.85f,.96f,1.f));
        Light->SetUseTemperature(true);Light->SetTemperature(6500.f);
        Light->SetAttenuationRadius(700.f);Light->SetSourceWidth(75.f);Light->SetSourceHeight(100.f);
        Light->SetCastShadows(true);
        DecorActors.Add(ArchivePageLight);
    }
    Part(TEXT("ArchiveSouthDoor"),FVector(1300,-1,130),FVector(200,4,260),Timber,TEXT("Timber"),false);
    Part(TEXT("ArchiveNorthLintel"),FVector(1300,1830,430),FVector(240,60,340),Plaster,TEXT("Stone"));
    ArchiveNorthGate=Part(TEXT("ArchiveNorthDoor"),FVector(1300,1830,130),FVector(240,20,260),Timber,TEXT("Timber"));
    ArchiveNorthGate->ComponentTags.Add(TEXT("ArchiveNorthGate"));
    Part(TEXT("ArchiveHighWindow"),FVector(1950,1798,450),FVector(90,4,60),FLinearColor(.008f,.016f,.03f),TEXT(""),false);
    for(int Bar=-1;Bar<=1;++Bar)
        Part(TEXT("ArchiveWindowLattice"),FVector(1950+Bar*24,1794,450),FVector(3,5,60),Timber,TEXT("Timber"),false);
    const FVector RimAt(1950,1745,450),RimLook(1750,1000,150);
    if(auto* Rim=GetWorld()->SpawnActor<ARectLight>(O+RimAt,(RimLook-RimAt).Rotation()))
    {
        Rim->SetMobility(EComponentMobility::Movable);
        auto* Light=Rim->RectLightComponent.Get();
        Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(650.f);
        Light->SetUseTemperature(true);Light->SetTemperature(10000.f);Light->SetAttenuationRadius(1900.f);
        Light->SetSourceWidth(90.f);Light->SetSourceHeight(60.f);Light->SetCastShadows(true);
        Light->SetBarnDoorAngle(35.f);Light->SetBarnDoorLength(80.f);
        Rim->Tags.Add(TEXT("ArchiveWindowRim"));DecorActors.Add(Rim);
    }

    // A physical connection across the current chapter layout. The long
    // landing is provisional architecture, not an authored final art claim.
    const double X=O.X+R::DoorX,Y=Zone.Rect.Max.Y,PX=Press.Rect.Min.X+300,PY=Press.Rect.Max.Y;
    const double WalkY=Y+R::WalkNorth;
    const auto RoutePart=[&](const TCHAR* Name,FVector At,FVector Size)
    {
        auto* P=Box(Name,At,Size,Timber,true,FRotator::ZeroRotator,TEXT("Timber"));
        P->ComponentTags.Add(TEXT("ArchivePressRoute"));return P;
    };
    RoutePart(TEXT("ArchiveDoorLanding"),FVector(X,Y+40,R::FloorCm-10),FVector(240,80,20));
    for(int I=0;I<R::Risers;++I)
    {
        const float Top=R::FloorCm-(I+1)*R::RiserCm;
        RoutePart(TEXT("ArchiveNorthStep"),FVector(X,Y+R::StairStart+(I+.5)*R::TreadCm,Top-10),FVector(200,R::TreadCm,20));
    }
    const double BottomY=Y+R::StairStart+R::Risers*R::TreadCm;
    RoutePart(TEXT("ArchiveStairFoot"),FVector(X,(BottomY+WalkY+100)/2,390),FVector(200,WalkY+100-BottomY,20));
    RoutePart(TEXT("ArchivePressWalk"),FVector((X+PX)/2,WalkY,390),FVector(PX-X+200,200,20));
    RoutePart(TEXT("ArchivePressLanding"),FVector(PX,(PY-120+WalkY+100)/2,390),FVector(200,WalkY+100-(PY-120),20));
    const auto Rail=[&](FVector2D A,FVector2D B,float Bottom,float Top)
    {
        RoutePart(TEXT("ArchiveWalkRail"),FVector((A+B)*.5,(Bottom+Top)*.5),
            FVector(FMath::Abs(B.X-A.X)+10,FMath::Abs(B.Y-A.Y)+10,Top-Bottom));
    };
    Rail({X-110,Y+80},{X-110,WalkY+100},400,R::FloorCm+R::GuardHeightCm);
    Rail({X+110,Y+80},{X+110,WalkY-100},400,R::FloorCm+R::GuardHeightCm);
    Rail({X-100,WalkY+110},{PX+100,WalkY+110},400,R::CatwalkCm+R::GuardHeightCm);
    Rail({X+100,WalkY-110},{PX-100,WalkY-110},400,R::CatwalkCm+R::GuardHeightCm);
    Rail({PX+110,PY+60},{PX+110,WalkY+100},400,R::CatwalkCm+R::GuardHeightCm);
    Rail({PX-110,PY+60},{PX-110,WalkY-100},400,R::CatwalkCm+R::GuardHeightCm);
}

void ASoraWorldBuilder::ShowArchivePage(const FSoraBeat& Beat,int32 Phase)
{
    // Derived from the existing phase/checkpoint, so retrying P1 hides it and
    // restoring P2 or entering the pledge lights the same physical slate.
    const bool InArchive=Beat.Id==TEXT("ch06.b09")||Beat.Id==TEXT("ch06.b10");
    if(IsValid(ArchiveExposure))
    {
        // This chapter builds several places together. Restore its ordinary
        // sun/sky and exposure when leaving the archive, including retry.
        ArchiveExposure->BlendWeight=InArchive?1.f:0.f;
        if(IsValid(RigSun)) RigSun->SetActorHiddenInGame(InArchive);
        if(IsValid(RigSky)) RigSky->SetActorHiddenInGame(InArchive);
    }
    const bool Lit=(Beat.Id==TEXT("ch06.b09")&&Phase>=1)||Beat.Id==TEXT("ch06.b10");
    if(IsValid(ArchiveNorthGate))
    {
        const bool Locked=Beat.Id==TEXT("ch06.b09");
        ArchiveNorthGate->SetVisibility(Locked);
        ArchiveNorthGate->SetCollisionEnabled(Locked?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
    }
    if(IsValid(ArchivePageText))
    {
        if(Lit&&!ArchivePageText->IsVisible()) ArchivePageText->RequestRedraw();
        ArchivePageText->SetVisibility(Lit);
    }
    if(IsValid(ArchivePageLight))
    {
        auto* Light=ArchivePageLight->RectLightComponent.Get();
        Light->SetIntensity(Lit?FamilyPageLumens:0.f); Light->SetVisibility(Lit);
    }
}

void ASoraWorldBuilder::StageArchiveReveal(float Seconds)
{
    const float Age=Seconds-SoraArchiveRules::ImpactSeconds;
    const float Shake=Age>=0&&Age<1.5f?FMath::Sin(Age*28.f)*1.4f*FMath::Exp(-Age*4.f):0.f;
    if(IsValid(ArchiveEastRack)) ArchiveEastRack->SetRelativeRotation(FRotator(0,0,Shake));
    // A negative time only resets the rack, leaving the phase-derived light.
    if(Seconds<0) return;
    const bool Lit=Age>=0;
    if(IsValid(ArchivePageText))
    {
        if(Lit&&!ArchivePageText->IsVisible()) ArchivePageText->RequestRedraw();
        ArchivePageText->SetVisibility(Lit);
    }
    if(IsValid(ArchivePageLight))
    {
        auto* Light=ArchivePageLight->RectLightComponent.Get();
        Light->SetIntensity(Lit?FamilyPageLumens:0.f);Light->SetVisibility(Lit);
    }
}
