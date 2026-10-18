#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"

// Functional staging for the authored final exchange. The board is a separate
// stand, never attached to the torii; its two plaques move on their spoken cues.
// These kit figures and board parts still need the art lane's final treatment.
void ASoraWorldBuilder::StageEpilogue(const FSoraBeat& Beat)
{
    if(Beat.Id!=TEXT("ch08.b17")&&Beat.Id!=TEXT("ch08.b18")) return;
    const TCHAR* Cube=TEXT("/Engine/BasicShapes/Cube.Cube");
    const FLinearColor Wood(.30f,.18f,.08f),Plaque(.65f,.47f,.23f),Lacquer(.08f,.025f,.02f);
    EpilogueBoard=Floor(Beat.Space.Closing);
    EpilogueSwordStand=Floor(Beat.Space.Anchor);
    const FVector B=EpilogueBoard,S=EpilogueSwordStand;
    for(int32 Side:{-1,1})
    {
        KitShape(TEXT("NameboardFoot"),Cube,B+FVector(0,Side*85,8),FVector(.9f,.16f,.16f),Wood,TEXT("Timber"));
        KitShape(TEXT("NameboardPost"),Cube,B+FVector(0,Side*85,95),FVector(.16f,.16f,1.9f),Wood,TEXT("Timber"));
    }
    KitShape(TEXT("NameboardRail"),Cube,B+FVector(0,0,195),FVector(.15f,2.f,.18f),Wood,TEXT("Timber"));
    ToranosukePlaque=KitShape(TEXT("ToranosukePlaque"),Cube,B+FVector(0,-38,155),FVector(.12f,.28f,.65f),Plaque,TEXT("Timber"));
    NyaakotoPlaque=KitShape(TEXT("NyaakotoPlaque"),Cube,B+FVector(0,38,105),FVector(.12f,.28f,.65f),Plaque,TEXT("Timber"));
    for(int32 Side:{-1,1})
        KitShape(TEXT("SwordTrayLeg"),Cube,S+FVector(0,Side*45,35),FVector(.12f,.12f,.7f),Wood,TEXT("Timber"));
    KitShape(TEXT("SwordTray"),Cube,S+FVector(0,0,72),FVector(.55f,1.35f,.1f),Lacquer,TEXT("Timber"));
    // The returned heirloom is a collectible, not a copy of Nyaakoto's weapon
    // entitlement. Its closed sheath and hilt move from the tray to its owner.
    WashioSword.Add(KitShape(TEXT("WashioSaya"),Cube,S+FVector(0,-14,83),FVector(.065f,.92f,.075f),Lacquer,TEXT("Timber")));
    WashioSword.Add(KitShape(TEXT("WashioHilt"),Cube,S+FVector(0,45,83),FVector(.07f,.26f,.07f),FLinearColor(.17f,.15f,.1f)));
    WashioSword.Add(KitShape(TEXT("WashioGuard"),Cube,S+FVector(0,30,83),FVector(.16f,.025f,.16f),FLinearColor(.48f,.36f,.12f),TEXT("Metal")));
    KitMember(TEXT("villager"),S+FVector(130,0,0),180.f);
    KitMember(TEXT("villager"),B+FVector(100,150,0),180.f);
    KitMember(TEXT("villager"),B+FVector(-150,-300,0),0.f);
    const auto Label=[&](USceneComponent* Parent,const TCHAR* Name,FVector At,float Size)
    {
        auto* Text=NewObject<UTextRenderComponent>(this);
        Text->SetupAttachment(Parent); Text->SetAbsolute(false,false,true);
        Text->SetHorizontalAlignment(EHTA_Center); Text->SetVerticalAlignment(EVRTA_TextCenter);
        Text->SetText(FText::FromString(Name)); Text->SetTextRenderColor(FColor(235,223,190)); Text->SetWorldSize(Size);
        Text->RegisterComponent(); AddInstanceComponent(Text);
        Text->SetWorldLocation(At); Text->SetWorldRotation(FRotator(0,180,0));
        EpilogueLabels.Add(Text);
    };
    Label(ToranosukePlaque,TEXT("Toranosuke"),B+FVector(-8,-38,155),5.f);
    Label(NyaakotoPlaque,TEXT("Nyaakoto"),B+FVector(-8,38,105),5.f);
    Label(RootComponent,TEXT("Toranosuke"),S+FVector(130,0,185),12.f);
    Label(RootComponent,TEXT("Sekireisai"),B+FVector(100,150,185),12.f);
    ShowEpilogue(false,false,Beat.Id==TEXT("ch08.b18")?2:0);
}
void ASoraWorldBuilder::ShowEpilogue(bool SwordFound,bool SwordReturned,int32 Plaques)
{
    if(!ToranosukePlaque||!NyaakotoPlaque) return;
    EpiloguePlaques=FMath::Clamp(Plaques,0,2);
    bEpilogueSwordReturned=SwordFound&&SwordReturned;
    ToranosukePlaque->SetVisibility(EpiloguePlaques>=1,true);
    NyaakotoPlaque->SetRelativeLocation(EpilogueBoard+FVector(0,38,EpiloguePlaques>=2?155:105));
    for(int32 I=0;I<WashioSword.Num();++I)
    {
        auto* Part=WashioSword[I].Get();
        if(!Part) continue;
        Part->SetVisibility(SwordFound);
        const float Along=I==0?-14.f:I==1?45.f:30.f;
        Part->SetRelativeLocation(EpilogueSwordStand+FVector(bEpilogueSwordReturned?125.f:0.f,Along,bEpilogueSwordReturned?100.f:83.f));
    }
}
