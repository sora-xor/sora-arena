#include "SoraWorldBuilder.h"
#include "ArenaKernelSubsystem.h"
#include "World/SoraPracticeArena.h"

// Silk Foundry, map 2: the levy loom beside the foundry production station.
void ASoraWorldBuilder::SilkFoundryLoom(FVector P)
{
    // The original silk loom is decorative beside the Silk Foundry
    // production station. Its meter and operator face the approach;
    // the established simple boxes retain gameplay collision.
    ImportedProp(TEXT("SM_SilkFoundry_LevyLoom"),P+FVector(-100,-450,0),FRotator::ZeroRotator);
}

// Practice: the foundry floor. Brick and iron halls, a furnace with a
// glowing mouth, loom rows hung with indigo silk, reeling machines and dye
// vats, all dressed inside the kernel's boxes; iron walkways follow the lanes.
void SoraPracticeDressing::SilkFoundryWall(FSoraPracticeArenaKit& Kit,const FSoraPracticeWall& Wall,int32 Index)
{
    using K=FSoraPracticeArenaKit;
    const FLinearColor Brick(.56f,.31f,.22f), Brass(.62f,.45f,.16f);
    const float H=K::Height(Wall);
    if(K::Labelled(Wall,TEXT("perimeter"))) Industrial(Kit,Wall,Brick,FLinearColor::Black,false);
    else if(K::Labelled(Wall,TEXT("furnace")))
    {
        // A furnace: the mouth glows at working height; the stack is iron.
        Kit.Course(Wall,0,60,TEXT("Stone"),FLinearColor(.4f,.39f,.37f));
        Kit.LitCourse(Wall,60,200,TEXT("Metal"),FLinearColor(.28f,.28f,.3f),FLinearColor(.16f,.05f,.02f),FLinearColor(1.f,.42f,.08f),2.4f,260.f,170.f);
        Kit.Course(Wall,200,H-120,TEXT("Stone"),Brick);
        Kit.Course(Wall,H-120,H,TEXT("Metal"),FLinearColor(.24f,.24f,.26f));
        const FVector Center=(Wall.Minimum+Wall.Maximum)*.5;
        for(int32 Side:{-1,1})
            Kit.Lamp(FVector(Center.X,Side>0?Wall.Maximum.Y+60.f:Wall.Minimum.Y-60.f,130.f),FLinearColor(1.f,.45f,.12f),4200.f,1100.f,Side>0);
    }
    else if(K::Labelled(Wall,TEXT("loom")))
    {
        // A loom row: timber frames strung with indigo silk.
        Kit.Course(Wall,0,20,TEXT("Timber"),FLinearColor(.3f,.21f,.16f));
        Kit.Bays(Wall,20,H-18,100.f,12.f,TEXT("Timber"),FLinearColor(.42f,.3f,.2f),nullptr,FLinearColor(.07f,.1f,.32f));
        Kit.Course(Wall,H-18,H,TEXT("Timber"),FLinearColor(.3f,.21f,.16f));
    }
    else if(K::Labelled(Wall,TEXT("dye vats")))
    {
        if(!Kit.FittedProp(TEXT("SM_Nyaagyu_IrrigationSluice"),Wall.Minimum,Wall.Maximum,1.45f)) Machine(Kit,Wall,FLinearColor(.1f,.14f,.42f));
    }
    else if(K::Labelled(Wall,TEXT("pillar"))) Column(Kit,Wall,FLinearColor(1.f,.55f,.2f),.8f);
    else if(K::Labelled(Wall,TEXT("boiler"))) Industrial(Kit,Wall,Brick,FLinearColor(1.f,.5f,.16f),true);
    else if(K::Labelled(Wall,TEXT("coal"))) Industrial(Kit,Wall,FLinearColor(.4f,.26f,.2f),FLinearColor::Black,false);
    else if(K::Labelled(Wall,TEXT("crate"))) Goods(Kit,Wall);
    else if(K::Labelled(Wall,TEXT("rail"))) Fence(Kit,Wall);
    else Machine(Kit,Wall,K::Labelled(Wall,TEXT("reeling"))?Brass:FLinearColor(.35f,.35f,.37f));
}
void SoraPracticeDressing::SilkFoundryGrounds(FSoraPracticeArenaKit& Kit)
{
    // Iron walkway plates along the lanes over the stone floor.
    Lanes(Kit,TEXT("Metal"),FLinearColor(.5f,.5f,.52f),150.f,2.f,false);
    // Production light over the hall, in the resistance's cyan.
    for(float X=Kit.Map.Minimum.X+800.f;X<Kit.Map.Maximum.X-600.f;X+=1400.f)
        for(int32 Side:{-1,1})
            Kit.Lamp(FVector(X,Side*900.f,650.f),FLinearColor(.72f,.9f,1.f),3200.f,1800.f);
}
