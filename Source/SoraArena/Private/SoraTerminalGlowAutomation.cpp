#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTerminalGlowTest,"SoraArena.Campaign.NoticeSquare.TerminalGlow",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FSoraTerminalGlowTest::RunTest(const FString&)
{
    if(!FSoraCatalog::Get().Load())return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("TerminalGlow"),2,9);
    if(!W.Start())return false;
    W.Harden();
    for(int I=0;I<3000&&!W.Mode()->IsPlaying();++I)if(!W.Tick(1))return false;
    // Directed light mechanics only. The notice square's authored geometry,
    // charge/fuse and rendered lighting require their own implementation/proof.
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)It->Destroy();
    const auto& Lamps=W.Craft().Lamps;
    const int Index=Lamps.IndexOfByPredicate([](const FSoraLamp& L){return L.Id==TEXT("terminal_glow_b10");});
    if(!TestTrue(TEXT("The terminal has a staged light"),Index>=0&&W.Fieldcraft()->Lamps().IsValidIndex(Index)))return false;
    const auto& Spec=Lamps[Index];auto* Glow=W.Fieldcraft()->Lamps()[Index].Get();
    TestEqual(TEXT("The terminal illuminates six metres"),Spec.RadiusCm,600.f);
    TestTrue(TEXT("The terminal cannot be snuffed"),Spec.Snuff==FSoraLamp::ESnuff::None);
    TestEqual(TEXT("The terminal offers no snuff hold"),Spec.HoldMs,0);
    W.Stand(FVector(Spec.At,0)+FVector(80,0,0));
    if(!W.Tick(4)||!W.Hold(EKeys::E,120))return false;
    TestTrue(TEXT("Holding Interact cannot darken the terminal"),Glow->IsLit());
    TestFalse(TEXT("The fieldcraft snuff entry point refuses the permanent glow"),W.Fieldcraft()->SnuffLamp(Index));
    FHitResult Hit;Hit.ImpactPoint=Glow->GetActorLocation();Hit.Location=Hit.ImpactPoint;
    SoraDamage::Strike(Glow,100.f,FSoraHit::Ranged(W.Hero()->GetActorLocation(),18),FVector::ForwardVector,Hit,
        W.Hero()->GetController(),W.Hero());
    TestTrue(TEXT("Shooting the glow cannot bypass the charge objective"),Glow->IsLit());
    TestFalse(TEXT("No terminal lamp-out event is emitted"),W.Raised(TEXT("lamp_out:terminal_glow_b10")));
    int StreetLanterns=0;
    for(const auto& L:Lamps)if(L.Id==TEXT("tsuji_andon_sw")||L.Id==TEXT("tsuji_andon_se"))
    {
        ++StreetLanterns;
        TestTrue(TEXT("The two licensed street lanterns retain their one-second snuff hold"),
            L.Snuff==FSoraLamp::ESnuff::Hold&&L.HoldMs==1000);
    }
    TestEqual(TEXT("Both licensed street lanterns remain staged"),StreetLanterns,2);
    return !HasAnyErrors();
}
#endif
