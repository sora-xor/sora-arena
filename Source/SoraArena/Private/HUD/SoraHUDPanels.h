#pragma once
#include "CoreMinimal.h"
class ASoraGameMode;
class ASoraHUD;
class ASoraPlayerCharacter;
struct FSoraChapter;

// One HUD frame's canvas size, the 1600x1000 layout scale, subtitle sizes
// with readable floors, and the palette every panel shares.
struct FSoraHUDFrame
{
    ASoraHUD& HUD;
    const ASoraGameMode& Mode;
    float W = 0.f, H = 0.f, S = 1.f;
    float JapaneseSubtitleScale = .65f, EnglishSubtitleScale = .60f;
    float JapaneseSpeakerScale = .55f, EnglishSpeakerScale = .52f;
    float JapaneseSubtitleLineHeight = 22.f, EnglishSubtitleLineHeight = 20.f;
    FLinearColor Ivory, Gold, Teal, Muted;
    FSoraHUDFrame(ASoraHUD& InHUD, const ASoraGameMode& InMode, float Width, float Height);
};

// Panels in draw order. Menu panels: SoraHUDMenuPanels.cpp. Title card,
// dialogue, notices and results: SoraHUDStoryPanels.cpp. Objective, dojo,
// boss and the hero's combat readouts: SoraHUDCombatPanels.cpp.
namespace SoraHUDPanels
{
void DrawTopBar(const FSoraHUDFrame& Frame);
void DrawMenu(const FSoraHUDFrame& Frame);
void DrawTitleCard(const FSoraHUDFrame& Frame, const FSoraChapter& Card);
void DrawObjective(const FSoraHUDFrame& Frame);
void DrawDojoLesson(const FSoraHUDFrame& Frame);
void DrawBoss(const FSoraHUDFrame& Frame);
void DrawHero(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
void DrawDialogue(const FSoraHUDFrame& Frame);
void DrawResult(const FSoraHUDFrame& Frame);
// Deterministic practice, drawn last (SoraHUDPracticePanels.cpp).
void DrawPractice(const FSoraHUDFrame& Frame);
}
