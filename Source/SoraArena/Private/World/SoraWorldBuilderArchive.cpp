#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraArchiveRules.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/WidgetComponent.h"
#include "Engine/Font.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Engine/World.h"
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
    const FLinearColor Cyan(.30f,.82f,.88f),Muted(.22f,.50f,.54f);
    auto Rows=SNew(SVerticalBox);
    Rows->AddSlot().AutoHeight().Padding(0,0,0,8)
        [SNew(STextBlock).Text(FText::FromString(TEXT("武家方記録"))).Font(Face(24)).ColorAndOpacity(Muted)];
    Rows->AddSlot().AutoHeight().Padding(0,0,0,30)
        [SNew(STextBlock).Text(FText::FromString(TEXT("鷲尾家"))).Font(Face(58)).ColorAndOpacity(Cyan)];
    const auto Row=[&](const TCHAR* Label,const TCHAR* Value,int32 Size,float Bottom)
    {
        Rows->AddSlot().AutoHeight().Padding(0,0,0,Bottom)
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(Label)).Font(Face(Size)).ColorAndOpacity(Cyan)]
            +SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text(FText::FromString(Value)).Font(Face(Size)).ColorAndOpacity(Cyan)]];
    };
    Row(TEXT("元本"),TEXT("120"),36,8);
    Row(TEXT("利息"),TEXT("22"),36,8);
    Row(TEXT("延滞金"),TEXT("36"),36,8);
    Row(TEXT("手数料"),TEXT("52"),36,8);
    Row(TEXT("返済"),TEXT("△40"),36,24);
    Row(TEXT("残高"),TEXT("190"),60,18);
    Row(TEXT("買取価格"),TEXT("30"),36,10);
    Rows->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("単位：石"))).Font(Face(22)).ColorAndOpacity(Muted)];
    return SNew(SBorder).Padding(40).BorderBackgroundColor(FLinearColor(.004f,.012f,.016f,1.f))[Rows];
}
constexpr float FamilyPageLumens=45.f;
}

void ASoraWorldBuilder::BuildArchive(const FSoraZone& Zone,const FSoraZone& Press)
{
    namespace R=SoraArchiveRules;
    const FVector O(Zone.Rect.Min,R::FloorCm);
    const FLinearColor Timber(.28f,.20f,.12f),Plaster(.43f,.41f,.35f),Slate(.09f,.14f,.16f);
    const auto Part=[&](const TCHAR* Name,FVector At,FVector Size,FLinearColor Color,const TCHAR* Role,bool Solid=true)
    { return Box(Name,O+At,Size,Color,Solid,FRotator::ZeroRotator,Role); };
    Part(TEXT("ArchiveBoardFloor"),FVector(1300,900,-40),FVector(2760,1960,80),Timber,TEXT("Timber"));
    Part(TEXT("ArchiveRoof"),FVector(1300,900,620),FVector(2760,1960,40),Timber,TEXT("Timber"));
    for(const FSoraBox& Wall:Zone.Walls)
        Box(TEXT("ArchiveWall"),FVector(Wall.Center,R::FloorCm+Wall.Height*.5f),FVector(Wall.Size,Wall.Height),Plaster,true,FRotator::ZeroRotator,TEXT("Stone"));
    for(int I=0;I<Zone.Cover.Num();++I)
    {
        const auto& Post=Zone.Cover[I];
        auto* P=Box(FString::Printf(TEXT("ArchiveDuelPost%d"),I),FVector(Post.Center,R::FloorCm+Post.Height*.5f),
            FVector(Post.Size,Post.Height),Timber,true,FRotator::ZeroRotator,TEXT("Timber"));
        P->ComponentTags.Add(TEXT("ArchiveDuelPost"));
    }
    // Physical racks occupy the authored 1.2 m strips; the four duel posts
    // alone occupy the ring. These are collision proxies pending final art.
    for(int Side:{0,1})
    {
        auto* Rack=Part(TEXT("ArchiveSlateRack"),FVector(Side?2540:60,900,180),FVector(120,1800,360),Slate,TEXT(""));
        if(Side) { ArchiveEastRack=Rack; Rack->ComponentTags.Add(TEXT("ArchiveEastRack")); }
        // The racks supply the authored ambient cyan light before the
        // family page wakes. Lights sit above the duel's heads, not inside
        // the staged rival's head as the old page point light did.
        for(float Y:{250.f,900.f,1550.f})
        {
            const float X=Side?2425.f:175.f;
            Part(TEXT("ArchiveRackLamp"),FVector(Side?2477:123,Y,300),FVector(4,75,30),FLinearColor(.06f,.24f,.27f),TEXT(""),false);
            if(auto* Lamp=GetWorld()->SpawnActor<APointLight>(O+FVector(X,Y,300),FRotator::ZeroRotator))
            {
                auto* Light=Lamp->PointLightComponent.Get();
                Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(450.f);
                Light->SetLightColor(FLinearColor(.25f,.66f,.78f));Light->SetAttenuationRadius(1100.f);
                Light->SetSourceRadius(45.f);Light->SetCastShadows(false);
                Lamp->Tags.Add(TEXT("ArchiveRackLight"));DecorActors.Add(Lamp);
            }
        }
    }
    ArchivePage=Part(TEXT("ArchiveWashioSlate"),FVector(2477,900,150),FVector(4,75,100),FLinearColor(.015f,.025f,.03f),TEXT(""),false);
    ArchivePage->ComponentTags.Add(TEXT("ArchiveFamilyPage"));
    ArchivePageFont=SoraUI::CreateUIFont(this);
    ArchivePageText=NewObject<UWidgetComponent>(this);
    ArchivePageText->SetupAttachment(RootComponent);
    ArchivePageText->SetWidgetSpace(EWidgetSpace::World);
    ArchivePageText->SetDrawSize(FVector2D(750,1000));ArchivePageText->SetPivot(FVector2D(.5f,.5f));
    ArchivePageText->SetBlendMode(EWidgetBlendMode::Opaque);
    ArchivePageText->SetBackgroundColor(FLinearColor(.004f,.012f,.016f,1.f));
    ArchivePageText->SetTintColorAndOpacity(FLinearColor(.65f,.65f,.65f,1.f));
    ArchivePageText->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    ArchivePageText->SetCanEverAffectNavigation(false);
    ArchivePageText->SetRelativeLocation(O+FVector(2474,900,150));
    ArchivePageText->SetRelativeRotation(FRotator(0,180,0));ArchivePageText->SetRelativeScale3D(FVector(.1f));
    ArchivePageText->SetSlateWidget(FamilyRecord(ArchivePageFont));
    ArchivePageText->SetVisibility(false);ArchivePageText->SetRedrawTime(1.f);
    ArchivePageText->RegisterComponent();AddInstanceComponent(ArchivePageText);
    ArchivePageText->ComponentTags.Add(TEXT("ArchiveFamilyRecord"));
    ArchivePageLight=GetWorld()->SpawnActor<APointLight>(O+FVector(2415,855,205),FRotator::ZeroRotator);
    if(ArchivePageLight)
    {
        ArchivePageLight->Tags.Add(TEXT("ArchiveFamilyPageLight"));
        auto* Light=ArchivePageLight->PointLightComponent.Get();
        Light->SetIntensityUnits(ELightUnits::Lumens);
        Light->SetIntensity(0.f); Light->SetVisibility(false);
        Light->SetLightColor(FLinearColor(.18f,.85f,1.f));
        Light->SetAttenuationRadius(700.f); Light->SetSourceRadius(15.f);
        Light->SetCastShadows(false);
        DecorActors.Add(ArchivePageLight);
    }
    Part(TEXT("ArchiveSouthDoor"),FVector(1300,-1,130),FVector(200,4,260),Timber,TEXT("Timber"),false);
    Part(TEXT("ArchiveNorthLintel"),FVector(1300,1830,430),FVector(240,60,340),Plaster,TEXT("Stone"));
    ArchiveNorthGate=Part(TEXT("ArchiveNorthDoor"),FVector(1300,1830,130),FVector(240,20,260),Timber,TEXT("Timber"));
    ArchiveNorthGate->ComponentTags.Add(TEXT("ArchiveNorthGate"));
    Part(TEXT("ArchiveHighWindow"),FVector(2100,1798,470),FVector(160,4,110),FLinearColor(.015f,.02f,.025f),TEXT("Timber"),false);
    const FVector RimAt(2100,1750,470),RimLook(1400,900,130);
    if(auto* Rim=GetWorld()->SpawnActor<ASpotLight>(O+RimAt,(RimLook-RimAt).Rotation()))
    {
        auto* Light=Rim->SpotLightComponent.Get();
        Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(240.f);
        Light->SetLightColor(FLinearColor(.56f,.67f,.82f));Light->SetAttenuationRadius(1900.f);
        Light->SetInnerConeAngle(20.f);Light->SetOuterConeAngle(50.f);Light->SetCastShadows(true);
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
        auto* Light=ArchivePageLight->PointLightComponent.Get();
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
        auto* Light=ArchivePageLight->PointLightComponent.Get();
        Light->SetIntensity(Lit?FamilyPageLumens:0.f);Light->SetVisibility(Lit);
    }
}
