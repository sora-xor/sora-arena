#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraWorldBuilder.generated.h"
class UStaticMeshComponent;
class UMaterialInterface;
struct FSoraPracticeMap;
struct FSoraChapter;
UCLASS()
class SORAARENA_API ASoraWorldBuilder : public AActor
{
    GENERATED_BODY()
public:
    ASoraWorldBuilder();
    void Build(int32 MapId, const FSoraChapter* Chapter = nullptr);
    void BuildPractice(int32 MapId, const FSoraPracticeMap& Map);
    bool ActivateNearest(const FVector& Location);
    int32 NearestInactiveNode(const FVector& Location) const;
    int32 ActiveNodes() const { return Activated.Num(); }
    int32 ActivatedMask() const;
    void RestoreActivatedMask(int32 Mask);
    FVector SpawnPoint(int32 Index) const;
    FVector ExitPoint() const { return FVector(2250,0,110); }
    FVector PlayerStart() const { return FVector(-2300,0,120); }
    static UStaticMeshComponent* Shape(AActor* Owner, USceneComponent* Parent, const FString& Name, const TCHAR* Asset, FVector Location, FVector Scale, FLinearColor Color, bool Collision = false);
    static void Tint(UStaticMeshComponent* Mesh, FLinearColor Color);
    static void Surface(UStaticMeshComponent* Mesh, const FString& Role, FLinearColor Color = FLinearColor::White);
    TArray<FVector> NodePositions;
private:
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Pieces;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Nodes;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> SiteEffects;
    TArray<FLinearColor> SiteRestoredColors;
    UPROPERTY() TArray<TObjectPtr<AActor>> DecorActors;
    TSet<int32> Activated;
    UStaticMeshComponent* Box(const FString& Name, FVector Location, FVector Size, FLinearColor Color, bool Collision = true, FRotator Rotation = FRotator::ZeroRotator, const FString& SurfaceRole = TEXT(""));
    void Building(FVector Location, FVector Size, FLinearColor Wall, bool HighTech);
    bool ImportedProp(const FString& Name, FVector Location, FRotator Rotation);
    void NyaagyuTerrain();
    void NyaagyuTree(FVector Location, FRotator Rotation, float Scale);
    void Torii(FVector Location, float Yaw);
    void ClearArena();
    void Lighting(int32 MapId);
};
