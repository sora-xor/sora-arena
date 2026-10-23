#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraCampaignLift.h"
#include "SoraHorse.h"
#include "SoraPlayerCharacter.h"
#include "Animation/AnimationAsset.h"
#include "Camera/CameraComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/PointLight.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

// The active beat's task kit, built at its space's points as the beat starts
// and shown as the task goes on (FSoraKitView):
// - sluice: a winch drum and handle turn, the weir board lifts and the water
//   rises in the channel with every turn;
// - bellows: the tatara's mouth glows brighter as the bellows are worked;
// - lift: a wheel turns and a platform of goods rises with the turns;
// - hold: the hold boundary fills as it is held, red when contested;
// - stations: one bench per manufacturing station, the current step's in gold,
//   finished ones in teal, and the output stacking beside the anchor;
// - carry: the loads at each pickup (a pack horse, or a stack that empties)
//   and what each drop-off has received (a pack horse's load, or a depot);
// - defend: each target (pack horse, furnace, aid tent or villager) with a
//   banner that pales to red as it is worn down and falls when it is lost;
// - escort: the party (villagers, an ox cart) walking where the director
//   puts them.
// Loose collectibles lie in their zones as small period objects with a faint
// glow, and a carried load sits in the hero's arms.
namespace
{
const TCHAR* const KitCube = TEXT("/Engine/BasicShapes/Cube.Cube");
const TCHAR* const KitCylinder = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
const TCHAR* const KitSphere = TEXT("/Engine/BasicShapes/Sphere.Sphere");
const FLinearColor KitStraw(.72f,.6f,.33f), KitTimber(.36f,.23f,.12f), KitIron(.1f,.1f,.11f), KitWater(.05f,.2f,.34f);
const FLinearColor KitGold(.94f,.65f,.21f), KitTeal(.1f,.62f,.55f), KitDim(.16f,.14f,.12f), KitLost(.72f,.08f,.06f);
constexpr int32 KitStackVisible = 12;
FLinearColor KitItemColor(FName Item)
{
    return Item==TEXT("bale")?KitStraw:Item==TEXT("bundle")?FLinearColor(.5f,.42f,.3f):Item==TEXT("box")?FLinearColor(.2f,.04f,.03f):KitTimber;
}
}

UStaticMeshComponent* ASoraWorldBuilder::KitShape(const FString& Name,const TCHAR* Asset,FVector Location,FVector Scale,FLinearColor Color,
    const FString& SurfaceRole,bool Collision)
{
    auto* Mesh=Shape(this,RootComponent,FString::Printf(TEXT("Kit%s%d"),*Name,KitPieces.Num()),Asset,Location,Scale,Color,Collision);
    if(!SurfaceRole.IsEmpty()) Surface(Mesh,SurfaceRole,Color);
    KitPieces.Add(Mesh);
    return Mesh;
}
ASoraHorse* ASoraWorldBuilder::KitHorse(FVector Location,float Yaw,FName Coat,bool bPack)
{
    if(!GetWorld()) return nullptr;
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Horse=GetWorld()->SpawnActor<ASoraHorse>(Location,FRotator(0,Yaw,0),Params);
    if(!Horse) return nullptr;
    Horse->Build(Coat,bPack?ASoraHorse::ETack::Pack:ASoraHorse::ETack::Riding);
    Horse->Place(Location,Yaw);
    KitActors.Add(Horse);
    return Horse;
}
USceneComponent* ASoraWorldBuilder::KitMember(FName Kind,FVector Location,float Yaw)
{
    auto* Root=NewObject<USceneComponent>(this,MakeUniqueObjectName(this,USceneComponent::StaticClass(),TEXT("KitMember")));
    Root->SetupAttachment(RootComponent); Root->SetRelativeLocation(Location); Root->SetRelativeRotation(FRotator(0,Yaw,0));
    Root->RegisterComponent(); AddInstanceComponent(Root);
    KitParty.Add(Root);
    if(Kind==TEXT("cart"))
    {
        // 牛車: a two-wheeled ox-drawn freight cart with its load.
        auto* Bed=Shape(this,Root,TEXT("KitCartBed"),KitCube,FVector(0,0,95),FVector(2.4f,1.3f,.18f),KitTimber); Surface(Bed,TEXT("Timber"),KitTimber);
        auto* Load=Shape(this,Root,TEXT("KitCartLoad"),KitCube,FVector(-10,0,130),FVector(2.f,1.1f,.5f),FLinearColor(.5f,.36f,.2f));
        KitPieces.Add(Bed); KitPieces.Add(Load);
        for(int32 Side:{-1,1})
        {
            auto* Wheel=Shape(this,Root,TEXT("KitCartWheel"),KitCylinder,FVector(0,Side*78,70),FVector(1.4f,1.4f,.1f),KitTimber,false);
            Wheel->SetRelativeRotation(FRotator(0,0,90)); KitPieces.Add(Wheel);
        }
        auto* Ox=Shape(this,Root,TEXT("KitOx"),KitSphere,FVector(230,0,95),FVector(1.9f,.9f,1.f),FLinearColor(.2f,.15f,.1f)); KitPieces.Add(Ox);
        return Root;
    }
    // A villager: the samurai cat rig walking, else its static mesh.
    if(auto* Rig=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Generated/Meshes/SK_NyaagyuSamurai.SK_NyaagyuSamurai"),nullptr,LOAD_NoWarn))
    {
        auto* Walker=NewObject<USkeletalMeshComponent>(this,MakeUniqueObjectName(this,USkeletalMeshComponent::StaticClass(),TEXT("KitWalker")));
        Walker->SetSkeletalMesh(Rig); Walker->SetupAttachment(Root);
        Walker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Walker->RegisterComponent(); AddInstanceComponent(Walker);
        if(auto* Idle=LoadObject<UAnimationAsset>(nullptr,TEXT("/Game/Generated/Animations/A_NyaagyuSamurai_Idle.A_NyaagyuSamurai_Idle"),nullptr,LOAD_NoWarn))
            Walker->PlayAnimation(Idle,true);
        KitWalkers.Add(Walker);
        return Root;
    }
    auto* Figure=Shape(this,Root,TEXT("KitVillager"),KitSphere,FVector(0,0,70),FVector(.55f,.55f,1.4f),FLinearColor(.28f,.24f,.2f));
    KitPieces.Add(Figure);
    return Root;
}
void ASoraWorldBuilder::KitItem(FName Item,FVector Location,int32 Index,TArray<TObjectPtr<UStaticMeshComponent>>& Into)
{
    // Rice and barley in straw bales, crates of tools and goods, ration
    // bundles, and the lacquered public registry box.
    const FVector At=Location+FVector((Index%3-1)*48.f,((Index/3)%2)*52.f-26.f,(Index/6)*42.f);
    UStaticMeshComponent* Mesh=Item==TEXT("bale")
        ?KitShape(TEXT("Bale"),KitCylinder,At+FVector(0,0,24),FVector(.4f,.4f,.62f),KitStraw)
        :Item==TEXT("bundle")?KitShape(TEXT("Bundle"),KitSphere,At+FVector(0,0,20),FVector(.45f,.35f,.4f),KitItemColor(Item))
        :Item==TEXT("box")?KitShape(TEXT("RegistryBox"),KitCube,At+FVector(0,0,12),FVector(.38f,.28f,.22f),KitItemColor(Item))
        :KitShape(TEXT("Crate"),KitCube,At+FVector(0,0,20),FVector(.44f,.36f,.4f),KitTimber,TEXT("Timber"));
    if(Item==TEXT("bale")) Mesh->SetRelativeRotation(FRotator(90,0,0));
    Into.Add(Mesh);
}
ASoraCampaignLift* ASoraWorldBuilder::CampaignLift() const { return Lift; }
void ASoraWorldBuilder::StageKit(const FSoraChapter& Chapter,int32 BeatIndex)
{
    ClearKit();
    if(!Chapter.Beats.IsValidIndex(BeatIndex)) return;
    const FSoraBeat& Beat=Chapter.Beats[BeatIndex];
    const FSoraBeatSpace& Space=Beat.Space;
    BeatLight(Beat);   // the beat's authored sun and sky (SoraWorldBuilderLighting.cpp)
    StageEpilogue(Beat);
    StageSupply(Beat);
    StageHelm(Beat);
    StageGalleryPois(Chapter,Beat);
    bSummitActive=Space.Summit.Enabled();
    ResetSpireAlarm(Space.Spire.Enabled());
    ShowSummitSpine(false,Beat.Id==TEXT("ch08.b15")?1.f:0.f);
    SetActorTickEnabled(bSummitActive||bSpireActive);
    if(Space.Summit.Enabled()&&Beat.Is(SoraBeatRules::EType::Boss))
        KitShape(TEXT("SummitStairSeal"),KitCube,FVector(Space.Summit.Center,16000)+FVector(0,-1850,125),
            FVector(3.4,.16,2.5),KitTeal,TEXT("Metal"),true);
    if(Space.Spire.Enabled())
    {
        const FVector C(Space.Spire.Center,2700);
        KitShape(TEXT("ParkedSpireBridge"),KitCube,C-FVector(0,0,15),FVector(6,2,.3),KitIron,TEXT("Metal"),true);
        for(int32 Sign:{-1,1})
            KitShape(TEXT("ParkedSpireRail"),KitCube,C+FVector(0,Sign*90,75),FVector(6,.2,1.5),KitIron,TEXT("Metal"),true);
    }
    if(Beat.Task.CarryGateMs>0)
        CarrySeal=KitShape(TEXT("GranarySeal"),KitCube,Floor(Space.CarryGate)+FVector(0,70,75),
            FVector(.18f,.55f,.9f),KitTeal);
    if(RecoveryHatch)
    {
        const bool Open=Beat.Task.RecoveryWeapons!=0u;
        RecoveryHatch->SetVisibility(!Open);
        RecoveryHatch->SetCollisionEnabled(Open?ECollisionEnabled::NoCollision:ECollisionEnabled::QueryAndPhysics);
    }
    if(Beat.Task.RecoveryWeapons!=0u)
    {
        const FVector P=Floor(Space.Recovery,-Beat.Task.RecoveryDepthCm+12.f);
        RecoveryBundle.Add(KitShape(TEXT("SwordBundle"),KitCube,P+FVector(-65,65,5),FVector(1.1f,.35f,.2f),FLinearColor(.38f,.3f,.16f),TEXT("Timber")));
        RecoveryBundle.Add(KitShape(TEXT("BowBag"),KitCube,P+FVector(-65,95,4),FVector(2.2f,.16f,.12f),FLinearColor(.24f,.27f,.2f)));
    }
    KitWork=Space.Work;
    KitAnchor=Floor(Space.Anchor,Space.HeightCm);
    const FVector A=KitAnchor;
    if(Space.Lift.bEnabled)
    {
        Lift=GetWorld()->SpawnActor<ASoraCampaignLift>();
        if(Lift) { Lift->Build(Space.Anchor,Beat.Task.Count,Beat.Task.MinTurnMs); KitActors.Add(Lift); }
    }
    else if(KitWork==TEXT("sluice"))
    {
        // The weir's winch beside the anchor, and the channel it lets the water into.
        for(int32 Side:{-1,1}) KitShape(TEXT("WinchPost"),KitCube,A+FVector(0,Side*95,90),FVector(.2f,.2f,1.8f),KitTimber,TEXT("Timber"),true);
        KitWheel=KitShape(TEXT("WinchDrum"),KitCylinder,A+FVector(0,0,150),FVector(.36f,.36f,1.7f),KitTimber,TEXT("Timber"));
        KitWheel->SetRelativeRotation(FRotator(0,0,90));
        auto* Handle=Shape(this,KitWheel,TEXT("KitWinchHandle"),KitCube,FVector(0,0,48),FVector(2.2f,.08f,.06f),KitIron); KitPieces.Add(Handle);
        KitShape(TEXT("Channel"),KitCube,A+FVector(0,-330,20),FVector(5.2f,2.2f,.4f),FLinearColor(.24f,.25f,.24f),TEXT("Stone"));
        KitGauge=KitShape(TEXT("Water"),KitCube,A+FVector(0,-330,4),FVector(5.f,2.f,.04f),KitWater);
        KitFill=KitShape(TEXT("WeirBoard"),KitCube,A+FVector(0,-215,60),FVector(.18f,2.2f,1.2f),KitTimber,TEXT("Timber"));
    }
    else if(KitWork==TEXT("bellows"))
    {
        // Independent tread boards, not the later seesaw bellows. Functional
        // proxies: the bespoke foot/cloth animation remains an art deliverable.
        for(int32 Side:{-1,1})
            BellowsFeet.Add(KitShape(TEXT("Tread"),KitCube,A+FVector(Side*48,-40,15),FVector(.7f,1.3f,.16f),KitTimber,TEXT("Timber")));
        for(int32 N=0;N<3;++N)
        {
            auto* Notch=KitShape(TEXT("FlameNotch"),KitCube,A+FVector(-22+N*22,-254,126),FVector(.12f,.07f,.22f),KitGold);
            Notch->ComponentTags.Add(TEXT("BellowsFlameNotch")); BellowsNotches.Add(Notch);
        }
        for(int32 N=0;N<8;++N)
        {
            auto* Spark=KitShape(TEXT("FlameSpark"),KitCube,A+FVector(0,-253,95),FVector(.025f,.025f,.11f),FLinearColor(1.f,.9f,.6f));
            Spark->ComponentTags.Add(TEXT("BellowsFlameSpark")); Spark->SetVisibility(false); BellowsSparks.Add(Spark);
        }
        // The tatara's bellows and the furnace mouth they feed.
        KitShape(TEXT("Bellows"),KitCube,A+FVector(0,-150,60),FVector(1.6f,.9f,1.2f),KitTimber,TEXT("Timber"),true);
        KitShape(TEXT("Furnace"),KitCube,A+FVector(0,-360,110),FVector(1.9f,1.9f,2.2f),FLinearColor(.25f,.22f,.2f),TEXT("Stone"),true);
        KitGauge=KitShape(TEXT("FurnaceMouth"),KitCube,A+FVector(0,-262,80),FVector(.8f,.08f,.6f),FLinearColor(.2f,.05f,.02f));
        if(auto* Light=GetWorld()?GetWorld()->SpawnActor<APointLight>(A+FVector(0,-240,90),FRotator::ZeroRotator):nullptr)
        {
            auto* Glow=Light->PointLightComponent.Get();
            Glow->SetIntensityUnits(ELightUnits::Lumens); Glow->SetIntensity(0.f); Glow->SetAttenuationRadius(700.f);
            Glow->SetUseTemperature(true); Glow->SetTemperature(1800.f); Glow->SetCastShadows(false);
            KitLight=Light;
        }
    }
    else if(KitWork==TEXT("lift"))
    {
        // The override wheel or capstan, and the platform of goods it moves.
        KitWheel=KitShape(TEXT("Wheel"),KitCylinder,A+FVector(0,0,150),FVector(1.8f,1.8f,.16f),KitIron,TEXT("Metal"));
        KitWheel->SetRelativeRotation(FRotator(0,0,90));
        auto* Spoke=Shape(this,KitWheel,TEXT("KitWheelSpoke"),KitCube,FVector::ZeroVector,FVector(1.7f,.1f,.3f),KitGold); KitPieces.Add(Spoke);
        KitShape(TEXT("LiftShaft"),KitCube,A+FVector(0,-420,160),FVector(3.4f,3.4f,.1f),KitIron,TEXT("Metal"));
        KitGauge=KitShape(TEXT("LiftPlatform"),KitCube,A+FVector(0,-420,10),FVector(3.f,3.f,.2f),KitTimber,TEXT("Timber"));
        for(int32 Crate=0;Crate<3;++Crate)
        {
            auto* Goods=Shape(this,KitGauge,TEXT("KitLiftGoods"),KitCube,FVector((Crate-1)*.3f,0,1.8f),FVector(.3f,.3f,2.f),KitTimber);
            KitPieces.Add(Goods);
        }
    }
    else if(KitWork==TEXT("hold")&&Space.Helm.bEnabled)
    {
        KitAnchor=Floor(Space.Helm.Hold.Center,Space.HeightCm);
        KitHoldSize=Space.Helm.Hold.Size;
        auto* Floor=KitShape(TEXT("HelmHoldFloor"),KitCube,KitAnchor+FVector(0,0,1),
            FVector(KitHoldSize.X/100,KitHoldSize.Y/100,.01),FLinearColor(.05f,.12f,.12f));
        Floor->ComponentTags.Add(TEXT("HelmHoldFloor"));
        KitFill=KitShape(TEXT("HelmHoldFill"),KitCube,KitAnchor+FVector(0,0,2),FVector(.01,KitHoldSize.Y/100,.012),KitGold);
        KitFill->ComponentTags.Add(TEXT("HelmHoldFill"));
    }
    else if(KitWork==TEXT("hold"))
    {
        // The ground to hold: its edge posts, a dark ring and a fill that grows.
        KitHoldRadius=420.f;
        KitShape(TEXT("HoldRing"),KitCylinder,A+FVector(0,0,1),FVector(8.4f,8.4f,.01f),FLinearColor(.05f,.12f,.12f));
        KitFill=KitShape(TEXT("HoldFill"),KitCylinder,A+FVector(0,0,2),FVector(.01f,.01f,.012f),KitGold);
        for(int32 Post=0;Post<6;++Post)
        {
            const FVector Edge=A+FRotator(0,Post*60.f,0).Vector()*KitHoldRadius;
            KitShape(TEXT("HoldPost"),KitCylinder,Edge+FVector(0,0,60),FVector(.1f,.1f,1.2f),KitTimber,TEXT("Timber"));
        }
    }
    else if(KitWork==TEXT("stations"))
    {
        for(int32 Station=0;Station<Space.Stations.Num();++Station)
        {
            const FVector P=Floor(Space.Stations[Station]);
            KitShape(TEXT("Bench"),KitCube,P+FVector(0,0,40),FVector(1.2f,.8f,.8f),KitTimber,TEXT("Timber"),true);
            KitStations.Add(KitShape(TEXT("StationMark"),KitCube,P+FVector(0,0,84),FVector(.9f,.5f,.06f),KitDim));
        }
        StageWorkshop(Beat);
    }
    else if(KitWork==TEXT("carry"))
    {
        KitItemKind=Space.Item;
        const int32 Share=Beat.Task.Pickups>=Beat.Task.Count?1:Beat.Task.Count;
        for(int32 Point=0;Point<Space.Pickups.Num();++Point)
        {
            const FVector P=Floor(Space.Pickups[Point]);
            if(Space.PickupKinds[Point]==TEXT("horse")) KitHorse(P+FVector(0,-160,0),0.f,TEXT("bay"),true);
            // A store holds the whole load; distinct pickups hold one each.
            for(int32 Item=0;Item<FMath::Min(Share,KitStackVisible);++Item) KitItem(Space.Item,P,Item,KitLoads);
        }
        for(int32 Point=0;Point<Space.Dropoffs.Num();++Point)
        {
            const FVector P=Floor(Space.Dropoffs[Point]);
            if(Space.DropoffKinds[Point]==TEXT("horse")) KitHorse(P+FVector(0,-160,0),0.f,TEXT("bay"),true);
            else KitShape(TEXT("Depot"),KitCube,P+FVector(0,0,8),FVector(1.8f,1.4f,.16f),KitTimber,TEXT("Timber"));
            KitDropoffs.Add(P+FVector(0,0,16));
            KitDeliveredShown.Add(0);
        }
    }
    else if(KitWork==TEXT("defend"))
    {
        BuildFoundryDefense(Space);
        for(int32 Target=0;Target<Space.Targets.Num();++Target)
        {
            const FVector P=Floor(Space.Targets[Target]);
            const FName Kind=Space.TargetKinds[Target];
            if(Kind==TEXT("horse")) KitHorse(P,90.f,TEXT("bay"),true);
            else if(Kind==TEXT("furnace"))
            {
                if(!Space.FoundryDefense.bEnabled) KitShape(TEXT("TargetFurnace"),KitCube,P+FVector(0,0,110),FVector(1.8f,1.8f,2.2f),FLinearColor(.25f,.22f,.2f),TEXT("Stone"),true);
                KitShape(TEXT("TargetFurnaceMouth"),KitCube,P+FVector(-92,0,70),FVector(.08f,.7f,.5f),FLinearColor(.9f,.35f,.08f));
            }
            else if(Kind==TEXT("tent"))
            {
                KitShape(TEXT("AidTent"),KitCube,P+FVector(0,0,110),FVector(2.6f,2.2f,.08f),FLinearColor(.78f,.74f,.64f));
                for(int32 Corner=0;Corner<4;++Corner)
                    KitShape(TEXT("AidPole"),KitCylinder,P+FVector(Corner%2?120:-120,Corner/2?100:-100,55),FVector(.06f,.06f,1.1f),KitTimber);
            }
            // A defended person is the beat's fieldcraft's own character (USoraFieldcraft).
            else if(Kind!=TEXT("person")) KitMember(TEXT("villager"),P,Target*45.f);
            // A banner beside each target pales to red as it is worn down.
            KitShape(TEXT("TargetPole"),KitCylinder,P+FVector(0,140,110),FVector(.05f,.05f,2.2f),KitTimber);
            KitTargets.Add(KitShape(TEXT("TargetBanner"),KitCube,P+FVector(0,165,190),FVector(.02f,.45f,.7f),KitTeal));
        }
    }
    else if(KitWork==TEXT("escort"))
    {
        for(int32 Member=0;Member<Space.Party.Num();++Member) KitMember(Space.Party[Member],Floor(Space.Entry),Space.EntryYaw);
    }
}
void ASoraWorldBuilder::ShowKit(const FSoraKitView& View)
{
    const float Progress=FMath::Clamp(View.ProgressPermille/1000.f,0.f,1.f);
    if(KitWork==TEXT("sluice")&&KitGauge&&KitFill&&KitWheel)
    {
        // Each turn winds the drum; the board lifts and the water rises with the turns.
        KitWheel->SetRelativeRotation(FRotator(Progress*360.f*6.f,0,90));
        KitFill->SetRelativeLocation(KitAnchor+FVector(0,-215,60.f+110.f*Progress));
        KitGauge->SetRelativeLocation(KitAnchor+FVector(0,-330,4.f+32.f*Progress));
        KitGauge->SetRelativeScale3D(FVector(5.f,2.f,.04f+.1f*Progress));
    }
    else if(KitWork==TEXT("bellows")&&KitGauge)
    {
        const int32 Band=FMath::Clamp(View.BellowsNotches,1,3);
        if(BellowsShownBand!=Band)
        {
            BellowsShownBand=Band;
            Tint(KitGauge,Band==1?FLinearColor(.24f,.025f,.012f):Band==2?FLinearColor(1.f,.62f,.03f):FLinearColor::White);
            for(int32 N=0;N<BellowsNotches.Num();++N) BellowsNotches[N]->SetVisibility(N<Band);
            if(auto* Light=Cast<APointLight>(KitLight.Get()))
            {
                Light->PointLightComponent->SetIntensity(Band==1?350.f:Band==2?2600.f:4000.f);
                Light->PointLightComponent->SetTemperature(Band==1?1500.f:Band==2?2600.f:6500.f);
            }
        }
        for(int32 N=0;N<BellowsFeet.Num();++N)
            BellowsFeet[N]->SetRelativeRotation(FRotator(View.BellowsFoot==(N==0?-1:1)?-8.f:0.f,0,0));
        // Fixed pool: no spawned actors or new materials in the per-frame path.
        for(int32 N=0;N<BellowsSparks.Num();++N)
        {
            BellowsSparks[N]->SetVisibility(Band==3);
            const float Phase=FMath::Fmod(GetWorld()->GetTimeSeconds()*1.8f+N*.137f,1.f);
            BellowsSparks[N]->SetRelativeLocation(KitAnchor+FVector((N%2?1:-1)*(8.f+Phase*(12.f+N*2)), -252.f,90.f+Phase*75.f));
        }
    }
    else if(KitWork==TEXT("lift")&&KitGauge&&KitWheel)
    {
        KitWheel->SetRelativeRotation(FRotator(Progress*360.f*8.f,0,90));
        KitGauge->SetRelativeLocation(KitAnchor+FVector(0,-420,10.f+300.f*Progress));
    }
    else if(KitWork==TEXT("hold")&&KitFill)
    {
        if(KitHoldSize.X>0)
        {
            KitFill->SetVisibility(Progress>0);
            if(Progress>0)
            {
                const float Width=KitHoldSize.X*Progress;
                KitFill->SetRelativeLocation(KitAnchor+FVector((Width-KitHoldSize.X)*.5,0,2));
                KitFill->SetRelativeScale3D(FVector(Width/100,KitHoldSize.Y/100,.012f));
            }
        }
        else
        {
            const float Radius=KitHoldRadius/50.f*FMath::Max(Progress,.01f);
            KitFill->SetRelativeScale3D(FVector(Radius,Radius,.012f));
        }
        Tint(KitFill,View.bContested?KitLost:Progress>=1.f?KitTeal:KitGold);
    }
    else if(KitWork==TEXT("stations"))
    {
        ShowWorkshop(View);
        for(int32 Station=0;Station<KitStations.Num();++Station)
            if(KitStations[Station]) Tint(KitStations[Station],Station<View.Step?KitTeal:Station==View.Step?KitGold:KitDim);
        // The output stacks beside the anchor, a piece for every stroke.
        const int32 Wanted=FMath::Min(View.Strokes,KitStackVisible);
        while(KitStacks.Num()<Wanted) KitItem(TEXT("crate"),KitAnchor+FVector(0,190,0),KitStacks.Num(),KitStacks);
    }
    else if(KitWork==TEXT("carry"))
    {
        if(CarrySeal) CarrySeal->SetVisibility(!View.bCarryGateOpen);
        for(int32 Slot=0;Slot<View.LooseLoads.Num();++Slot)
        {
            const bool Visible=(View.LooseMask&(1u<<Slot))!=0u;
            if(Visible)
                while(KitLooseLoads.Num()<=Slot)
                {
                    KitItem(KitItemKind,FVector::ZeroVector,0,KitLooseLoads);
                    KitLooseLoads.Last()->SetVisibility(false);
                }
            if(KitLooseLoads.IsValidIndex(Slot)&&KitLooseLoads[Slot])
            {
                KitLooseLoads[Slot]->SetVisibility(Visible);
                KitLooseLoads[Slot]->SetRelativeLocation(View.LooseLoads[Slot]+FVector(0,0,KitItemKind==TEXT("box")?12.f:KitItemKind==TEXT("bale")?24.f:20.f));
            }
        }
        // Loads leave their pickups as they are taken; drop-offs fill as they receive them.
        for(int32 Item=0;Item<KitLoads.Num();++Item)
            if(KitLoads[Item]) KitLoads[Item]->SetVisibility(!View.PickupTaken.IsValidIndex(Item)||!View.PickupTaken[Item]);
        for(int32 Point=0;Point<KitDropoffs.Num()&&Point<View.Delivered.Num();++Point)
            for(;KitDeliveredShown[Point]<FMath::Min(View.Delivered[Point],KitStackVisible);++KitDeliveredShown[Point])
                KitItem(KitItemKind,KitDropoffs[Point],KitDeliveredShown[Point],KitStacks);
    }
    else if(KitWork==TEXT("defend"))
    {
        for(int32 Target=0;Target<KitTargets.Num()&&Target<View.TargetHealth.Num();++Target)
        {
            const float Health=View.TargetHealth[Target];
            if(!KitTargets[Target]) continue;
            KitTargets[Target]->SetVisibility(Health>0.f);
            Tint(KitTargets[Target],FMath::Lerp(KitLost,KitTeal,Health));
        }
    }
    else if(KitWork==TEXT("escort"))
    {
        for(int32 Member=0;Member<KitParty.Num()&&Member<View.Party.Num();++Member)
            if(KitParty[Member])
            {
                KitParty[Member]->SetRelativeLocation(View.Party[Member]);
                KitParty[Member]->SetRelativeRotation(FRotator(0,View.PartyYaw,0));
            }
        static const TCHAR* const Walk=TEXT("/Game/Generated/Animations/A_NyaagyuSamurai_Walk.A_NyaagyuSamurai_Walk");
        static const TCHAR* const Idle=TEXT("/Game/Generated/Animations/A_NyaagyuSamurai_Idle.A_NyaagyuSamurai_Idle");
        for(const auto& Walker:KitWalkers)
            if(Walker&&Walker->ComponentHasTag(TEXT("Walking"))!=View.bPartyWalking)
                if(auto* Animation=LoadObject<UAnimationAsset>(nullptr,View.bPartyWalking?Walk:Idle,nullptr,LOAD_NoWarn))
                {
                    Walker->PlayAnimation(Animation,true);
                    if(View.bPartyWalking) Walker->ComponentTags.AddUnique(TEXT("Walking"));
                    else Walker->ComponentTags.Remove(TEXT("Walking"));
                }
    }
}
float ASoraWorldBuilder::KitGaugeHeight() const
{
    return Lift?Lift->Height():KitGauge?KitGauge->GetRelativeLocation().Z:0.f;
}
void ASoraWorldBuilder::ShowRecoveryBundle(bool Visible)
{
    for(const auto& Piece:RecoveryBundle) if(Piece) Piece->SetVisibility(Visible);
}
void ASoraWorldBuilder::ClearKit()
{
    FoundryActor.Reset(); FoundryTubs.Reset(); FoundryBellows.Reset(); FoundryUsedShown=~0u;
    SetActorTickEnabled(false);
    ResetSpireAlarm(false);
    SupplyCrate=nullptr; SupplyId.Reset();
    GalleryTargets.Reset(); GalleryIds.Reset(); GalleryFloors.Reset(); GalleryLabel=nullptr; GalleryMon=nullptr;
    bSummitActive=false; ResetSeizure();
    for(const auto& Label:EpilogueLabels) if(Label) Label->DestroyComponent();
    EpilogueLabels.Reset();
    for(const auto& Mesh:KitPieces) if(Mesh) Mesh->DestroyComponent();
    for(const auto& Walker:KitWalkers) if(Walker) Walker->DestroyComponent();
    for(const auto& Member:KitParty) if(Member) Member->DestroyComponent();
    for(const auto& Actor:KitActors) if(Actor) Actor->Destroy();
    if(KitLight) KitLight->Destroy();
    ToranosukePlaque=nullptr; NyaakotoPlaque=nullptr; WashioSword.Reset(); EpiloguePlaques=0; bEpilogueSwordReturned=false;
    RecoveryBundle.Reset(); KitPieces.Reset(); KitWalkers.Reset(); KitParty.Reset(); KitActors.Reset(); KitStations.Reset(); KitTargets.Reset();
    KitStacks.Reset(); KitLoads.Reset(); KitDropoffs.Reset(); KitDeliveredShown.Reset(); KitItemKind=NAME_None;
    KitLooseLoads.Reset(); CarrySeal=nullptr;
    BellowsNotches.Reset(); BellowsSparks.Reset(); BellowsFeet.Reset(); BellowsShownBand=0;
    WorkshopParts.Reset(); WorkshopRing.Reset(); WorkshopStep=-1; bWorkshopHammer=false;
    HelmWheel=nullptr; HelmNeedle=nullptr;
    KitGauge=nullptr; KitWheel=nullptr; KitFill=nullptr; KitLight=nullptr; Lift=nullptr;
    KitWork=NAME_None; KitHoldRadius=0.f;
    KitHoldSize=FVector2D::ZeroVector;
}
void ASoraWorldBuilder::ShowPickups(const FSoraChapter& Chapter,const TArray<int32>& Loose)
{
    for(const auto& Mesh:PickupPieces) if(Mesh) Mesh->DestroyComponent();
    for(const auto& Light:PickupLights) if(Light) Light->Destroy();
    PickupPieces.Reset(); PickupLights.Reset();
    for(const int32 Index:Loose)
    {
        if(!Chapter.Space.Pickups.IsValidIndex(Index)) continue;
        const FSoraPickup& Pickup=Chapter.Space.Pickups[Index];
        const FString& Category=Chapter.Collectibles[Pickup.Collectible].Category;
        const FVector P=Floor(Pickup.At);
        auto Add=[&](const TCHAR* Asset,FVector Offset,FVector Scale,FLinearColor Color)
        {
            auto* Mesh=Shape(this,RootComponent,FString::Printf(TEXT("Pickup%d"),Index),Asset,P+Offset,Scale,Color);
            Mesh->SetCastShadow(false);
            PickupPieces.Add(Mesh);
            return Mesh;
        };
        // A scroll on a low stand, a seizure notice with its seal, a stone
        // marked with the sky mon, a lacquered heirloom box, or a registry book.
        if(Category==TEXT("scroll_fragment"))
        {
            Add(KitCube,FVector(0,0,20),FVector(.5f,.4f,.4f),KitTimber);
            Add(KitCylinder,FVector(0,0,46),FVector(.08f,.08f,.42f),FLinearColor(.9f,.86f,.74f))->SetRelativeRotation(FRotator(0,0,90));
        }
        else if(Category==TEXT("seizure_notice"))
        {
            Add(KitCube,FVector(0,0,60),FVector(.05f,.5f,.7f),FLinearColor(.86f,.82f,.72f));
            Add(KitCylinder,FVector(-4,0,70),FVector(.12f,.12f,.01f),FLinearColor(.1f,.7f,.75f))->SetRelativeRotation(FRotator(0,0,90));
        }
        else if(Category==TEXT("league_mark"))
        {
            Add(KitSphere,FVector(0,0,30),FVector(.9f,.8f,.6f),FLinearColor(.35f,.35f,.33f));
            Add(KitCylinder,FVector(-40,0,40),FVector(.3f,.3f,.01f),KitTeal)->SetRelativeRotation(FRotator(0,0,90));
        }
        else if(Category==TEXT("heirloom"))
            Add(KitCube,FVector(0,0,15),FVector(.36f,.28f,.3f),FLinearColor(.18f,.03f,.02f));
        else
            Add(KitCube,FVector(0,0,8),FVector(.3f,.22f,.12f),FLinearColor(.55f,.48f,.34f));
        if(auto* Light=GetWorld()?GetWorld()->SpawnActor<APointLight>(P+FVector(0,0,90),FRotator::ZeroRotator):nullptr)
        {
            auto* Glow=Light->PointLightComponent.Get();
            Glow->SetIntensityUnits(ELightUnits::Lumens); Glow->SetIntensity(140.f); Glow->SetAttenuationRadius(260.f);
            Glow->SetUseTemperature(true); Glow->SetTemperature(2600.f); Glow->SetCastShadows(false);
            PickupLights.Add(Light);
        }
    }
}
void ASoraWorldBuilder::ShowCarried(ASoraPlayerCharacter* Hero,FName Item)
{
    if(CarriedLoad) { CarriedLoad->DestroyComponent(); CarriedLoad=nullptr; }
    if(!Hero||Item.IsNone()||!Hero->GetCamera()) return;
    // The load sits low in both arms, in view of the hero's own eye.
    const TCHAR* Asset=Item==TEXT("bale")?KitCylinder:Item==TEXT("bundle")?KitSphere:KitCube;
    const FVector Scale=Item==TEXT("bale")?FVector(.34f,.34f,.55f):Item==TEXT("box")?FVector(.3f,.22f,.16f):FVector(.46f,.36f,.34f);
    CarriedLoad=Shape(Hero,Hero->GetCamera(),TEXT("CarriedLoad"),Asset,FVector(60,0,-42),Scale,KitItemColor(Item));
    if(Item==TEXT("bale")) CarriedLoad->SetRelativeRotation(FRotator(0,0,90));
    CarriedLoad->SetCastShadow(false);
}
int32 ASoraWorldBuilder::LooseLoadVisualCount() const
{
    int32 Count=0;
    for(const auto& Load:KitLooseLoads) if(Load&&Load->IsVisible()) ++Count;
    return Count;
}
