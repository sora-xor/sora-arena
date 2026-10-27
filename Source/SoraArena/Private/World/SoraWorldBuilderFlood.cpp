#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraFloodRules.h"

void ASoraWorldBuilder::BuildFlood(const FSoraBeat& Beat)
{
    const FVector O(Beat.Space.Flood.Origin,0);
    const FLinearColor Stone(.19f,.23f,.21f), Iron(.10f,.12f,.13f);
    const auto Slab=[&](const TCHAR* Name,float X,float Y,float Z,float SX,float SY,float SZ,const FRotator& R=FRotator::ZeroRotator)
    { return Box(Name,O+FVector(X,Y,Z),FVector(SX,SY,SZ),Stone,true,R,TEXT("Stone")); };
    // No generic zone floor covers the submerged channel.
    Slab(TEXT("FloodWalkFloor"),(SoraFloodRules::DescentStart-100)*.5f,0,-20,SoraFloodRules::DescentStart+100,240,40);
    const auto Descent=SoraFloodRules::DescentRamp();
    Slab(TEXT("FloodDescent"),Descent.CenterX,0,Descent.CenterZ,Descent.Length,240,
        SoraFloodRules::DescentThickness,FRotator(Descent.PitchDegrees,0,0));
    Slab(TEXT("FloodDeepFloor"),8250,0,-220,1500,240,40);
    for(int32 Side:{-1,1}) Slab(TEXT("FloodCulvertWall"),4500,Side*140,0,9200,40,480);
    Slab(TEXT("FloodVaultEnd"),-120,0,110,40,320,260);
    const float Roofs[][2]={{-100,1900},{2100,4400},{4600,6900},{7100,7500}};
    for(const auto& R:Roofs) Slab(TEXT("FloodCulvertRoof"),(R[0]+R[1])*.5f,0,240,R[1]-R[0],320,40);
    for(const float X:{2000.f,4500.f,7000.f,8250.f})
    {
        // Narrow real bars admit lamp rays but cannot admit a player's capsule.
        for(float Across=-110;Across<=110;Across+=28)
            Box(TEXT("FloodGrate"),O+FVector(X,Across,226),FVector(200,8,12),Iron,true);
    }
    for(const auto& R:{FVector2D(7500,8150),FVector2D(8350,9000)})
        Slab(TEXT("FloodSubmergedRoof"),(R.X+R.Y)*.5f,0,120,R.Y-R.X,320,200);
    // The visible shaft has open air up to its safety grate; there is no
    // dry horizontal route over either submerged roof.
    Slab(TEXT("FloodShaftWestLip"),8135,0,235,30,320,30);
    Slab(TEXT("FloodShaftEastLip"),8365,0,235,30,320,30);
    Slab(TEXT("FloodBasinFloor"),9500,0,-220,1000,800,40);
    Slab(TEXT("FloodBasinNorth"),9500,420,20,1080,40,480);
    Slab(TEXT("FloodBasinEast"),10020,0,20,40,800,480);
    for(int32 Side:{-1,1}) Slab(TEXT("FloodBasinWest"),8980,Side*280,20,40,320,480);
    // Half-raised timber gate: all arrivals still cross its physical opening.
    Box(TEXT("FloodHalfOpenGate"),O+FVector(9500,-400,290),FVector(400,25,140),Iron,true);
    for(int32 Side:{-1,1}) Slab(TEXT("FloodGatePost"),9500+Side*230,-400,120,60,80,400);
    Slab(TEXT("FloodWinchLanding"),9850,-230,180,220,260,40);
    Box(TEXT("FloodWinch"),O+FVector(9820,-280,270),FVector(45,45,100),Iron,false);
    Slab(TEXT("FloodMoatFloor"),-100,-2200,-220,22000,3600,40);
    // Only the basin gate opens the north embankment; the exit is the south bank.
    Slab(TEXT("FloodMoatNorthWest"),-900,-390,100,20400,40,400);
    Slab(TEXT("FloodMoatNorthEast"),10300,-390,100,1200,40,400);
    for(const float X:{-5300.f,3700.f})
        Slab(TEXT("FloodSearchlightFoundation"),X,800,-125,200,200,250);
    Slab(TEXT("FloodOuterBank"),8900,-4450,175,4000,500,50);
    const auto Ramp=SoraFloodRules::BankRamp();
    Slab(TEXT("FloodBankSlope"),8900,Ramp.CenterY,Ramp.CenterZ,4000,Ramp.Length,
        SoraFloodRules::BankRampThickness,FRotator(0,0,Ramp.RollDegrees));
    // The lamp boat is a moving, collidable fieldcraft component.
}
