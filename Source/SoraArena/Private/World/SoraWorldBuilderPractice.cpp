#include "SoraWorldBuilder.h"
#include "ArenaKernelSubsystem.h"
#include "Components/StaticMeshComponent.h"

// Deterministic practice: the Rust kernel's bounds and walls only. No campaign
// terrain, props, cover or scenery may add collision or visuals here.
void ASoraWorldBuilder::BuildPractice(int32 MapId,const FSoraPracticeMap& Map)
{
    ClearArena();
    const FVector Size=Map.Maximum-Map.Minimum;
    const FVector Center=(Map.Minimum+Map.Maximum)*.5;
    Box(TEXT("KernelGround"),FVector(Center.X,Center.Y,Map.Minimum.Z-25),FVector(Size.X+160,Size.Y+160,50),FLinearColor(.2,.22,.18),true,FRotator::ZeroRotator,TEXT("Soil"));
    // Visual/collision bounds and every obstacle come from the loaded reference kernel.
    // No campaign cover, trees or scenery may introduce additional collision here.
    for(int32 I=0;I<Map.Walls.Num();++I)
    {
        const auto& Wall=Map.Walls[I];
        Box(FString::Printf(TEXT("KernelWall%d"),I),(Wall.Minimum+Wall.Maximum)*.5,Wall.Maximum-Wall.Minimum,FLinearColor(.3,.31,.29),true,FRotator::ZeroRotator,MapId<2?TEXT("Timber"):TEXT("Metal"));
    }
    for(int32 Side:{-1,1})
    {
        const float X=Side<0?Map.Minimum.X:Map.Maximum.X;
        const float Y=Side<0?Map.Minimum.Y:Map.Maximum.Y;
        // The kernel clamps movement at the perimeter but does not define tall
        // bullet-blocking perimeter walls. Mark that limit on the floor only.
        Box(FString::Printf(TEXT("KernelBoundaryX%d"),Side),FVector(X,Center.Y,1),FVector(12,Size.Y,2),FLinearColor(.08,.6,.65),false);
        Box(FString::Printf(TEXT("KernelBoundaryY%d"),Side),FVector(Center.X,Y,1),FVector(Size.X,12,2),FLinearColor(.08,.6,.65),false);
    }
    Lighting(MapId);
}
