#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraLiftAutomation.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"
#include "GameFramework/DamageType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWardGateBrazierTest,"SoraArena.Fieldcraft.WardGateBrazier",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWardGateBrazierTest::RunTest(const FString&)
{
    using SoraFieldcraftAutomation::FBeatWorld;
    if(!FSoraCatalog::Get().Load())return false;
    FBeatWorld W(*this,TEXT("WardGateBrazier"),2,2);if(!W.Start())return false;
    W.Harden();SoraLiftAutomation::HoldThreats(*W.World);
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    if(!TestTrue(TEXT("Gate entry dialogue releases control"),W.Mode()->IsPlaying()))return false;
    ASoraLamp* Brazier=nullptr;ASoraLamp* Andon=nullptr;
    for(int I=0;I<W.Craft().Lamps.Num();++I)
    {
        const auto& Row=W.Craft().Lamps[I];
        if(Row.Id==TEXT("brazier_b03"))Brazier=W.Fieldcraft()->Lamps()[I];
        if(Row.Id==TEXT("andon_b03_bansho"))Andon=W.Fieldcraft()->Lamps()[I];
    }
    if(!TestNotNull(TEXT("The gate brazier is staged"),Brazier)||!TestNotNull(TEXT("The hut's andon is staged"),Andon))return false;
    APointLight* Light=nullptr;
    for(TActorIterator<APointLight> It(W.World->GetTestWorld());It;++It)if(It->GetOwner()==Brazier)Light=*It;
    if(!TestNotNull(TEXT("The brazier owns an actual point light"),Light))return false;
    TestEqual(TEXT("The visible light retains the authored four-metre reach"),Light->PointLightComponent->AttenuationRadius,400.f);
    W.Stand(Brazier->Glow()+FVector(60,0,0));W.LookAt(Brazier->Glow());
    TestTrue(TEXT("The permanent brazier offers no snuff work"),
        W.Fieldcraft()->Readout(*W.Hero()).HoldHere!=FSoraFieldcraftReadout::EHold::Snuff);
    if(!W.Hold(EKeys::E,90))return false;
    TestTrue(TEXT("Holding the real interaction key cannot extinguish the brazier"),Brazier->IsLit());
    UGameplayStatics::ApplyDamage(Brazier,100.f,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
    if(!W.Tick(1))return false;
    TestTrue(TEXT("The brazier also ignores the lamp damage interface"),Brazier->IsLit());
    TestTrue(TEXT("The permanent light still illuminates the guard's light query"),
        W.Stealth()->LightAt(Brazier->Glow()+FVector(60,0,0))>0&&Light->PointLightComponent->Intensity>0);
    W.Stand(Andon->Glow()+FVector(60,0,0));W.LookAt(Andon->Glow());
    if(!W.Hold(EKeys::E,90))return false;
    TestTrue(TEXT("The nearby hut lamp remains snuffable without darkening the brazier"),!Andon->IsLit()&&Brazier->IsLit());
    TestTrue(TEXT("Only the mutable lamp emits lamp_out"),W.Raised(TEXT("lamp_out:andon_b03_bansho"))&&!W.Raised(TEXT("lamp_out:brazier_b03")));
    AddInfo(TEXT("Directed light/interaction fixture with threats held. Gate geometry, scanner hazard, routes and ordinary stealth remain unqualified."));
    return !HasAnyErrors();
}
#endif
