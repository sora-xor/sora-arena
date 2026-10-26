#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraLedgerRules.h"
#include "Components/StaticMeshComponent.h"

void ASoraWorldBuilder::BuildLedger(const FSoraZone& Zone)
{
    namespace R=SoraLedgerRules;
    const FVector O(Zone.Rect.Min+FVector2D(1000,0),0);
    const FLinearColor Shelf(.025f,.065f,.085f);
    const auto Span=[&](const TCHAR* Name,float X0,float Y0,float X1,float Y1,float Z0,float Z1,
        const FLinearColor& Color=FLinearColor(.045f,.055f,.065f))
    {
        return Box(Name,O+FVector((X0+X1)*.5f,(Y0+Y1)*.5f,(Z0+Z1)*.5f),
            FVector(X1-X0,Y1-Y0,Z1-Z0),Color,true,FRotator::ZeroRotator,TEXT("Stone"));
    };
    Span(TEXT("LedgerMainFloor"),0,0,R::HallWidth,R::HallLength,-40,0);
    Span(TEXT("LedgerAnnexFloor"),-1000,0,0,800,-40,0);
    Span(TEXT("LedgerPalaceLinkFloor"),1965,6400,2400,6670,-40,0);
    Span(TEXT("LedgerSouthWall"),-1000,-20,2400,0,0,600);
    Span(TEXT("LedgerAnnexWest"),-1020,0,-1000,800,0,600);
    Span(TEXT("LedgerAnnexNorth"),-1000,800,0,820,0,600);
    Span(TEXT("LedgerAnnexDoorSouth"),-20,0,0,250,0,600);
    Span(TEXT("LedgerAnnexDoorNorth"),-20,550,0,6400,0,600);
    Span(TEXT("LedgerAnnexDoorLintel"),-20,250,0,550,250,600);
    Span(TEXT("LedgerEastWall"),2400,0,2420,6400,0,600);
    Span(TEXT("LedgerNorthWallWest"),0,6400,1965,6420,0,600);
    Span(TEXT("LedgerNorthWallEast"),2235,6400,2400,6420,0,600);
    Span(TEXT("LedgerNorthDoorLintel"),1965,6400,2235,6420,250,600);
    Span(TEXT("LedgerLinkWest"),1945,6400,1965,6670,0,300);
    Span(TEXT("LedgerLinkNorth"),1965,6670,2400,6690,0,300);
    Span(TEXT("LedgerMainCeiling"),0,0,2400,6400,600,620);
    Span(TEXT("LedgerAnnexCeiling"),-1000,0,0,800,600,620);
    Span(TEXT("LedgerLinkCeiling"),1965,6400,2400,6670,300,320);
    for(int Bank=0;Bank<6;++Bank)
        for(const auto& Run:R::ShelfY)
        {
            const int X=R::ShelfX[Bank],Niche=R::NicheY[Bank];
            const auto ShelfPart=[&](int Low,int High)
            {
                auto* Part=Span(TEXT("LedgerShelfBank"),X,Low,X+R::ShelfWidth,High,0,R::ShelfHeight,Shelf);
                Part->ComponentTags.Add(TEXT("LedgerShelfBank"));
            };
            if(Niche>Run.X&&Niche<Run.Y)
            { ShelfPart(Run.X,Niche-50);ShelfPart(Niche+50,Run.Y); }
            else ShelfPart(Run.X,Run.Y);
        }
    // Collision and route dimensions are authoritative here. Household
    // slate craft, nonrepeating emissive numerals and annex dressing remain
    // separate art work; these shelf banks are construction geometry.
}
