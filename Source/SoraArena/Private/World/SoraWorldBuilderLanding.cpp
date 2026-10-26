#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraLandingSpaceRules.h"
#include "Components/StaticMeshComponent.h"

// Functional geometry of ch03's west landing. Final period craft and material
// review remain art work; these solids own the routes, cover and sight lines.
void ASoraWorldBuilder::BuildLanding(const FSoraZone& Zone)
{
    namespace R=SoraLandingSpaceRules;
    const FLinearColor Earth(.23f,.19f,.13f),Stone(.27f,.29f,.28f),Wood(.26f,.17f,.09f),Plaster(.65f,.63f,.57f);
    const auto Slab=[&](const FString& Name,float X0,float Y0,float X1,float Y1,float Top,const FLinearColor& Color,const TCHAR* Role)
    { return Box(Name,FVector((X0+X1)*.5f,(Y0+Y1)*.5f,Top-30),FVector(X1-X0,Y1-Y0,60),Color,true,FRotator::ZeroRotator,Role); };
    Slab(TEXT("LandingEarth"),R::MinX,R::MinY,R::MaxX,R::MaxY,0,Earth,TEXT("Soil"));
    Slab(TEXT("LandingWarehouseGround"),R::MinX,R::MaxY,R::MaxX,R::ZoneMaxY,0,Earth,TEXT("Soil"));
    Slab(TEXT("LandingApproachNorthBank"),R::ZoneMinX,R::MinY,R::MinX,R::ZoneMaxY,0,Earth,TEXT("Soil"));
    Slab(TEXT("LandingSouthBank"),R::ZoneMinX,R::ZoneMinY,R::MaxX,R::CanalMinY,0,Earth,TEXT("Soil"));
    // A real shallow canal bed permits the water-edge route without a
    // floating stone floor. Six west steps descend into forty-centimetre
    // water; the east mooring gangplank returns to the exit-side bank.
    Slab(TEXT("LandingCanalBed"),R::ZoneMinX,R::CanalMinY,R::MaxX,R::MinY,R::BedZ,Stone,TEXT("Stone"));
    for(int I=0;I<6;++I)
        Slab(FString::Printf(TEXT("LandingStep%d"),I),-11600,-2850-I*50,-11000,-2800-I*50,
             (I+1)*(R::WaterZ/6.f),Stone,TEXT("Stone"));
    const float Rise=-float(R::BedZ),RampPitch=FMath::RadiansToDegrees(FMath::Atan2(Rise,500.f));
    const FRotator RampRotation(RampPitch,90,0);
    // Align the walking surface with the bank edge, not a point 100 cm
    // inland: the former placement met the ground's vertical face 40 cm
    // below its top and stopped the crouched water route. Offset thickness
    // along the plank normal so the surface reaches Z=0 at Y=MinY.
    const FVector RampSurface(-7900,R::MinY-250,R::BedZ*.5f);
    Box(TEXT("LandingEastGangplank"),RampSurface-RampRotation.RotateVector(FVector(0,0,8)),
        FVector(FMath::Sqrt(500.f*500.f+Rise*Rise)+20,180,16),
        Wood,true,RampRotation,TEXT("Timber"));
    Box(TEXT("LandingCanalWater"),FVector((R::ZoneMinX+R::MaxX)*.5f,(R::CanalMinY+R::MinY)*.5f,R::WaterZ-1),
        FVector(R::MaxX-R::ZoneMinX,R::MinY-R::CanalMinY,2),FLinearColor(.035f,.085f,.09f),false);
    // The land's bank is 1.6 m above the water, broken only at its steps and
    // the east gangplank. These faces do not intrude into either flight lane.
    for(const auto Range:{FVector2D(R::ZoneMinX,-11600),FVector2D(-11000,-8000),FVector2D(-7800,R::MaxX)})
        Box(TEXT("LandingStoneBank"),FVector((Range.X+Range.Y)*.5f,R::MinY+10,R::BedZ*.5f),FVector(Range.Y-Range.X,20,-R::BedZ),
            Stone,true,FRotator::ZeroRotator,TEXT("Stone"));
    Box(TEXT("LandingSouthStoneBank"),FVector((R::ZoneMinX+R::MaxX)*.5f,R::CanalMinY-10,R::BedZ*.5f),
        FVector(R::MaxX-R::ZoneMinX,20,-R::BedZ),Stone,true,FRotator::ZeroRotator,TEXT("Stone"));
    for(int I=0;I<Zone.Walls.Num();++I)
    {
        const auto& W=Zone.Walls[I];
        // The outer boundary now sits beyond both banks, not in the canal.
        // Its foundation also closes the bed at the scene's two far ends.
        Box(FString::Printf(TEXT("LandingBoundary%d"),I),FVector(W.Center,(W.Height-250)*.5f),
            FVector(W.Size,W.Height+250),Stone,true,FRotator::ZeroRotator,TEXT("Stone"));
    }
    // The b01 approach crosses a timber bridge at X -160 m. The lowest
    // stringer is exactly 2.4 m above the water, with the deck above it.
    const float Low=R::WaterZ+R::BridgeClearance,Deck=Low+60;
    const float CanalY=(R::CanalMinY+R::MinY)*.5f;
    for(int Side:{-1,1})
    {
        Box(TEXT("LandingBridgeStringer"),FVector(R::BridgeX+Side*150,CanalY,Low+14),FVector(28,1120,28),
            Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        Box(TEXT("LandingBridgeRail"),FVector(R::BridgeX+Side*195,CanalY,Deck+95),FVector(16,1120,18),
            Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        for(int Y:{R::CanalMinY-40,R::MinY+40})
            Box(TEXT("LandingBridgePost"),FVector(R::BridgeX+Side*195,Y,(Deck+110)*.5f),FVector(20,20,Deck+110),
                Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        const float BankY=Side<0?R::CanalMinY-250:R::MinY+250;
        Box(TEXT("LandingBridgeBankRamp"),FVector(R::BridgeX,BankY,Deck*.5f-8),
            FVector(FMath::Sqrt(500.f*500.f+Deck*Deck),400,16),Wood,true,
            FRotator(-Side*FMath::RadiansToDegrees(FMath::Atan2(Deck,500.f)),90,0),TEXT("Timber"));
    }
    Box(TEXT("LandingBridgeDeck"),FVector(R::BridgeX,CanalY,Deck-16),FVector(420,1120,32),
        Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    // Three 7.2 x 5.4 m two-storey warehouses, 2 m apart. Their south faces
    // meet the yard's north edge; the dry eaves strip remains clear of cargo.
    for(int I=0;I<3;++I)
    {
        const float X=-11800+I*920+360;
        const FString Name=FString::Printf(TEXT("LandingWarehouse%d"),I);
        Box(Name+TEXT("Body"),FVector(X,-930,310),FVector(720,540,620),Plaster,true,FRotator::ZeroRotator,TEXT("Plaster"));
        Box(Name+TEXT("Base"),FVector(X,-930,24),FVector(730,550,48),Stone,true,FRotator::ZeroRotator,TEXT("Stone"));
        for(int Side:{-1,1})
            Box(Name+TEXT("Roof"),FVector(X,-930+Side*170,645),FVector(780,380,30),Wood,true,
                FRotator(0,0,Side*18.f),TEXT("Timber"));
        Box(Name+TEXT("Eave"),FVector(X,-1245,598),FVector(780,90,20),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        Slab(Name+TEXT("DryStrip"),X-360,-1320,X+360,-1200,1,Earth,TEXT("Soil"));
        Box(Name+TEXT("Door"),FVector(X,-1203,130),FVector(180,6,260),Wood,false,FRotator::ZeroRotator,TEXT("Timber"));
        for(int Side:{-1,1})
            Box(Name+TEXT("UpperWindow"),FVector(X+Side*190,-1204,450),FVector(90,8,110),Wood,false,FRotator::ZeroRotator,TEXT("Timber"));
    }
    // Fence closes the unused north frontage, leaving the authored 3.6 m
    // exit lane (-8000..-7640) open from the yard to the gate-plaza trigger.
    Box(TEXT("LandingExitWestFence"),FVector(-8620,-1185,115),FVector(1240,30,230),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    Box(TEXT("LandingExitEastFence"),FVector(-7620,-1185,115),FVector(40,30,230),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    // Open shed, exactly X -90..-82 m and Y -20..-16 m. Its solid roof
    // interrupts aerial sight, while all four sides remain traversable.
    for(int X:{-8988,-8212})for(int Y:{-1988,-1612})
        Box(TEXT("LandingShedPost"),FVector(X,Y,140),FVector(24,24,280),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    Box(TEXT("LandingShedRoof"),FVector(-8600,-1800,294),FVector(800,400,28),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
    for(int I=0;I<6;++I)
        Box(TEXT("LandingShedRoofStone"),FVector(-8920+I*125,-1800,316),FVector(40,50,16),Stone,false,FRotator::ZeroRotator,TEXT("Stone"));
    for(int I=0;I<Zone.Cover.Num();++I)
    {
        const auto& C=Zone.Cover[I];
        auto* Solid=Box(FString::Printf(TEXT("LandingCargo%d"),I),FVector(C.Center,C.Height*.5f),FVector(C.Size,C.Height),
            Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        if(ImportedProp(TEXT("SM_Nyaagyu_CargoStack"),FVector(C.Center,0),FRotator::ZeroRotator))Solid->SetVisibility(false);
    }
    // Two shallow-draft hulls east of the steps. Their bottoms sit between
    // the canal bed and the waterline; the gunwales provide low route cover.
    for(int I=0;I<2;++I)
    {
        const float X=-10450+I*1400;
        const FString Name=FString::Printf(TEXT("LandingBoat%d"),I);
        Box(Name+TEXT("Hull"),FVector(X,-2980,-150),FVector(1000,260,90),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        for(int Side:{-1,1})
            Box(Name+TEXT("Gunwale"),FVector(X,-2980+Side*130,-80),FVector(1040,18,80),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        for(int Side:{-1,1})
            Box(Name+TEXT("End"),FVector(X+Side*500,-2980,-90),FVector(20,260,100),Wood,true,FRotator::ZeroRotator,TEXT("Timber"));
        for(int Beam=0;Beam<4;++Beam)
            Box(Name+TEXT("Thwart"),FVector(X-340+Beam*220,-2980,-94),FVector(40,240,22),Wood,false,FRotator::ZeroRotator,TEXT("Timber"));
    }
}
