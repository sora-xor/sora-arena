#include "UI/SSoraFrontEnd.h"
#include "UI/SoraFrontEndInputTrace.h"
#include "ArenaWalletSubsystem.h"
#include "SoraGameMode.h"
#include "SoraSettings.h"
#include "UI/SoraWalletText.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace SoraMenuStyle
{
// The HUD palette, shared with the canvas panels.
const FLinearColor Ivory(.93f, .90f, .80f);
const FLinearColor Gold(.94f, .65f, .21f);
const FLinearColor Teal(.22f, .81f, .75f);
const FLinearColor Muted(.56f, .63f, .65f);
const FLinearColor Night(.013f, .027f, .033f);
const FLinearColor Row(.07f, .095f, .11f, .88f);
const FLinearColor RowFocus(.08f, .25f, .26f, .95f);
const FLinearColor RowDisabled(.05f, .06f, .07f, .55f);
// Slate points at the 1080p reference; the viewport scales them by 0.666 at
// 720p. Japanese never goes below SoraUI::MinJapaneseFontSize, English below
// SoraUI::MinEnglishFontSize.
constexpr float Hero = 120.f, HeroEnglish = 30.f, Heading = 40.f, HeadingEnglish = 22.f;
constexpr float RowText = 28.f, Value = 26.f, Hint = 26.f, HintEnglish = 22.f, Body = SoraUI::MinJapaneseFontSize, Small = SoraUI::MinEnglishFontSize;
// The Controls screen's two key columns.
constexpr float KeyColumn = 260.f;
}

namespace
{
const FSlateBrush* MenuWhite() { return FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")); }
bool IsDialog(SoraUI::EScreen Screen) { return Screen == SoraUI::EScreen::Confirm || Screen == SoraUI::EScreen::Capture; }
}

void SSoraFrontEnd::Construct(const FArguments& InArgs)
{
    FrontEnd = InArgs._FrontEnd;
    FontObject = InArgs._Font;
    TitleArt = InArgs._TitleArt;
    Logo = InArgs._Logo;
    if (UTexture2D* Art = TitleArt.Get())
    {
        TitleBrush.SetResourceObject(Art);
        TitleBrush.ImageSize = FVector2D(Art->GetSizeX(), Art->GetSizeY());
    }
    if (UTexture2D* Insignia = Logo.Get())
    {
        LogoBrush.SetResourceObject(Insignia);
        LogoBrush.ImageSize = FVector2D(Insignia->GetSizeX(), Insignia->GetSizeY());
    }
    TWeakObjectPtr<USoraFrontEnd> Weak = FrontEnd;
    SetVisibility(TAttribute<EVisibility>::CreateLambda([Weak]()
    {
        return Weak.IsValid() && Weak->IsOpen() ? EVisibility::Visible : EVisibility::Collapsed;
    }));
    Refresh();
}

void SSoraFrontEnd::Refresh()
{
    Retired = ChildSlot.GetWidget();
    FontSizes.Reset();
    DrawnLines.Reset();
    RowWidgets.Reset();
    RowScroll.Reset();
    CreditsScroll.Reset();
    CodexScroll.Reset();
    CodexContent.Reset();
    ChildSlot[BuildScreen()];
}

void SSoraFrontEnd::Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime)
{
    SCompoundWidget::Tick(AllottedGeometry, InCurrentTime, InDeltaTime);
    Retired.Reset();
    if (CodexScroll && FrontEnd.IsValid())
        CodexScroll->SetScrollOffset(CodexScroll->GetScrollOffsetOfEnd() * FrontEnd->CodexScrollFraction());
}
float SSoraFrontEnd::CodexScrollOffset() const { return CodexScroll ? CodexScroll->GetScrollOffset() : 0.f; }
float SSoraFrontEnd::CodexScrollEnd() const { return CodexScroll ? CodexScroll->GetScrollOffsetOfEnd() : 0.f; }
FGeometry SSoraFrontEnd::CodexViewportGeometry() const { return CodexScroll ? CodexScroll->GetCachedGeometry() : FGeometry(); }
FGeometry SSoraFrontEnd::CodexContentGeometry() const { return CodexContent ? CodexContent->GetCachedGeometry() : FGeometry(); }

FReply SSoraFrontEnd::OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
    USoraFrontEnd* Model = FrontEnd.Get();
    if (!Model || !Model->IsOpen())
        return FReply::Unhandled();
#if WITH_DEV_AUTOMATION_TESTS
    SoraFrontEndInputTrace::FScope InputTrace(Model, TEXT("slate-key"), InKeyEvent.GetKey().GetFName(), InKeyEvent.IsRepeat());
#endif
    Model->HandleKey(InKeyEvent.GetKey(), InKeyEvent.IsRepeat());
    // An open screen owns every key, so none falls through to play or to
    // Slate's own focus navigation.
    return FReply::Handled();
}

FReply SSoraFrontEnd::OnKeyUp(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
    return FrontEnd.IsValid() && FrontEnd->IsOpen() ? FReply::Handled() : FReply::Unhandled();
}

FReply SSoraFrontEnd::OnAnalogValueChanged(const FGeometry& MyGeometry, const FAnalogInputEvent& InAnalogInputEvent)
{
    // The left stick arrives as Gamepad_LeftStick_* key presses with repeats.
    return FrontEnd.IsValid() && FrontEnd->IsOpen() ? FReply::Handled() : FReply::Unhandled();
}

FReply SSoraFrontEnd::OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
    USoraFrontEnd* Model = FrontEnd.Get();
    if (!Model || !Model->IsOpen())
        return FReply::Unhandled();
#if WITH_DEV_AUTOMATION_TESTS
    SoraFrontEndInputTrace::FScope InputTrace(Model, TEXT("slate-button"), MouseEvent.GetEffectingButton().GetFName());
#endif
    // A rebind takes the button itself; the dialog's own Cancel handles its clicks first.
    if (Model->IsCapturing())
    {
        Model->CaptureKey(MouseEvent.GetEffectingButton());
        return FReply::Handled();
    }
    Model->NoteDevice(SoraUI::EDevice::KeyboardMouse);
    if (Model->Screen() == SoraUI::EScreen::Title)
        Model->Command(SoraUI::ECommand::Accept);
    else if (MouseEvent.GetEffectingButton() == EKeys::RightMouseButton || MouseEvent.GetEffectingButton() == EKeys::ThumbMouseButton)
        Model->Command(SoraUI::ECommand::Back);
    return FReply::Handled();
}

FReply SSoraFrontEnd::OnMouseWheel(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
    USoraFrontEnd* Model = FrontEnd.Get();
    if (!Model || !Model->IsOpen())
        return FReply::Unhandled();
    if (Model->IsCapturing())
    {
        Model->CaptureKey(MouseEvent.GetWheelDelta() > 0.f ? EKeys::MouseScrollUp : EKeys::MouseScrollDown);
        return FReply::Handled();
    }
    Model->NoteDevice(SoraUI::EDevice::KeyboardMouse);
    Model->Command(MouseEvent.GetWheelDelta() > 0.f ? SoraUI::ECommand::Up : SoraUI::ECommand::Down);
    return FReply::Handled();
}

FSlateFontInfo SSoraFrontEnd::Font(float Size)
{
    FontSizes.Add(Size);
    if (const UObject* Object = FontObject.Get())
        return FSlateFontInfo(Object, Size);
    return FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), Size);
}

TSharedRef<SWidget> SSoraFrontEnd::Text(const FString& Line, float Size, const FLinearColor& Color, bool bWrap)
{
    DrawnLines.Add(Line);
    return SNew(STextBlock)
        .Text(FText::FromString(Line))
        .Font(Font(Size))
        .ColorAndOpacity(FSlateColor(Color))
        .AutoWrapText(bWrap);
}

TSharedRef<SWidget> SSoraFrontEnd::Bilingual(const FString& Japanese, const FString& English, float JapaneseSize, float EnglishSize,
    const FLinearColor& JapaneseColor, bool bWrap)
{
    TSharedRef<SVerticalBox> Box = SNew(SVerticalBox);
    if (!Japanese.IsEmpty())
        Box->AddSlot().AutoHeight()[Text(Japanese, JapaneseSize, JapaneseColor, bWrap)];
    if (!English.IsEmpty() && FrontEnd.IsValid() && FrontEnd->ShowsEnglish())
        Box->AddSlot().AutoHeight().Padding(0, 2, 0, 0)[Text(English, EnglishSize, SoraMenuStyle::Muted, bWrap)];
    return Box;
}

TSharedRef<SWidget> SSoraFrontEnd::BuildScreen()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    if (!Model || !Model->IsOpen())
        return SNullWidget::NullWidget;
    if (Model->Screen() == SoraUI::EScreen::Title)
        return BuildTitle();
    TSharedRef<SOverlay> Screen = SNew(SOverlay)
        + SOverlay::Slot()[Backdrop()]
        + SOverlay::Slot()[BuildMenu()];
    if (IsDialog(Model->Screen()))
        Screen->AddSlot()[BuildConfirm()];
    return Screen;
}

TSharedRef<SWidget> SSoraFrontEnd::Backdrop()
{
    // The title art behind the title and its menus; the paused round shows
    // through a dark veil behind the pause menu.
    const bool bPause = FrontEnd->IsPauseContext();
    const bool bArt = TitleArt.IsValid() && !bPause;
    TSharedRef<SOverlay> Layers = SNew(SOverlay);
    if (bArt)
        Layers->AddSlot()
        [
            SNew(SScaleBox)
            .Stretch(EStretch::ScaleToFill)
            [
                SNew(SImage).Image(&TitleBrush).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, .8f))
            ]
        ];
    Layers->AddSlot()
    [
        SNew(SImage)
        .Image(MenuWhite())
        .ColorAndOpacity(FLinearColor(SoraMenuStyle::Night.R, SoraMenuStyle::Night.G, SoraMenuStyle::Night.B, bPause ? .74f : bArt ? .58f : .94f))
    ];
    return Layers;
}

TSharedRef<SWidget> SSoraFrontEnd::Logotype(float Size)
{
    if (!Logo.IsValid())
        return SNullWidget::NullWidget;
    return SNew(SBox).WidthOverride(Size).HeightOverride(Size)[SNew(SImage).Image(&LogoBrush)];
}

TSharedRef<SWidget> SSoraFrontEnd::BuildTitle()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    const bool bEnglish = Model->ShowsEnglish();
    const FText Title = NSLOCTEXT("SoraArena", "MenuTitle", "猫柳生");
    TSharedRef<SVerticalBox> Column = SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[Logotype(150.f)]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 20, 0, 0)
        [
            Text(NSLOCTEXT("SoraArena.Menu", "Title.Resistance", "SORA 抵抗軍").ToString(), 30.f, SoraMenuStyle::Gold)
        ]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
        [
            SNew(STextBlock).Text(Title).Font(Font(SoraMenuStyle::Hero)).ColorAndOpacity(FSlateColor(SoraMenuStyle::Ivory))
        ];
    // The English title, in capitals, stands for the resistance line above it too.
    if (bEnglish)
        Column->AddSlot().AutoHeight().HAlign(HAlign_Center)[Text(SoraText::English(Title).ToUpper(), SoraMenuStyle::HeroEnglish, SoraMenuStyle::Muted)];
    const SoraText::FLine Motto = SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Title.Motto", "剣を、工房を、民の手に。"));
    Column->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0, 28, 0, 0)
    [
        SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[Text(Motto.Japanese, 30.f, SoraMenuStyle::Ivory)]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
        [
            bEnglish ? Text(Motto.English, SoraMenuStyle::HintEnglish, SoraMenuStyle::Muted) : SNullWidget::NullWidget
        ]
    ];
    if (!Model->BannerJapanese.IsEmpty())
        Column->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0, 28, 0, 0)[BuildBanner()];
    Column->AddSlot().AutoHeight().HAlign(HAlign_Center).Padding(0, 40, 0, 0)[Prompt(SoraUI::ECommand::Accept, NSLOCTEXT("SoraArena.Menu", "Prompt.Begin", "はじめる"))];
    // The column centres in the space above the footer, so the two never meet.
    return SNew(SOverlay)
        + SOverlay::Slot()[Backdrop()]
        + SOverlay::Slot().Padding(80, 40, 80, 40)
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().FillHeight(1.f).HAlign(HAlign_Center).VAlign(VAlign_Center)[Column]
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right).Padding(0, 24, 0, 0)[BuildNotes(true)]
        ];
}

TSharedRef<SWidget> SSoraFrontEnd::BuildMenu()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    const bool bEnglish = Model->ShowsEnglish();
    const SoraText::FLine GameName = SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Heading.Game", "SORA 抵抗軍　猫柳生"));
    TSharedRef<SHorizontalBox> Heading = SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 24, 0)[Logotype(76.f)]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)[Text(GameName.Japanese, SoraMenuStyle::Body, SoraMenuStyle::Gold)]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom).Padding(18, 0, 0, 2)
                [
                    bEnglish ? Text(GameName.English, SoraMenuStyle::Small, SoraMenuStyle::Muted) : SNullWidget::NullWidget
                ]
            ]
            + SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)[Text(Model->TitleJapanese(), SoraMenuStyle::Heading, SoraMenuStyle::Ivory)]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom).Padding(24, 0, 0, 8)
                [
                    bEnglish ? Text(Model->TitleEnglish(), SoraMenuStyle::HeadingEnglish, SoraMenuStyle::Muted) : SNullWidget::NullWidget
                ]
            ]
        ]
        + SHorizontalBox::Slot().FillWidth(1.f).HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(32, 0, 0, 0)
        [
            BuildNotes(Model->BaseScreen() == SoraUI::EScreen::Main && !Model->IsPauseContext())
        ];
    // Under a dialog the list belongs to the dialog; the screen keeps its frame.
    TSharedRef<SWidget> Body = SNullWidget::NullWidget;
    if (Model->Screen() == SoraUI::EScreen::Credits)
        Body = SNew(SVerticalBox)
            + SVerticalBox::Slot().FillHeight(1.f)[BuildCredits()]
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left).Padding(0, 20, 0, 0)[SNew(SBox).WidthOverride(560.f)[BuildRows()]];
    else if (Model->Screen() == SoraUI::EScreen::CodexEntry)
        Body = SNew(SVerticalBox)
            + SVerticalBox::Slot().FillHeight(1.f)[BuildCodexReader()]
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left).Padding(0, 20, 0, 0)[SNew(SBox).WidthOverride(560.f)[BuildRows()]];
    else if (!IsDialog(Model->Screen()))
    {
        // The Controls list carries two key columns, so it takes more of the width.
        const float RowShare = Model->Screen() == SoraUI::EScreen::Controls ? .7f : .58f;
        Body = SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(RowShare)[BuildRows()]
            + SHorizontalBox::Slot().FillWidth(1.f - RowShare).Padding(40, 0, 0, 0)
            [
                SNew(SScrollBox)
                .ConsumeMouseWheel(EConsumeMouseWheel::Never)
                + SScrollBox::Slot()[BuildDetail()]
            ];
    }
    return SNew(SBox)
        .Padding(FMargin(80, 48, 80, 40))
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[Heading]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 16, 0, 0)[BuildBanner()]
            + SVerticalBox::Slot().FillHeight(1.f).Padding(0, 28, 0, 24)[Body]
            + SVerticalBox::Slot().AutoHeight()[BuildPrompts()]
        ];
}

TSharedRef<SWidget> SSoraFrontEnd::BuildConfirm()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    FString Question, Warning, QuestionEnglish, WarningEnglish;
    if (!Model->ConfirmJapanese().Split(TEXT("\n"), &Question, &Warning))
        Question = Model->ConfirmJapanese();
    if (!Model->ConfirmEnglish().Split(TEXT("\n"), &QuestionEnglish, &WarningEnglish))
        QuestionEnglish = Model->ConfirmEnglish();
    const bool bEnglish = Model->ShowsEnglish();
    return SNew(SOverlay)
        + SOverlay::Slot()[SNew(SImage).Image(MenuWhite()).ColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, .55f))]
        + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
        [
            SNew(SBox)
            .WidthOverride(1000.f)
            [
                SNew(SBorder)
                .BorderImage(MenuWhite())
                .BorderBackgroundColor(FLinearColor(SoraMenuStyle::Night.R, SoraMenuStyle::Night.G, SoraMenuStyle::Night.B, .98f))
                .Padding(FMargin(44, 36))
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight()[Text(Question, 34.f, SoraMenuStyle::Gold, true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 12, 0, 0)[Text(Warning, SoraMenuStyle::Hint, SoraMenuStyle::Ivory, true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 14, 0, 0)
                    [
                        bEnglish ? Bilingual(FString(), QuestionEnglish + TEXT(" ") + WarningEnglish, SoraMenuStyle::Body, SoraMenuStyle::HintEnglish, SoraMenuStyle::Muted)
                            : SNullWidget::NullWidget
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 28, 0, 0)[BuildRows()]
                ]
            ]
        ];
}

TSharedRef<SWidget> SSoraFrontEnd::BuildRows()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    TSharedRef<SVerticalBox> List = SNew(SVerticalBox);
    RowWidgets.Reset();
    const TArray<SoraUI::FRow>& Rows = Model->Rows();
    for (int32 Index = 0; Index < Rows.Num(); ++Index)
    {
        TSharedRef<SWidget> Row = BuildRow(Index, Rows[Index], Index == Model->Focus());
        RowWidgets.Add(Row);
        List->AddSlot().AutoHeight().Padding(0, 0, 0, 6)[Row];
    }
    RowScroll = SNew(SScrollBox)
        .ConsumeMouseWheel(EConsumeMouseWheel::Never)
        .ScrollBarVisibility(EVisibility::Collapsed)
        + SScrollBox::Slot()[List];
    if (RowWidgets.IsValidIndex(Model->Focus()))
        RowScroll->ScrollDescendantIntoView(RowWidgets[Model->Focus()], false, EDescendantScrollDestination::IntoView);
    return RowScroll.ToSharedRef();
}

TSharedRef<SWidget> SSoraFrontEnd::BuildRow(int32 Index, const SoraUI::FRow& Row, bool bFocused)
{
    USoraFrontEnd* Model = FrontEnd.Get();
    const bool bEnglish = FrontEnd->ShowsEnglish();
    if (Row.bHeading)
        return BuildHeading(Row);
    const FLinearColor Label = Row.bEnabled ? SoraMenuStyle::Ivory : SoraMenuStyle::Muted * FLinearColor(1.f, 1.f, 1.f, .8f);
    const FLinearColor Fill = !Row.bEnabled ? SoraMenuStyle::RowDisabled : bFocused ? SoraMenuStyle::RowFocus : SoraMenuStyle::Row;
    TWeakObjectPtr<USoraFrontEnd> Weak = FrontEnd;
    // A plain row reads Japanese then English on one line, the English
    // wrapping below when the screen is narrow. An option row stacks each
    // label over its subtitle so a long value never runs into it; the label
    // clips rather than overlap. A binding row's label wraps beside its keys.
    const bool bStacked = Row.bOption || Row.bBinding;
    const FString ValueEnglish = Row.ValueEnglish == Row.ValueJapanese ? FString() : Row.ValueEnglish;
    const bool bCodex = Model->Screen() == SoraUI::EScreen::Codex;
    const float CodexScale = bCodex && Model->Mode().Settings()
        ? SoraAccessibility::SubtitleScale(Model->Mode().Settings()->SubtitleSize()) : 1.f;
    TSharedRef<SWidget> Title = bCodex
        ? Bilingual(Row.Japanese, Row.English, SoraMenuStyle::RowText * CodexScale, SoraMenuStyle::Small * CodexScale, Label)
        : bStacked
        ? SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[Text(Row.Japanese, SoraMenuStyle::Value, Label, Row.bBinding)]
            + SVerticalBox::Slot().AutoHeight()[bEnglish ? Text(Row.English, SoraMenuStyle::Small, SoraMenuStyle::Muted, Row.bBinding) : SNullWidget::NullWidget]
        : StaticCastSharedRef<SWidget>(SNew(SWrapBox)
            .UseAllottedSize(true)
            + SWrapBox::Slot().VAlign(VAlign_Center).Padding(0, 0, 18, 0)[Text(Row.Japanese, SoraMenuStyle::RowText, Label)]
            + SWrapBox::Slot().VAlign(VAlign_Center).Padding(0, 4, 0, 0)
            [
                bEnglish ? Text(Row.English, SoraMenuStyle::Small, SoraMenuStyle::Muted) : SNullWidget::NullWidget
            ]);
    TSharedRef<SHorizontalBox> Line = SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth()
        [
            SNew(SBox)
            .WidthOverride(6.f)
            [
                SNew(SImage).Image(MenuWhite()).ColorAndOpacity(bFocused ? SoraMenuStyle::Gold : FLinearColor::Transparent)
            ]
        ]
        + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(20, bStacked ? 2 : 8, 12, bStacked ? 2 : 8)
        [
            SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)[Title]
        ];
    if (Row.bBinding)
    {
        // The keyboard-or-mouse key and the pad button, in fixed columns.
        const auto Cap = [this, &Row, Label](int32 Slot) -> TSharedRef<SWidget>
        {
            return SNew(SBox)
                .WidthOverride(SoraMenuStyle::KeyColumn)
                .HAlign(HAlign_Left)
                [
                    SNew(SBorder).BorderImage(&KeyBrush).Padding(FMargin(14, 2))[Text(Row.Keys[Slot], SoraMenuStyle::Body, Label)]
                ];
        };
        Line->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8, 4, 12, 4)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth()[Cap(0)]
            + SHorizontalBox::Slot().AutoWidth().Padding(12, 0, 0, 0)[Cap(1)]
        ];
    }
    else if (Row.bOption || !Row.ValueJapanese.IsEmpty())
    {
        const auto Arrow = [this, Weak, Index, &Row](const TCHAR* Glyph, SoraUI::ECommand Direction) -> TSharedRef<SWidget>
        {
            if (!Row.bOption)
                return SNullWidget::NullWidget;
            return SNew(SBorder)
                .BorderImage(MenuWhite())
                .BorderBackgroundColor(FLinearColor::Transparent)
                .Padding(FMargin(10, 2))
                .OnMouseButtonDown_Lambda([Weak, Index, Direction](const FGeometry&, const FPointerEvent& Event)
                {
                    if (Event.GetEffectingButton() != EKeys::LeftMouseButton || !Weak.IsValid())
                        return FReply::Unhandled();
                    Weak->Click(Index, Direction);
                    return FReply::Handled();
                })
                [
                    Text(Glyph, SoraMenuStyle::Value, Row.bEnabled ? SoraMenuStyle::Gold : SoraMenuStyle::Muted)
                ];
        };
        const FLinearColor ValueColor = Row.bEnabled ? SoraMenuStyle::Teal : SoraMenuStyle::Muted;
        TSharedRef<SWidget> Value = bStacked
            ? SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[Text(Row.ValueJapanese, SoraMenuStyle::Value, ValueColor)]
                + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
                [
                    bEnglish && !ValueEnglish.IsEmpty() ? Text(ValueEnglish, SoraMenuStyle::Small, SoraMenuStyle::Muted) : SNullWidget::NullWidget
                ]
            : StaticCastSharedRef<SWidget>(SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Text(Row.ValueJapanese, SoraMenuStyle::Value, ValueColor)]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(12, 4, 0, 0)
                [
                    bEnglish && !ValueEnglish.IsEmpty() ? Text(ValueEnglish, SoraMenuStyle::Small, SoraMenuStyle::Muted) : SNullWidget::NullWidget
                ]);
        Line->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0, 12, 0)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Arrow(TEXT("◀"), SoraUI::ECommand::Left)]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8, 0)[Value]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Arrow(TEXT("▶"), SoraUI::ECommand::Right)]
        ];
    }
    return SNew(SBorder)
        .BorderImage(MenuWhite())
        .BorderBackgroundColor(Fill)
        .Padding(0.f)
        .OnMouseMove_Lambda([Weak, Index](const FGeometry&, const FPointerEvent& Event)
        {
            // Only a real move takes focus, so rebuilt rows under a still
            // cursor never steal it from the pad or keyboard.
            if (Weak.IsValid() && !Event.GetCursorDelta().IsNearlyZero())
                Weak->Hover(Index);
            return FReply::Unhandled();
        })
        .OnMouseButtonDown_Lambda([Weak, Index](const FGeometry&, const FPointerEvent& Event)
        {
            if (Event.GetEffectingButton() != EKeys::LeftMouseButton || !Weak.IsValid())
                return FReply::Unhandled();
            Weak->Click(Index);
            return FReply::Handled();
        })
        [
            Line
        ];
}

TSharedRef<SWidget> SSoraFrontEnd::BuildHeading(const SoraUI::FRow& Row)
{
    // A section title; on the Controls screen it also names the key columns.
    TSharedRef<SHorizontalBox> Line = SNew(SHorizontalBox)
        + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Bottom).Padding(26, 18, 12, 4)
        [
            Bilingual(Row.Japanese, Row.English, SoraMenuStyle::Value, SoraMenuStyle::Small, SoraMenuStyle::Gold, true)
        ];
    if (!Row.Keys[0].IsEmpty())
        Line->AddSlot().AutoWidth().VAlign(VAlign_Bottom).Padding(8, 18, 12, 4)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth()
            [
                SNew(SBox).WidthOverride(SoraMenuStyle::KeyColumn)[Bilingual(Row.Keys[0], Row.KeysEnglish[0], SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold, true)]
            ]
            + SHorizontalBox::Slot().AutoWidth().Padding(12, 0, 0, 0)
            [
                SNew(SBox).WidthOverride(SoraMenuStyle::KeyColumn)[Bilingual(Row.Keys[1], Row.KeysEnglish[1], SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold, true)]
            ]
        ];
    return Line;
}

TSharedRef<SWidget> SSoraFrontEnd::BuildDetail()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    TSharedRef<SVerticalBox> Detail = SNew(SVerticalBox);
    if (Model->Screen() == SoraUI::EScreen::Codex)
        Detail->AddSlot().AutoHeight().Padding(0, 0, 0, 28)
            [Bilingual(Model->CodexSummary(), SoraMenuStyle::Hint, SoraMenuStyle::HintEnglish, SoraMenuStyle::Gold)];
    const TArray<SoraUI::FRow>& Rows = Model->Rows();
    if (Rows.IsValidIndex(Model->Focus()))
    {
        const SoraUI::FRow& Row = Rows[Model->Focus()];
        if (!Row.HintJapanese.IsEmpty() || !Row.HintEnglish.IsEmpty())
            Detail->AddSlot().AutoHeight()[Bilingual(Row.HintJapanese, Row.HintEnglish, SoraMenuStyle::Hint, SoraMenuStyle::HintEnglish, SoraMenuStyle::Ivory)];
    }
    if (Model->Screen() == SoraUI::EScreen::Wallet)
        Detail->AddSlot().AutoHeight().Padding(0, 28, 0, 0)[BuildWallet()];
    if (Model->Screen() == SoraUI::EScreen::Accessibility && Rows.IsValidIndex(Model->Focus()) &&
        Rows[Model->Focus()].Action == SoraUI::EAction::TelegraphPalette)
        Detail->AddSlot().AutoHeight().Padding(0, 28, 0, 0)[BuildPalette()];
    if (Model->Screen() == SoraUI::EScreen::Graphics)
        Detail->AddSlot().AutoHeight().Padding(0, 28, 0, 0)
        [
            Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Settings", "Graphics.Unmeasured", "プリセットは目標値。この機体での性能はまだ計測していない。")),
                SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Muted)
        ];
    if (Model->Screen() == SoraUI::EScreen::Practice)
        Detail->AddSlot().AutoHeight().Padding(0, 28, 0, 0)
        [
            Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Lobby.Offline", "オフラインの稽古。XOR・NFT の預け入れも報酬もない。")),
                SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Teal)
        ];
    return Detail;
}

TSharedRef<SWidget> SSoraFrontEnd::BuildPalette()
{
    // The chosen palette's two telegraph colours, as the lines appear in play.
    USoraFrontEnd* Model = FrontEnd.Get();
    const USoraSettings* Settings = Model->Mode().Settings();
    const SoraAccessibility::EPalette Palette = Settings ? Settings->TelegraphPalette() : SoraAccessibility::EPalette::Standard;
    const FText Names[] = {
        NSLOCTEXT("SoraArena.Settings", "Telegraph.Cleave", "斬撃・範囲の予兆"),
        NSLOCTEXT("SoraArena.Settings", "Telegraph.Lock", "照準・光線の予兆"),
    };
    static_assert(UE_ARRAY_COUNT(Names) == static_cast<int32>(SoraAccessibility::ETelegraph::Count), "one name per telegraph");
    TSharedRef<SVerticalBox> Swatches = SNew(SVerticalBox);
    for (int32 Kind = 0; Kind < static_cast<int32>(SoraAccessibility::ETelegraph::Count); ++Kind)
        Swatches->AddSlot().AutoHeight().Padding(0, 0, 0, 12)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [
                SNew(SBox).WidthOverride(120.f).HeightOverride(12.f)
                [
                    SNew(SImage).Image(MenuWhite()).ColorAndOpacity(SoraAccessibility::TelegraphColor(Palette, static_cast<SoraAccessibility::ETelegraph>(Kind)))
                ]
            ]
            + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(20, 0, 0, 0)
            [
                Bilingual(SoraText::Line(Names[Kind]), SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Ivory)
            ]
        ];
    return Swatches;
}

TSharedRef<SWidget> SSoraFrontEnd::BuildWallet()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    const bool bEnglish = Model->ShowsEnglish();
    const UGameInstance* Instance = Model->Mode().GetGameInstance();
    const UArenaWalletSubsystem* Wallet = Instance ? Instance->GetSubsystem<UArenaWalletSubsystem>() : nullptr;
    TSharedRef<SVerticalBox> Panel = SNew(SVerticalBox);
    const auto Add = [&Panel](const TSharedRef<SWidget>& Widget, float Top = 10.f) { Panel->AddSlot().AutoHeight().Padding(0, Top, 0, 0)[Widget]; };
    // A requested term: the Japanese label, its English label and the value.
    const auto Field = [&](const FText& Label, const FString& Value, const FLinearColor& Color)
    {
        const SoraText::FLine Name = SoraText::Line(Label);
        Add(Text(bEnglish ? FString::Printf(TEXT("%s  %s: %s"), *Name.Japanese, *Name.English, *Value) : FString::Printf(TEXT("%s: %s"), *Name.Japanese, *Value),
            SoraMenuStyle::Body, Color, true), 6.f);
    };
    const EArenaWalletState State = Wallet ? Wallet->State : EArenaWalletState::Unavailable;
    const SoraText::FLine StateLine = SoraUI::WalletStateText(State);
    Add(Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Status", "接続の状態")), SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold), 0.f);
    Add(Bilingual(Wallet && !Wallet->StatusText.IsEmpty() ? Wallet->StatusText : StateLine.Japanese, StateLine.English,
        SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Ivory));
    if (Wallet && !Wallet->ApprovedAccount.IsEmpty())
        Field(NSLOCTEXT("SoraArena.Wallet", "ApprovedAccount", "承認済みの口座"), Wallet->ApprovedAccount.Left(62), SoraMenuStyle::Teal);
    if (Wallet && Wallet->TransactionState != EArenaTransactionState::None && State != EArenaWalletState::AwaitingApproval)
    {
        const SoraText::FLine Transaction = SoraUI::TransactionStateText(Wallet->TransactionState);
        Add(Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "TransactionStatus", "署名・台帳の状態")),
            SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold), 20.f);
        Add(Bilingual(Wallet->TransactionStatusText.IsEmpty() ? Transaction.Japanese : Wallet->TransactionStatusText, Transaction.English,
            SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Ivory));
    }
    if (Wallet && Wallet->bHasUnverifiedJoinPreview)
    {
        Add(Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "JoinPreview", "参加条件の下書き（未検証）")),
            SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold), 20.f);
        Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.Stake", "申請入金額"), Wallet->JoinPreviewStake, SoraMenuStyle::Ivory);
        Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.Asset", "資産 ID（申請）"), Wallet->JoinPreviewAsset, SoraMenuStyle::Muted);
        Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.NftReservations", "NFT 装備予約（申請）"), Wallet->JoinPreviewNftReservations, SoraMenuStyle::Ivory);
        if (!Wallet->JoinPreviewNftMetadata.IsEmpty())
        {
            Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.NftMetadata", "NFT 情報ハッシュ（申請）"), Wallet->JoinPreviewNftMetadata, SoraMenuStyle::Muted);
            Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.NftRole", "装備ロール ID（申請）"), Wallet->JoinPreviewNftRole, SoraMenuStyle::Muted);
            Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.NftPolicy", "返還規則（申請）"), Wallet->JoinPreviewNftPolicy, SoraMenuStyle::Muted);
        }
        Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.FeePayer", "手数料負担の申請"), Wallet->JoinPreviewFeePayer, SoraMenuStyle::Ivory);
        Field(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.FeeCaps", "手数料上限明細（申請）"), Wallet->JoinPreviewFeeCaps, SoraMenuStyle::Ivory);
        Add(Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.Unchecked", "死亡時の損失・最大損失：未確認。台帳の試合規則・残高・所有権は未照合。")),
            SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold));
        Add(Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "JoinPreview.NoSigning", "この画面から署名・入金はできない。")),
            SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Teal));
    }
    if (Wallet && State == EArenaWalletState::AwaitingApproval && Wallet->WalletQrTexture)
    {
        // Whole texels per module keep the code sharp enough to scan.
        UTexture2D* Qr = Wallet->WalletQrTexture;
        const int32 Pixels = FMath::Max(Qr->GetSizeX(), 1);
        const float Size = Pixels * FMath::Max(1, 320 / Pixels);
        QrBrush.SetResourceObject(Qr);
        QrBrush.ImageSize = FVector2D(Size, Size);
        Add(SNew(SBox).WidthOverride(Size).HeightOverride(Size).HAlign(HAlign_Left)[SNew(SImage).Image(&QrBrush)], 20.f);
        Add(Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Qr", "接続用 QR コード（この画面のみ）")),
            SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Muted), 8.f);
    }
    Add(Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "NotADeposit", "ウォレットとの接続は資産の預け入れではない。対戦の決済と NFT の売買はまだ公開していない。")),
        SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Muted), 24.f);
    return Panel;
}

TSharedRef<SWidget> SSoraFrontEnd::BuildCredits()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    CreditsScroll = SNew(SScrollBox).ConsumeMouseWheel(EConsumeMouseWheel::Never);
    TArray<TSharedRef<SWidget>> Lines;
    if (!Model->CreditsError().IsEmpty())
        CreditsScroll->AddSlot().Padding(0, 0, 0, 12)[Bilingual(Model->CreditsError(), SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold)];
    const bool bEnglish = Model->ShowsEnglish();
    for (const SoraUI::FCreditLine& Credit : Model->Credits())
    {
        // Our own lines carry their English after a slash, as the subtitles allow.
        const FString Shown = bEnglish && !Credit.English.IsEmpty() ? Credit.Line + TEXT("  /  ") + Credit.English : Credit.Line;
        TSharedRef<SWidget> Line = Credit.Kind == SoraUI::FCreditLine::Heading ? Text(Shown, SoraMenuStyle::Hint, SoraMenuStyle::Gold, true)
            : Credit.Kind == SoraUI::FCreditLine::Entry ? Text(Shown, SoraMenuStyle::Body, SoraMenuStyle::Ivory, true)
            : Text(Shown, SoraMenuStyle::Small, SoraMenuStyle::Muted, true);
        Lines.Add(Line);
        CreditsScroll->AddSlot().Padding(0, Credit.Kind == SoraUI::FCreditLine::Heading ? 18.f : 3.f, 16.f, 0)[Line];
    }
    if (Lines.IsValidIndex(Model->CreditsScroll))
        CreditsScroll->ScrollDescendantIntoView(Lines[Model->CreditsScroll], false, EDescendantScrollDestination::TopOrLeft);
    return CreditsScroll.ToSharedRef();
}

TSharedRef<SWidget> SSoraFrontEnd::BuildBanner()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    if (Model->BannerJapanese.IsEmpty() && Model->BannerEnglish.IsEmpty())
        return SNullWidget::NullWidget;
    return SNew(SBorder)
        .BorderImage(MenuWhite())
        .BorderBackgroundColor(FLinearColor(.20f, .13f, .04f, .92f))
        .Padding(FMargin(20, 12))
        [
            Bilingual(Model->BannerJapanese, Model->BannerEnglish, SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Gold)
        ];
}

TSharedRef<SWidget> SSoraFrontEnd::Prompt(SoraUI::ECommand Command, const FText& Label)
{
    const FString Key = SoraUI::PromptKey(Command, FrontEnd->Device());
    if (Key.IsEmpty())
        return SNullWidget::NullWidget;
    TWeakObjectPtr<USoraFrontEnd> Weak = FrontEnd;
    const bool bEnglish = FrontEnd->ShowsEnglish();
    const SoraText::FLine Line = SoraText::Line(Label);
    return SNew(SBorder)
        .BorderImage(MenuWhite())
        .BorderBackgroundColor(FLinearColor::Transparent)
        .Padding(FMargin(0, 0, 32, 0))
        .OnMouseButtonDown_Lambda([Weak, Command](const FGeometry&, const FPointerEvent& Event)
        {
            if (Event.GetEffectingButton() != EKeys::LeftMouseButton || !Weak.IsValid())
                return FReply::Unhandled();
#if WITH_DEV_AUTOMATION_TESTS
            SoraFrontEndInputTrace::FScope InputTrace(Weak.Get(), TEXT("slate-prompt-button"), Event.GetEffectingButton().GetFName());
#endif
            Weak->NoteDevice(SoraUI::EDevice::KeyboardMouse);
            Weak->Command(Command);
            return FReply::Handled();
        })
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [
                SNew(SBorder).BorderImage(&KeyBrush).Padding(FMargin(14, 4))[Text(Key, SoraMenuStyle::Small, SoraMenuStyle::Ivory)]
            ]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(12, 0, 0, 0)[Text(Line.Japanese, SoraMenuStyle::Body, SoraMenuStyle::Ivory)]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(10, 2, 0, 0)
            [
                bEnglish ? Text(Line.English, SoraMenuStyle::Small, SoraMenuStyle::Muted) : SNullWidget::NullWidget
            ]
        ];
}

TSharedRef<SWidget> SSoraFrontEnd::BuildCodexReader()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    const auto* Entry = Model->SelectedCodexEntry();
    if (!Entry) return SNullWidget::NullWidget;
    const auto* Settings = Model->Mode().Settings();
    const float Scale = Settings ? SoraAccessibility::SubtitleScale(Settings->SubtitleSize()) : 1.f;
    // Wrap against the allotted viewport, at the player's selected size. The
    // title and both complete bodies are inside the same explicitly scrolled
    // region, so extra-large text never covers the Back row or key prompts.
    CodexContent = SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()[Bilingual(Entry->Context, SoraMenuStyle::Body * Scale, SoraMenuStyle::Small * Scale, SoraMenuStyle::Muted)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 16, 0, 32)[Bilingual(Entry->Title, 36.f * Scale, 28.f * Scale, SoraMenuStyle::Gold)]
        + SVerticalBox::Slot().AutoHeight()[Bilingual(Entry->Body, 28.f * Scale, 24.f * Scale, SoraMenuStyle::Ivory)];
    return SNew(SBox).HAlign(HAlign_Center)
        [SNew(SBox).MaxDesiredWidth(1120.f)
        [SAssignNew(CodexScroll, SScrollBox)
            .ConsumeMouseWheel(EConsumeMouseWheel::Never)
            .ScrollBarVisibility(EVisibility::Visible)
            .OnUserScrolled_Lambda([this](float Offset)
            {
                if (FrontEnd.IsValid() && CodexScroll)
                {
                    const float End = CodexScroll->GetScrollOffsetOfEnd();
                    FrontEnd->SetCodexScrollFraction(End > 0.f ? Offset / End : 0.f);
                }
            })
            + SScrollBox::Slot().Padding(0, 0, 20, 32)
            [CodexContent.ToSharedRef()]
        ]];
}

TSharedRef<SWidget> SSoraFrontEnd::BuildPrompts()
{
    USoraFrontEnd* Model = FrontEnd.Get();
    const SoraUI::EScreen Screen = Model->Screen();
    TSharedRef<SHorizontalBox> Prompts = SNew(SHorizontalBox);
    const auto Add = [&](SoraUI::ECommand Command, const FText& Label)
    {
        Prompts->AddSlot().AutoWidth().VAlign(VAlign_Center)[Prompt(Command, Label)];
    };
    const TArray<SoraUI::FRow>& Rows = Model->Rows();
    const SoraUI::FRow* Focused = Rows.IsValidIndex(Model->Focus()) ? &Rows[Model->Focus()] : nullptr;
    if (Screen == SoraUI::EScreen::Capture)
    {
        // Every other key is the new binding; only Esc or Start cancels.
        Add(SoraUI::ECommand::Start, NSLOCTEXT("SoraArena.Menu", "Cancel", "やめる"));
        return Prompts;
    }
    if (Screen == SoraUI::EScreen::CodexEntry)
    {
        Add(SoraUI::ECommand::Up, NSLOCTEXT("SoraArena.Codex", "ScrollUp", "上へ"));
        Add(SoraUI::ECommand::Down, NSLOCTEXT("SoraArena.Codex", "ScrollDown", "下へ"));
        Add(SoraUI::ECommand::Back, NSLOCTEXT("SoraArena.Menu", "Back", "戻る"));
        return Prompts;
    }
    if (Screen == SoraUI::EScreen::Credits)
        Add(SoraUI::ECommand::Down, NSLOCTEXT("SoraArena.Menu", "Prompt.Scroll", "送る"));
    else if (Focused && Focused->bOption)
        Add(SoraUI::ECommand::Right, NSLOCTEXT("SoraArena.Menu", "Prompt.Change", "変更"));
    if (Focused && Focused->bBinding)
        Add(SoraUI::ECommand::Accept, NSLOCTEXT("SoraArena.Menu", "Prompt.Rebind", "割り当て"));
    else
        Add(SoraUI::ECommand::Accept, NSLOCTEXT("SoraArena.Menu", "Prompt.Select", "決定"));
    if (Screen == SoraUI::EScreen::Pause)
        Add(SoraUI::ECommand::Back, NSLOCTEXT("SoraArena.Menu", "Pause.Resume", "再開"));
    else if (Screen == SoraUI::EScreen::Main && !Model->IsPauseContext())
        Add(SoraUI::ECommand::Back, NSLOCTEXT("SoraArena.Menu", "Prompt.Title", "タイトルへ"));
    else
        Add(SoraUI::ECommand::Back, NSLOCTEXT("SoraArena.Menu", "Back", "戻る"));
    return Prompts;
}

TSharedRef<SWidget> SSoraFrontEnd::BuildNotes(bool bKeyVisual)
{
    TSharedRef<SVerticalBox> Notes = SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
        [
            Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Note.OfflineBuild", "オフライン開発版・XOR と NFT の送金なし")),
                SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Muted)
        ];
    if (bKeyVisual && TitleArt.IsValid())
        Notes->AddSlot().AutoHeight().HAlign(HAlign_Right).Padding(0, 6, 0, 0)
        [
            Bilingual(SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Note.KeyVisual", "背景は生成キービジュアル（ゲーム画面ではない）")),
                SoraMenuStyle::Body, SoraMenuStyle::Small, SoraMenuStyle::Muted)
        ];
    return Notes;
}

bool FSoraInputDeviceTracker::HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent)
{
    if (USoraFrontEnd* Model = FrontEnd.Get())
        Model->NoteDevice(SoraUI::DeviceForKey(InKeyEvent.GetKey()));
    return false;
}

bool FSoraInputDeviceTracker::HandleAnalogInputEvent(FSlateApplication& SlateApp, const FAnalogInputEvent& InAnalogInputEvent)
{
    // A resting stick reports small values; only a deliberate push counts.
    if (USoraFrontEnd* Model = FrontEnd.Get())
        if (InAnalogInputEvent.GetKey().IsGamepadKey() && FMath::Abs(InAnalogInputEvent.GetAnalogValue()) > .35f)
            Model->NoteDevice(SoraUI::EDevice::Gamepad);
    return false;
}

bool FSoraInputDeviceTracker::HandleMouseMoveEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent)
{
    if (USoraFrontEnd* Model = FrontEnd.Get())
        if (MouseEvent.GetCursorDelta().SizeSquared() > 4.f)
            Model->NoteDevice(SoraUI::EDevice::KeyboardMouse);
    return false;
}

bool FSoraInputDeviceTracker::HandleMouseButtonDownEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent)
{
    if (USoraFrontEnd* Model = FrontEnd.Get())
        Model->NoteDevice(SoraUI::EDevice::KeyboardMouse);
    return false;
}
