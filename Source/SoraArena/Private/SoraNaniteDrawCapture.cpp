#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "World/SoraPresentationCapabilities.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DataDrivenShaderPlatformInfo.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Misc/SecureHash.h"
#include "UObject/Package.h"
#include "Materials/MaterialInterface.h"
#include "NaniteVisualizationData.h"
#include "RHI.h"
#include "DynamicRHI.h"
#include "RHIGlobals.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectIterator.h"
#include "UnrealClient.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "DistanceFieldAtlas.h"
#include "MeshCardBuild.h"
#include "MeshDescription.h"
#include "Rendering/NaniteResources.h"
#include "ShaderCompiler.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshResources.h"
#endif

// Development-only evidence capture. Never changes assets, r.Nanite, the
// environment tier, or materials. Visualization and the camera are temporary;
// a success here means originals were captured, not that Nanite drew anything.
// The archive verifier must find green Mask pixels on the production dojo and
// a corresponding different Triangles frame. Zero coverage is a failed gate.
namespace SoraNaniteDrawCapture
{
constexpr const TCHAR* Scope=TEXT("production dojo renderer diagnostic; unadmitted art; not gameplay or platform release acceptance");
const TCHAR* Cameras[]={TEXT("entry"),TEXT("ceiling")};
const TCHAR* Modes[]={TEXT("Lit"),TEXT("Mask"),TEXT("Triangles")};
const FVector Locations[]={FVector(8420,0,154),FVector(9500,-200,154)};
const FRotator Rotations[]={FRotator(4,0,0),FRotator(52,20,0)};
TArray<TSharedPtr<FJsonValue>> Vec(const FVector& V)
{ return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)}; }
#if WITH_EDITOR
// CPU asset observations only. These are not GPU atlas residency, card capture
// coverage or lighting acceptance. Do not rebuild, save or request streamed data.
namespace DerivedData
{
void VectorField(const TSharedRef<FJsonObject>& O,const TCHAR* Name,const FVector& V)
{
    if (V.ContainsNaN()) O->SetStringField(Name,TEXT("unavailable_nonfinite"));
    else O->SetArrayField(Name,Vec(V));
}
TSharedRef<FJsonObject> Bounds(const FBox& B)
{
    auto O=MakeShared<FJsonObject>();
    const bool Valid=B.IsValid&&!B.Min.ContainsNaN()&&!B.Max.ContainsNaN();
    O->SetBoolField(TEXT("valid"),Valid);
    if (Valid) { VectorField(O,TEXT("min"),B.Min); VectorField(O,TEXT("max"),B.Max); }
    return O;
}
TSharedRef<FJsonObject> ObserveDistanceField(const FDistanceFieldVolumeData* D)
{
    auto O=MakeShared<FJsonObject>();
    O->SetStringField(TEXT("status"),!D?TEXT("absent"):D->bAsyncBuilding?TEXT("unavailable_async_building"):TEXT("available"));
    if (!D||D->bAsyncBuilding) return O;
    O->SetBoolField(TEXT("valid"),D->IsValid());
    O->SetObjectField(TEXT("bounds"),Bounds(FBox(D->LocalSpaceMeshBounds)));
    O->SetBoolField(TEXT("mostly_two_sided"),D->bMostlyTwoSided);
    TArray<TSharedPtr<FJsonValue>> Mips;
    for (int32 I=0;I<::DistanceField::NumMips;++I)
    {
        const auto& M=D->Mips[I]; auto P=MakeShared<FJsonObject>();
        P->SetNumberField(TEXT("index"),I);
        P->SetArrayField(TEXT("indirection_dimensions"),{MakeShared<FJsonValueNumber>(M.IndirectionDimensions.X),
            MakeShared<FJsonValueNumber>(M.IndirectionDimensions.Y),MakeShared<FJsonValueNumber>(M.IndirectionDimensions.Z)});
        P->SetNumberField(TEXT("bricks"),M.NumDistanceFieldBricks);
        VectorField(P,TEXT("volume_to_virtual_uv_scale"),FVector(M.VolumeToVirtualUVScale));
        VectorField(P,TEXT("volume_to_virtual_uv_add"),FVector(M.VolumeToVirtualUVAdd));
        if (M.DistanceFieldToVolumeScaleBias.ContainsNaN()) P->SetStringField(TEXT("distance_field_to_volume_scale_bias"),TEXT("unavailable_nonfinite"));
        else P->SetArrayField(TEXT("distance_field_to_volume_scale_bias"),{MakeShared<FJsonValueNumber>(M.DistanceFieldToVolumeScaleBias.X),
            MakeShared<FJsonValueNumber>(M.DistanceFieldToVolumeScaleBias.Y)});
        P->SetNumberField(TEXT("bulk_offset"),M.BulkOffset); P->SetNumberField(TEXT("bulk_bytes"),M.BulkSize);
        Mips.Add(MakeShared<FJsonValueObject>(P));
    }
    O->SetArrayField(TEXT("mips"),Mips);
    O->SetNumberField(TEXT("always_loaded_bytes"),D->AlwaysLoadedMip.Num());
    O->SetStringField(TEXT("always_loaded_hash_algorithm"),TEXT("MD5 of exact byte-array payload; no struct memory"));
    O->SetStringField(TEXT("always_loaded_md5"),FMD5::HashBytes(D->AlwaysLoadedMip.GetData(),D->AlwaysLoadedMip.Num()));
    O->SetNumberField(TEXT("streamable_bytes"),double(D->StreamableMips.GetBulkDataSize()));
    O->SetBoolField(TEXT("streamable_cpu_resident"),D->StreamableMips.IsBulkDataLoaded());
    O->SetStringField(TEXT("streamable_payload_status"),TEXT("not_read; no bulk lock or streaming request"));
    return O;
}
TSharedRef<FJsonObject> Cards(const FCardRepresentationData* D)
{
    auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("status"),D?TEXT("available"):TEXT("absent"));
    if (!D) return O;
    const auto& Data=D->MeshCardsBuildData;
    O->SetObjectField(TEXT("bounds"),Bounds(Data.Bounds)); O->SetBoolField(TEXT("mostly_two_sided"),Data.bMostlyTwoSided);
    O->SetBoolField(TEXT("contains_nonfinite"),Data.ContainsNaN()); O->SetNumberField(TEXT("count"),Data.CardBuildData.Num());
    TArray<TSharedPtr<FJsonValue>> Items;
    for (const auto& Card:Data.CardBuildData)
    {
        auto C=MakeShared<FJsonObject>();
        VectorField(C,TEXT("origin"),FVector(Card.OBB.Origin)); VectorField(C,TEXT("extent"),FVector(Card.OBB.Extent));
        VectorField(C,TEXT("axis_x"),FVector(Card.OBB.AxisX)); VectorField(C,TEXT("axis_y"),FVector(Card.OBB.AxisY));
        VectorField(C,TEXT("axis_z"),FVector(Card.OBB.AxisZ));
        C->SetNumberField(TEXT("direction_index"),Card.AxisAlignedDirectionIndex);
        C->SetNumberField(TEXT("dilation_mode"),static_cast<uint8>(Card.DilationMode));
        Items.Add(MakeShared<FJsonValueObject>(C));
    }
    O->SetArrayField(TEXT("cards"),Items); return O;
}
TSharedRef<FJsonObject> Description(const UStaticMesh& Mesh,const FMeshDescription* D)
{
    auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("status"),D?TEXT("available"):TEXT("absent"));
    if (!D) return O;
    O->SetNumberField(TEXT("vertices"),D->Vertices().Num()); O->SetNumberField(TEXT("triangles"),D->Triangles().Num());
    const FStaticMeshConstAttributes Attributes(*D);
    const auto Slots=Attributes.GetPolygonGroupMaterialSlotNames();
    O->SetBoolField(TEXT("imported_slot_attribute_valid"),Slots.IsValid());
    TArray<TSharedPtr<FJsonValue>> Groups; int32 Ordinal=0;
    for (const FPolygonGroupID Id:D->PolygonGroups().GetElementIDs())
    {
        auto G=MakeShared<FJsonObject>(); G->SetNumberField(TEXT("id"),Id.GetValue()); G->SetNumberField(TEXT("ordinal"),Ordinal);
        const auto Triangles=D->GetPolygonGroupTriangles(Id); G->SetNumberField(TEXT("triangles"),Triangles.Num());
        FBox B(ForceInit); bool Finite=true;
        for (const FTriangleID Triangle:Triangles)
            for (const FVertexID Vertex:D->GetTriangleVertices(Triangle))
            {
                const FVector P(D->GetVertexPosition(Vertex));
                if (P.ContainsNaN()) Finite=false; else B+=P;
            }
        G->SetBoolField(TEXT("all_positions_finite"),Finite); G->SetObjectField(TEXT("source_bounds"),Bounds(B));
        if (Slots.IsValid())
        {
            const FName Slot=Slots[Id]; const int32 Material=Mesh.GetMaterialIndexFromImportedMaterialSlotName(Slot);
            G->SetStringField(TEXT("imported_slot"),Slot.ToString()); G->SetNumberField(TEXT("slot_resolved_material"),Material);
        }
        const auto& Map=Mesh.GetSectionInfoMap();
        G->SetBoolField(TEXT("lod0_section_info_exists"),Map.IsValidSection(0,Ordinal));
        G->SetNumberField(TEXT("lod0_section_info_material_or_default"),Map.Get(0,Ordinal).MaterialIndex);
        // Raw source group order, not a call to the mesh builder. Its setup and
        // degenerate removal can change the final generated section contents.
        Groups.Add(MakeShared<FJsonValueObject>(G)); ++Ordinal;
    }
    O->SetArrayField(TEXT("polygon_groups"),Groups); return O;
}
TSharedRef<FJsonObject> ObserveMesh(const UStaticMesh& Mesh)
{
    auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("mesh"),Mesh.GetPathName());
    O->SetStringField(TEXT("scope"),TEXT("existing CPU generated data and raw editor source correspondence; no GPU coverage or causal claim"));
    O->SetBoolField(TEXT("mesh_async_compiling"),Mesh.IsCompiling());
    if (Mesh.IsCompiling()) { O->SetStringField(TEXT("status"),TEXT("unavailable_async_compiling")); return O; }
    const auto* Render=Mesh.GetRenderData();
    O->SetStringField(TEXT("render_data_status"),Render?TEXT("available"):TEXT("absent"));
    TArray<TSharedPtr<FJsonValue>> Materials;
    const auto& Slots=Mesh.GetStaticMaterials();
    for (int32 I=0;I<Slots.Num();++I)
    {
        const auto& S=Slots[I]; auto M=MakeShared<FJsonObject>(); const auto* Material=S.MaterialInterface.Get();
        M->SetNumberField(TEXT("index"),I); M->SetStringField(TEXT("slot"),S.MaterialSlotName.ToString());
        M->SetStringField(TEXT("imported_slot"),S.ImportedMaterialSlotName.ToString());
        M->SetStringField(TEXT("material"),GetPathNameSafe(Material));
        if (Material) { M->SetNumberField(TEXT("blend_mode"),Material->GetBlendMode()); M->SetBoolField(TEXT("two_sided"),Material->IsTwoSided()); }
        Materials.Add(MakeShared<FJsonValueObject>(M));
    }
    O->SetArrayField(TEXT("static_materials"),Materials);
    if (Render&&Render->LODResources.Num()>0)
    {
        const auto& LOD=Render->LODResources[0];
        O->SetObjectField(TEXT("distance_field"),ObserveDistanceField(LOD.DistanceFieldData));
        O->SetObjectField(TEXT("card_representation"),Cards(LOD.CardRepresentationData));
        TArray<TSharedPtr<FJsonValue>> Sections;
        for (int32 I=0;I<LOD.Sections.Num();++I)
        {
            const auto& S=LOD.Sections[I]; const auto Info=Mesh.GetSectionInfoMap().Get(0,I); auto P=MakeShared<FJsonObject>();
            P->SetNumberField(TEXT("index"),I); P->SetNumberField(TEXT("triangles"),S.NumTriangles);
            P->SetNumberField(TEXT("material"),S.MaterialIndex); P->SetBoolField(TEXT("affect_distance_field_lighting"),S.bAffectDistanceFieldLighting);
            P->SetBoolField(TEXT("cast_shadow"),S.bCastShadow);
            P->SetBoolField(TEXT("section_info_exists"),Mesh.GetSectionInfoMap().IsValidSection(0,I));
            P->SetNumberField(TEXT("section_info_material_or_default"),Info.MaterialIndex);
            P->SetBoolField(TEXT("section_info_affect_distance_field_lighting"),Info.bAffectDistanceFieldLighting);
            Sections.Add(MakeShared<FJsonValueObject>(P));
        }
        O->SetArrayField(TEXT("lod0_sections"),Sections);
    }
    else O->SetStringField(TEXT("lod0_status"),TEXT("unavailable"));
    O->SetStringField(TEXT("nanite_voxel_materials_mask_hex"),Render&&Render->NaniteResourcesPtr.IsValid()?
        FString::Printf(TEXT("%016llx"),static_cast<unsigned long long>(Render->NaniteResourcesPtr->VoxelMaterialsMask)):TEXT("unavailable"));
    O->SetBoolField(TEXT("nanite_enabled"),Mesh.IsNaniteEnabled());
    O->SetObjectField(TEXT("lod0_source"),Description(Mesh,Mesh.GetNumSourceModels()>0&&Mesh.IsMeshDescriptionValid(0)?Mesh.GetMeshDescription(0):nullptr));
    O->SetObjectField(TEXT("hires_source"),Description(Mesh,Mesh.IsHiResMeshDescriptionValid()?Mesh.GetHiResMeshDescription():nullptr));
    O->SetStringField(TEXT("source_mapping_limit"),TEXT("raw polygon-group ordinal and slot lookup versus LOD0 section map; not rebuilt or proof of cached SDF input"));
    return O;
}
}
#endif
struct FCVar
{
    IConsoleVariable* Var=nullptr; FString Name,Value; EConsoleVariableFlags Flags=ECVF_Default;
    bool Save(const TCHAR* InName)
    {
        Name=InName; Var=IConsoleManager::Get().FindConsoleVariable(InName);
        if (!Var) return false; Value=Var->GetString(); Flags=Var->GetFlags(); return true;
    }
    void Set(const TCHAR* V) const { Var->Set(V,static_cast<EConsoleVariableFlags>(Flags&ECVF_SetByMask)); }
    bool Restore() const
    {
        if (!Var) return true;
        Set(*Value); Var->SetFlags(Flags);
        return Var->GetString()==Value&&Var->GetFlags()==Flags;
    }
};
class FRun final:public IAutomationLatentCommand
{
public:
    FRun(FAutomationTestBase& InTest,bool InSM6):Test(InTest),SM6(InSM6) {}
    ~FRun() { Cleanup(); }
    bool Update() override
    {
        if (!Started) { Started=true; Begin(); }
        if (Failed||Step==Count()) { Cleanup(); return true; }
        if (FPlatformTime::Seconds()-StartTime>150) { Fail(TEXT("Nanite draw capture timed out")); Cleanup(); return true; }
        if (!M.IsValid()||!Camera.IsValid()||!PC()||!M->GetWorld()->IsPaused())
        { Fail(TEXT("Capture lost its paused production world/camera")); return false; }
        if (!Waiting&&FPlatformTime::Seconds()-ChangedAt>=3) Capture();
        return false;
    }
private:
    FAutomationTestBase& Test;
    bool NaniteEligible=false,SM6=false,Started=false,Failed=false,Cleaned=false,BackedUp=false,ChangedWorld=false,Waiting=false;
    bool WasCampaign=false,WasPractice=false,WasPaused=false,ShowHUD=true;
    int32 Step=0,OldViewMode=0; double StartTime=0,ChangedAt=0;
    TWeakObjectPtr<ASoraGameMode> M;
    TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<AActor> OldTarget;
    TWeakObjectPtr<AHUD> HUD;
    SoraUI::EScreen OldScreen=SoraUI::EScreen::Title;
    FEngineShowFlags OldFlags{ESFIM_Game}; FName OldNaniteMode;
    FString Slot,Slots[3],Folder,Pending,ShaderPlatform;
    TArray<uint8> Profile[3]; bool Existed[3]={};
    FCVar Visualize,Composite,Edges,Shading;
    FDelegateHandle Screenshot;
    FVector2D ViewportSize=FVector2D::ZeroVector;
    TArray<TSharedPtr<FJsonValue>> Frames,Meshes,AssetFiles,DerivedAssets,CoverageInputs,ChapterEstateHalls;
    FString ChapterId;
    TSet<FString> HashedFiles;
    int32 Count() const { return SM6?6:2; }
    APlayerController* PC() const { return M.IsValid()?UGameplayStatics::GetPlayerController(M.Get(),0):nullptr; }
    UGameViewportClient* Viewport() const { return M.IsValid()?M->GetWorld()->GetGameViewport():nullptr; }
    void Fail(const TCHAR* Reason) { if (!Failed) Test.AddError(Reason); Failed=true; }
    FString CVar(const TCHAR* Name) const
    { const auto* V=IConsoleManager::Get().FindConsoleVariable(Name); return V?V->GetString():TEXT("absent"); }
    TSharedRef<FJsonObject> RenderState() const
    {
        auto O=MakeShared<FJsonObject>();
        for (const TCHAR* Name:{TEXT("r.Nanite"),TEXT("r.Nanite.ProxyRenderMode"),TEXT("r.Nanite.Visualize"),
            TEXT("r.Nanite.Visualize.Composite"),TEXT("r.Nanite.Visualize.EdgeDetect"),TEXT("r.Nanite.Visualize.DebugShading"),
            TEXT("r.ScreenPercentage"),TEXT("r.AntiAliasingMethod"),TEXT("sora.HallInstanced"),
            TEXT("r.Lumen.DiffuseIndirect.Allow"),TEXT("r.Lumen.TraceMeshSDFs.Allow"),
            TEXT("r.DistanceFields.DefaultVoxelDensity"),TEXT("r.DistanceFields.MaxPerMeshResolution")}) O->SetStringField(Name,CVar(Name));
        return O;
    }
    void Begin()
    {
        StartTime=FPlatformTime::Seconds();
        for (const auto& C:GEngine->GetWorldContexts())
            if (C.WorldType==EWorldType::Game&&C.World()) M=Cast<ASoraGameMode>(C.World()->GetAuthGameMode());
        if (!M.IsValid()||!PC()||!PC()->PlayerCameraManager||!Viewport()||!M->GetWorld()->Scene||!M->Campaign()||!M->FrontEnd()||!FSoraCatalog::Get().IsReady()||GUsingNullRHI)
        { Fail(TEXT("Nanite evidence requires a rendered game with its production catalog")); return; }
        // Rebuilding an active game would lose unsaved play. Only a disposable
        // launch at Title/Main is permitted; cleanup rebuilds that checkpoint.
        OldScreen=M->FrontEnd()->Screen();
        if (!M->bMenu||M->bDeterministicPractice||!M->GetWorld()->IsPaused()||
            (OldScreen!=SoraUI::EScreen::Title&&OldScreen!=SoraUI::EScreen::Main))
        { Fail(TEXT("Start this diagnostic in a fresh paused Title/Main session, never active play")); return; }
        const EShaderPlatform Platform=M->GetWorld()->Scene->GetShaderPlatform();
        if (!FDataDrivenShaderPlatformInfo::IsValid(Platform)) { Fail(TEXT("Actual scene shader platform is invalid")); return; }
        ShaderPlatform=FDataDrivenShaderPlatformInfo::GetName(Platform).ToString();
        const bool Eligible=SoraPresentation::UsesNaniteEnvironment(M->GetWorld()); NaniteEligible=Eligible;
        if ((SM6&&(!ShaderPlatform.Contains(TEXT("SM6"))||!Eligible))||
            (!SM6&&(!ShaderPlatform.Contains(TEXT("SM5"))||Eligible)))
        { Fail(TEXT("Actual shader platform/capability does not match the separately requested SM6 or SM5 diagnostic")); return; }
        Viewport()->GetViewportSize(ViewportSize);
        if (ViewportSize!=FVector2D(1280,720)&&ViewportSize!=FVector2D(1920,1080))
        { Fail(TEXT("Nanite capture requires 1280x720 or 1920x1080")); return; }
        Slots[0]=M->SaveSlotName; Slots[1]=M->ControlSlotName; Slots[2]=M->SettingsSlotName;
        for (int32 I=0;I<3;++I)
        {
            Existed[I]=UGameplayStatics::DoesSaveGameExist(Slots[I],0);
            if (Existed[I]&&!UGameplayStatics::LoadDataFromSlot(Profile[I],Slots[I],0))
            { Fail(TEXT("Could not preserve original profile bytes")); return; }
        }
        WasCampaign=M->bCampaign; WasPractice=M->bDeterministicPractice; WasPaused=M->GetWorld()->IsPaused();
        OldTarget=PC()->GetViewTarget(); HUD=PC()->GetHUD(); if (HUD.IsValid()) ShowHUD=HUD->bShowHUD;
        OldViewMode=Viewport()->ViewModeIndex; OldFlags=Viewport()->EngineShowFlags; OldNaniteMode=Viewport()->GetCurrentNaniteVisualizationMode();
        BackedUp=true;
        GetNaniteVisualizationData(); // Initializes the engine-owned cvar registry.
        if (!Visualize.Save(TEXT("r.Nanite.Visualize"))||!Composite.Save(TEXT("r.Nanite.Visualize.Composite"))||
            !Edges.Save(TEXT("r.Nanite.Visualize.EdgeDetect"))||!Shading.Save(TEXT("r.Nanite.Visualize.DebugShading")))
        { Fail(TEXT("Engine Nanite visualization controls are unavailable")); return; }
        Slot=TEXT("SoraNaniteDraw_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraNaniteDraw")/
            FString::Printf(TEXT("%dx%d"),int32(ViewportSize.X),int32(ViewportSize.Y))/FGuid::NewGuid().ToString(EGuidFormats::Digits));
        IFileManager::Get().MakeDirectory(*Folder,true);
        auto* Save=Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save||!USoraCampaignDirector::SeedCheckpoint(*Save,0,1)||!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
        { Fail(TEXT("Could not create the isolated production dojo checkpoint")); return; }
        ChangedWorld=true; M->SaveSlotName=Slot; M->bCampaign=true; M->bDeterministicPractice=false;
        if (!M->Campaign()->LoadSave()) { Fail(TEXT("Dojo checkpoint did not load")); return; }
        M->ResetRound(); M->SetMenuOpen(false); UGameplayStatics::SetGamePaused(M.Get(),true);
        if (HUD.IsValid()) HUD->bShowHUD=false;
        Camera=M->GetWorld()->SpawnActor<ACameraActor>();
        if (!Camera.IsValid()) { Fail(TEXT("Could not create a temporary diagnostic camera")); return; }
        Camera->GetCameraComponent()->SetFieldOfView(94.f);
        PC()->SetViewTarget(Camera.Get());
#if WITH_EDITOR
        FAssetCompilingManager::Get().FinishAllCompilation();
        if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
#endif
        Inventory();
        Screenshot=FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this,&FRun::Captured);
        Switch();
    }
    void Inventory()
    {
        const FSoraChapter* Chapter=M->Campaign()->ActiveChapter();
        if (!Chapter) { Fail(TEXT("Nanite capture has no active chapter")); return; }
        ChapterId=Chapter->Id;
        for (const FSoraZone& Zone:Chapter->Space.Zones)
        {
            if (Zone.Style!=TEXT("estate")||Zone.Form!=TEXT("hall")) continue;
            auto Hall=MakeShared<FJsonObject>(); Hall->SetStringField(TEXT("zone"),Zone.Id);
            Hall->SetArrayField(TEXT("rect"),{MakeShared<FJsonValueNumber>(Zone.Rect.Min.X),MakeShared<FJsonValueNumber>(Zone.Rect.Min.Y),
                MakeShared<FJsonValueNumber>(Zone.Rect.Max.X),MakeShared<FJsonValueNumber>(Zone.Rect.Max.Y)});
            Hall->SetNumberField(TEXT("wall_cm"),Zone.WallHeight); ChapterEstateHalls.Add(MakeShared<FJsonValueObject>(Hall));
        }
        TSet<const UStaticMesh*> ObservedAssets;
        // Only actual registered components from the current production world.
        // Bounds/asset validity are identities, never a visible-draw counter.
        for (TObjectIterator<UStaticMeshComponent> It;It;++It)
        {
            auto* C=*It; auto* Mesh=C->GetStaticMesh().Get();
            if (C->GetWorld()!=M->GetWorld()||!C->IsRegistered()||!C->IsVisible()||!Mesh) continue;
            const bool Timber=Mesh->GetPathName().StartsWith(TEXT("/Game/Generated/Environment/DojoTimbers/"));
            if (!Timber&&!Mesh->GetPathName().StartsWith(TEXT("/Game/Generated/Environment/DojoKit/"))) continue;
            auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("component"),C->GetPathName());
            O->SetStringField(TEXT("asset_family"),Timber?TEXT("DojoTimbers"):TEXT("DojoKit"));
            O->SetStringField(TEXT("mesh"),Mesh->GetPathName()); O->SetStringField(TEXT("class"),C->GetClass()->GetName());
            O->SetBoolField(TEXT("has_nanite_data"),Mesh->HasValidNaniteData());
            if (Mesh->HasValidNaniteData()) O->SetBoolField(TEXT("has_platform_fallback"),Mesh->HasNaniteFallbackMesh(M->GetWorld()->Scene->GetShaderPlatform()));
            O->SetBoolField(TEXT("disallow_nanite"),C->IsDisallowNanite());
            O->SetBoolField(TEXT("force_disable_nanite"),C->IsForceDisableNanite());
            O->SetBoolField(TEXT("affect_distance_field_lighting"),C->bAffectDistanceFieldLighting);
            const FString Package=FPaths::ConvertRelativePathToFull(FPackageName::LongPackageNameToFilename(Mesh->GetOutermost()->GetName(),FPackageName::GetAssetPackageExtension()));
            O->SetStringField(TEXT("package_file"),Package);
            if (IFileManager::Get().FileSize(*Package)<=0) { Fail(TEXT("This uncooked diagnostic requires the original loose dojo mesh packages")); return; }
            for (const FString& File:{Package,FPaths::ChangeExtension(Package,TEXT("uexp")),FPaths::ChangeExtension(Package,TEXT("ubulk"))})
            {
                const int64 Size=IFileManager::Get().FileSize(*File);
                if (Size<=0||HashedFiles.Contains(File)) continue;
                auto A=MakeShared<FJsonObject>(); A->SetStringField(TEXT("path"),File); A->SetNumberField(TEXT("bytes"),double(Size));
                A->SetStringField(TEXT("md5"),LexToString(FMD5Hash::HashFile(*File)));
                AssetFiles.Add(MakeShared<FJsonValueObject>(A)); HashedFiles.Add(File);
            }
#if WITH_EDITORONLY_DATA
            O->SetBoolField(TEXT("authoring_nanite_enabled"),Mesh->IsNaniteEnabled());
#endif
            if (!ObservedAssets.Contains(Mesh))
            {
                ObservedAssets.Add(Mesh);
#if WITH_EDITOR
                DerivedAssets.Add(MakeShared<FJsonValueObject>(DerivedData::ObserveMesh(*Mesh)));
#else
                auto D=MakeShared<FJsonObject>(); D->SetStringField(TEXT("mesh"),Mesh->GetPathName());
                D->SetStringField(TEXT("status"),TEXT("unavailable_noneditor")); DerivedAssets.Add(MakeShared<FJsonValueObject>(D));
#endif
            }
            // Instances were just populated; the public cached Bounds can
            // still be zero before the first frame. Query their actual mesh
            // and instance transforms without changing the production scene.
            const FBoxSphereBounds Bounds=C->CalcBounds(C->GetComponentTransform());
            O->SetStringField(TEXT("bounds_source"),TEXT("component CalcBounds at current transform; not render coverage"));
            O->SetArrayField(TEXT("bounds_origin"),Vec(Bounds.Origin)); O->SetArrayField(TEXT("bounds_extent"),Vec(Bounds.BoxExtent));
            O->SetArrayField(TEXT("cached_bounds_origin"),Vec(C->Bounds.Origin)); O->SetArrayField(TEXT("cached_bounds_extent"),Vec(C->Bounds.BoxExtent));
            const auto* Instances=Cast<UInstancedStaticMeshComponent>(C);
            O->SetNumberField(TEXT("instances"),Instances?Instances->GetInstanceCount():1);
            if (Timber)
            {
                TArray<TSharedPtr<FJsonValue>> Transforms;
                for (int32 I=0;I<(Instances?Instances->GetInstanceCount():1);++I)
                {
                    FTransform Transform=C->GetComponentTransform();
                    if (Instances&&!Instances->GetInstanceTransform(I,Transform,true))
                    { Fail(TEXT("Timber instance world transform is unavailable")); return; }
                    auto T=MakeShared<FJsonObject>(); const FRotator R=Transform.Rotator();
                    T->SetArrayField(TEXT("location"),Vec(Transform.GetLocation()));
                    T->SetArrayField(TEXT("rotation"),Vec(FVector(R.Pitch,R.Yaw,R.Roll)));
                    T->SetArrayField(TEXT("scale"),Vec(Transform.GetScale3D())); Transforms.Add(MakeShared<FJsonValueObject>(T));
                }
                O->SetArrayField(TEXT("instance_transforms"),Transforms);
            }
            TArray<TSharedPtr<FJsonValue>> Materials;
            for (int32 I=0;I<C->GetNumMaterials();++I)
                Materials.Add(MakeShared<FJsonValueString>(GetPathNameSafe(C->GetMaterial(I))));
            O->SetArrayField(TEXT("materials"),Materials); Meshes.Add(MakeShared<FJsonValueObject>(O));
        }
        if (Meshes.IsEmpty()) Fail(TEXT("Production dojo geometry is absent; primitive replacements are not evidence"));
        // Preserve exact current inputs, including absence. Archive validation
        // binds them to committed chapters and the reviewed immutable binder.
        // Never manufacture expectations from meshes that happened to load.
        TArray<FString> Inputs;
        for (int32 ChapterIndex=1;ChapterIndex<=8;++ChapterIndex)
            Inputs.Add(FString::Printf(TEXT("Content/Data/campaign/chapter_%02d.json"),ChapterIndex));
        for (const TCHAR* Input:{TEXT("Content/SourceArt/Environment/NyaagyuDojoTimbers/manifest.json"),
            TEXT("Content/SourceArt/Environment/NyaagyuDojoTimbers/Rails/manifest.json"),
            TEXT("Content/SourceArt/Environment/NyaagyuDojoTimbers/Floor/manifest.json"),
            TEXT("scripts/art/dojo_hall_placements.py"),TEXT("scripts/art/create_nyaagyu_dojo_timbers.py"),
            TEXT("scripts/art/create_nyaagyu_dojo_rails.py"),TEXT("scripts/art/create_nyaagyu_dojo_floor.py"),
            TEXT("Content/SourceArt/Environment/NyaagyuDojoTimbers/campaign_binding.json"),TEXT("scripts/art/bind_dojo_timbers.py"),
            TEXT("scripts/art/sora_timber_lib.py"),TEXT("scripts/art/sora_timber_lookdev.py"),TEXT("scripts/art/sora_timber_bake.py"),
            TEXT("scripts/art/sora_prop_lib.py"),TEXT("scripts/art/create_runtime_weapon_lib.py")}) Inputs.Add(Input);
        for (const FString& Relative:Inputs)
        {
            const FString File=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/Relative);
            const int64 Size=IFileManager::Get().FileSize(*File);
            auto Input=MakeShared<FJsonObject>(); Input->SetStringField(TEXT("path"),Relative);
            Input->SetBoolField(TEXT("exists"),Size>=0);
            if (Size>=0)
            {
                Input->SetNumberField(TEXT("bytes"),double(Size));
                Input->SetStringField(TEXT("md5"),LexToString(FMD5Hash::HashFile(*File)));
            }
            CoverageInputs.Add(MakeShared<FJsonValueObject>(Input));
        }
    }
    void Switch()
    {
        const int32 Cam=SM6?Step/3:Step, Mode=SM6?Step%3:0;
        Camera->SetActorLocationAndRotation(Locations[Cam],Rotations[Cam]);
        // Update the ordinary camera cache even though gameplay is paused.
        PC()->PlayerCameraManager->UpdateCamera(0.f);
        Viewport()->SetViewMode(VMI_Lit);
        Viewport()->SetCurrentNaniteVisualizationMode(NAME_None);
        Visualize.Set(Mode?Modes[Mode]:TEXT("off"));
        Composite.Set(TEXT("1")); Edges.Set(TEXT("0")); Shading.Set(TEXT("0"));
        Viewport()->EngineShowFlags.SetVisualizeNanite(Mode!=0);
        ChangedAt=FPlatformTime::Seconds();
    }
    void Capture()
    {
        const int32 Cam=SM6?Step/3:Step, Mode=SM6?Step%3:0;
        // Read the engine renderer's completed mode selection, not a locally
        // forced Update. This synchronization is not a performance sample.
        FlushRenderingCommands();
        const auto& Data=GetNaniteVisualizationData();
        if (Mode&&(Data.GetActiveModeName()!=FName(Modes[Mode])||!Data.IsActive()))
        { Fail(TEXT("Engine did not activate the requested Nanite visualization")); return; }
        if (!Mode&&Data.IsActive()) { Fail(TEXT("Normal comparison still has Nanite visualization active")); return; }
        const FVector At=PC()->PlayerCameraManager->GetCameraLocation();
        const FRotator Rot=PC()->PlayerCameraManager->GetCameraRotation();
        if (!At.Equals(Locations[Cam],.01)||!Rot.Equals(Rotations[Cam],.001)||PC()->GetViewTarget()!=Camera.Get())
        { Fail(TEXT("Actual camera differs from the fixed production-dojo view")); return; }
        const FString Name=FString(Cameras[Cam])+TEXT("-")+Modes[Mode];
        auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("name"),Name); O->SetStringField(TEXT("mode"),Modes[Mode]);
        O->SetStringField(TEXT("camera_id"),Cameras[Cam]); O->SetArrayField(TEXT("camera"),Vec(At));
        O->SetArrayField(TEXT("rotation"),Vec(FVector(Rot.Pitch,Rot.Yaw,Rot.Roll)));
        O->SetNumberField(TEXT("fov"),PC()->PlayerCameraManager->GetFOVAngle());
        O->SetNumberField(TEXT("request_frame"),double(GFrameCounter)); O->SetNumberField(TEXT("settle_seconds"),FPlatformTime::Seconds()-ChangedAt);
        O->SetStringField(TEXT("active_visualization"),Data.GetActiveModeName().ToString());
        O->SetNumberField(TEXT("active_mode_id"),Data.GetActiveModeID());
        O->SetBoolField(TEXT("show_visualize_nanite"),Viewport()->EngineShowFlags.VisualizeNanite);
        O->SetObjectField(TEXT("cvars"),RenderState());
        O->SetBoolField(TEXT("paused"),M->GetWorld()->IsPaused()); O->SetBoolField(TEXT("hud_hidden"),!HUD.IsValid()||!HUD->bShowHUD);
        Frames.Add(MakeShared<FJsonValueObject>(O)); Pending=Folder/(Name+TEXT(".png")); Waiting=true;
        FScreenshotRequest::RequestScreenshot(Pending,false,false);
    }
    void Captured()
    {
        if (!Waiting) return;
        if (IFileManager::Get().FileSize(*Pending)<=0) { Fail(TEXT("Original Nanite diagnostic screenshot was not written")); return; }
        Frames.Last()->AsObject()->SetStringField(TEXT("file"),FPaths::GetCleanFilename(Pending));
        Frames.Last()->AsObject()->SetNumberField(TEXT("screenshot_processed_frame"),double(GFrameCounter));
        UE_LOG(LogTemp,Display,TEXT("SORA_NANITE_DRAW_FRAME %s"),*Pending);
        Waiting=false; Pending.Reset(); ++Step;
        if (Step<Count()) Switch();
    }
    void Cleanup()
    {
        if (Cleaned) return; Cleaned=true;
        if (Waiting) FScreenshotRequest::Reset();
        FScreenshotRequest::OnScreenshotRequestProcessed().Remove(Screenshot);
        bool Restored=true;
        for (const FCVar* V:{&Visualize,&Composite,&Edges,&Shading}) Restored=V->Restore()&&Restored;
        if (BackedUp&&!M.IsValid()) Restored=false;
        if (BackedUp&&M.IsValid())
        {
            if (ChangedWorld)
            {
                M->SetMenuOpen(true); M->SaveSlotName=Slots[0]; M->bCampaign=WasCampaign; M->bDeterministicPractice=WasPractice;
                Restored=M->Campaign()->LoadSave()&&Restored; M->ResetRound();
                if (OldScreen==SoraUI::EScreen::Title) M->FrontEnd()->ShowTitle(); else M->FrontEnd()->ShowMain();
            }
            if (PC()) PC()->SetViewTarget(OldTarget.IsValid()?OldTarget.Get():M->Hero());
            if (Camera.IsValid()) Camera->Destroy();
            if (HUD.IsValid()) HUD->bShowHUD=ShowHUD;
            if (Viewport())
            {
                Viewport()->SetViewMode(static_cast<EViewModeIndex>(OldViewMode));
                Viewport()->EngineShowFlags=OldFlags; Viewport()->SetCurrentNaniteVisualizationMode(OldNaniteMode);
            }
            UGameplayStatics::SetGamePaused(M.Get(),WasPaused);
            Restored=(M->SaveSlotName==Slots[0]&&M->bCampaign==WasCampaign&&M->bDeterministicPractice==WasPractice&&
                M->bMenu&&M->FrontEnd()->Screen()==OldScreen&&M->GetWorld()->IsPaused()==WasPaused&&
                (!HUD.IsValid()||HUD->bShowHUD==ShowHUD)&&Viewport()&&Viewport()->ViewModeIndex==OldViewMode&&
                Viewport()->GetCurrentNaniteVisualizationMode()==OldNaniteMode&&
                Viewport()->EngineShowFlags.VisualizeNanite==OldFlags.VisualizeNanite)&&Restored;
        }
        if (BackedUp)
        {
            // LoadSave/ResetRound may create a missing default save. Restore
            // raw bytes/existence AFTER that reconstruction, including failure.
            for (int32 I=0;I<3;++I)
            {
                if (Existed[I]) Restored=UGameplayStatics::SaveDataToSlot(Profile[I],Slots[I],0)&&Restored;
                else if (UGameplayStatics::DoesSaveGameExist(Slots[I],0)) Restored=UGameplayStatics::DeleteGameInSlot(Slots[I],0)&&Restored;
                TArray<uint8> After;
                Restored=(UGameplayStatics::DoesSaveGameExist(Slots[I],0)==Existed[I]&&
                    (!Existed[I]||(UGameplayStatics::LoadDataFromSlot(After,Slots[I],0)&&After==Profile[I])))&&Restored;
            }
        }
        if (!Slot.IsEmpty()&&UGameplayStatics::DoesSaveGameExist(Slot,0)) Restored=UGameplayStatics::DeleteGameInSlot(Slot,0)&&Restored;
        Test.TestTrue(TEXT("Nanite diagnostic restores original menu checkpoint, HUD, profile bytes/existence and temporary cvars"),Restored);
        if (!Folder.IsEmpty())
        {
            auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("schema"),TEXT("sora-arena.nanite-draw.v3"));
            O->SetStringField(TEXT("scope"),Scope); O->SetBoolField(TEXT("sm6_requested"),SM6);
            O->SetBoolField(TEXT("nanite_eligible"),NaniteEligible);
            O->SetStringField(TEXT("shader_platform"),ShaderPlatform); O->SetStringField(TEXT("rhi"),GDynamicRHI?GDynamicRHI->GetName():TEXT("none"));
            O->SetStringField(TEXT("adapter"),GRHIAdapterName); O->SetBoolField(TEXT("null_rhi"),GUsingNullRHI);
            O->SetArrayField(TEXT("viewport"),{MakeShared<FJsonValueNumber>(ViewportSize.X),MakeShared<FJsonValueNumber>(ViewportSize.Y)});
            O->SetArrayField(TEXT("asset_files"),AssetFiles); O->SetArrayField(TEXT("meshes"),Meshes); O->SetArrayField(TEXT("frames"),Frames); O->SetNumberField(TEXT("frame_count"),Frames.Num());
            O->SetArrayField(TEXT("derived_assets"),DerivedAssets);
            O->SetArrayField(TEXT("coverage_inputs"),CoverageInputs);
            O->SetStringField(TEXT("chapter_id"),ChapterId); O->SetArrayField(TEXT("chapter_estate_halls"),ChapterEstateHalls);
            auto CaptureScope=MakeShared<FJsonObject>();
            CaptureScope->SetStringField(TEXT("chapter_file"),TEXT("Content/Data/campaign/chapter_01.json"));
            CaptureScope->SetStringField(TEXT("zone"),TEXT("pl_tsumagizaka_dojo"));
            CaptureScope->SetArrayField(TEXT("rect"),{MakeShared<FJsonValueNumber>(8000),MakeShared<FJsonValueNumber>(-1300),
                MakeShared<FJsonValueNumber>(11600),MakeShared<FJsonValueNumber>(1300)});
            O->SetObjectField(TEXT("capture_scope"),CaptureScope);
            auto Coverage=MakeShared<FJsonObject>();
            Coverage->SetStringField(TEXT("status"),TEXT("requires_archive_source_binding"));
            Coverage->SetBoolField(TEXT("qualified"),false);
            O->SetObjectField(TEXT("timber_placement_coverage"),Coverage);
            O->SetBoolField(TEXT("restored"),Restored); O->SetBoolField(TEXT("passed"),!Failed&&!Test.HasAnyErrors()&&Step==Count());
            O->SetStringField(TEXT("acceptance"),TEXT("original pixel validation and human geometry attribution required; no GPU counters inferred"));
            FString Json; FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Json));
            Test.TestTrue(TEXT("Writes original Nanite draw observation report"),FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("capture.json"))));
        }
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNaniteDrawSM6Test,"SoraCapture.NaniteDraw.DojoSM6",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraNaniteDrawSM6Test::RunTest(const FString& Parameters)
{ (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraNaniteDrawCapture::FRun>(*this,true)); return true; }
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNaniteDrawSM5Test,"SoraCapture.NaniteDraw.DojoSM5",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraNaniteDrawSM5Test::RunTest(const FString& Parameters)
{ (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraNaniteDrawCapture::FRun>(*this,false)); return true; }
#endif
