#include "SoraFrontEnd.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
void AddCredit(TArray<SoraUI::FCreditLine>& Out, SoraUI::FCreditLine::EKind Kind, const FString& Line, const FString& English = FString())
{
    SoraUI::FCreditLine Credit;
    Credit.Kind = Kind;
    Credit.Line = Line;
    Credit.English = English;
    Out.Add(MoveTemp(Credit));
}
void AddCredit(TArray<SoraUI::FCreditLine>& Out, SoraUI::FCreditLine::EKind Kind, const SoraText::FLine& Line)
{
    AddCredit(Out, Kind, Line.Japanese, Line.English);
}

// Markdown as the notice generator writes it: headings, tables (one entry per
// row, header and rule rows dropped), bullets and paragraphs.
void AddMarkdown(TArray<SoraUI::FCreditLine>& Out, const TArray<FString>& Lines)
{
    for (int32 Index = 0; Index < Lines.Num(); ++Index)
    {
        const FString Line = Lines[Index].TrimStartAndEnd();
        if (Line.IsEmpty())
            continue;
        if (Line.StartsWith(TEXT("#")))
        {
            FString Heading = Line;
            while (Heading.StartsWith(TEXT("#")))
                Heading.RightChopInline(1);
            AddCredit(Out, SoraUI::FCreditLine::Heading, Heading.TrimStart());
            continue;
        }
        if (Line.StartsWith(TEXT("|")))
        {
            const FString Next = Lines.IsValidIndex(Index + 1) ? Lines[Index + 1].TrimStartAndEnd() : FString();
            const bool bRule = Line.Replace(TEXT("|"), TEXT("")).Replace(TEXT("-"), TEXT("")).Replace(TEXT(":"), TEXT("")).TrimStartAndEnd().IsEmpty();
            const bool bHeader = Next.StartsWith(TEXT("|")) && Next.Contains(TEXT("---"));
            if (bRule || bHeader)
                continue;
            TArray<FString> Cells;
            Line.ParseIntoArray(Cells, TEXT("|"), true);
            TArray<FString> Kept;
            for (FString& Cell : Cells)
            {
                Cell.TrimStartAndEndInline();
                Cell.RemoveFromStart(TEXT("<"));
                Cell.RemoveFromEnd(TEXT(">"));
                if (!Cell.IsEmpty())
                    Kept.Add(Cell);
            }
            AddCredit(Out, SoraUI::FCreditLine::Entry, FString::Join(Kept, TEXT("  —  ")));
            continue;
        }
        FString Text = Line;
        if (Text.StartsWith(TEXT("- ")) || Text.StartsWith(TEXT("* ")))
            Text = TEXT("• ") + Text.RightChop(2);
        AddCredit(Out, SoraUI::FCreditLine::Text, Text.Replace(TEXT("**"), TEXT("")).Replace(TEXT("`"), TEXT("")));
    }
}
}

bool SoraUI::LoadCredits(TArray<FCreditLine>& Out, SoraText::FLine& Error)
{
    AddCredit(Out, FCreditLine::Heading, SoraText::Line(NSLOCTEXT("SoraArena.Credits", "Game", "SORA Arena: 猫柳生")));
    AddCredit(Out, FCreditLine::Entry, SoraText::Line(NSLOCTEXT("SoraArena.Credits", "MadeBy", "制作 SORA")));
    AddCredit(Out, FCreditLine::Entry, SoraText::Line(NSLOCTEXT("SoraArena.Credits", "Insignia", "紋章：SORA ロゴ")));
    AddCredit(Out, FCreditLine::Heading, SoraText::Line(NSLOCTEXT("SoraArena.Credits", "Typeface", "書体")));
    AddCredit(Out, FCreditLine::Entry, TEXT("Noto Sans CJK JP  —  SIL Open Font License 1.1  —  Content/SourceArt/Fonts/OFL.txt"));
    // Every notice the package stages; a missing directory is reported, not hidden.
    const FString Directory = FPaths::ProjectDir() / TEXT("ThirdPartyNotices");
    TArray<FString> Files;
    IFileManager::Get().FindFiles(Files, *(Directory / TEXT("*.md")), true, false);
    TArray<FString> TextFiles;
    IFileManager::Get().FindFiles(TextFiles, *(Directory / TEXT("*.txt")), true, false);
    Files.Append(TextFiles);
    Files.Sort();
    int32 Read = 0;
    for (const FString& File : Files)
    {
        TArray<FString> Lines;
        if (!FFileHelper::LoadFileToStringArray(Lines, *(Directory / File)))
            continue;
        ++Read;
        if (File.EndsWith(TEXT(".md")))
        {
            AddMarkdown(Out, Lines);
            continue;
        }
        AddCredit(Out, FCreditLine::Heading, FPaths::GetBaseFilename(File));
        for (const FString& Line : Lines)
            if (!Line.TrimStartAndEnd().IsEmpty())
                AddCredit(Out, FCreditLine::Text, Line.TrimStartAndEnd());
    }
    if (Read == 0)
    {
        Error = SoraText::Format(NSLOCTEXT("SoraArena.Credits", "Missing", "権利表記を読み込めません：{Directory}"),
            {{TEXT("Directory"), Directory}});
        return false;
    }
    return true;
}
