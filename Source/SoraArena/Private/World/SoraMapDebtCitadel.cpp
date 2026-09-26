#include "SoraWorldBuilder.h"
#include "ArenaKernelSubsystem.h"
#include "World/SoraPracticeArena.h"

// Debt Citadel, map 3: the alien debt kiosk beside the second production site.
void ASoraWorldBuilder::DebtCitadelKiosk()
{
    ImportedProp(TEXT("SM_Alien_DebtKiosk"),NodePositions[1]+FVector(315,0,0),FRotator(0,90,0));
}

// Practice: the invaders' debt citadel. Vault masonry with cold lit seams,
// columns ringed with light, ledger shelves and coin counters, and the
// authored debt kiosk and street terminal where the kernel keeps a ledger
// terminal or a bond press.
void SoraPracticeDressing::DebtCitadelWall(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,int32 Index)
{
    using K=FSoraPracticeArenaKit;
    const FLinearColor Cyan(.05f,.62f,.85f), DebtRed(.9f,.06f,.08f);
    if(K::Labelled(Wall,TEXT("perimeter"))) Vault(Kit,Wall,Cyan,false);
    else if(K::Labelled(Wall,TEXT("security"))) Vault(Kit,Wall,DebtRed,false);
    else if(K::Labelled(Wall,TEXT("vault column"))) Column(Kit,Wall,Cyan,1.3f);
    else if(K::Labelled(Wall,TEXT("vault block"))||K::Labelled(Wall,TEXT("archive"))) Vault(Kit,Wall,DebtRed,true);
    else if(K::Labelled(Wall,TEXT("ledger terminal")))
    {
        if(!Kit.FittedProp(TEXT("SM_Alien_DebtKiosk"),Wall.Minimum,Wall.Maximum,1.35f)&&!Kit.FittedProp(TEXT("SM_Alien_StreetDebtTerminal"),Wall.Minimum,Wall.Maximum,1.35f))
            Machine(Kit,Wall,Cyan);
    }
    else if(K::Labelled(Wall,TEXT("bond press")))
    {
        if(!Kit.FittedProp(TEXT("SM_Alien_StreetDebtTerminal"),Wall.Minimum,Wall.Maximum,1.35f)&&!Kit.FittedProp(TEXT("SM_Alien_DebtKiosk"),Wall.Minimum,Wall.Maximum,1.35f))
            Machine(Kit,Wall,DebtRed);
    }
    else if(K::Labelled(Wall,TEXT("coin counter"))) Machine(Kit,Wall,FLinearColor(.78f,.58f,.14f));
    else if(K::Labelled(Wall,TEXT("ledger shelf"))) Shelves(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("conduit"))) Column(Kit,Wall,Cyan,1.5f);
    else Vault(Kit,Wall,Cyan,false);
}
void SoraPracticeDressing::DebtCitadelGrounds(FSoraPracticeArenaKit& Kit)
{
    // Polished stone lanes edged with thin cyan guide lights.
    Lanes(Kit,TEXT("Stone"),FLinearColor(.6f,.62f,.68f),160.f,1.5f,false);
    for(const FSoraPracticeLane& Lane:Kit.Map.Lanes)
        for(int32 Index=1;Index<Lane.Points.Num();++Index)
        {
            const FVector A=Lane.Points[Index-1], B=Lane.Points[Index];
            const FVector Along=(B-A).GetSafeNormal2D(), Side(-Along.Y,Along.X,0);
            for(int32 Edge:{-1,1})
            {
                const FVector From=A+Side*Edge*86.f, To=B+Side*Edge*86.f;
                const FVector Mid=(From+To)*.5f;
                const float Length=FVector::Dist2D(From,To);
                const FVector Half=FVector(FMath::Abs(Along.X)*Length*.5f+FMath::Abs(Side.X)*4.f,FMath::Abs(Along.Y)*Length*.5f+FMath::Abs(Side.Y)*4.f,0);
                Kit.Lit(FVector(Mid.X-Half.X,Mid.Y-Half.Y,0),FVector(Mid.X+Half.X,Mid.Y+Half.Y,1.8f),FLinearColor(.05f,.62f,.85f),.7f);
            }
        }
    for(float X=Kit.Map.Minimum.X+900.f;X<Kit.Map.Maximum.X-700.f;X+=1500.f)
        Kit.Lamp(FVector(X,0,700.f),FLinearColor(.6f,.82f,1.f),3000.f,2000.f);
}
