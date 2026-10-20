#include "UI/SoraCreditsRowDiagnostics.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Rendering/DrawElements.h"
#include "Widgets/Text/STextBlock.h"

class SSoraCreditsProbeText;
template <>
struct TWidgetTypeTraits<SSoraCreditsProbeText> : TWidgetTypeTraits<STextBlock>
{
};

class SSoraCreditsProbeText : public STextBlock
{
public:
    SLATE_BEGIN_ARGS(SSoraCreditsProbeText)
    {
        // Match STextBlock's named-argument default as well as its paint path.
        _Clipping = EWidgetClipping::OnDemand;
    }
        SLATE_ARGUMENT(FString, Text)
        SLATE_ARGUMENT(FSlateFontInfo, Font)
        SLATE_ARGUMENT(FLinearColor, Color)
        SLATE_ARGUMENT(bool, Wrap)
        SLATE_ARGUMENT(TSharedPtr<FSoraCreditsLabelProbe>, Probe)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args)
    {
        Probe = Args._Probe;
        STextBlock::Construct(STextBlock::FArguments()
            .Text(FText::FromString(Args._Text)).Font(Args._Font)
            .ColorAndOpacity(FSlateColor(Args._Color)).AutoWrapText(Args._Wrap));
    }

    virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Cull,
        FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool bEnabled) const override
    {
        // Observe the same incoming paint arguments, then call the unchanged
        // STextBlock path. No cache flush, forced repaint or alternate font.
        ++Probe->PaintCalls;
        Probe->LastPaintFrame = GFrameCounter;
        Probe->PaintBounds = Geometry.GetRenderBoundingRect();
        Probe->CullingBounds = Cull;
        Probe->bParentEnabled = bEnabled;
        Probe->PaintTint = Style.GetColorAndOpacityTint() * GetColorAndOpacity().GetColor(Style);
        Probe->ScissorBounds.Reset();
        Probe->bStencilClip = false;
        const TOptional<FSlateClippingState> Clip = Elements.GetClippingState();
        if (Clip.IsSet())
        {
            if (Clip->ScissorRect.IsSet())
                Probe->ScissorBounds = Clip->ScissorRect->GetBoundingBox();
            else
                Probe->bStencilClip = true;
        }
        return STextBlock::OnPaint(Args, Geometry, Cull, Elements, Layer, Style, bEnabled);
    }
private:
    TSharedPtr<FSoraCreditsLabelProbe> Probe;
};

namespace
{
bool Contains(const FSlateRect& Outer, const FSlateRect& Inner)
{
    constexpr float Rounding = .5f;
    return Inner.Left >= Outer.Left - Rounding && Inner.Top >= Outer.Top - Rounding &&
        Inner.Right <= Outer.Right + Rounding && Inner.Bottom <= Outer.Bottom + Rounding;
}

FString DescribeCreditsRect(const FSlateRect& Value)
{
    return FString::Printf(TEXT("[%.2f,%.2f,%.2f,%.2f]"), Value.Left, Value.Top, Value.Right, Value.Bottom);
}
}

TSharedRef<SWidget> SoraCreditsProbeText(const FString& Text, const FSlateFontInfo& Font,
    const FLinearColor& Color, bool bWrap, const TSharedRef<FSoraCreditsLabelProbe>& Probe)
{
    TSharedRef<SSoraCreditsProbeText> Widget = SNew(SSoraCreditsProbeText)
        .Text(Text).Font(Font).Color(Color).Wrap(bWrap).Probe(Probe);
    Probe->Widget = Widget;
    return Widget;
}

bool SoraInspectCreditsLabel(const FSoraCreditsLabelProbe& Probe, const FSlateRect& RowBounds,
    FString& Diagnostic)
{
    const TSharedPtr<STextBlock> Widget = Probe.Widget.Pin();
    if (!Widget)
    {
        Diagnostic = FString::Printf(TEXT("language=%s widget_missing=1 glyph_pixels_verified=0"), *Probe.Language);
        return false;
    }
    const FString ActualText = Widget->GetText().ToString();
    const FSlateRect Cached = Widget->GetCachedGeometry().GetRenderBoundingRect();
    const FVector2D Desired = Widget->GetDesiredSize();
    const FSlateFontInfo Font = Widget->GetFont();
    const bool bPositive = Probe.PaintBounds.Right > Probe.PaintBounds.Left &&
        Probe.PaintBounds.Bottom > Probe.PaintBounds.Top && Desired.X > 0 && Desired.Y > 0;
    const bool bInsideRow = Contains(RowBounds, Probe.PaintBounds);
    const bool bInsideCull = Contains(Probe.CullingBounds, Probe.PaintBounds);
    const bool bInsideScissor = !Probe.ScissorBounds.IsSet() || Contains(*Probe.ScissorBounds, Probe.PaintBounds);
    const bool bVisible = Widget->GetVisibility().IsVisible() && Widget->GetRenderOpacity() > 0 &&
        Probe.PaintTint.A > 0;
    Diagnostic = FString::Printf(
        TEXT("language=%s expected=\"%s\" actual=\"%s\" widget=%p font_object=%s font_size=%.2f face=%s desired=[%.2f,%.2f] cached=%s paint=%s row=%s cull=%s scissor=%s stencil=%d visible=%d opacity=%.3f tint=[%.3f,%.3f,%.3f,%.3f] parent_enabled=%d paint_calls=%u last_paint_frame=%llu current_frame=%llu inside_row=%d inside_cull=%d inside_scissor=%d glyph_pixels_verified=0"),
        *Probe.Language, *Probe.ExpectedText, *ActualText, Widget.Get(), *GetPathNameSafe(Font.FontObject), Font.Size,
        *Font.TypefaceFontName.ToString(), Desired.X, Desired.Y, *DescribeCreditsRect(Cached), *DescribeCreditsRect(Probe.PaintBounds), *DescribeCreditsRect(RowBounds),
        *DescribeCreditsRect(Probe.CullingBounds), Probe.ScissorBounds.IsSet() ? *DescribeCreditsRect(*Probe.ScissorBounds) : TEXT("<none>"),
        Probe.bStencilClip ? 1 : 0, bVisible ? 1 : 0, Widget->GetRenderOpacity(),
        Probe.PaintTint.R, Probe.PaintTint.G, Probe.PaintTint.B, Probe.PaintTint.A, Probe.bParentEnabled ? 1 : 0,
        Probe.PaintCalls, static_cast<unsigned long long>(Probe.LastPaintFrame), static_cast<unsigned long long>(GFrameCounter),
        bInsideRow ? 1 : 0, bInsideCull ? 1 : 0, bInsideScissor ? 1 : 0);
    return !Probe.ExpectedText.IsEmpty() && ActualText == Probe.ExpectedText && bPositive && bVisible &&
        Probe.PaintCalls > 0 && bInsideRow && bInsideCull && bInsideScissor && !Probe.bStencilClip;
}
#endif
