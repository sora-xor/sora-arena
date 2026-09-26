#include "HUD/SoraHUDPanels.h"
#include "SoraCaptions.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraText.h"

namespace
{
// Where a sound came from, seen from the hero's view: ahead, left, right or
// behind; nothing without a source.
SoraText::FLine Direction(const ASoraPlayerCharacter* Hero, const FSoraCaption& Caption)
{
    if (!Hero || !Caption.bHasSource)
        return SoraText::FLine();
    const FVector To = (Caption.Source - Hero->GetActorLocation()).GetSafeNormal2D();
    if (To.IsNearlyZero())
        return SoraText::FLine();
    const FVector Forward = Hero->GetControlRotation().Vector().GetSafeNormal2D();
    const float Ahead = FVector::DotProduct(Forward, To);
    const float Right = FVector::CrossProduct(Forward, To).Z;
    if (Ahead >= .7071f)
        return SoraText::Line(NSLOCTEXT("SoraArena.Captions", "Ahead", "前"));
    if (Ahead <= -.7071f)
        return SoraText::Line(NSLOCTEXT("SoraArena.Captions", "Behind", "後ろ"));
    return Right > 0.f ? SoraText::Line(NSLOCTEXT("SoraArena.Captions", "Right", "右"))
        : SoraText::Line(NSLOCTEXT("SoraArena.Captions", "Left", "左"));
}
}

void SoraHUDPanels::DrawCaptions(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter* Hero)
{
    const USoraCaptions* Captions = Frame.bSoundCaptions ? USoraCaptions::Get(&Frame.Mode) : nullptr;
    if (!Captions)
        return;
    // Top right, clear of the objective, the boss bar and the dialogue.
    ASoraHUD& HUD = Frame.HUD;
    const ASoraGameMode* G = &Frame.Mode;
    const float S = Frame.S;
    const float JapaneseLine = Frame.DialogueJapaneseLineHeight, EnglishLine = G->bEnglishSubtitles ? Frame.DialogueEnglishLineHeight : 0.f;
    float Y = 90 * S;
    for (const FSoraCaption& Caption : Captions->Live())
    {
        const SoraText::FLine Where = Direction(Hero, Caption);
        const FString Count = Caption.Count > 1 ? FString::Printf(TEXT(" ×%d"), Caption.Count) : FString();
        const SoraText::FArg Sound(TEXT("Caption"), SoraText::FLine{Caption.Japanese + Count, Caption.English + Count});
        const SoraText::FLine Line = Where.IsEmpty()
            ? SoraText::Format(NSLOCTEXT("SoraArena.Captions", "Caption", "［{Caption}］"), {Sound})
            : SoraText::Format(NSLOCTEXT("SoraArena.Captions", "CaptionFrom", "［{Caption}］ {Direction}"), {Sound, {TEXT("Direction"), Where}});
        const FString& Japanese = Line.Japanese;
        const FString& English = Line.English;
        const float Width = FMath::Max3(360 * S, HUD.LabelWidth(Japanese, Frame.DialogueJapaneseScale),
            G->bEnglishSubtitles ? HUD.LabelWidth(English, Frame.DialogueEnglishScale) : 0.f) + 28 * S;
        const float X = Frame.W - Width - 20 * S, Height = 10 * S + JapaneseLine + EnglishLine;
        HUD.Panel(X, Y, Width, Height, FLinearColor(.013f, .027f, .033f, .86f));
        HUD.Label(Japanese, X + 14 * S, Y + 5 * S, Frame.DialogueJapaneseScale, Frame.Ivory);
        if (G->bEnglishSubtitles)
            HUD.Label(English, X + 14 * S, Y + 5 * S + JapaneseLine, Frame.DialogueEnglishScale, Frame.Muted);
        Y += Height + 6 * S;
    }
}
