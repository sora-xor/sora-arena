#include "HUD/SoraHUDPanels.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "Engine/Texture2D.h"

bool SoraHUDPanels::ShowsRegistry(const ASoraGameMode& Mode)
{
    return Mode.bCampaign&&!Mode.bDeterministicPractice&&!Mode.bDefeated&&Mode.bChapterComplete&&Mode.Campaign()->ActiveChapter();
}
namespace
{
void Inspection(const FSoraHUDFrame& F,float X,float Y)
{
    ASoraHUD& HUD=F.HUD;
    const float S=F.S;
    const FLinearColor Seal(.73f,.22f,.13f),Wood(.57f,.39f,.18f);
    // Functional split-tally mark: one crest crosses the split, each half
    // remaining on its own piece. This uses the existing exact logo texture.
    HUD.Panel(X,Y+8*S,30*S,48*S,Wood);
    HUD.Panel(X+34*S,Y+8*S,30*S,48*S,Wood);
    if(UTexture2D* Logo=HUD.ResistanceLogo())
    {
        HUD.DrawTexture(Logo,X,Y+15*S,30*S,32*S,0,0,.5f,1,Seal);
        HUD.DrawTexture(Logo,X+34*S,Y+15*S,30*S,32*S,.5f,0,.5f,1,Seal);
    }
    const SoraText::FLine Roles[]={
        SoraText::Line(NSLOCTEXT("SoraArena.Registry","Maker","作り手")),
        SoraText::Line(NSLOCTEXT("SoraArena.Registry","Receiver","受け手")),
        SoraText::Line(NSLOCTEXT("SoraArena.Registry","Inspector","改め役"))};
    for(int32 Index=0;Index<3;++Index)
    {
        const float At=X+(80+58*Index)*S;
        HUD.Panel(At,Y+8*S,50*S,40*S,Seal);
        HUD.Panel(At+2*S,Y+10*S,46*S,36*S,FLinearColor(.04f,.03f,.025f));
        HUD.Label(Roles[Index].Japanese,At+4*S,Y+17*S,.29f*S,F.Ivory);
        if(F.Mode.bEnglishSubtitles) HUD.Label(Roles[Index].English,At,Y+52*S,.24f*S,F.Muted);
    }
}
}
void SoraHUDPanels::DrawRegistry(const FSoraHUDFrame& F)
{
    ASoraHUD& HUD=F.HUD;
    const auto* Campaign=F.Mode.Campaign();
    const FSoraChapter* Chapter=Campaign->ActiveChapter();
    if(!Chapter) return;
    const auto Rows=Campaign->RegistryRows();
    const bool English=F.Mode.bEnglishSubtitles;
    const float S=F.S,Width=FMath::Min(1240*S,F.W-80*S),RowHeight=(English?110.f:84.f)*S;
    const float Height=200*S+Rows.Num()*RowHeight,Left=(F.W-Width)*.5f,Top=(F.H-Height)*.5f;
    const float X=Left+36*S,TextWidth=Width-350*S;
    HUD.Panel(Left,Top,Width,Height,FLinearColor(.012f,.026f,.034f,.97f));
    HUD.Panel(Left,Top,5*S,Height,F.Teal);
    const SoraText::FLine Title=SoraText::Line(NSLOCTEXT("SoraArena.Registry","Title","生産改帳"));
    HUD.Label(Title.Japanese,X,Top+20*S,.95f*S,F.Ivory);
    if(English) HUD.Label(Title.English,X+200*S,Top+35*S,.46f*S,F.Muted);
    HUD.Label(Chapter->Title,X,Top+72*S,.6f*S,F.Teal);
    if(English) HUD.Label(Chapter->TitleEnglish,X,Top+104*S,.4f*S,F.Muted);
    if(UTexture2D* Logo=HUD.ResistanceLogo())
        HUD.DrawTexture(Logo,Left+Width-105*S,Top+25*S,65*S,65*S,0,0,1,1,FLinearColor(.73f,.22f,.13f));
    float Y=Top+142*S;
    for(const FSoraRegistryRow& Row:Rows)
    {
        HUD.Panel(X,Y-8*S,Width-72*S,1*S,FLinearColor(.2f,.27f,.28f));
        HUD.WrappedLabel(Row.Entry.Japanese(),X,Y,.62f*S,F.Ivory,TextWidth,30*S,1);
        if(English) HUD.WrappedLabel(Row.Entry.English(),X,Y+32*S,.42f*S,F.Muted,TextWidth,24*S,1);
        const SoraText::FLine Status=SoraRegistry::Status(Row.State);
        const float StatusY=Y+(English?62:34)*S;
        HUD.WrappedLabel(Status.Japanese,X,StatusY,.36f*S,F.Gold,TextWidth,20*S,1);
        if(English) HUD.WrappedLabel(Status.English,X,StatusY+21*S,.32f*S,F.Muted,TextWidth,18*S,1);
        if(Row.HasSplitTally()) Inspection(F,Left+Width-285*S,Y);
        Y+=RowHeight;
    }
    const SoraText::FLine Next=SoraText::Format(NSLOCTEXT("SoraArena.HUD","Result.Next","{Enter}  続ける    |    {Menu}  メニュー"),
        {{TEXT("Enter"),SoraUI::ActionKey(&HUD,TEXT("Enter"))},{TEXT("Menu"),SoraUI::ActionKey(&HUD,TEXT("Menu"))}});
    HUD.Label(English?Next.Japanese+TEXT("    ")+Next.English:Next.Japanese,X,Top+Height-36*S,.45f*S,F.Muted);
}
