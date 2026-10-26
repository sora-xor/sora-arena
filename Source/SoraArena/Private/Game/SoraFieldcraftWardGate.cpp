#include "SoraFieldcraft.h"
#include "SoraAudio.h"
#include "SoraWardGateRules.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraStealth.h"
#include "SoraEnemy.h"
#include "SoraPlayerCharacter.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"

void USoraFieldcraft::StageWardGate(const FSoraBeat& Beat)
{
    bWardGate=Beat.Space.bWardGate;
    if(!bWardGate)return;
    namespace R=SoraWardGateRules;
    WardWicket=Piece(TEXT("WardWicket"),SoraFieldcraftLayout::Cube,FVector(R::FenceX,R::WicketY,60),
        FVector(.16f,.9f,1.2f),FLinearColor(.24f,.16f,.09f),true,SoraFieldcraftLayout::Timber);
    // The sensor is a visible nonblocking sheet just outside the shut main
    // leaves. The separately barred wicket lies beyond its positive-Y edge.
    Piece(TEXT("WardScannerSheet"),SoraFieldcraftLayout::Cube,FVector(-6220,-45,120),
        FVector(.02f,2.7f,2.4f),FLinearColor(.05f,.8f,.95f),false);
    for(int Y:{-185,95})Piece(TEXT("WardScannerPost"),SoraFieldcraftLayout::Cube,FVector(-6220,Y,122),
        FVector(.12f,.1f,2.44f),FLinearColor(.055f,.065f,.075f),false,SoraFieldcraftLayout::Metal);
    Piece(TEXT("WardScannerHeader"),SoraFieldcraftLayout::Cube,FVector(-6220,-45,248),
        FVector(.12f,2.9f,.12f),FLinearColor(.055f,.065f,.075f),false,SoraFieldcraftLayout::Metal);
    if (auto* Audio = USoraAudioSubsystem::Get(this))
        Audio->StartAmbientEmitter(Props, TEXT("ward_culvert"), FVector(-6200,-650,-85));
    bWardHavePosition=false;bWardWicketOpen=false;bWardScannerInside=false;
}
void USoraFieldcraft::AssignWardGuard(ASoraEnemy& Guard,int32 Index)
{ if(bWardGate&&Index==0)WardKidoban=&Guard; }

bool USoraFieldcraft::FreeWardKidoban(const AActor* Actor)
{
    if(!bWardGate||bWardWicketOpen||Actor!=WardKidoban.Get()||!WardKidoban.IsValid()||!WardKidoban->IsFreed())return false;
    bWardWicketOpen=true;
    if(WardWicket.IsValid())
    {
        // Swing clear about the north jamb, retaining the opened leaf's
        // physical collision. Its former opening is now 90 x 120 cm.
        WardWicket->SetRelativeLocation(FVector(-6155,180,60));
        WardWicket->SetRelativeRotation(FRotator(0,90,0));
    }
    Raise(TEXT("wicket_open:kidoban"));
    return true;
}
void USoraFieldcraft::TickWardGate()
{
    if(!bWardGate)return;
    const auto* Player=Hero();if(!Player)return;
    const FVector At=Player->GetActorLocation();
    const FVector Before=bWardHavePosition?WardLastPosition:At;
    const auto* Capsule=Player->GetCapsuleComponent();
    const double Radius=Capsule->GetScaledCapsuleRadius(),HalfHeight=Capsule->GetScaledCapsuleHalfHeight();
    const bool Inside=SoraWardGateRules::CrossesScanner(At.X,At.Y,At.Z,At.X,At.Y,At.Z,Radius,HalfHeight);
    const bool Crossed=SoraWardGateRules::CrossesScanner(Before.X,Before.Y,Before.Z,At.X,At.Y,At.Z,Radius,HalfHeight);
    WardLastPosition=At;bWardHavePosition=true;
    const bool Entered=!bWardScannerInside&&Crossed;bWardScannerInside=Inside;
    if(Entered)
    {
        if(auto* Stealth=USoraStealth::Get(this))Stealth->RaiseSensorAlarm(At);
        if(bWardGate&&Staged)Raise(TEXT("scanner_enter:scan_arch_b03"));
    }
}
