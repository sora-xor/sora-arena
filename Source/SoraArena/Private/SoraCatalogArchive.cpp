#include "SoraCatalogArchive.h"
#include "SoraCatalog.h"
#include "SoraArchiveRules.h"

namespace
{
bool PortalWalls(const FSoraZone& Z,double DoorX)
{
    const auto A=Z.Rect.Min,B=Z.Rect.Max;
    const FVector2D Centers[]={{A.X-30,(A.Y+B.Y)/2},{B.X+30,(A.Y+B.Y)/2},
        {(A.X+B.X)/2,A.Y-30},{(A.X+DoorX-120)/2,B.Y+30},{(DoorX+120+B.X)/2,B.Y+30}};
    const FVector2D Sizes[]={{60,B.Y-A.Y+120},{60,B.Y-A.Y+120},{B.X-A.X,60},
        {DoorX-120-A.X,60},{B.X-DoorX-120,60}};
    if(Z.Walls.Num()!=5) return false;
    for(int I=0;I<5;++I)
        if(Z.Walls[I].Center!=Centers[I]||Z.Walls[I].Size!=Sizes[I]||Z.Walls[I].Height!=Z.WallHeight) return false;
    return true;
}
}

bool SoraCatalogArchive::Valid(const FSoraBeat& Beat,const FSoraSpace& Space)
{
    if(Beat.Id!=TEXT("ch06.b09")&&Beat.Id!=TEXT("ch06.b10")) return true;
    const auto& B=Beat.Space;
    if(Beat.Place!=TEXT("pl_archive")||!Space.Zones.IsValidIndex(B.Zone)||B.HeightCm!=SoraArchiveRules::FloorCm) return false;
    const auto& Z=Space.Zones[B.Zone];const FVector2D O=Z.Rect.Min;
    if(Z.Id!=TEXT("pl_archive")||Z.Place!=Beat.Place||Z.Rect.GetSize()!=FVector2D(2600,1800)||Z.WallHeight!=600||
        Z.Cover.Num()!=4||!Z.Props.IsEmpty()||Z.Entry!=O+FVector2D(1300,200)||Z.EntryYaw!=90||
        B.Entry!=Z.Entry||B.EntryYaw!=90||B.Anchor!=O+FVector2D(1300,900)||
        B.Exit.Center!=O+FVector2D(1300,1600)||B.Exit.Size!=FVector2D(400,300)||
        B.Spawns.Num()!=6||!B.Patrols.IsEmpty()) return false;
    const FVector2D Posts[]={{900,600},{1700,600},{900,1200},{1700,1200}};
    const FVector2D Spawns[]={{1300,1300},{1300,500},{1100,900},{1500,900},{1100,500},{1500,1300}};
    for(int I=0;I<4;++I)
        if(Z.Cover[I].Center!=O+Posts[I]||Z.Cover[I].Size!=FVector2D(60,60)||Z.Cover[I].Height!=600) return false;
    for(int I=0;I<6;++I) if(B.Spawns[I]!=O+Spawns[I]) return false;
    const auto* Press=Space.Zones.FindByPredicate([](const FSoraZone& Zone){return Zone.Id==TEXT("pl_press_hall");});
    if(!Press||!PortalWalls(Z,O.X+1300)||!PortalWalls(*Press,Press->Rect.Min.X+300)) return false;
    if(Beat.Id==TEXT("ch06.b10"))
    {
        const auto Landing=Press->Rect.Min+FVector2D(300,2340);
        if(!Beat.Task.AnchorAfterLines||Beat.ClosingEvent!=TEXT("volume_enter:vol_archive_press_landing")||
            !B.bClosing||B.Closing!=Landing||B.Volumes.Num()!=1) return false;
        const auto& V=B.Volumes[0];
        if(V.Event!=Beat.ClosingEvent||V.Center!=Landing||V.Size!=FVector2D(300,120)||!V.bHeight||V.FloorCm!=400) return false;
    }
    return true;
}
