#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "SoraFrontEnd.h"
#include "SoraWorldBuilder.h"
#include "SoraEquipmentComponent.h"
#include "SoraHistoricalArms.h"
#include "SoraViewmodelComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

bool USoraCampaignDirector::IsHelmHold() const
{
    return Mode().bCampaign&&ActiveSpace()&&ActiveSpace()->Helm.bEnabled;
}
void USoraCampaignDirector::ResetHelm()
{
    CancelHelm();
    Helm={};
    if(IsHelmHold()) Helm.DeadlineMs=ActiveSpace()->Helm.Contract.DeadlineMs[static_cast<int32>(SoraAccessibility::CampaignDifficulty(this))];
}
void USoraCampaignDirector::CancelHelm()
{
    const bool Working=Helm.Working;
    SoraHelmRules::Cancel(Helm);
    if(Working&&Mode().Hero()) Mode().Hero()->GetViewmodel()->SetHiddenInGame(CrankOccupiesHands(),true);
}
FVector USoraCampaignDirector::HelmWheelPoint() const
{
    return IsHelmHold()?FVector(ActiveSpace()->Helm.Wheel,ActiveSpace()->HeightCm):FVector::ZeroVector;
}
bool USoraCampaignDirector::InHelmFloor(const FVector& At) const
{
    return IsHelmHold()&&ActiveSpace()->Helm.Hold.Contains(At)&&FMath::Abs(At.Z-ActiveSpace()->HeightCm)<180.f;
}
bool USoraCampaignDirector::AtHelmWheel() const
{
    return IsHelmHold()&&Mode().Hero()&&Mode().Arena()&&Mode().Arena()->CanReachHelm(*Mode().Hero());
}
bool USoraCampaignDirector::InteractHelm(ASoraPlayerCharacter& Player)
{
    if(!HelmNeedsTrim()||!Mode().IsPlaying()||!Player.CanPlay()||!AtHelmWheel()) return false;
    auto* Kit=Player.GetEquipment();
    if(Kit->IsStaggered()||Kit->IsCommittedStrike()||Kit->IsStepping()||Kit->bReloading)
    {
        Notify(TEXT("動作を終えてから舵輪に手を添えよう。"),TEXT("Finish the current action before taking the wheel."),3.f);
        return true;
    }
    if(SoraHistoricalArms::IsMelee(Player.WeaponId)&&!Kit->IsSheathed())
    {
        const auto Key=SoraUI::ActionKey(this,TEXT("Sheathe"));
        Notify(FString::Printf(TEXT("まず %s で納刀し、武器を収めてから舵輪を操作しよう。"),*Key.Japanese),
            FString::Printf(TEXT("Use %s to stow the blade, then hold Interact at the wheel."),*Key.English),3.f);
        return true;
    }
    if(!Helm.Working)
    {
        Kit->Halt(); Kit->DropStance(); Player.StopSprint();
        Helm.Working=true; Helm.HeldMs=0;
        Player.GetViewmodel()->SetHiddenInGame(true,true);
        Fire(TEXT("interact_start:helm_trim_wheel"));
    }
    return true;
}
bool USoraCampaignDirector::TickHelm(SoraBeatRules::FTick Step)
{
    if(!IsHelmHold()) return false;
    auto* Hero=Mode().Hero();
    const unsigned Raised=Helm.Raised,Corrected=Helm.Corrected;
    const auto* Kit=Hero?Hero->GetEquipment():nullptr;
    const bool Held=Hero&&Hero->CanPlay()&&Hero->IsActionHeld(TEXT("Interact"))&&AtHelmWheel()&&
        !Kit->IsStaggered()&&!Kit->IsCommittedStrike()&&!Kit->IsStepping()&&!Kit->bReloading&&
        (!SoraHistoricalArms::IsMelee(Hero->WeaponId)||Kit->IsSheathed());
    if(!Held) CancelHelm();
    const bool WasWorking=Helm.Working;
    SoraHelmRules::Tick(Helm,ActiveSpace()->Helm.Contract,TaskState,Task,Step,Held);
    if(WasWorking&&!Helm.Working&&Hero) Hero->GetViewmodel()->SetHiddenInGame(CrankOccupiesHands(),true);
    if(Helm.Failed)
    {
        Fire(TEXT("timer_expired"));
        HandleFailure(SoraBeatRules::ERetry::Checkpoint,TEXT("helm_timer_expired"));
        Mode().Notice=TEXT("避難路に間に合わなかった。Enter で舵を守り直そう。");
        Mode().NoticeEnglish=TEXT("The ship reached the evacuation route. Press Enter to retry the helm.");
        return true;
    }
    if(Helm.Raised!=Raised)
    {
        Fire(TEXT("trim_event"));
        const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
        Notify(FString::Printf(TEXT("舵がずれた。舵輪で %s を 2 秒長押し。猶予 8 秒。"),*Key.Japanese),
            FString::Printf(TEXT("Heading off course. Hold %s at the wheel for 2 s. Grace: 8 s."),*Key.English),8.f);
        UpdateObjective();
    }
    if(Helm.Corrected!=Corrected)
    {
        Fire(TEXT("interact:helm_trim_wheel"));
        Notify(TEXT("針が中央に戻った。舵を守ろう。"),TEXT("Heading centered. Keep holding the helm."),3.f);
        UpdateObjective();
    }
    if(Mode().Arena()) Mode().Arena()->ShowHelm(HelmNeedsTrim(),Helm.Working?static_cast<float>(Helm.HeldMs)/ActiveSpace()->Helm.Contract.WorkMs:0.f);
    return true;
}
FString USoraCampaignDirector::HelmText(bool English) const
{
    const int32 Left=FMath::Max(0,FMath::DivideAndRoundUp(Helm.DeadlineMs-TaskState.ElapsedMs,1000));
    const FString Progress=English?FString::Printf(TEXT("Helm %d / 60 s | Time left %d s"),TaskState.Progress/1000,Left):
        FString::Printf(TEXT("舵を守る %d / 60 秒 | 残り %d 秒"),TaskState.Progress/1000,Left);
    if(!HelmNeedsTrim()) return Progress;
    const auto Key=SoraUI::ActionKey(this,TEXT("Interact"));
    const int32 Grace=FMath::DivideAndRoundUp(Helm.GraceMs,1000);
    return Progress+(English?FString::Printf(TEXT(" | Wheel: hold %s 2 s (%s)"),*Key.English,
        *(Grace>0?FString::Printf(TEXT("grace %d s"),Grace):FString(TEXT("progress falling")))):
        FString::Printf(TEXT(" | 舵輪：%s 長押し 2 秒（%s）"),*Key.Japanese,
        *(Grace>0?FString::Printf(TEXT("猶予 %d 秒"),Grace):FString(TEXT("進捗減少中")))));
}
