#pragma once
#include "CoreMinimal.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Framework/Application/IInputProcessor.h"
#include "SoraFrontEnd.h"
#include "Styling/SlateBrush.h"
#include "Widgets/SCompoundWidget.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "UI/SoraCreditsRowDiagnostics.h"
#endif
class SScrollBox;
class UTexture2D;

// Draws USoraFrontEnd in the game viewport with Slate built in C++ (no widget
// Blueprints) and forwards its input: keys and pad buttons, row clicks and
// hovers, clickable prompts and the wheel. While a screen is open it holds
// keyboard and pad focus, so nothing reaches UPlayerInput. Text uses the
// bundled Noto Sans CJK JP; sizes are Slate points at the 1080p reference and
// never fall below SoraUI::MinJapaneseFontSize / MinEnglishFontSize.
class SSoraFrontEnd : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SSoraFrontEnd) {}
        SLATE_ARGUMENT(TWeakObjectPtr<USoraFrontEnd>, FrontEnd)
        // The runtime Noto Sans CJK JP UFont; the engine default font without it.
        SLATE_ARGUMENT(TWeakObjectPtr<const UObject>, Font)
        SLATE_ARGUMENT(TWeakObjectPtr<UTexture2D>, TitleArt)
        SLATE_ARGUMENT(TWeakObjectPtr<UTexture2D>, Logo)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);
    // Rebuilds for the front end's current screen. The previous widgets live
    // until the next tick, so a click handler may trigger this safely.
    void Refresh();
    // Rows drawn by the last Refresh, for automation.
    int32 RowWidgetCount() const { return RowWidgets.Num(); }
    TSharedPtr<SWidget> RowWidget(int32 Index) const { return RowWidgets.IsValidIndex(Index) ? RowWidgets[Index] : nullptr; }
    // Every font size and every line of text the last Refresh used.
    const TArray<float>& FontSizesUsed() const { return FontSizes; }
    const TArray<FString>& LinesDrawn() const { return DrawnLines; }
#if WITH_DEV_AUTOMATION_TESTS
    // Opted into by the rendered tour before it opens Credits. Observes its
    // two labels without changing the ordinary widget/font/refresh policies.
    void SetCreditsRowDiagnosticsEnabled(bool bEnabled) { bCreditsRowDiagnostics = bEnabled; }
    bool InspectCreditsRow(TArray<FString>& Diagnostics) const;
#endif

    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual void Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime) override;
    virtual FReply OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent) override;
    virtual FReply OnKeyUp(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent) override;
    virtual FReply OnAnalogValueChanged(const FGeometry& MyGeometry, const FAnalogInputEvent& InAnalogInputEvent) override;
    virtual FReply OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
    virtual FReply OnMouseWheel(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;

private:
    TWeakObjectPtr<USoraFrontEnd> FrontEnd;
    TWeakObjectPtr<const UObject> FontObject;
    TWeakObjectPtr<UTexture2D> TitleArt;
    TWeakObjectPtr<UTexture2D> Logo;
    FSlateBrush TitleBrush, LogoBrush, QrBrush;
    FSlateRoundedBoxBrush KeyBrush{FLinearColor(.08f, .11f, .12f, .95f), 6.f, FLinearColor(.93f, .90f, .80f, .8f), 1.5f};
    TSharedPtr<SWidget> Retired;
    TSharedPtr<SScrollBox> RowScroll;
    TSharedPtr<SScrollBox> CreditsScroll;
    TArray<TSharedPtr<SWidget>> RowWidgets;
    TArray<float> FontSizes;
    TArray<FString> DrawnLines;
#if WITH_DEV_AUTOMATION_TESTS
    bool bCreditsRowDiagnostics = false;
    uint32 DiagnosticRefreshes = 0;
    uint64 DiagnosticRefreshFrame = 0;
    TArray<TSharedRef<FSoraCreditsLabelProbe>> CreditsLabelProbes;
#endif

    FSlateFontInfo Font(float Size);
    TSharedRef<SWidget> Text(const FString& Line, float Size, const FLinearColor& Color, bool bWrap = false,
        const TCHAR* DiagnosticLanguage = nullptr);
    // A Japanese line with its English subtitle, if subtitles are on.
    TSharedRef<SWidget> Bilingual(const FString& Japanese, const FString& English, float JapaneseSize, float EnglishSize,
        const FLinearColor& JapaneseColor, bool bWrap = true);
    TSharedRef<SWidget> Bilingual(const SoraText::FLine& Line, float JapaneseSize, float EnglishSize, const FLinearColor& JapaneseColor, bool bWrap = true)
    {
        return Bilingual(Line.Japanese, Line.English, JapaneseSize, EnglishSize, JapaneseColor, bWrap);
    }
    TSharedRef<SWidget> BuildScreen();
    TSharedRef<SWidget> BuildTitle();
    TSharedRef<SWidget> BuildMenu();
    TSharedRef<SWidget> BuildConfirm();
    TSharedRef<SWidget> BuildRows();
    TSharedRef<SWidget> BuildRow(int32 Index, const SoraUI::FRow& Row, bool bFocused);
    TSharedRef<SWidget> BuildHeading(const SoraUI::FRow& Row);
    TSharedRef<SWidget> BuildDetail();
    // The accessibility screen's telegraph swatches for the chosen palette.
    TSharedRef<SWidget> BuildPalette();
    TSharedRef<SWidget> BuildWallet();
    TSharedRef<SWidget> BuildCredits();
    TSharedRef<SWidget> BuildBanner();
    // Device-aware prompts for the open screen, and the build notes (with the
    // key-visual disclaimer on the title and main menu).
    TSharedRef<SWidget> BuildPrompts();
    TSharedRef<SWidget> BuildNotes(bool bKeyVisual);
    TSharedRef<SWidget> Prompt(SoraUI::ECommand Command, const FText& Label);
    TSharedRef<SWidget> Backdrop();
    TSharedRef<SWidget> Logotype(float Size);
};

// Notes the device behind every key, stick, click and mouse move before any
// widget sees it, so prompts and the cursor follow the player's hands in play
// and in menus alike. It never consumes input.
class FSoraInputDeviceTracker : public IInputProcessor
{
public:
    explicit FSoraInputDeviceTracker(TWeakObjectPtr<USoraFrontEnd> InFrontEnd) : FrontEnd(InFrontEnd) {}
    virtual void Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor) override {}
    virtual bool HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override;
    virtual bool HandleAnalogInputEvent(FSlateApplication& SlateApp, const FAnalogInputEvent& InAnalogInputEvent) override;
    virtual bool HandleMouseMoveEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override;
    virtual bool HandleMouseButtonDownEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override;
    virtual const TCHAR* GetDebugName() const override { return TEXT("SoraInputDeviceTracker"); }
private:
    TWeakObjectPtr<USoraFrontEnd> FrontEnd;
};
