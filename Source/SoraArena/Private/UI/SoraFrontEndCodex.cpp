#include "SoraFrontEnd.h"
#include "SoraCampaignDirector.h"
#include "SoraCampaignRules.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"

void USoraFrontEnd::RefreshCodexEntries()
{
    DiscoveredEntries.Reset();
    const auto* Campaign = Mode().Campaign();
    const auto& Catalog = FSoraCatalog::Get();
    if (!Campaign || !Catalog.IsReady()) return;
    const uint64 Found = Campaign->CollectedMask();
    for (int32 Chapter = 0; Chapter < Catalog.Chapters.Num(); ++Chapter)
        for (const auto& Item : Catalog.Chapters[Chapter].Collectibles)
        {
            if (!(Found & SoraCampaignRules::CollectibleBit(Chapter, Item.MaskBit))) continue;
            const auto* Category = Catalog.CollectibleCategories.FindByPredicate(
                [&](const FSoraCollectibleCategory& Row) { return Row.Id == Item.Category; });
            if (!Category) continue; // The catalog normally rejects this before play.
            SoraUI::FCodexEntry Entry;
            Entry.Key = Chapter * FSoraCatalog::CollectiblesPerChapter + Item.MaskBit;
            Entry.Id = Item.Id;
            Entry.Context = SoraText::Format(NSLOCTEXT("SoraArena.Codex", "Context", "第{Chapter}章 · {Category}"),
                {{TEXT("Chapter"), Chapter + 1}, {TEXT("Category"), SoraText::FLine{Category->Japanese, Category->English}}});
            Entry.Title = Item.Title.IsEmpty()
                ? SoraText::Format(NSLOCTEXT("SoraArena.Codex", "Untitled", "第{Chapter}章 · {Category} · {Number}"),
                    {{TEXT("Chapter"), Chapter + 1}, {TEXT("Category"), SoraText::FLine{Category->Japanese, Category->English}},
                     {TEXT("Number"), Item.MaskBit + 1}})
                : SoraText::FLine{Item.Title, Item.TitleEnglish};
            Entry.Body = {Item.Codex, Item.CodexEnglish};
            DiscoveredEntries.Add(MoveTemp(Entry));
        }
    DiscoveredEntries.Sort([](const SoraUI::FCodexEntry& A, const SoraUI::FCodexEntry& B) { return A.Key < B.Key; });
    if (Campaign->HasToshiyaCodex())
    {
        SoraUI::FCodexEntry Entry;
        Entry.Key = 48;
        Entry.Id = TEXT("codex_toshiya");
        Entry.Title = SoraText::Line(NSLOCTEXT("SoraArena.Codex", "Toshiya", "通し矢"));
        Entry.Context = SoraText::Line(NSLOCTEXT("SoraArena.Codex", "Challenge", "弓の挑戦"));
        // Keep the authored implementation's explicitly provisional history
        // verbatim. The reader neither expands it nor grants the challenge.
        Entry.Body = {Campaign->ToshiyaCodex(false), Campaign->ToshiyaCodex(true)};
        DiscoveredEntries.Add(MoveTemp(Entry));
    }
}

const SoraUI::FCodexEntry* USoraFrontEnd::SelectedCodexEntry() const
{
    return DiscoveredEntries.FindByPredicate([this](const SoraUI::FCodexEntry& Entry) { return Entry.Key == CodexKey; });
}

SoraText::FLine USoraFrontEnd::CodexSummary() const
{
    const int32 Count = DiscoveredEntries.FilterByPredicate([](const SoraUI::FCodexEntry& E) { return E.Key < 48; }).Num();
    return SoraText::Format(NSLOCTEXT("SoraArena.Codex", "Summary", "収集品 {Count} / 48\n見つけた記録を選んで読む。"), {{TEXT("Count"), Count}});
}

void USoraFrontEnd::BuildCodexRows()
{
    RefreshCodexEntries();
    if (Screen() == SoraUI::EScreen::Codex)
    {
        for (const auto& Entry : DiscoveredEntries)
        {
            SoraUI::FRow Row;
            Row.Action = SoraUI::EAction::CodexEntry;
            Row.Param = Entry.Key;
            Row.SetLabel(Entry.Title);
            Row.SetHint(Entry.Context);
            RowList.Add(MoveTemp(Row));
        }
        if (DiscoveredEntries.IsEmpty())
        {
            SoraUI::FRow Row;
            Row.bEnabled = false;
            Row.SetLabel(SoraText::Line(NSLOCTEXT("SoraArena.Codex", "Empty", "まだ記録を見つけていない。")));
            RowList.Add(MoveTemp(Row));
        }
    }
    SoraUI::FRow Back;
    Back.Action = SoraUI::EAction::Back;
    Back.SetLabel(SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Back", "戻る")));
    RowList.Add(MoveTemp(Back));
}
