#include "SoraCatalogArchive.h"
#include "SoraCatalog.h"

bool SoraCatalogArchive::Valid(const FSoraBeat& Beat,const FSoraSpace& Space)
{
    if(Beat.Id!=TEXT("ch06.b09")&&Beat.Id!=TEXT("ch06.b10")) return true;
    const auto& B=Beat.Space;
    if(Beat.Place!=TEXT("pl_archive")||!Space.Zones.IsValidIndex(B.Zone)||B.HeightCm!=0) return false;
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
    return true;
}
