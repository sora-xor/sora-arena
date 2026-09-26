#pragma once
#include "CoreMinimal.h"
class ASoraWorldBuilder;
class UInstancedStaticMeshComponent;
class UStaticMeshComponent;
struct FSoraPracticeMap;
struct FSoraPracticeWall;

// Dresses a kernel practice arena. The Rust kernel is the only collision:
// ASoraWorldBuilder::BuildPractice gives each kernel wall one hidden box of
// exactly its size and the floor one ground slab, and nothing else collides.
// Every visible piece is one of:
//   - inside a kernel wall's box: boxes (courses, bays, lit bands) that tile
//     the box exactly, so every face a player can touch or a shot can strike
//     is a face of the kernel's box. An imported mesh never fills a wall: its
//     bounds would hide a narrower body behind invisible collision;
//   - flat on the floor, no higher than FlatHeight (paths, pads);
//   - inside a hazard volume (embers, slag, grates), which never blocks;
//   - outside the arena bounds, as backdrop.
// The SoraArena.Practice.ArenaDressing automation checks this on all four arenas.
struct FSoraPracticeArenaKit
{
    static constexpr float FlatHeight = 8.f;
    ASoraWorldBuilder& Builder;
    const FSoraPracticeMap& Map;
    FSoraPracticeArenaKit(ASoraWorldBuilder& InBuilder, const FSoraPracticeMap& InMap) : Builder(InBuilder), Map(InMap) {}

    // A visual box exactly Minimum..Maximum on a world-aligned photographed
    // surface (Timber, Stone, Metal, Plaster, Kawara, Soil, TerrainSoil,
    // TerrainStone), a flat paint or additive light. Boxes of one look share
    // one instanced component tagged PracticeWallPiece while bWallPieces is
    // set (a kernel wall's dressing) and PracticeGroundPiece otherwise.
    void Block(const FVector& Minimum, const FVector& Maximum, const TCHAR* Role, FLinearColor Tint = FLinearColor::White);
    void Painted(const FVector& Minimum, const FVector& Maximum, FLinearColor Color, float Roughness = .6f, float Metallic = 0.f);
    void Lit(const FVector& Minimum, const FVector& Maximum, FLinearColor Color, float Strength);
    void Lamp(FVector Location, FLinearColor Color, float Lumens, float Radius, bool bShadows = false);
    bool bWallPieces = false;

    // Wall courses, with heights measured from the wall's base. Each fills the
    // wall's whole footprint between Bottom and Top.
    void Course(const FSoraPracticeWall& Wall, float Bottom, float Top, const TCHAR* Role, FLinearColor Tint = FLinearColor::White);
    void PaintedCourse(const FSoraPracticeWall& Wall, float Bottom, float Top, FLinearColor Color, float Roughness = .6f, float Metallic = 0.f);
    // Posts and panels alternating along the wall's long side, each through
    // the whole thickness. A null PanelRole paints the panels PanelTint.
    void Bays(const FSoraPracticeWall& Wall, float Bottom, float Top, float Spacing, float Post, const TCHAR* PostRole, FLinearColor PostTint,
        const TCHAR* PanelRole, FLinearColor PanelTint);
    // Lit windows on every face: an opaque core 2 cm inside the faces and,
    // on each face, a 2 cm skin of frame and glowing panes.
    void LitCourse(const FSoraPracticeWall& Wall, float Bottom, float Top, const TCHAR* FrameRole, FLinearColor FrameTint, FLinearColor Core,
        FLinearColor Glow, float Strength, float Spacing, float Pane);
    // A flat strip from A to B on the floor.
    void Strip(FVector A, FVector B, float Width, float StripHeight, const TCHAR* Role, FLinearColor Tint);
    // A part made elsewhere, adopted so that ClearArena removes it with the
    // rest. The arena loads no campaign art (scripts/unreal/validate_content.py).
    void Adopt(UStaticMeshComponent* Mesh);
    // Bounds, length and name helpers.
    static float Height(const FSoraPracticeWall& Wall);
    static bool Labelled(const FSoraPracticeWall& Wall, const TCHAR* Word);
    // Every piece placed by the kit, for the owner's dressing count.
    int32 Pieces = 0;
private:
    void Place(const FString& Look, TFunctionRef<void(UStaticMeshComponent*)> Style, const FVector& Center, const FVector& Size, FRotator Rotation);
    TMap<FString, UInstancedStaticMeshComponent*> Batches;
};

// Per-arena dressing (World/SoraMap*.cpp): *Wall dresses one kernel wall in
// the arena's architecture, *Grounds lays paths, lights and backdrop. The
// shared styles and the hazards are in SoraWorldBuilderPractice.cpp; every
// style fills its wall's box exactly.
namespace SoraPracticeDressing
{
void PlasterWall(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, FLinearColor Plaster);
void Townhouse(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, FLinearColor Plaster, bool bLattice, bool bLit);
void Storehouse(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void StoneLantern(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void Screen(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void Hedge(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void Goods(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void Rock(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void Fence(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void LanternPost(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
void Industrial(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, FLinearColor Brick, FLinearColor Glow, bool bLit);
void Machine(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, FLinearColor Accent);
void Column(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, FLinearColor Band, float Strength);
void Vault(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, FLinearColor Seam, bool bWindows);
void Shelves(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall);
// Lane paths from the arena data: flat strips along each lane polyline.
void Lanes(FSoraPracticeArenaKit& Kit, const TCHAR* Role, FLinearColor Tint, float Width, float Height, bool bSkipMid);
void EstateWall(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, int32 Index);
void EstateGrounds(FSoraPracticeArenaKit& Kit);
void LanternWardWall(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, int32 Index);
void LanternWardGrounds(FSoraPracticeArenaKit& Kit);
void SilkFoundryWall(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, int32 Index);
void SilkFoundryGrounds(FSoraPracticeArenaKit& Kit);
void DebtCitadelWall(FSoraPracticeArenaKit& Kit, const FSoraPracticeWall& Wall, int32 Index);
void DebtCitadelGrounds(FSoraPracticeArenaKit& Kit);
// Shared by every arena: the hazard volumes' look (embers, slag, grates).
void Hazards(FSoraPracticeArenaKit& Kit);
}
