#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraMoatRules.h"

void ASoraWorldBuilder::BuildMoat(const FSoraBeat& Beat)
{
    const FVector O(Beat.Space.Moat.Origin,0);
    const FLinearColor Stone(.18f,.22f,.20f),Earth(.18f,.16f,.10f),Wood(.16f,.10f,.055f);
    const auto Slab=[&](const TCHAR* Name,float X0,float Y0,float Z0,float X1,float Y1,float Z1)
    { return Box(Name,O+FVector((X0+X1)*.5f,(Y0+Y1)*.5f,(Z0+Z1)*.5f),FVector(X1-X0,Y1-Y0,Z1-Z0),Stone,true,FRotator::ZeroRotator,TEXT("Stone")); };
    // The bed is split around the deeper gate pocket. No generic floor is built.
    Slab(TEXT("MoatBed"),0,0,-280,20000,3600,-240);
    Slab(TEXT("MoatEastBed"),21400,0,-280,22000,3600,-240);
    Slab(TEXT("MoatPocketSouthBed"),20000,0,-280,21400,3000,-240);
    Slab(TEXT("MoatGateBed"),20000,3000,-340,21400,4500,-300);
    Slab(TEXT("MoatOuterBank"),-1000,-1000,60,23000,-400,100);
    // Top endpoints (Y=-400,Z=100) and (Y=0,Z=-240), thickness below the top.
    const auto Ramp=SoraMoatRules::BankRamp();
    Box(TEXT("MoatBankSlope"),O+FVector(11000,Ramp.CenterY,Ramp.CenterZ),
        FVector(22000,Ramp.Length,40),Earth,true,FRotator(0,0,Ramp.RollDegrees),TEXT("Stone"));
    Slab(TEXT("MoatWestBank"),-100,0,-340,0,3640,370);
    Slab(TEXT("MoatEastBank"),22000,0,-340,22100,3640,370);
    // The old gate is the sole opening through the inner wall. Its actual
    // collision aperture is 60 cm high at 1.2--1.8 m below the water.
    Slab(TEXT("MoatInnerWallWest"),0,3560,-340,20600,3640,370);
    Slab(TEXT("MoatInnerWallEast"),21000,3560,-340,22000,3640,370);
    Slab(TEXT("MoatGateSill"),20600,3560,-340,21000,3640,-180);
    Slab(TEXT("MoatGateLintel"),20600,3560,-120,21000,3640,370);
    Slab(TEXT("MoatBasinWest"),20320,3640,-340,20400,4580,370);
    Slab(TEXT("MoatBasinEast"),21400,3640,-340,21480,4580,370);
    Slab(TEXT("MoatBasinNorth"),20400,4500,-340,21400,4580,370);
    // Terrace and keep wall are outside the water. The parapet has a real
    // standing deck; sight to the water still has to clear the stone below it.
    Slab(TEXT("MoatTerrace"),0,3640,110,20320,4240,150);
    Slab(TEXT("MoatKeepWall"),0,4800,150,22000,5060,1750);
    Slab(TEXT("MoatParapet"),2500,4800,1710,21500,5060,1750);
    for(const float X:{6000.f,15000.f})
        Box(TEXT("MoatSearchlightPillar"),O+FVector(X,4920,850),FVector(80,80,1700),Stone,true);
    for(float X=8840;X<=9560;X+=240)
        for(float Y:{500.f,1500.f,2500.f,3100.f})
            Box(TEXT("MoatPiling"),O+FVector(X,Y,-10),FVector(48,48,500),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    for(const FVector2D P:{FVector2D(7200,3300),FVector2D(14000,3300),FVector2D(19600,3000)})
        Box(TEXT("MoatBoatHull"),O+FVector(P,15),FVector(450,180,110),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
}
