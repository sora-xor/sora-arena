#include "SoraCatalogArchery.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraArcheryRules.h"

bool SoraCatalogArchery::Read(const FJsonObject& Object,FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    using namespace SoraArcheryRules;
    const bool Lesson=Beat.Id==TEXT("ch01.b07"),Smithy=Beat.Id==TEXT("ch01.b09");
    if(!Lesson&&!Smithy) return true;
    const auto Ext=Child(Object,TEXT("ext"));
    const auto After=Ext?Child(*Ext,TEXT("quiver_after")):nullptr;
    int32 Value=0;
    if(!After||!Int(*After,TEXT("usable"),Value)||Value!=(Lesson?UsableAfter:Quiver)) return false;
    if(Smithy) return true;
    const auto Mato=Child(*Ext,TEXT("mato_rules")),Tsuri=Child(*Ext,TEXT("tsuri")),Shaho=Child(*Ext,TEXT("shaho"));
    const auto Radii=Mato?Child(*Mato,TEXT("hit_collider_radius_cm")):nullptr;
    const auto Params=Child(Object,TEXT("params"));
    FString Text;
    if(!Mato||!Tsuri||!Shaho||!Radii||!Params||
        !Str(*Params,TEXT("target_kind"),Text)||Text!=TEXT("mato")||
        !Int(*After,TEXT("bent"),Value)||Value!=BentAfter||
        !Int(*Mato,TEXT("distance_m"),Value)||Value*100!=NearCm||
        !Int(*Mato,TEXT("target_cm"),Value)||Value!=36||
        !Int(*Mato,TEXT("shots_per_set"),Value)||Value!=SetSize||
        !Int(*Mato,TEXT("hits_required"),Value)||Value!=RequiredHits||
        !Str(*Mato,TEXT("between_sets"),Text)||Text!=TEXT("yatori_arrow_fetch_8s")||
        !Str(*Mato,TEXT("ammo"),Text)||Text!=TEXT("own_quiver_12")) return false;
    const TCHAR* Keys[]={TEXT("easy"),TEXT("normal"),TEXT("hard")};
    for(int32 I=0;I<3;++I) if(!Int(*Radii,Keys[I],Value)||Value!=HitRadius[I]) return false;
    const auto Distances=Rows(*Tsuri,TEXT("distances_m"));
    if(!Distances||Distances->Num()!=3) return false;
    for(int32 I=0;I<3;++I)
    {
        double Distance=0;
        if(!(*Distances)[I]->TryGetNumber(Distance)||Distance!=HangingCm[I]/100) return false;
    }
    double Seconds=0;
    bool NoSprint=false;
    if(!Int(*Tsuri,TEXT("hits_each"),Value)||Value!=1||
        !Int(*Tsuri,TEXT("swing_amplitude_cm"),Value)||Value!=SwingCm||
        !Num(*Tsuri,TEXT("period_s"),Seconds)||Seconds!=PeriodMs/1000.0||
        !Int(*Tsuri,TEXT("target_cm"),Value)||Value!=45||
        !Int(*Shaho,TEXT("draw_ms"),Value)||Value!=DrawMs||
        !Num(*Shaho,TEXT("hold_sway_after_s"),Seconds)||Seconds!=4.0||
        !Shaho->TryGetBoolField(TEXT("no_fire_while_sprinting"),NoSprint)||!NoSprint||
        !Beat.bSparring||Beat.Task.Goal!=SoraBeatRules::EGoal::WavesCleared||Beat.Task.WaveCount!=2||
        Beat.Task.Waves[0].Trigger!=SoraBeatRules::EWaveTrigger::Start||
        Beat.Task.Waves[1].Trigger!=SoraBeatRules::EWaveTrigger::PrevCleared||
        Beat.Task.Waves[0].Lethal!=1||Beat.Task.Waves[1].Lethal!=3||
        Beat.Task.Waves[0].Nonlethal!=0||Beat.Task.Waves[1].Nonlethal!=0||
        Beat.Waves.Num()!=2||Beat.Waves[0].Groups.Num()!=1||Beat.Waves[1].Groups.Num()!=1||
        Beat.Waves[0].Groups[0].Type!=TEXT("mato_kinteki")||Beat.Waves[1].Groups[0].Type!=TEXT("mato_tsuri")) return false;
    Beat.bArcheryLesson=true;
    return true;
}
