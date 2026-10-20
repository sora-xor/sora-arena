#pragma once

#if WITH_DEV_AUTOMATION_TESTS
#include "CoreMinimal.h"
#include "Layout/SlateRect.h"
#include "Fonts/SlateFontInfo.h"

class STextBlock;
class SWidget;

// Two labels in the rendered credits fixture only. Paint invocation and valid
// geometry are diagnostic evidence; neither proves visible glyph pixels.
struct FSoraCreditsLabelProbe
{
    FString Language;
    FString ExpectedText;
    TWeakPtr<STextBlock> Widget;
    uint32 PaintCalls = 0;
    uint64 LastPaintFrame = 0;
    FSlateRect PaintBounds{0, 0, 0, 0};
    FSlateRect CullingBounds{0, 0, 0, 0};
    TOptional<FSlateRect> ScissorBounds;
    bool bStencilClip = false;
    bool bParentEnabled = false;
    FLinearColor PaintTint = FLinearColor::Transparent;
};

TSharedRef<SWidget> SoraCreditsProbeText(const FString& Text, const FSlateFontInfo& Font,
    const FLinearColor& Color, bool bWrap, const TSharedRef<FSoraCreditsLabelProbe>& Probe);

// Logs one bounded snapshot and checks the real label's text, allocation,
// clipping and paint invocation, without touching font or invalidation policy.
bool SoraInspectCreditsLabel(const FSoraCreditsLabelProbe& Probe, const FSlateRect& RowBounds,
    FString& Diagnostic);
#endif
