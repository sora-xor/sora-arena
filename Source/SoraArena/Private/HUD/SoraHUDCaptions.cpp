#include "HUD/SoraHUDPanels.h"
#include "SoraCaptions.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraText.h"
#include "Engine/Canvas.h"
#include "Engine/Font.h"
#include "EngineFontServices.h"
#include "Fonts/FontCache.h"

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

FBox2D SoraHUDPanels::CaptionGlyphBounds(const FSoraHUDFrame& F,const FString& Text,float Scale)
{
    // Same glyph offsets and atlas sizes used by CanvasItem's runtime-font
    // drawing. Trim only empty font ascent/descent; selected type stays large.
    FBox2D Bounds(ForceInit);
    const auto* Font=F.HUD.JapaneseFontObject();
    if(FEngineFontServices::IsInitialized())
    {
        const auto Cache=FEngineFontServices::Get().GetFontCache();
        if(Cache.IsValid())
        {
            const auto Info=Font->GetLegacySlateFontInfo();
            auto& Characters=Cache->GetCharacterList(Info,1.f);
            const float MaxHeight=Characters.GetMaxHeight()*Scale;
            float X=0;
            for(int32 I=0;I<Text.Len();++I)
            {
                const auto Entry=Characters.GetCharacter(Text[I],Info.FontFallback);
                if(I>0&&Entry.Valid&&!FChar::IsWhitespace(Text[I]))
                {
                    const auto Previous=Characters.GetCharacter(Text[I-1],Info.FontFallback);
                    // Canvas stores scaled kerning in an int32, not a float.
                    X+=static_cast<int32>(Characters.GetKerning(Previous,Entry)*Scale);
                }
                if(Entry.Valid&&!FChar::IsWhitespace(Text[I])&&Entry.BitmapRenderScale>0)
                {
                    const FVector2D At(X+Entry.HorizontalOffset*Scale,-Entry.VerticalOffset*Scale+
                        (Entry.GlobalDescender*Scale+MaxHeight)/Entry.BitmapRenderScale);
                    Bounds+=At; Bounds+=At+FVector2D(Entry.USize*Scale*Entry.BitmapRenderScale,Entry.VSize*Scale*Entry.BitmapRenderScale);
                }
                X+=Entry.XAdvance*Scale;
            }
        }
    }
    if(!Bounds.bIsValid)
    {
        int32 W=0,H=0; UCanvas::ClippedStrLen(Font,Scale,Scale,W,H,Text);
        Bounds=FBox2D(FVector2D::ZeroVector,FVector2D(W,H));
    }
    return Bounds;
}
namespace
{
TArray<FString> CaptionLines(const FSoraHUDFrame& F,const FString& Text,float Scale,float Width,float& Leading)
{
    TArray<FString> Lines; FString Line;
    for(int32 I=0;I<Text.Len();++I)
    {
        int32 W=0,H=0;
        UCanvas::ClippedStrLen(F.HUD.JapaneseFontObject(),Scale,Scale,W,H,Line+Text.Mid(I,1));
        if(Text[I]=='\n') { Lines.Add(Line); Line.Empty(); continue; }
        if(!Line.IsEmpty()&&W>Width)
        {
            int32 Space=INDEX_NONE;
            if(Line.FindLastChar(' ',Space)&&Space>0) { Lines.Add(Line.Left(Space+1)); Line=Line.Mid(Space+1); }
            else { Lines.Add(Line); Line.Empty(); }
        }
        Line+=Text.Mid(I,1);
    }
    if(!Line.IsEmpty()) Lines.Add(Line);
    for(const auto& Part:Lines)
        Leading=FMath::Max(Leading,static_cast<float>(SoraHUDPanels::CaptionGlyphBounds(F,Part,Scale).GetSize().Y)+3.f);
    return Lines;
}
}
TArray<FSoraCaptionPanel> SoraHUDPanels::MeasureCaptions(const FSoraHUDFrame& F,float Width)
{
    TArray<FSoraCaptionPanel> Panels;
    const auto* Captions=F.bSoundCaptions?USoraCaptions::Get(&F.Mode):nullptr;
    if(!Captions||Width<=28*F.S) return Panels;
    const float Padding=14*F.S,Inner=Width-2*Padding;
    for(const auto& Caption:Captions->Live())
    {
        const auto Where=Direction(F.Mode.Hero(),Caption);
        const FString Count=Caption.Count>1?FString::Printf(TEXT(" ×%d"),Caption.Count):FString();
        const SoraText::FArg Sound(TEXT("Caption"),SoraText::FLine{Caption.Japanese+Count,Caption.English+Count});
        auto Line=Where.IsEmpty()?SoraText::Format(NSLOCTEXT("SoraArena.Captions","Caption","［{Caption}］"),{Sound}):
            SoraText::Format(NSLOCTEXT("SoraArena.Captions","CaptionFrom","［{Caption}］ {Direction}"),{Sound,{TEXT("Direction"),Where}});
        if(F.Mode.bEnglishSubtitles)
        {
            // The panel already identifies this as a sound caption. Keep
            // both sound/direction translations, with the shared repeat
            // count once instead of duplicating brackets and numerals.
            Line.Japanese=Caption.Japanese+(Where.IsEmpty()?FString():TEXT(" ")+Where.Japanese);
            Line.English=Caption.English+Count+(Where.IsEmpty()?FString():TEXT(" ")+Where.English);
        }
        float JL=F.DialogueJapaneseLineHeight,EL=F.DialogueEnglishLineHeight;
        const auto Japanese=CaptionLines(F,Line.Japanese,F.DialogueJapaneseScale,Inner,JL);
        TArray<FString> English;
        if(F.Mode.bEnglishSubtitles) English=CaptionLines(F,Line.English,F.DialogueEnglishScale,Inner,EL);
        const bool Inline=Japanese.Num()==1&&English.Num()==1&&
            F.HUD.LabelWidth(Line.Japanese,F.DialogueJapaneseScale)+10*F.S+F.HUD.LabelWidth(Line.English,F.DialogueEnglishScale)<=Inner;
        FSoraCaptionPanel Panel;
        float Y=2*F.S;
        const auto AddText=[&](const FString& Text,float X,float At,float Scale,bool English)
        {
            const auto Ink=CaptionGlyphBounds(F,Text,Scale);
            Panel.Text.Add({Text,FVector2D(X,At)-Ink.Min,Scale,English});
        };
        for(const auto& Text:Japanese) { AddText(Text,Padding,Y,F.DialogueJapaneseScale,false); Y+=JL; }
        if(Inline)
        {
            AddText(Line.English,Padding+F.HUD.LabelWidth(Line.Japanese,F.DialogueJapaneseScale)+10*F.S,2*F.S,F.DialogueEnglishScale,true);
            Y=2*F.S+FMath::Max(JL,EL);
        }
        else for(const auto& Text:English) { AddText(Text,Padding,Y,F.DialogueEnglishScale,true); Y+=EL; }
        Panel.Bounds=FBox2D(FVector2D::ZeroVector,FVector2D(Width,Y+2*F.S));
        Panels.Add(MoveTemp(Panel));
    }
    return Panels;
}
void SoraHUDPanels::DrawCaptions(const FSoraHUDFrame& Frame,const ASoraPlayerCharacter* Hero)
{
    (void)Hero;
    for(const auto& Panel:CaptionLayout(Frame).Panels)
    {
        const auto Size=Panel.Bounds.GetSize();
        Frame.HUD.Panel(Panel.Bounds.Min.X,Panel.Bounds.Min.Y,Size.X,Size.Y,FLinearColor(.013f,.027f,.033f,.86f));
        for(const auto& Text:Panel.Text)
            Frame.HUD.Label(Text.Text,Text.At.X,Text.At.Y,Text.Scale,Text.bEnglish?Frame.Muted:Frame.Ivory);
    }
}
