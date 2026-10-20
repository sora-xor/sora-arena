#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGalleryRules.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"

namespace
{
const FName GalleryIds[]={TEXT("poi_child_toy"),TEXT("poi_covered_mon")};
int32 GalleryIndex(FName Id)
{
    for(int32 Index=0;Index<SoraGalleryRules::Count;++Index) if(GalleryIds[Index]==Id) return Index;
    return INDEX_NONE;
}
}
int32 USoraCampaignDirector::GalleryPoiMask() const { return Save?Save->GalleryPoiMask:0; }
bool USoraCampaignDirector::HasGalleryPoi(FName Id) const
{
    return (GalleryPoiMask()&SoraGalleryRules::Bit(GalleryIndex(Id)))!=0;
}
void USoraCampaignDirector::TickGalleryPois()
{
    const auto* Hero=Mode().Hero();
    const auto* Arena=Mode().Arena();
    if(!bLiftGallery||!Hero||!Arena||!Mode().IsPlaying()) return;
    for(const FName Id:GalleryIds)
    {
        const FString Event=TEXT("gallery_hint:")+Id.ToString();
        if(HasGalleryPoi(Id)||BeatEvents.Contains(Event)||!Arena->CanReachGalleryPoi(Id,*Hero)) continue;
        const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
        const bool Toy=Id==GalleryIds[SoraGalleryRules::Toy];
        const FString Japanese=Toy?FString::Printf(TEXT("張子の玩具：%s で調べる。"),*Key.Japanese):
            FString::Printf(TEXT("陣羽織：%s で差押札を剥がす。"),*Key.Japanese);
        const FString English=Toy?FString::Printf(TEXT("Paper toy: %s to inspect."),*Key.English):
            FString::Printf(TEXT("Jinbaori: %s to tear off the seizure label."),*Key.English);
        Notify(Japanese,English,6.f);
        BeatEvents.Add(Event);
        return;
    }
}
bool USoraCampaignDirector::InteractGalleryPoi(ASoraPlayerCharacter& Player)
{
    const auto* Chapter=ActiveChapter();
    auto* Arena=Mode().Arena();
    if(!bLiftGallery||!Save||!Chapter||!Arena||!Mode().IsPlaying()||!Player.CanPlay()) return false;
    const int32 Gallery=Chapter->Beats.IndexOfByPredicate([](const FSoraBeat& B) { return B.Id==TEXT("ch08.b12"); });
    if(Gallery==INDEX_NONE) return false;
    for(int32 Index=0;Index<SoraGalleryRules::Count;++Index)
    {
        const FName Id=GalleryIds[Index];
        if(!Arena->CanReachGalleryPoi(Id,Player)) continue;
        // Repeated input at a discovered object is consumed without replay,
        // cache completion, ammunition or any other task side effect.
        if(!SoraGalleryRules::Record(Save->GalleryPoiMask,Index)) return true;
        IdleMs=0;
        Arena->ShowGalleryPois(Save->GalleryPoiMask);
        Fire(TEXT("event:")+Id.ToString(),Gallery);
        // Durable optional lore, not a new checkpoint at a partly travelled
        // lift. The next restore still starts b11 on its lower landing.
        SaveProgress();
        return true;
    }
    return false;
}
