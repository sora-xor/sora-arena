#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"

void ASoraWorldBuilder::BuildArchive(const FSoraZone& Zone)
{
    const FVector O(Zone.Rect.Min,0);
    const FLinearColor Timber(.28f,.20f,.12f),Plaster(.43f,.41f,.35f),Slate(.09f,.14f,.16f);
    const auto Part=[&](const TCHAR* Name,FVector At,FVector Size,FLinearColor Color,const TCHAR* Role,bool Solid=true)
    { return Box(Name,O+At,Size,Color,Solid,FRotator::ZeroRotator,Role); };
    Part(TEXT("ArchiveBoardFloor"),FVector(1300,900,-40),FVector(2760,1960,80),Timber,TEXT("Timber"));
    Part(TEXT("ArchiveRoof"),FVector(1300,900,620),FVector(2760,1960,40),Timber,TEXT("Timber"));
    for(const FSoraBox& Wall:Zone.Walls)
        Box(TEXT("ArchiveWall"),FVector(Wall.Center,Wall.Height*.5f),FVector(Wall.Size,Wall.Height),Plaster,true,FRotator::ZeroRotator,TEXT("Stone"));
    for(int I=0;I<Zone.Cover.Num();++I)
    {
        const auto& Post=Zone.Cover[I];
        auto* P=Box(FString::Printf(TEXT("ArchiveDuelPost%d"),I),FVector(Post.Center,Post.Height*.5f),
            FVector(Post.Size,Post.Height),Timber,true,FRotator::ZeroRotator,TEXT("Timber"));
        P->ComponentTags.Add(TEXT("ArchiveDuelPost"));
    }
    // Physical racks occupy the authored 1.2 m strips; the four duel posts
    // alone occupy the ring. These are collision proxies pending final art.
    for(int Side:{0,1})
        Part(TEXT("ArchiveSlateRack"),FVector(Side?2540:60,900,180),FVector(120,1800,360),Slate,TEXT("Metal"));
    ArchivePage=Part(TEXT("ArchiveWashioSlate"),FVector(2477,900,150),FVector(4,75,100),FLinearColor(.025f,.04f,.05f),TEXT("Metal"),false);
    ArchivePage->ComponentTags.Add(TEXT("ArchiveFamilyPage"));
    ArchivePageLight=GetWorld()->SpawnActor<APointLight>(O+FVector(2440,900,150),FRotator::ZeroRotator);
    if(ArchivePageLight)
    {
        ArchivePageLight->Tags.Add(TEXT("ArchiveFamilyPageLight"));
        auto* Light=ArchivePageLight->PointLightComponent.Get();
        Light->SetIntensityUnits(ELightUnits::Lumens);
        Light->SetIntensity(0.f); Light->SetVisibility(false);
        Light->SetLightColor(FLinearColor(.18f,.85f,1.f));
        Light->SetAttenuationRadius(700.f); Light->SetSourceRadius(15.f);
        Light->SetCastShadows(false);
        DecorActors.Add(ArchivePageLight);
    }
    for(float Y:{-1.f,1801.f})
        Part(TEXT("ArchiveDoor"),FVector(1300,Y,130),FVector(200,4,260),Timber,TEXT("Timber"),false);
    Part(TEXT("ArchiveHighWindow"),FVector(2100,1798,470),FVector(160,4,110),FLinearColor(.015f,.02f,.025f),TEXT("Timber"),false);
}

void ASoraWorldBuilder::ShowArchivePage(const FSoraBeat& Beat,int32 Phase)
{
    // Derived from the existing phase/checkpoint, so retrying P1 hides it and
    // restoring P2 or entering the pledge lights the same physical slate.
    const bool Lit=(Beat.Id==TEXT("ch06.b09")&&Phase>=1)||Beat.Id==TEXT("ch06.b10");
    if(IsValid(ArchivePage)) Tint(ArchivePage,Lit?FLinearColor(.12f,.72f,.82f):FLinearColor(.025f,.04f,.05f));
    if(IsValid(ArchivePageLight))
    {
        auto* Light=ArchivePageLight->PointLightComponent.Get();
        Light->SetIntensity(Lit?450.f:0.f); Light->SetVisibility(Lit);
    }
}
