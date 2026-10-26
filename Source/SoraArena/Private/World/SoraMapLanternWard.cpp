#include "SoraWorldBuilder.h"
#include "ArenaKernelSubsystem.h"
#include "World/SoraPracticeArena.h"
#include "Components/StaticMeshComponent.h"

// Lantern Ward, map 1: the occupied street's alien debt terminal.
void ASoraWorldBuilder::LanternWardTerminal()
{
    // The occupied street faces the road at local -Y. Use the same simple
    // campaign collision whether the authored mesh imported or not.
    const int First=Pieces.Num();
    TerminalPieces.Reset();bTerminalDestroyed=false;
    const FVector StreetTerminal(-730,460,0);
    const bool HasStreetTerminal=ImportedProp(TEXT("SM_Alien_StreetDebtTerminal"),StreetTerminal,FRotator::ZeroRotator);
    auto* Proxy=Box(TEXT("StreetDebtTerminalCollision"),StreetTerminal+FVector(0,0,121),
        FVector(140,74,242),FLinearColor(.10f,.15f,.20f),true);
    if(HasStreetTerminal) Proxy->SetVisibility(false);
    for(int I=First;I<Pieces.Num();++I)if(Pieces[I]->IsVisible())TerminalPieces.Add(Pieces[I]);
    BrokenTerminal=Box(TEXT("BrokenDebtTerminal"),StreetTerminal+FVector(0,0,65),FVector(140,74,130),
        FLinearColor(.035f,.04f,.045f),false);
    BrokenTerminal->SetVisibility(false);
}

void ASoraWorldBuilder::SetTerminalDestroyed(bool Destroyed)
{
    bTerminalDestroyed=Destroyed;
    for(auto* P:TerminalPieces)if(IsValid(P))P->SetVisibility(!Destroyed);
    if(IsValid(BrokenTerminal))BrokenTerminal->SetVisibility(Destroyed);
}

// Practice: the occupied merchant street. Machiya with koshi lattices and lit
// shoji line the street inside ochre plaster walls, lantern towers light the
// corners and goods are stacked where the kernel keeps a stall, cart or
// barrels, each filling its kernel box exactly.
void SoraPracticeDressing::LanternWardWall(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,int32 Index)
{
    using K=FSoraPracticeArenaKit;
    const FLinearColor Ochre(.86f,.74f,.55f);
    if(K::Labelled(Wall,TEXT("perimeter"))) PlasterWall(Kit,Wall,Ochre);
    else if(K::Labelled(Wall,TEXT("machiya"))) Townhouse(Kit,Wall,Ochre,true,true);
    else if(K::Labelled(Wall,TEXT("teahouse"))) Townhouse(Kit,Wall,FLinearColor(.92f,.86f,.72f),false,true);
    else if(K::Labelled(Wall,TEXT("warehouse"))) Storehouse(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("bathhouse"))) Townhouse(Kit,Wall,FLinearColor(.84f,.8f,.74f),false,true);
    else if(K::Labelled(Wall,TEXT("merchant house"))) Townhouse(Kit,Wall,FLinearColor(.8f,.66f,.48f),true,true);
    else if(K::Labelled(Wall,TEXT("lantern"))) LanternPost(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("stall"))||K::Labelled(Wall,TEXT("cart"))||K::Labelled(Wall,TEXT("barrels"))) Goods(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("fence"))) Fence(Kit,Wall);
    else PlasterWall(Kit,Wall,Ochre);
}
void SoraPracticeDressing::LanternWardGrounds(FSoraPracticeArenaKit& Kit)
{
    // Worn paving along the lanes; the main street is the widest.
    Lanes(Kit,TEXT("Stone"),FLinearColor(.9f,.86f,.8f),170.f,1.5f,true);
    for(const FSoraPracticeLane& Lane:Kit.Map.Lanes)
        if(Lane.Name==TEXT("mid"))
            for(int32 Index=1;Index<Lane.Points.Num();++Index)
                Kit.Strip(Lane.Points[Index-1],Lane.Points[Index],420.f,1.2f,TEXT("Stone"),FLinearColor(.95f,.92f,.86f));
    // Evening light hangs over the street from the eaves.
    for(float X=Kit.Map.Minimum.X+600.f;X<Kit.Map.Maximum.X-500.f;X+=1100.f)
        Kit.Lamp(FVector(X,0,420.f),FLinearColor(1.f,.6f,.32f),1800.f,1300.f);
}
