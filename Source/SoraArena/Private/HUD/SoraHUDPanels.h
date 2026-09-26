#pragma once
#include "CoreMinimal.h"
#include "SoraText.h"
class ASoraGameMode;
class ASoraHUD;
class ASoraPlayerCharacter;
struct FSoraChapter;

// Where the dialogue panel's lines go, as offsets from Top. The panel sits
// on the same bottom edge at every subtitle size and grows upwards.
struct FSoraDialogueLayout
{
    float Top = 0.f, Height = 0.f, SpeakerY = 0.f, JapaneseY = 0.f, EnglishY = 0.f;
};

// One HUD frame's canvas size, the 1600x1000 layout scale, subtitle sizes
// with readable floors, the player's display settings, and the palette every
// panel shares.
struct FSoraHUDFrame
{
    ASoraHUD& HUD;
    const ASoraGameMode& Mode;
    float W = 0.f, H = 0.f, S = 1.f;
    float JapaneseSubtitleScale = .65f, EnglishSubtitleScale = .60f;
    float JapaneseSpeakerScale = .55f, EnglishSpeakerScale = .52f;
    float JapaneseSubtitleLineHeight = 22.f, EnglishSubtitleLineHeight = 20.f;
    // Dialogue and sound captions at the subtitle-size setting; the other
    // panels keep the sizes above so their fixed layouts hold.
    float DialogueJapaneseScale = .65f, DialogueEnglishScale = .60f;
    float DialogueJapaneseSpeakerScale = .55f, DialogueEnglishSpeakerScale = .52f;
    float DialogueJapaneseLineHeight = 22.f, DialogueEnglishLineHeight = 20.f;
    bool bSpeakerNames = true;
    bool bSoundCaptions = false;
    // Flashes fade gently instead of blinking.
    bool bReduceFlashing = false;
    FLinearColor Ivory, Gold, Teal, Muted;
    FSoraHUDFrame(ASoraHUD& InHUD, const ASoraGameMode& InMode, float Width, float Height);
    // The dialogue panel for up to two lines of each language.
    FSoraDialogueLayout DialogueLayout(bool bEnglish) const;
    // A key prompt or short readout: the Japanese, then its English beside it,
    // smaller and muted, while English subtitles are on. Keys in prompts come
    // from SoraUI::ActionKey, so they follow the device and rebinding.
    void LabelWithEnglish(const SoraText::FLine& Line, float X, float Y, float Scale, FLinearColor Color) const;
};

// Panels in draw order during play; menus are the Slate front end in
// Private/UI. Title card, dialogue, notices and results:
// SoraHUDStoryPanels.cpp. Objective, dojo, boss and the hero's combat
// readouts: SoraHUDCombatPanels.cpp. Sound captions: SoraHUDCaptions.cpp.
namespace SoraHUDPanels
{
void DrawTopBar(const FSoraHUDFrame& Frame);
void DrawTitleCard(const FSoraHUDFrame& Frame, const FSoraChapter& Card);
void DrawObjective(const FSoraHUDFrame& Frame);
void DrawDojoLesson(const FSoraHUDFrame& Frame);
void DrawBoss(const FSoraHUDFrame& Frame);
void DrawHero(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
void DrawDialogue(const FSoraHUDFrame& Frame);
void DrawResult(const FSoraHUDFrame& Frame);
void DrawCaptions(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter* Hero);
}
