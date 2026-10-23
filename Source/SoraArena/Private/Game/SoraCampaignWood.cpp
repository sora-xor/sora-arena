#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCampaignRules.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraProjectile.h"
#include "SoraSaveGame.h"
#include "SoraWoodRules.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
const TCHAR* WoodIds[]={TEXT("poi_ch01_issoseki"),TEXT("poi_ch01_vista"),TEXT("poi_ch01_sakaiishi"),TEXT("poi_ch01_hokora")};
bool AtWoodFloor(const ASoraPlayerCharacter& Hero,const FVector2D& At,double Radius)
{
    const double Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    return Hero.GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(Feet)<=SoraWoodRules::FloorToleranceCm&&
        FVector::Dist2D(Hero.GetActorLocation(),FVector(At,0))<=Radius;
}
}
int32 USoraCampaignDirector::WoodPoiMask() const { return Save?Save->WoodPoiMask:0; }
bool USoraCampaignDirector::HasToshiyaCodex() const { return (WoodPoiMask()&SoraWoodRules::Bit(SoraWoodRules::Toshiya))!=0; }
bool USoraCampaignDirector::IsWoodExplore() const
{
    const auto* Chapter=ActiveChapter();
    return Mode().bCampaign&&Chapter&&Chapter->Wood.Enabled()&&BeatIndex==Chapter->Wood.Beat&&!bWoodTransit;
}
FString USoraCampaignDirector::ToshiyaCodex(bool English) const
{
    if(!HasToshiyaCodex()) return FString();
    // Provisional editorial copy: no invented named record or combat bonus.
    return English?TEXT("Toshiya — provisional codex draft. Long-distance archery contests were held in Japan in the early 1600s. Archers practiced sustaining accuracy over many shots."):
        TEXT("通し矢 — 図鑑仮稿。十七世紀初めの日本では、遠くへ矢を通す競技が行われた。射手は繰り返し射ながら正確さを保つ技を磨いた。");
}
bool USoraCampaignDirector::BeginWoodTransit()
{
    const auto* Chapter=ActiveChapter();
    if(!Chapter||!Chapter->Wood.Enabled()||
        (BeatIndex!=Chapter->Wood.Beat-1&&BeatIndex!=Chapter->Wood.Beat)) return false;
    ClearArchery(); WoodShots.Reset();
    bWoodTransit=true;
    // The wood exit saves the next required checkpoint, without moving the
    // live hero. Walking the final bridge still belongs to this world.
    Save->WoodJunction=BeatIndex==Chapter->Wood.Beat-1;
    SaveCheckpoint(Chapter->Wood.Beat+1);
    Notify(TEXT("林を散策するか、南の道から鍛冶場へ進む。"),
        TEXT("Explore the wood, or follow the south terrace to the smithy."),10.f);
    if(auto* Arena=Mode().Arena()) Arena->ShowObjective(nullptr);
    return true;
}
bool USoraCampaignDirector::ResumeWoodJunction()
{
    const auto* Chapter=ActiveChapter(); auto* Hero=Mode().Hero();
    if(!Save||!Save->WoodJunction||!Chapter||!Chapter->Wood.Enabled()||!Hero) return false;
    BeatIndex=Chapter->Wood.Beat-1; BeatPhase=0;
    Task=Chapter->Beats[BeatIndex].Task; TaskState=SoraBeatRules::StartTask(Task,0);
    bWoodTransit=true;
    // Checkpoint restoration has an explicit junction spawn. Live traversal
    // never uses this repositioning and does not start the smithy early.
    Hero->SetActorLocation(FVector(Chapter->Wood.Approach[1],120),false,nullptr,ETeleportType::TeleportPhysics);
    RestoreDojoQuiver();
    Notify(TEXT("林を散策するか、南の道から鍛冶場へ進む。"),TEXT("Explore the wood, or follow the south terrace to the smithy."),10.f);
    UpdateObjective();
    Telemetry(TEXT("resume_junction"));
    return true;
}
bool USoraCampaignDirector::AtWoodExit() const
{
    const auto* Hero=Mode().Hero(); const auto* Space=ActiveSpace();
    return IsWoodExplore()&&Hero&&Space&&Space->Exit.Contains(Hero->GetActorLocation())&&
        AtWoodFloor(*Hero,Space->Exit.Center,300);
}
bool USoraCampaignDirector::TickWoodTransit()
{
    if(!bWoodTransit) return false;
    const auto* Chapter=ActiveChapter(); auto* Hero=Mode().Hero();
    if(!Chapter||!Hero||!Mode().IsPlaying()) return true;
    const auto& W=Chapter->Wood;
    int32 Next=INDEX_NONE;
    if(SoraBeatRules::CanStartBeat(BeatState,Chapter->Rules.GetData(),Chapter->Rules.Num(),W.Beat)&&
        AtWoodFloor(*Hero,W.Entry,120)) Next=W.Beat;
    else if(AtWoodFloor(*Hero,W.Arrival,230)) Next=W.Beat+1;
    if(Next!=INDEX_NONE)
    {
        bWoodTransit=false; Save->WoodJunction=false;
        LeaveBeatSpace();
        BeginBeat(Next,0,false);
    }
    return true;
}
bool USoraCampaignDirector::InteractWood(ASoraPlayerCharacter& Player)
{
    auto* Arena=Mode().Arena(); const auto* Chapter=ActiveChapter();
    if(!IsWoodExplore()||!Save||!Chapter||!Arena||!Mode().IsPlaying()||!Player.CanPlay()) return false;
    for(int32 Index=0;Index<4;++Index)
    {
        if(!Arena->CanReachWoodPoi(Index,Player)) continue;
        if(!SoraWoodRules::Record(Save->WoodPoiMask,Index)) return true;
        IdleMs=0;
        const FString Id=WoodIds[Index];
        const auto* Poi=Chapter->Beats[BeatIndex].Pois.FindByPredicate([&](const FSoraExplorePoi& P) { return P.Id==Id; });
        const auto* Item=Poi&&Chapter->Collectibles.IsValidIndex(Poi->Collectible)?&Chapter->Collectibles[Poi->Collectible]:nullptr;
        if(Item)
        {
            const auto Bit=SoraCampaignRules::CollectibleBit(ChapterId,Item->MaskBit);
            if((static_cast<uint64>(Save->Collectibles)&Bit)==0)
            {
                Save->Collectibles=static_cast<int64>(static_cast<uint64>(Save->Collectibles)|Bit);
                for(const auto& Category:FSoraCatalog::Get().CollectibleCategories)
                    if(Category.Id==Item->Category)
                        Tell(FSoraStoryNotice::EKind::Collectible,TEXT("見つけた：")+Category.Japanese,TEXT("Found: ")+Category.English,Item->Codex,Item->CodexEnglish);
                Fire(TEXT("collectible:")+Item->Id); Fire(TEXT("collectible_found:")+Item->Id);
            }
        }
        Fire(TEXT("interact:")+Id);
        if(Index==SoraWoodRules::Shrine)
            Notify(TEXT("小さな祠。林の静けさが続いている。"),TEXT("A small shrine stands in the quiet wood."),5.f);
        SaveProgress();
        return true;
    }
    return false;
}
void USoraCampaignDirector::RegisterWoodArrow(ASoraProjectile& Arrow)
{
    const auto* Chapter=ActiveChapter(); const auto* Hero=Mode().Hero();
    if(!IsWoodExplore()||HasToshiyaCodex()||!Chapter||!Hero||!Mode().IsPlaying()||!Hero->CanPlay()||
        Arrow.GetOwner()!=Hero||!Arrow.bArrow||Arrow.WeaponId!=18||NextWoodShot==MAX_uint64||
        !AtWoodFloor(*Hero,Chapter->Wood.Pois[SoraWoodRules::Vista],SoraWoodRules::ShotOriginRadiusCm)) return;
    Arrow.WoodShotId=++NextWoodShot;
    WoodShots.Add(Arrow.WoodShotId,&Arrow);
}
void USoraCampaignDirector::ResolveWoodArrow(ASoraProjectile& Arrow,const FHitResult* Hit)
{
    const uint64 Id=Arrow.WoodShotId; Arrow.WoodShotId=0;
    const auto* PendingShot=WoodShots.Find(Id);
    const bool Issued=PendingShot&&PendingShot->Get()==&Arrow;
    WoodShots.Remove(Id);
    const auto* Arena=Mode().Arena();
    if(!Issued||!IsWoodExplore()||!Save||!Arena||Arrow.GetOwner()!=Mode().Hero()||!Arrow.bArrow||Arrow.WeaponId!=18||
        !Hit||!Arena->IsWoodClapperHit(*Hit)||!SoraWoodRules::Record(Save->WoodPoiMask,SoraWoodRules::Toshiya)) return;
    Tell(FSoraStoryNotice::EKind::Collectible,TEXT("通し矢"),TEXT("Toshiya"),ToshiyaCodex(false),ToshiyaCodex(true));
    Fire(TEXT("challenge_complete:poi_ch01_naruko"));
    Fire(TEXT("codex_unlocked:codex_toshiya"));
    Telemetry(TEXT("codex_toshiya"));
    SaveProgress();
}
