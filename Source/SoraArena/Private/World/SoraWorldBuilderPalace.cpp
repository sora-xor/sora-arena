#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/StaticMeshComponent.h"

void ASoraWorldBuilder::BuildPalace(const FSoraZone& Zone)
{
    const FVector O(Zone.Rect.Min+FVector2D(600,270),0);
    const FLinearColor Timber(.22f,.15f,.085f),Plaster(.53f,.50f,.44f);
    const auto Part=[&](const TCHAR* Name,FVector At,FVector Size,bool Solid=true)
    { return Box(Name,O+At,Size,Timber,Solid,FRotator::ZeroRotator,TEXT("Timber")); };
    const auto Span=[&](const TCHAR* Name,float X0,float Y0,float X1,float Y1,float Bottom,float Top,bool Solid=true)
    { return Part(Name,FVector((X0+X1)*.5f,(Y0+Y1)*.5f,(Bottom+Top)*.5f),FVector(X1-X0,Y1-Y0,Top-Bottom),Solid); };
    Span(TEXT("PalaceBase"),-600,-270,4400,3400,-40,0);
    for(const FSoraBox& Wall:Zone.Walls)
        Box(TEXT("PalaceBoundary"),FVector(Wall.Center,Wall.Height*.5f),FVector(Wall.Size,Wall.Height),Plaster,true,FRotator::ZeroRotator,TEXT(""));

    // L5's registry: the level perimeter remains 1.8 m wide along the south.
    auto* Upper=Span(TEXT("RegistryJodan"),-600,2380,200,3400,0,30);
    auto* Middle=Span(TEXT("RegistryChudan"),200,2380,1000,3400,0,15);
    Upper->ComponentTags.Add(TEXT("RegistryTier"));Middle->ComponentTags.Add(TEXT("RegistryTier"));
    Span(TEXT("RegistrySouthWall"),-600,2180,2200,2200,0,500);
    Span(TEXT("RegistryEastWallSouth"),2200,2200,2220,2380,0,500);
    Span(TEXT("RegistryEastWallNorth"),2200,2680,2220,3400,0,500);
    Span(TEXT("RegistryEntryLintel"),2200,2380,2220,2680,250,500);
    Span(TEXT("RegistryCeiling"),-600,2200,2200,3400,500,520);
    for(float X:{-540.f,140.f,940.f,2140.f})
        for(float Y:{2260.f,3340.f})
            Part(TEXT("RegistryPost"),FVector(X,Y,250),FVector(16,16,500));
    for(float X=-500;X<2200;X+=200)
        Span(TEXT("RegistryCofferX"),X,2200,X+8,3400,480,500,false);
    for(float Y=2300;Y<3400;Y+=200)
        Span(TEXT("RegistryCofferY"),-600,Y,2200,Y+8,480,500,false);
    Part(TEXT("RegistryNorthOrnamentalDoor"),FVector(-200,3396,160),FVector(220,8,260),false);

    // Vestibule and seized store occupy their authored locations. Their
    // entrances are actual gaps, with standing clearance below the lintels.
    Span(TEXT("VestibuleNorth"),2220,2800,3000,2820,0,400);
    Span(TEXT("VestibuleSouthWest"),2220,2180,2400,2200,0,400);
    Span(TEXT("VestibuleSouthEast"),2670,2180,3000,2200,0,400);
    Span(TEXT("VestibuleCeiling"),2200,2200,3000,2800,400,420);
    Span(TEXT("StoreWestSouth"),2980,2000,3000,2380,0,400);
    Span(TEXT("StoreWestNorth"),2980,2620,3000,3000,0,400);
    Span(TEXT("StoreEntryLintel"),2980,2380,3000,2620,250,400);
    Span(TEXT("StoreSouth"),3000,1980,4400,2000,0,400);
    Span(TEXT("StoreNorth"),3000,3000,4400,3020,0,400);
    Span(TEXT("StoreCeiling"),3000,2000,4400,3000,400,420);
    // This is traversable geometry, not final shoin craft or the complete
    // b06 nightingale/garden route. The latter still needs connected placement.
}
