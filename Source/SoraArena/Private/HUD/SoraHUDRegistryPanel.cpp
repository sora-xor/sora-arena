#include "HUD/SoraHUDPanels.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "Engine/Texture2D.h"
#include "Engine/Canvas.h"

bool SoraHUDPanels::ShowsRegistry(const ASoraGameMode& Mode)
{
    return Mode.bCampaign&&!Mode.bDeterministicPractice&&!Mode.bDefeated&&Mode.bChapterComplete&&Mode.Campaign()->ActiveChapter();
}
namespace
{
// Use the same static font measure as UCanvas::TextSize, including its pixel
// rounding. It also works between draw calls in the capture verification.
FVector2D RegistryTextSize(ASoraHUD& HUD,const FString& Text,float Scale)
{
    int32 Width=0,Height=0;
    UCanvas::ClippedStrLen(HUD.JapaneseFontObject(),Scale,Scale,Width,Height,Text);
    return FVector2D(Width,Height);
}
struct FTextBlock
{
    TArray<FString> Lines;
    FString Source;
    float Scale=0,Leading=0,Width=0;
    FLinearColor Color;
    float Height() const { return Lines.Num()*Leading; }
    void Draw(ASoraHUD& HUD,float X,float& Y) const
    {
        for(const FString& Line:Lines) { HUD.Label(Line,X,Y,Scale,Color); Y+=Leading; }
    }
};
FTextBlock Wrap(ASoraHUD& HUD,const FString& Text,float Scale,float Leading,float Width,FLinearColor Color)
{
    FTextBlock Block;
    Block.Source=Text; Block.Scale=Scale; Block.Leading=Leading; Block.Width=Width; Block.Color=Color;
    FString Line;
    for(int32 Index=0;Index<Text.Len();++Index)
    {
        const FString Character=Text.Mid(Index,1);
        if(Text[Index]=='\n'||(!Line.IsEmpty()&&RegistryTextSize(HUD,Line+Character,Scale).X>Width))
        {
            Block.Lines.Add(Line); Line.Empty();
        }
        if(Text[Index]!='\n') Line+=Character;
    }
    if(!Line.IsEmpty()) Block.Lines.Add(Line);
    for(const FString& Wrapped:Block.Lines)
        Block.Leading=FMath::Max(Block.Leading,static_cast<float>(RegistryTextSize(HUD,Wrapped,Scale).Y)+4.f);
    return Block;
}
struct FInspectionLayout
{
    float Width=0,Height=0,TallyWidth=0,Gap=0,CellWidth=0,CellHeight=0;
    TArray<FTextBlock> Japanese,English;
};
FInspectionLayout BuildInspectionLayout(const FSoraHUDFrame& F)
{
    FInspectionLayout Mark;
    const float S=F.S,JapaneseScale=FMath::Max(.36f*S,.55f),EnglishScale=FMath::Max(.32f*S,.5f);
    const SoraText::FLine Roles[]={
        SoraText::Line(NSLOCTEXT("SoraArena.Registry","Maker","作り手")),
        SoraText::Line(NSLOCTEXT("SoraArena.Registry","Receiver","受け手")),
        SoraText::Line(NSLOCTEXT("SoraArena.Registry","Inspector","改め役"))};
    Mark.TallyWidth=64*S; Mark.Gap=8*S; Mark.CellWidth=64*S; Mark.CellHeight=40*S;
    for(const SoraText::FLine& Role:Roles)
    {
        Mark.CellWidth=FMath::Max(Mark.CellWidth,static_cast<float>(RegistryTextSize(F.HUD,Role.Japanese,JapaneseScale).X)+16*S);
        if(F.Mode.bEnglishSubtitles)
            Mark.CellWidth=FMath::Max(Mark.CellWidth,static_cast<float>(RegistryTextSize(F.HUD,Role.English,EnglishScale).X)+16*S);
    }
    float EnglishHeight=0;
    for(const SoraText::FLine& Role:Roles)
    {
        Mark.Japanese.Add(Wrap(F.HUD,Role.Japanese,JapaneseScale,20*S,Mark.CellWidth-8*S,F.Ivory));
        Mark.CellHeight=FMath::Max(Mark.CellHeight,Mark.Japanese.Last().Height()+8*S);
        if(F.Mode.bEnglishSubtitles)
        {
            Mark.English.Add(Wrap(F.HUD,Role.English,EnglishScale,20*S,Mark.CellWidth-8*S,F.Muted));
            EnglishHeight=FMath::Max(EnglishHeight,Mark.English.Last().Height());
        }
    }
    Mark.Width=Mark.TallyWidth+16*S+3*Mark.CellWidth+2*Mark.Gap;
    Mark.Height=8*S+FMath::Max(48*S,Mark.CellHeight+EnglishHeight)+8*S;
    return Mark;
}
void DrawInspection(const FSoraHUDFrame& F,const FInspectionLayout& Mark,float X,float Y)
{
    ASoraHUD& HUD=F.HUD;
    const float S=F.S;
    const FLinearColor Seal(.73f,.22f,.13f),Wood(.57f,.39f,.18f);
    // Functional split-tally mark: the existing crest crosses two pieces.
    HUD.Panel(X,Y+8*S,30*S,48*S,Wood);
    HUD.Panel(X+34*S,Y+8*S,30*S,48*S,Wood);
    if(UTexture2D* Logo=HUD.ResistanceLogo())
    {
        HUD.DrawTexture(Logo,X,Y+15*S,30*S,32*S,0,0,.5f,1,Seal);
        HUD.DrawTexture(Logo,X+34*S,Y+15*S,30*S,32*S,.5f,0,.5f,1,Seal);
    }
    for(int32 Index=0;Index<Mark.Japanese.Num();++Index)
    {
        const float At=X+Mark.TallyWidth+16*S+Index*(Mark.CellWidth+Mark.Gap);
        HUD.Panel(At,Y+8*S,Mark.CellWidth,Mark.CellHeight,Seal);
        HUD.Panel(At+2*S,Y+10*S,Mark.CellWidth-4*S,Mark.CellHeight-4*S,FLinearColor(.04f,.03f,.025f));
        float TextY=Y+12*S;
        Mark.Japanese[Index].Draw(HUD,At+4*S,TextY);
        if(Mark.English.IsValidIndex(Index))
        {
            TextY=Y+8*S+Mark.CellHeight;
            Mark.English[Index].Draw(HUD,At+4*S,TextY);
        }
    }
}
struct FRegistryRowLayout
{
    TArray<FTextBlock> Text;
    float Height=0;
    bool bTally=false;
};
struct FRegistryLayout
{
    float Width=0,Height=0,Left=0,Top=0,HeaderHeight=0;
    TArray<FTextBlock> Chapter,Footer;
    TArray<FRegistryRowLayout> Rows;
    FInspectionLayout Inspection;
};
FRegistryLayout BuildRegistryLayout(const FSoraHUDFrame& F)
{
    FRegistryLayout Page;
    ASoraHUD& HUD=F.HUD;
    const float S=F.S;
    const bool English=F.Mode.bEnglishSubtitles;
    const FSoraChapter* Chapter=F.Mode.Campaign()->ActiveChapter();
    Page.Width=FMath::Min(1240*S,F.W-80*S);
    if(!Chapter) return Page;
    Page.Inspection=BuildInspectionLayout(F);
    Page.Chapter.Add(Wrap(HUD,Chapter->Title,FMath::Max(.6f*S,.6f),32*S,Page.Width-160*S,F.Teal));
    if(English) Page.Chapter.Add(Wrap(HUD,Chapter->TitleEnglish,FMath::Max(.4f*S,.5f),24*S,Page.Width-160*S,F.Muted));
    const SoraText::FLine Result=SoraHUDPanels::ResultHeadline(F.Mode);
    Page.Chapter.Add(Wrap(HUD,English?Result.Japanese+TEXT(" / ")+Result.English:Result.Japanese,
        FMath::Max(.4f*S,.55f),24*S,Page.Width-160*S,F.Ivory));
    Page.HeaderHeight=72*S;
    for(const FTextBlock& Block:Page.Chapter) Page.HeaderHeight+=Block.Height();
    Page.HeaderHeight=FMath::Max(142*S,Page.HeaderHeight+14*S);
    Page.Height=Page.HeaderHeight;
    for(const FSoraRegistryRow& Row:F.Mode.Campaign()->RegistryRows())
    {
        FRegistryRowLayout Item;
        const float Width=Page.Width-72*S-(Row.HasSplitTally()?Page.Inspection.Width+18*S:0);
        Item.Text.Add(Wrap(HUD,Row.Entry.Japanese(),FMath::Max(.62f*S,.6f),32*S,Width,F.Ivory));
        if(English) Item.Text.Add(Wrap(HUD,Row.Entry.English(),FMath::Max(.42f*S,.5f),28*S,Width,F.Muted));
        const SoraText::FLine Status=SoraRegistry::Status(Row.State);
        // Keep the complete bilingual status on one wrapped line at a readable
        // floor, leaving room for all four entries at the smaller viewport.
        Item.Text.Add(Wrap(HUD,English?Status.Japanese+TEXT(" / ")+Status.English:Status.Japanese,
            FMath::Max(.36f*S,.55f),24*S,Width,F.Gold));
        for(const FTextBlock& Block:Item.Text) Item.Height+=Block.Height();
        Item.Height=FMath::Max((English?110.f:84.f)*S,Item.Height+14*S);
        Item.bTally=Row.HasSplitTally();
        if(Item.bTally) Item.Height=FMath::Max(Item.Height,Page.Inspection.Height+8*S);
        Page.Height+=Item.Height;
        Page.Rows.Add(MoveTemp(Item));
    }
    const SoraText::FLine Next=SoraText::Format(NSLOCTEXT("SoraArena.HUD","Result.Next","{Enter}  続ける    |    {Menu}  メニュー"),
        {{TEXT("Enter"),SoraUI::ActionKey(&HUD,TEXT("Enter"))},{TEXT("Menu"),SoraUI::ActionKey(&HUD,TEXT("Menu"))}});
    Page.Footer.Add(Wrap(HUD,Next.Japanese,FMath::Max(.45f*S,.55f),27*S,Page.Width-72*S,F.Muted));
    if(English) Page.Footer.Add(Wrap(HUD,Next.English,FMath::Max(.36f*S,.5f),24*S,Page.Width-72*S,F.Muted));
    for(const FTextBlock& Block:Page.Footer) Page.Height+=Block.Height();
    Page.Height+=24*S;
    Page.Left=(F.W-Page.Width)*.5f; Page.Top=(F.H-Page.Height)*.5f;
    return Page;
}
}

bool SoraHUDPanels::RegistryLayoutFits(const FSoraHUDFrame& F,FString& Why)
{
    const FRegistryLayout Page=BuildRegistryLayout(F);
    Why.Empty();
    if(Page.Rows.IsEmpty()||RegistryTextSize(F.HUD,TEXT("米"),F.S).X<=0)
        Why=TEXT("Registry rows or font measurements are missing");
    else if(Page.Left<0||Page.Top<87*F.S||Page.Left+Page.Width>F.W||Page.Top+Page.Height>F.H-24*F.S)
        Why=TEXT("Registry page exceeds its viewport margins");
    const auto Check=[&](const FTextBlock& Block)
    {
        FString Joined;
        for(const FString& Line:Block.Lines)
        {
            Joined+=Line;
            const FVector2D Size=RegistryTextSize(F.HUD,Line,Block.Scale);
            if(Size.X>Block.Width+1.f) Why=TEXT("Registry text exceeds its column");
            if(Size.Y+3.f>Block.Leading) Why=TEXT("Registry text exceeds its measured line height");
        }
        if(Joined!=Block.Source.Replace(TEXT("\n"),TEXT(""))) Why=TEXT("Registry wrapping dropped authored text");
        if(Block.Scale<.5f) Why=TEXT("Registry text is below its readable scale floor");
    };
    for(const FTextBlock& Block:Page.Chapter) Check(Block);
    for(const FRegistryRowLayout& Row:Page.Rows) for(const FTextBlock& Block:Row.Text) Check(Block);
    for(const FTextBlock& Block:Page.Footer) Check(Block);
    for(const FTextBlock& Block:Page.Inspection.Japanese) Check(Block);
    for(const FTextBlock& Block:Page.Inspection.English) Check(Block);
    return Why.IsEmpty();
}

void SoraHUDPanels::DrawRegistry(const FSoraHUDFrame& F)
{
    ASoraHUD& HUD=F.HUD;
    if(!F.Mode.Campaign()->ActiveChapter()) return;
    const FRegistryLayout Page=BuildRegistryLayout(F);
    const float S=F.S,X=Page.Left+36*S;
    HUD.Panel(Page.Left,Page.Top,Page.Width,Page.Height,FLinearColor(.012f,.026f,.034f,.97f));
    HUD.Panel(Page.Left,Page.Top,5*S,Page.Height,F.Teal);
    const SoraText::FLine Title=SoraText::Line(NSLOCTEXT("SoraArena.Registry","Title","生産改帳"));
    HUD.Label(Title.Japanese,X,Page.Top+20*S,.95f*S,F.Ivory);
    if(F.Mode.bEnglishSubtitles) HUD.Label(Title.English,X+200*S,Page.Top+35*S,FMath::Max(.46f*S,.55f),F.Muted);
    float Y=Page.Top+72*S;
    for(const FTextBlock& Block:Page.Chapter) Block.Draw(HUD,X,Y);
    if(UTexture2D* Logo=HUD.ResistanceLogo())
        HUD.DrawTexture(Logo,Page.Left+Page.Width-105*S,Page.Top+25*S,65*S,65*S,0,0,1,1,FLinearColor(.73f,.22f,.13f));
    Y=Page.Top+Page.HeaderHeight;
    for(const FRegistryRowLayout& Row:Page.Rows)
    {
        HUD.Panel(X,Y-8*S,Page.Width-72*S,1*S,FLinearColor(.2f,.27f,.28f));
        float TextY=Y;
        for(const FTextBlock& Block:Row.Text) Block.Draw(HUD,X,TextY);
        if(Row.bTally) DrawInspection(F,Page.Inspection,Page.Left+Page.Width-36*S-Page.Inspection.Width,Y);
        Y+=Row.Height;
    }
    for(const FTextBlock& Block:Page.Footer) Block.Draw(HUD,X,Y);
}
