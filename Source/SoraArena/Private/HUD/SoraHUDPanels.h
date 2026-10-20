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
    // Draw-local occupancy: later projected labels also clear earlier labels.
    mutable TArray<FBox2D> WorldMarkerBounds;
    FSoraHUDFrame(ASoraHUD& InHUD, const ASoraGameMode& InMode, float Width, float Height);
    // The dialogue panel for up to two lines of each language.
    FSoraDialogueLayout DialogueLayout(bool bEnglish) const;
    // A key prompt or short readout: the Japanese, then its English beside it,
    // smaller and muted, while English subtitles are on. Keys in prompts come
    // from SoraUI::ActionKey, so they follow the device and rebinding.
    void LabelWithEnglish(const SoraText::FLine& Line, float X, float Y, float Scale, FLinearColor Color) const;
};

// Every visible sound caption keeps its measured text; the story layout
// chooses a clear column and the late caption draw uses those same bounds.
struct FSoraCaptionText { FString Text; FVector2D At; float Scale=0.f; bool bEnglish=false; };
struct FSoraCaptionPanel { FBox2D Bounds=FBox2D(ForceInit); TArray<FSoraCaptionText> Text; };
struct FSoraCaptionLayout { TArray<FSoraCaptionPanel> Panels; bool bFits=true; };

// Panels in draw order during play; menus are the Slate front end in
// Private/UI. Title card, dialogue, notices and results:
// SoraHUDStoryPanels.cpp. Objective, dojo, boss and the hero's combat
// readouts: SoraHUDCombatPanels.cpp. The stealth zone's detection meter,
// guard marks and prompts: SoraHUDStealthPanel.cpp. Sound captions:
// SoraHUDCaptions.cpp. Deterministic practice: SoraHUDPracticePanels.cpp.
namespace SoraHUDPanels
{
void DrawTopBar(const FSoraHUDFrame& Frame);
void DrawTitleCard(const FSoraHUDFrame& Frame, const FSoraChapter& Card);
void DrawObjective(const FSoraHUDFrame& Frame);
void DrawDojoLesson(const FSoraHUDFrame& Frame);
void DrawBoss(const FSoraHUDFrame& Frame);
void DrawStealth(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
TArray<FBox2D> StealthPanelBounds(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
void DrawHero(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
void DrawWeapon(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
// Capture checks the same measured weapon layout that the live HUD draws.
bool WeaponLayoutFits(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero, FString& Why);
void DrawArmsNotice(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
// Actual bottom-right rectangles, including active windup and arm-change notice.
TArray<FBox2D> WeaponPanelBounds(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
// Top of the lower full-width story stack; fieldcraft prompts stay above it.
float GameplayStoryTop(const FSoraHUDFrame& Frame);
// The measured tracker/notices must fit above the lower story stack, retaining all targets.
// Full rhythm sweep and measured localized Interact label share no pixels.
bool RhythmCueLayoutFits(const FSoraHUDFrame& Frame, FString& Why);
bool StoryTrackerLayoutFits(const FSoraHUDFrame& Frame, FString& Why);
bool BottomHUDLayoutFits(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero, FString& Why);
// The campaign's arms wheel and the arm a key took up; the beat's fieldcraft:
// the hand's work, breath, grip, stones, the candle, the signal and the
// downed (SoraHUDFieldcraftPanel.cpp).
void DrawArmsWheel(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
void DrawFieldcraft(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero);
void DrawDialogue(const FSoraHUDFrame& Frame);
void DrawResult(const FSoraHUDFrame& Frame);
bool ShowsRegistry(const ASoraGameMode& Mode);
void DrawRegistry(const FSoraHUDFrame& Frame);
// Capture qualification uses the same measured, fully wrapped layout as draw.
bool RegistryLayoutFits(const FSoraHUDFrame& Frame, FString& Why);
// Relative caption rows at a candidate column width; no truncation.
FBox2D CaptionGlyphBounds(const FSoraHUDFrame& Frame, const FString& Text, float Scale);
TArray<FSoraCaptionPanel> MeasureCaptions(const FSoraHUDFrame& Frame, float Width);
FSoraCaptionLayout CaptionLayout(const FSoraHUDFrame& Frame);
// Actual upper gameplay panels are excluded from caption fallback columns.
TArray<FBox2D> UpperGameplayPanelBounds(const FSoraHUDFrame& Frame);
bool CaptionStoryLayoutFits(const FSoraHUDFrame& Frame, FString& Why);
// Keep projected site/objective labels clear of measured fixed HUD panels.
FVector2D WorldMarkerPosition(const FSoraHUDFrame& Frame, FVector2D Desired, FVector2D Size);
void DrawCaptions(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter* Hero);
// Deterministic practice, drawn last (SoraHUDPracticePanels.cpp).
void DrawPractice(const FSoraHUDFrame& Frame);
// A campaign HUD prompt (Content/Data/campaign ui_prompts) with each {Action}
// token replaced by the player's key for that input action (SoraUI::ActionKey),
// bracketed in both languages. validate_campaign.py admits only tokens that
// name an action in Config/DefaultInput.ini.
SoraText::FLine KeyPrompt(const UObject* WorldContext, const FString& Japanese, const FString& English);
// The result screen's headline for the round that ended: a fall, a chapter
// (the dojo's training, a district, the liberation), the training arena or
// deterministic practice.
SoraText::FLine ResultHeadline(const ASoraGameMode& Mode);
}
