#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraGalleryRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeActors.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraWorldBuilder::StageGalleryPois(const FSoraChapter& Chapter,const FSoraBeat& Beat)
{
    if(!Beat.Space.Lift.bEnabled) return;
    const auto* Gallery=Chapter.Beats.FindByPredicate([](const FSoraBeat& B) { return B.Id==TEXT("ch08.b12"); });
    if(!Gallery) return;
    const FName Ids[]={TEXT("poi_child_toy"),TEXT("poi_covered_mon")};
    const TCHAR* Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
    const FVector Origin=Floor(Gallery->Space.Anchor,Gallery->Space.HeightCm);
    for(int32 Index=0;Index<SoraGalleryRules::Count;++Index)
    {
        if(!Gallery->Pois.ContainsByPredicate([&](const FSoraExplorePoi& P) { return P.Id==Ids[Index].ToString(); })) continue;
        const FVector At=Origin+FVector(SoraGalleryRules::OffsetX,SoraGalleryRules::OffsetY[Index],0);
        GalleryIds.Add(Ids[Index]); GalleryFloors.Add(At);
        KitShape(TEXT("GalleryPlinth"),Cube,At+FVector(0,0,35),FVector(1.2,1.5,.7),
            FLinearColor(.055,.06,.065),TEXT("Metal"),true);
        // Functional proxies only. The paper toy, tailored jinbaori and the
        // seizure-label tearing animation still need the authored art pass.
        if(Index==SoraGalleryRules::Toy)
        {
            GalleryTargets.Add(KitShape(TEXT("GalleryPaperToy"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),
                At+FVector(0,0,100),FVector(.5,.6,.6),FLinearColor(.8,.58,.34),FString(),true));
            KitShape(TEXT("ToyValuationLabel"),Cube,At+FVector(-36,0,80),FVector(.025,.4,.18),FLinearColor(.5,.6,.62));
        }
        else
        {
            GalleryTargets.Add(KitShape(TEXT("GalleryJinbaori"),Cube,At+FVector(0,0,145),
                FVector(.1,1.4,1.5),FLinearColor(.19,.13,.085),FString(),true));
            // Reuse the pinned SVG's unchanged mon mesh and its red material;
            // never draw an approximation on an alien display.
            GalleryMon=SoraPracticeArt::Part(this,RootComponent,TEXT("GalleryNyaagyuMon"),
                SoraPracticeArt::SoraMon,At+FVector(-7,0,160),FVector(1,.5,.5),FRotator(0,180,0));
            KitPieces.Add(GalleryMon);
            GalleryLabel=KitShape(TEXT("GallerySeizureLabel"),Cube,At+FVector(-12,0,160),
                FVector(.06,.64,.64),FLinearColor(.06,.32,.36),FString(),true);
            GalleryLabel->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            GalleryLabel->SetCanEverAffectNavigation(false);
            GalleryLabel->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
        }
        if(auto* Light=GetWorld()->SpawnActor<APointLight>(At+FVector(-100,0,240),FRotator::ZeroRotator))
        {
            auto* Glow=Light->PointLightComponent.Get();
            Glow->SetIntensityUnits(ELightUnits::Lumens); Glow->SetIntensity(260.f);
            Glow->SetAttenuationRadius(420.f); Glow->SetUseTemperature(true);
            Glow->SetTemperature(3800.f); Glow->SetCastShadows(false);
            KitActors.Add(Light);
        }
    }
    ShowGalleryPois(0);
}

bool ASoraWorldBuilder::GalleryPoiFloor(FName Id,FVector& Out) const
{
    const int32 Index=GalleryIds.Find(Id);
    if(!GalleryFloors.IsValidIndex(Index)||!GalleryTargets.IsValidIndex(Index)||!IsValid(GalleryTargets[Index])) return false;
    Out=GalleryFloors[Index];
    return true;
}
bool ASoraWorldBuilder::CanReachGalleryPoi(FName Id,const ASoraPlayerCharacter& Hero) const
{
    FVector At;
    if(!GalleryPoiFloor(Id,At)||!Hero.GetCharacterMovement()->IsMovingOnGround()) return false;
    const float Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet-At.Z)>SoraGalleryRules::FloorToleranceCm||
        FVector::Dist2D(Hero.GetActorLocation(),At)>SoraGalleryRules::ReachCm) return false;
    const int32 Index=GalleryIds.Find(Id);
    auto* Target=GalleryTargets[Index].Get();
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraGalleryReach),false,&Hero);
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Hero.GetCamera()->GetComponentLocation(),
        Target->GetComponentLocation(),ECC_Visibility,Query)) return false;
    return Hit.GetComponent()==Target||(Id==TEXT("poi_covered_mon")&&Hit.GetComponent()==GalleryLabel);
}
void ASoraWorldBuilder::ShowGalleryPois(int32 FoundMask)
{
    const bool Torn=(FoundMask&SoraGalleryRules::Bit(SoraGalleryRules::Mon))!=0;
    if(GalleryMon) GalleryMon->SetVisibility(Torn);
    if(GalleryLabel)
    {
        GalleryLabel->SetVisibility(!Torn);
        GalleryLabel->SetCollisionEnabled(Torn?ECollisionEnabled::NoCollision:ECollisionEnabled::QueryOnly);
    }
}
bool ASoraWorldBuilder::GalleryLabelVisible() const { return GalleryLabel&&GalleryLabel->IsVisible(); }
bool ASoraWorldBuilder::GalleryMonVisible() const { return GalleryMon&&GalleryMon->IsVisible(); }
