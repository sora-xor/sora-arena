#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraRelayRules.h"

void ASoraWorldBuilder::BuildRelayRoom(const FSoraBeat& Beat)
{
    const FVector O(Beat.Space.RelayRoom.Origin,0);
    const FLinearColor Wood(.25f,.16f,.085f),Plaster(.55f,.53f,.45f),Alien(.025f,.045f,.055f);
    const auto Part=[&](const TCHAR* Name,const FVector& At,const FVector& Size,const FLinearColor& Color,const TCHAR* Role)
    { return Box(Name,O+At,Size,Color,true,FRotator::ZeroRotator,Role); };
    // Functional shell only. The old turret and fused annex need final art;
    // the openings are real collision gaps, without a hidden generic wall.
    Part(TEXT("RelayTurretFloor"),FVector(600,500,-25),FVector(1200,1000,50),Wood,TEXT("Timber"));
    Part(TEXT("RelayAnnexFloor"),FVector(1600,500,-25),FVector(800,1000,50),Alien,TEXT("Metal"));
    Part(TEXT("RelaySouthTurret"),FVector(600,-20,400),FVector(1200,40,800),Plaster,TEXT("Stone"));
    Part(TEXT("RelaySouthAnnex"),FVector(1600,-20,400),FVector(800,40,800),Alien,TEXT("Metal"));
    Part(TEXT("RelayNorthAnnex"),FVector(1600,1020,400),FVector(800,40,800),Alien,TEXT("Metal"));
    // The west crawl gap is 60 cm high, matching the preceding climb's
    // aperture. Beat travel still stages the hero inside at the checkpoint.
    for(int Side:{-1,1})
        Part(TEXT("RelayWestWall"),FVector(-20,500+Side*300,400),FVector(40,400,800),Plaster,TEXT("Stone"));
    Part(TEXT("RelayCrawlLintel"),FVector(-20,500,430),FVector(40,200,740),Plaster,TEXT("Stone"));
    // East doorway/bridge opening; the actual exit still needs all nodes.
    for(int Side:{-1,1})
        Part(TEXT("RelayEastWall"),FVector(2020,500+Side*325,400),FVector(40,350,800),Alien,TEXT("Metal"));
    Part(TEXT("RelayEastLintel"),FVector(2020,500,530),FVector(40,300,540),Alien,TEXT("Metal"));
    Part(TEXT("RelayBridgeThreshold"),FVector(2100,500,-15),FVector(200,300,30),Alien,TEXT("Metal"));
    // Upper north slatted window centred at the authored (10,10,5.5) m.
    // Physical slats admit sight between them and stop a capsule climbing out.
    Part(TEXT("RelayNorthWest"),FVector(450,1020,400),FVector(900,40,800),Plaster,TEXT("Stone"));
    Part(TEXT("RelayNorthEast"),FVector(1150,1020,400),FVector(100,40,800),Plaster,TEXT("Stone"));
    Part(TEXT("RelayWindowSill"),FVector(1000,1020,230),FVector(200,40,460),Plaster,TEXT("Stone"));
    Part(TEXT("RelayWindowHead"),FVector(1000,1020,720),FVector(200,40,160),Plaster,TEXT("Stone"));
    for(int X=910;X<1100;X+=32)
        Part(TEXT("RelayWindowSlat"),FVector(X,1020,550),FVector(8,40,180),Wood,TEXT("Timber"));
    Part(TEXT("RelayLookoutPerch"),FVector(1000,1140,450),FVector(240,280,20),Wood,TEXT("Timber"));
}
