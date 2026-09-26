#pragma once
#include "SoraFrontEnd.h"

// Row builders shared by the front end's screens. Labels and hints are
// NSLOCTEXT; the row keeps their Japanese and English.
namespace SoraUI
{
// A value an option row steps through, and the hint shown while it is chosen.
struct FChoice
{
    FText Label;
    FText Hint;
};
inline FRow NewMenuRow(EAction Action, const FText& Label, const FText& Hint = FText::GetEmpty())
{
    FRow Row;
    Row.Action = Action;
    Row.SetLabel(SoraText::Line(Label));
    if (!Hint.IsEmpty())
        Row.SetHint(SoraText::Line(Hint));
    return Row;
}
inline FRow NewOptionRow(EAction Action, const FText& Label, const SoraText::FLine& Value)
{
    FRow Row = NewMenuRow(Action, Label);
    Row.bOption = true;
    Row.SetValue(Value);
    return Row;
}
// An option row showing Choice, with its hint unless Hint replaces it.
inline FRow NewChoiceRow(EAction Action, const FText& Label, const FChoice& Choice, const FText& Hint = FText::GetEmpty())
{
    FRow Row = NewOptionRow(Action, Label, SoraText::Line(Choice.Label));
    const FText& Shown = Hint.IsEmpty() ? Choice.Hint : Hint;
    if (!Shown.IsEmpty())
        Row.SetHint(SoraText::Line(Shown));
    return Row;
}
inline FRow NewBackRow() { return NewMenuRow(EAction::Back, NSLOCTEXT("SoraArena.Menu", "Back", "戻る")); }
}
