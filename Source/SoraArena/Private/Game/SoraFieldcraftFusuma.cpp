#include "SoraFieldcraft.h"
#include "SoraPlayerCharacter.h"
#include "Combat/SoraStealth.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Game/SoraCampaignReach.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"

void USoraFieldcraft::StageFusuma(const FSoraBeat& Beat)
{
    if(Beat.Id!=TEXT("ch06.b06")||!Beat.Space.LedgerHall.bEnabled) return;
    const FVector Origin(Beat.Space.LedgerHall.PalaceOrigin,0);
    // Panels run just inside the room, parallel to the existing partition.
    // A 264 cm travel parks the entire 260 cm leaf beside its opening;
    // neither the wall nor the 270 cm corridor is widened.
    const FVector Centers[]={{250,-294,120},{1186,-670,120},{2150,-294,120}};
    const FVector Travel[]={{264,0,0},{0,264,0},{-264,0,0}};
    for(int I=0;I<3;++I)
    {
        FFusuma& Door=Fusuma.AddDefaulted_GetRef();
        Door.Closed=Origin+Centers[I];Door.Travel=Travel[I];
        auto* Panel=Piece(TEXT("PalaceFusuma"),SoraFieldcraftLayout::Cube,Door.Closed,
            I==1?FVector(.08f,2.6f,2.4f):FVector(2.6f,.08f,2.4f),FLinearColor(.58f,.53f,.42f),true);
        Panel->SetMobility(EComponentMobility::Movable);
        Panel->ComponentTags.Add(TEXT("PalaceFusuma"));
        Panel->ComponentTags.Add(FName(*FString::Printf(TEXT("PalaceFusuma%d"),I)));
        Door.Panel=Panel;
    }
}

int32 USoraFieldcraft::FusumaAt(const ASoraPlayerCharacter& Player) const
{
    const float Feet=Player.GetActorLocation().Z-Player.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Feet)>45.f) return INDEX_NONE;
    int32 Best=INDEX_NONE;float Distance=SoraCampaignReach::Interact;
    for(int I=0;I<Fusuma.Num();++I)
    {
        const auto* Panel=Fusuma[I].Panel.Get();if(!Panel) continue;
        const FVector Along=Fusuma[I].Travel.GetSafeNormal();
        FVector Hand=Panel->GetComponentLocation();
        Hand+=Along*FMath::Clamp(FVector::DotProduct(Player.GetActorLocation()-Hand,Along),-120.f,120.f);
        Hand.Z=110.f;
        const float Reach=FVector::Dist2D(Player.GetActorLocation(),Hand);
        if(Reach>=Distance) continue;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(FusumaReach),false,&Player);
        Query.AddIgnoredActor(Props);
        FHitResult Hit;
        if(GetWorld()->LineTraceSingleByChannel(Hit,Player.GetActorLocation(),Hand,ECC_Visibility,Query)) continue;
        Best=I;Distance=Reach;
    }
    return Best;
}

bool USoraFieldcraft::InteractFusuma(const ASoraPlayerCharacter& Player)
{
    const int32 I=FusumaAt(Player);if(!Fusuma.IsValidIndex(I)) return false;
    FFusuma& Door=Fusuma[I];Door.bOpen=!Door.bOpen;Door.bSounded=false;Door.bBlocked=false;
    return true;
}

void USoraFieldcraft::TickFusuma(float DeltaSeconds)
{
    for(int I=0;I<Fusuma.Num();++I)
    {
        FFusuma& Door=Fusuma[I];auto* Panel=Door.Panel.Get();if(!Panel) continue;
        // One second per full slide. The subsystem's game-state gate stops
        // this clock in pause, defeat and dialogue. A blocked leaf waits;
        // it never shoves a pawn or disables collision to finish its move.
        const float Next=FMath::FInterpConstantTo(Door.Fraction,Door.bOpen?1.f:0.f,DeltaSeconds,1.f);
        Door.bBlocked=false;if(Next==Door.Fraction) continue;
        const FVector Target=Door.Closed+Door.Travel*Next;
        FCollisionObjectQueryParams Objects(ECC_Pawn);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(FusumaOccupancy),false,Props);
        FHitResult Hit;
        const FVector Half=Panel->GetComponentScale().GetAbs()*50.f+FVector(1.f);
        if(GetWorld()->SweepSingleByObjectType(Hit,Panel->GetComponentLocation(),Target,FQuat::Identity,
            Objects,FCollisionShape::MakeBox(Half),Query))
        { Door.bBlocked=true;continue; }
        Door.Fraction=Next;Panel->SetWorldLocation(Target);
        if(!Door.bSounded)
        {
            Door.bSounded=true;
            if(auto* Stealth=USoraStealth::Get(this))
                Stealth->MakeNoise(SoraStealthRules::ENoise::Fusuma,Target,Target,Props);
            Raise(FString::Printf(TEXT("fusuma_slide:%d"),I));
        }
    }
}
