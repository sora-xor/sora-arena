#include "HUD/SoraHUDPanels.h"
#include "ArenaKernelSubsystem.h"
#include "SoraCatalog.h"
#include "SoraCharacterBase.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPracticeActors.h"
#include "SoraPracticeDirector.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

// Deterministic practice: scores, the objective, the kill feed, markers over
// allies and seen enemies, the respawn and loadout choice while down, the
// spectator line, and the results with the match's zero-stake XOR ledger.
// Japanese leads every line; English follows while subtitles are on.
namespace
{
struct FPracticeView
{
    const FSoraHUDFrame& Frame;
    ASoraHUD& HUD;
    const ASoraGameMode& Mode;
    const UArenaKernelSubsystem& Kernel;
    const USoraPracticeDirector& Director;
    float W, H, S;
    bool bEnglish;
    bool bTeams;
};
const TCHAR* ModeName(int32 Mode,bool bEnglish)
{
    static const TCHAR* Japanese[]={TEXT("乱戦"),TEXT("陣取り"),TEXT("荷駄護送"),TEXT("剣戟")};
    static const TCHAR* English[]={TEXT("Free-for-all"),TEXT("Control"),TEXT("Payload"),TEXT("Melee")};
    const int32 Index=FMath::Clamp(Mode,0,3);
    return bEnglish?English[Index]:Japanese[Index];
}
FString Name(const FPracticeView& V,int32 Slot,bool bEnglish)
{
    if(Slot==0) return bEnglish?TEXT("You"):TEXT("あなた");
    if(!V.Kernel.PracticePlayers.IsValidIndex(Slot)) return TEXT("—");
    const FSoraClass& Class=FSoraCatalog::Get().Class(V.Kernel.PracticePlayers[Slot].ClassId);
    return FString::Printf(TEXT("%s %d"),bEnglish?*Class.NameEnglish:*Class.Name,Slot);
}
FString Clock(int32 Ticks)
{
    const int32 Seconds=FMath::Max(0,Ticks+59)/60;
    return FString::Printf(TEXT("%d:%02d"),Seconds/60,Seconds%60);
}
FLinearColor Faded(FLinearColor Color,float Alpha) { Color.A=Alpha; return Color; }
// Japanese, then its English smaller and muted beside it while subtitles are on.
float Pair(const FPracticeView& V,const FString& Japanese,const FString& English,float X,float Y,float Scale,FLinearColor Color)
{
    V.HUD.Label(Japanese,X,Y,Scale,Color);
    float Width=V.HUD.LabelWidth(Japanese,Scale);
    if(V.bEnglish&&!English.IsEmpty())
    {
        const float Small=Scale*.78f;
        V.HUD.Label(English,X+Width+12*V.S,Y+30*(Scale-Small),Small,Faded(V.Frame.Muted,Color.A));
        Width+=12*V.S+V.HUD.LabelWidth(English,Small);
    }
    return Width;
}
void Bar(const FPracticeView& V,float X,float Y,float Width,float Height,float Fraction,FLinearColor Color)
{
    V.HUD.Panel(X,Y,Width,Height,FLinearColor(.12f,.16f,.18f,.9f));
    V.HUD.Panel(X,Y,Width*FMath::Clamp(Fraction,0.f,1.f),Height,Color);
}
bool Ahead(const FPracticeView& V,const FVector& Location,FVector& Screen)
{
    const APlayerController* Controller=V.HUD.PlayerOwner;
    if(!Controller||!Controller->PlayerCameraManager) return false;
    const FVector Camera=Controller->PlayerCameraManager->GetCameraLocation();
    if(FVector::DotProduct(Location-Camera,Controller->PlayerCameraManager->GetCameraRotation().Vector())<=0.f) return false;
    Screen=V.HUD.Project(Location);
    return Screen.X>0&&Screen.X<V.W&&Screen.Y>80*V.S&&Screen.Y<V.H;
}
bool InSight(const FPracticeView& V,const FVector& Location)
{
    const APlayerController* Controller=V.HUD.PlayerOwner;
    const FVector Camera=Controller->PlayerCameraManager->GetCameraLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PracticeMarkerSight),false);
    for(int32 Slot=0;Slot<V.Director.ParticipantCount();++Slot) if(AActor* Pawn=V.Director.Participant(Slot)) Query.AddIgnoredActor(Pawn);
    FHitResult Hit;
    return !V.HUD.GetWorld()->LineTraceSingleByChannel(Hit,Camera,Location,ECC_Visibility,Query);
}

void DrawScores(const FPracticeView& V)
{
    const auto& O=V.Kernel.PracticeObjective;
    const float S=V.S, X=V.W-470*S, Y=87*S, Width=450*S;
    V.HUD.Panel(X,Y,Width,V.bTeams?78*S:120*S,FLinearColor(.013f,.027f,.033f,.82f));
    Pair(V,FString::Printf(TEXT("%s / %d 人"),ModeName(V.Director.Config.Mode,false),V.Director.Config.PlayerCount),
        FString::Printf(TEXT("%s, %d players"),ModeName(V.Director.Config.Mode,true),V.Director.Config.PlayerCount),X+14*S,Y+6*S,.44f*S,V.Frame.Gold);
    if(V.bTeams)
    {
        int32 Kills[2]={0,0};
        for(const FSoraPracticePlayer& P:V.Kernel.PracticePlayers) Kills[P.Team]+=P.Kills;
        for(int32 Team=0;Team<2;++Team)
        {
            const float RowY=Y+(30+Team*23)*S;
            V.HUD.Panel(X+14*S,RowY+4*S,10*S,16*S,SoraPracticeArt::TeamColor(Team));
            const FString Score=V.Director.Config.Mode==SoraPractice::Control
                ?FString::Printf(TEXT("%s / %s"),*Clock(O.Score[Team]),*Clock(O.ScoreTarget))
                :Team==0?FString::Printf(TEXT("%d%%"),FMath::RoundToInt(100.f*O.PayloadProgress/FMath::Max(1.f,O.PayloadLength))):FString(TEXT("—"));
            Pair(V,FString::Printf(TEXT("%s  %s  撃破 %d"),Team==0?TEXT("味方 SORA"):TEXT("敵 債権団"),*Score,Kills[Team]),
                Team==0?TEXT("Allies"):TEXT("Invaders"),X+32*S,RowY,.42f*S,Team==0?V.Frame.Ivory:V.Frame.Muted);
        }
        return;
    }
    // Free-for-all and Melee: the four leaders by kills, then fewest deaths.
    TArray<int32> Order;
    for(int32 Slot=0;Slot<V.Kernel.PracticePlayers.Num();++Slot) Order.Add(Slot);
    const auto& Players=V.Kernel.PracticePlayers;
    Order.Sort([&Players](int32 A,int32 B){ return Players[A].Kills!=Players[B].Kills?Players[A].Kills>Players[B].Kills:Players[A].Deaths!=Players[B].Deaths?Players[A].Deaths<Players[B].Deaths:A<B; });
    for(int32 Rank=0;Rank<FMath::Min(4,Order.Num());++Rank)
    {
        const int32 Slot=Order[Rank];
        const float RowY=Y+(30+Rank*21)*S;
        V.HUD.Panel(X+14*S,RowY+4*S,10*S,14*S,V.Director.ParticipantColor(Slot));
        V.HUD.Label(FString::Printf(TEXT("%d. %s   %d / %d"),Rank+1,*Name(V,Slot,false),Players[Slot].Kills,Players[Slot].Deaths),X+32*S,RowY,.4f*S,Slot==0?V.Frame.Gold:V.Frame.Ivory);
    }
}
void DrawObjectiveStatus(const FPracticeView& V)
{
    const auto& O=V.Kernel.PracticeObjective;
    const float S=V.S, Width=620*S, X=(V.W-Width)*.5f, Y=V.H-150*S;
    if(V.Director.Config.Mode==SoraPractice::Control)
    {
        V.HUD.Panel(X,Y,Width,62*S,FLinearColor(.013f,.027f,.033f,.82f));
        const bool bLocked=V.Kernel.PracticeTick<O.UnlockTick;
        if(bLocked)
            Pair(V,FString::Printf(TEXT("陣は %s 後に開く"),*Clock(O.UnlockTick-V.Kernel.PracticeTick)),TEXT("The point opens soon"),X+14*S,Y+6*S,.46f*S,V.Frame.Ivory);
        else
        {
            const TCHAR* Owner=O.ControlOwner==0?TEXT("味方が保持"):O.ControlOwner==1?TEXT("敵が保持"):TEXT("無主");
            const TCHAR* OwnerEnglish=O.ControlOwner==0?TEXT("Allies hold"):O.ControlOwner==1?TEXT("Invaders hold"):TEXT("Unclaimed");
            Pair(V,FString::Printf(TEXT("陣：%s  味方 %d  敵 %d%s%s"),Owner,O.ControlCount[0],O.ControlCount[1],O.Contested?TEXT("  争奪中"):TEXT(""),O.Overtime?TEXT("  延長戦"):TEXT("")),
                FString::Printf(TEXT("%s%s%s"),OwnerEnglish,O.Contested?TEXT(", contested"):TEXT(""),O.Overtime?TEXT(", overtime"):TEXT("")),X+14*S,Y+6*S,.46f*S,O.Contested?V.Frame.Gold:V.Frame.Ivory);
        }
        // Capture progress from the centre: left for the allies, right for the invaders.
        const float Mid=X+Width*.5f, Half=(Width-28*S)*.5f, BarY=Y+40*S;
        V.HUD.Panel(X+14*S,BarY,Width-28*S,10*S,FLinearColor(.12f,.16f,.18f,.9f));
        const float Fraction=FMath::Clamp(static_cast<float>(O.ControlProgress)/O.ControlCapture,-1.f,1.f);
        if(Fraction<0) V.HUD.Panel(Mid+Half*Fraction,BarY,-Half*Fraction,10*S,SoraPracticeArt::TeamColor(0));
        else V.HUD.Panel(Mid,BarY,Half*Fraction,10*S,SoraPracticeArt::TeamColor(1));
        V.HUD.Panel(Mid-1*S,BarY-3*S,2*S,16*S,V.Frame.Ivory);
    }
    else if(V.Director.Config.Mode==SoraPractice::Payload)
    {
        V.HUD.Panel(X,Y,Width,62*S,FLinearColor(.013f,.027f,.033f,.82f));
        const bool bRolling=O.PayloadRollbackDelay>0&&O.PayloadIdle>=O.PayloadRollbackDelay;
        const FString State=O.PayloadAttackers>0&&O.PayloadDefenders>0?TEXT("押し合い"):O.PayloadAttackers>0?FString::Printf(TEXT("前進中 %d 人"),O.PayloadAttackers):bRolling?TEXT("後退中"):TEXT("停止");
        const FString StateEnglish=O.PayloadAttackers>0&&O.PayloadDefenders>0?TEXT("contested"):O.PayloadAttackers>0?TEXT("advancing"):bRolling?TEXT("rolling back"):TEXT("halted");
        Pair(V,FString::Printf(TEXT("荷駄：%s  関所 %d / 3（あなたの隊が押す）"),*State,O.PayloadCheckpoints),FString::Printf(TEXT("Payload %s; your team escorts"),*StateEnglish),X+14*S,Y+6*S,.46f*S,bRolling?V.Frame.Gold:V.Frame.Ivory);
        const float BarX=X+14*S, BarW=Width-28*S, BarY=Y+40*S;
        Bar(V,BarX,BarY,BarW,10*S,O.PayloadProgress/FMath::Max(1.f,O.PayloadLength),SoraPracticeArt::TeamColor(0));
        for(int32 Index=0;Index<3;++Index)
        {
            const float At=BarX+BarW*V.Kernel.PracticeMap.Checkpoints[Index]/FMath::Max(1.f,V.Kernel.PracticeMap.RouteLength);
            V.HUD.Panel(At-2*S,BarY-4*S,4*S,18*S,Index<O.PayloadCheckpoints?V.Frame.Gold:V.Frame.Muted);
        }
    }
}
void DrawFeed(const FPracticeView& V)
{
    const float S=V.S, X=V.W-470*S;
    float Y=(V.bTeams?172:214)*S;
    const uint32 Now=V.Kernel.PracticeTick;
    for(const FSoraPracticeFeedEntry& Entry:V.Director.Feed())
    {
        // Lines stay six seconds, then fade over two.
        const int32 Age=static_cast<int32>(Now-Entry.Tick);
        if(Age>8*60) continue;
        const float Alpha=FMath::Clamp(1.f-(Age-6*60)/120.f,0.f,1.f);
        FString Japanese,English; FLinearColor Color=Faded(V.Frame.Ivory,Alpha);
        const auto Side=[](int32 Team,bool bEnglish){ return Team==0?(bEnglish?TEXT("Allies"):TEXT("味方")):(bEnglish?TEXT("Invaders"):TEXT("敵")); };
        switch(Entry.Kind)
        {
        case FSoraPracticeFeedEntry::Kill:
        {
            const FSoraWeapon& Weapon=FSoraCatalog::Get().Weapon(FMath::Max(0,Entry.WeaponId));
            Japanese=FString::Printf(TEXT("%s ─%s→ %s"),*Name(V,Entry.Actor,false),Entry.WeaponId>=0?*Weapon.Name:TEXT(""),*Name(V,Entry.Target,false));
            English=FString::Printf(TEXT("%s > %s"),*Name(V,Entry.Actor,true),*Name(V,Entry.Target,true));
            if(Entry.Actor==0||Entry.Target==0) Color=Faded(V.Frame.Gold,Alpha);
            break;
        }
        case FSoraPracticeFeedEntry::Hazard:
            Japanese=FString::Printf(TEXT("%s は火と罠に倒れた"),*Name(V,Entry.Target,false)); English=FString::Printf(TEXT("%s fell to a hazard"),*Name(V,Entry.Target,true)); break;
        case FSoraPracticeFeedEntry::Fall:
            Japanese=FString::Printf(TEXT("%s 自滅"),*Name(V,Entry.Target,false)); English=FString::Printf(TEXT("%s fell"),*Name(V,Entry.Target,true)); break;
        case FSoraPracticeFeedEntry::Captured:
            Japanese=FString::Printf(TEXT("%sが陣を奪った"),Side(Entry.Detail,false)); English=FString::Printf(TEXT("%s took the point"),Side(Entry.Detail,true));
            Color=Faded(SoraPracticeArt::TeamColor(Entry.Detail),Alpha); break;
        case FSoraPracticeFeedEntry::Overtime:
            Japanese=TEXT("延長戦"); English=TEXT("Overtime"); Color=Faded(V.Frame.Gold,Alpha); break;
        case FSoraPracticeFeedEntry::Checkpoint:
            Japanese=FString::Printf(TEXT("荷駄が関所 %d を越えた"),Entry.Detail+1); English=FString::Printf(TEXT("Checkpoint %d reached"),Entry.Detail+1);
            Color=Faded(V.Frame.Gold,Alpha); break;
        case FSoraPracticeFeedEntry::Winner:
            Japanese=TEXT("決着"); English=TEXT("Decided"); Color=Faded(V.Frame.Gold,Alpha); break;
        }
        const float Width=V.HUD.LabelWidth(Japanese,.4f*S)+(V.bEnglish?V.HUD.LabelWidth(English,.31f*S)+12*S:0.f);
        V.HUD.Panel(X,Y,FMath::Min(450*S,Width+20*S),24*S,FLinearColor(.013f,.027f,.033f,.7f*Alpha));
        Pair(V,Japanese,English,X+10*S,Y+2*S,.4f*S,Color);
        Y+=26*S;
    }
}
void DrawMarkers(const FPracticeView& V)
{
    const float S=V.S;
    const APlayerController* Controller=V.HUD.PlayerOwner;
    if(!Controller||!Controller->PlayerCameraManager) return;
    const FVector Camera=Controller->PlayerCameraManager->GetCameraLocation();
    const float Head=V.Kernel.PracticeMap.EyeHeight+55.f;
    for(int32 Slot=1;Slot<V.Kernel.PracticePlayers.Num();++Slot)
    {
        const FSoraPracticePlayer& P=V.Kernel.PracticePlayers[Slot];
        if(!P.Alive||(V.Director.IsSpectating()&&V.Director.SpectatedSlot()==Slot)) continue;
        const FVector Top=V.Director.PresentedFeet(Slot)+FVector(0,0,Head);
        FVector Screen;
        if(!Ahead(V,Top,Screen)) continue;
        const bool bAlly=V.bTeams&&P.Team==0;
        // Allies show through walls; enemies only in plain sight and range.
        if(!bAlly&&(FVector::Dist(Camera,Top)>3500.f||!InSight(V,Top-FVector(0,0,70)))) continue;
        const FLinearColor Color=V.Director.ParticipantColor(Slot);
        if(bAlly)
        {
            V.HUD.DrawLine(Screen.X-7*S,Screen.Y-8*S,Screen.X,Screen.Y,Color,2.f);
            V.HUD.DrawLine(Screen.X,Screen.Y,Screen.X+7*S,Screen.Y-8*S,Color,2.f);
            V.HUD.Label(Name(V,Slot,false),Screen.X-30*S,Screen.Y-30*S,.32f*S,V.Frame.Ivory);
        }
        Bar(V,Screen.X-30*S,Screen.Y+4*S,60*S,5*S,static_cast<float>(P.Health)/FMath::Max(1,P.MaxHealth),Color);
        if(P.MarkedTicks>0) V.HUD.Label(TEXT("標"),Screen.X+34*S,Screen.Y-8*S,.5f*S,FLinearColor(1.f,.15f,.1f));
    }
    // Barricades and decoys that can be struck show their health up close.
    for(const auto& Item:V.Director.EntityActors())
    {
        const ASoraPracticeEntityActor* Actor=Item.Value.Get();
        if(!Actor) continue;
        const FSoraPracticeEntity& E=Actor->State();
        if(E.MaxHealth<=0) continue;
        const FVector Top=E.Position+FVector(0,0,E.Kind==SoraPractice::Barricade?E.Extent.Z+25.f:Head);
        FVector Screen;
        if(FVector::Dist(Camera,Top)>2200.f||!Ahead(V,Top,Screen)) continue;
        Bar(V,Screen.X-26*S,Screen.Y,52*S,4*S,static_cast<float>(E.Health)/E.MaxHealth,V.Director.ParticipantColor(E.Owner));
    }
}
void DrawRespawn(const FPracticeView& V,const FSoraPracticePlayer& Me)
{
    const float S=V.S, Width=FMath::Min(V.W-40*S,860*S), X=(V.W-Width)*.5f, Y=V.H*.24f;
    V.HUD.Panel(X,Y,Width,(V.bEnglish?360:330)*S,FLinearColor(.013f,.027f,.033f,.9f));
    Pair(V,FString::Printf(TEXT("倒れた ― 復帰まで %.1f 秒"),Me.RespawnTicks/60.f),FString::Printf(TEXT("Down: back in %.1f s"),Me.RespawnTicks/60.f),X+24*S,Y+14*S,.72f*S,V.Frame.Gold);
    float RowY=Y+62*S;
    // The class to return as: Q and E (pad LB and Y) turn through them.
    Pair(V,TEXT("流儀  Q ◀ ▶ E"),TEXT("Class: Q / E"),X+24*S,RowY,.42f*S,V.Frame.Muted);
    RowY+=28*S;
    const float Cell=(Width-48*S)/SoraPractice::ClassCount;
    for(int32 Class=0;Class<SoraPractice::ClassCount;++Class)
    {
        const bool bChosen=Class==V.Director.DesiredClass();
        const float CellX=X+24*S+Class*Cell;
        V.HUD.Panel(CellX,RowY,Cell-6*S,(V.bEnglish?50:34)*S,bChosen?FLinearColor(.08f,.25f,.26f,.95f):FLinearColor(.07f,.095f,.11f,.9f));
        V.HUD.Label(FSoraCatalog::Get().Class(Class).Name,CellX+8*S,RowY+4*S,.46f*S,bChosen?V.Frame.Teal:V.Frame.Ivory);
        if(V.bEnglish) V.HUD.Label(FSoraCatalog::Get().Class(Class).NameEnglish,CellX+8*S,RowY+28*S,.3f*S,V.Frame.Muted);
    }
    RowY+=(V.bEnglish?62:46)*S;
    Pair(V,TEXT("武器  1・2・3"),TEXT("Weapon: 1 / 2 / 3"),X+24*S,RowY,.42f*S,V.Frame.Muted);
    RowY+=28*S;
    const float Slot=(Width-48*S)/3;
    for(int32 Index=0;Index<3;++Index)
    {
        const int32 Weapon=USoraPracticeDirector::LoadoutWeapon(V.Director.DesiredClass(),Index);
        const bool bAllowed=V.Director.CanSelectLoadout(V.Director.DesiredClass(),Index);
        const bool bChosen=Index==V.Director.DesiredLoadout();
        const float CellX=X+24*S+Index*Slot;
        V.HUD.Panel(CellX,RowY,Slot-6*S,(V.bEnglish?50:34)*S,bChosen&&bAllowed?FLinearColor(.08f,.25f,.26f,.95f):FLinearColor(.07f,.095f,.11f,bAllowed?.9f:.5f));
        const FSoraWeapon& Info=FSoraCatalog::Get().Weapon(Weapon);
        const FLinearColor Color=!bAllowed?Faded(V.Frame.Muted,.55f):bChosen?V.Frame.Teal:V.Frame.Ivory;
        V.HUD.Label(FString::Printf(TEXT("%d  %s"),Index+1,*Info.Name),CellX+8*S,RowY+4*S,.44f*S,Color);
        if(V.bEnglish) V.HUD.Label(bAllowed?Info.NameEnglish:(Index==2?TEXT("special not admitted"):TEXT("blades only")),CellX+8*S,RowY+28*S,.3f*S,Faded(V.Frame.Muted,bAllowed?1.f:.6f));
    }
    RowY+=(V.bEnglish?62:46)*S;
    const bool bPending=Me.PendingClass!=INDEX_NONE;
    const int32 NextClass=bPending?Me.PendingClass:Me.ClassId, NextWeapon=bPending?Me.PendingWeapon:Me.WeaponId;
    Pair(V,FString::Printf(TEXT("次の復帰：%s / %s%s"),*FSoraCatalog::Get().Class(NextClass).Name,*FSoraCatalog::Get().Weapon(NextWeapon).Name,bPending?TEXT("（カーネルが受理）"):TEXT("")),
        FString::Printf(TEXT("Next life: %s, %s"),*FSoraCatalog::Get().Class(NextClass).NameEnglish,*FSoraCatalog::Get().Weapon(NextWeapon).NameEnglish),X+24*S,RowY,.44f*S,V.Frame.Ivory);
    RowY+=30*S;
    if(V.Director.IsSpectating()&&V.Director.SpectatedSlot()!=INDEX_NONE)
        Pair(V,FString::Printf(TEXT("観戦中：%s   左クリック・Ctrl で切替"),*Name(V,V.Director.SpectatedSlot(),false)),
            FString::Printf(TEXT("Watching %s; Fire / Block to switch"),*Name(V,V.Director.SpectatedSlot(),true)),X+24*S,RowY,.4f*S,V.Frame.Muted);
    RowY+=28*S;
    Pair(V,TEXT("無入金の稽古：倒れても XOR は動きません。"),TEXT("Zero-stake practice: no XOR moves when you fall."),X+24*S,RowY,.38f*S,V.Frame.Teal);
}
void DrawResults(const FPracticeView& V,const FSoraPracticeResults& R)
{
    const float S=V.S, X=80*S, Width=V.W-160*S;
    V.HUD.Panel(0,75*S,V.W,V.H-75*S,FLinearColor(.01f,.02f,.026f,.97f));
    float Y=100*S;
    FString Title,TitleEnglish; FLinearColor TitleColor=V.Frame.Teal;
    if(R.WinnerKind==SoraPractice::WinnerTeam)
    {
        Title=R.WinnerValue==0?TEXT("勝利 ― SORA 抵抗軍"):TEXT("敗北 ― 異星の債権団の勝ち");
        TitleEnglish=R.WinnerValue==0?TEXT("Victory for the SORA resistance"):TEXT("Defeat: the banker invaders win");
        TitleColor=SoraPracticeArt::TeamColor(R.WinnerValue);
    }
    else if(R.WinnerKind==SoraPractice::WinnerSlot)
    {
        Title=R.WinnerValue==0?TEXT("勝利 ― 最多撃破"):FString::Printf(TEXT("%s の勝ち"),*Name(V,R.WinnerValue,false));
        TitleEnglish=R.WinnerValue==0?TEXT("Victory: most kills"):FString::Printf(TEXT("%s wins"),*Name(V,R.WinnerValue,true));
        TitleColor=R.WinnerValue==0?V.Frame.Gold:V.Director.ParticipantColor(R.WinnerValue);
    }
    else { Title=TEXT("引き分け"); TitleEnglish=TEXT("Draw"); TitleColor=V.Frame.Ivory; }
    V.HUD.Label(Title,X,Y,1.3f*S,TitleColor);
    if(V.bEnglish) V.HUD.Label(TitleEnglish,X,Y+64*S,.56f*S,V.Frame.Muted);
    Y+=(V.bEnglish?104:74)*S;
    FString Summary,SummaryEnglish;
    switch(R.Mode)
    {
    case SoraPractice::Control:
        Summary=FString::Printf(TEXT("陣の保持：味方 %s ／ 敵 %s（目標 %s）"),*Clock(R.Score[0]),*Clock(R.Score[1]),*Clock(R.ScoreTarget));
        SummaryEnglish=FString::Printf(TEXT("Point held: allies %s, invaders %s (target %s)"),*Clock(R.Score[0]),*Clock(R.Score[1]),*Clock(R.ScoreTarget));
        break;
    case SoraPractice::Payload:
        Summary=FString::Printf(TEXT("荷駄 %d%%・関所 %d / 3"),FMath::RoundToInt(100.f*R.PayloadProgress/FMath::Max(1.f,R.PayloadLength)),R.Checkpoints);
        SummaryEnglish=FString::Printf(TEXT("Payload %d%% of the route, %d of 3 checkpoints"),FMath::RoundToInt(100.f*R.PayloadProgress/FMath::Max(1.f,R.PayloadLength)),R.Checkpoints);
        break;
    default:
        Summary=TEXT("最多撃破が勝ち、同数なら戦死の少ない方"); SummaryEnglish=TEXT("Most kills wins; fewest deaths breaks a tie");
        break;
    }
    Pair(V,FString::Printf(TEXT("%s ／ %s ／ %s"),ModeName(R.Mode,false),*Clock(static_cast<int32>(R.Tick)),*Summary),FString::Printf(TEXT("%s, %s. %s"),ModeName(R.Mode,true),*Clock(static_cast<int32>(R.Tick)),*SummaryEnglish),X,Y,.5f*S,V.Frame.Ivory);
    Y+=46*S;
    // The table: every participant with the kernel's own bond figures.
    static const TCHAR* Headers[]={TEXT("参加者"),TEXT("陣営"),TEXT("流儀"),TEXT("撃破"),TEXT("戦死"),TEXT("入金"),TEXT("残高"),TEXT("獲得")};
    static const TCHAR* HeadersEnglish[]={TEXT("Participant"),TEXT("Side"),TEXT("Class"),TEXT("Kills"),TEXT("Deaths"),TEXT("Bond"),TEXT("Reserve"),TEXT("Earned")};
    static const float Columns[]={0.f,.2f,.34f,.5f,.58f,.66f,.78f,.9f};
    for(int32 Column=0;Column<8;++Column)
    {
        V.HUD.Label(Headers[Column],X+Width*Columns[Column],Y,.4f*S,V.Frame.Gold);
        if(V.bEnglish) V.HUD.Label(HeadersEnglish[Column],X+Width*Columns[Column],Y+22*S,.28f*S,V.Frame.Muted);
    }
    Y+=(V.bEnglish?44:28)*S;
    TArray<int32> Order;
    for(int32 Slot=0;Slot<R.Players.Num();++Slot) Order.Add(Slot);
    const bool bTeams=V.bTeams;
    Order.Sort([&R,bTeams](int32 A,int32 B)
    {
        const FSoraPracticePlayer& P=R.Players[A]; const FSoraPracticePlayer& Q=R.Players[B];
        if(bTeams&&P.Team!=Q.Team) return P.Team<Q.Team;
        return P.Kills!=Q.Kills?P.Kills>Q.Kills:P.Deaths!=Q.Deaths?P.Deaths<Q.Deaths:A<B;
    });
    const float Row=FMath::Min(30.f,(V.H-Y-230*S)/FMath::Max(1,Order.Num())/S)*S;
    for(const int32 Slot:Order)
    {
        const FSoraPracticePlayer& P=R.Players[Slot];
        if(Slot==0) V.HUD.Panel(X-8*S,Y-2*S,Width+16*S,Row,FLinearColor(.08f,.25f,.26f,.5f));
        V.HUD.Panel(X,Y+5*S,8*S,Row-12*S,V.Director.ParticipantColor(Slot));
        const FLinearColor Color=Slot==0?V.Frame.Gold:V.Frame.Ivory;
        const float Scale=FMath::Min(.42f,Row/S/60.f)*S;
        V.HUD.Label(Name(V,Slot,false),X+Width*Columns[0]+16*S,Y,Scale,Color);
        V.HUD.Label(bTeams?(P.Team==0?TEXT("SORA 抵抗軍"):TEXT("債権団")):(Slot==0?TEXT("SORA"):TEXT("単騎")),X+Width*Columns[1],Y,Scale,Color);
        V.HUD.Label(FSoraCatalog::Get().Class(P.ClassId).Name,X+Width*Columns[2],Y,Scale,Color);
        V.HUD.Label(FString::FromInt(P.Kills),X+Width*Columns[3],Y,Scale,Color);
        V.HUD.Label(FString::FromInt(P.Deaths),X+Width*Columns[4],Y,Scale,Color);
        V.HUD.Label(FString::Printf(TEXT("%llu XOR"),P.InitialBond),X+Width*Columns[5],Y,Scale,Color);
        V.HUD.Label(FString::Printf(TEXT("%llu XOR"),P.RemainingBond),X+Width*Columns[6],Y,Scale,Color);
        V.HUD.Label(FString::Printf(TEXT("%llu XOR"),P.Earnings),X+Width*Columns[7],Y,Scale,Color);
        Y+=Row;
    }
    // The ledger: what the kernel reports, and what practice means for XOR.
    Y+=10*S;
    V.HUD.Panel(X-8*S,Y,Width+16*S,(V.bEnglish?150:106)*S,FLinearColor(.02f,.05f,.06f,.95f));
    Pair(V,TEXT("XOR 精算 ― 無入金の稽古"),TEXT("XOR settlement: zero-stake practice"),X,Y+8*S,.5f*S,V.Frame.Gold);
    Pair(V,FString::Printf(TEXT("入金合計 %llu XOR ＝ 残高 %llu XOR ＋ 獲得 %llu XOR  %s"),R.Deposited,R.Remaining,R.Earnings,R.bConserved?TEXT("保存則を確認"):TEXT("保存則の検証に失敗")),
        FString::Printf(TEXT("Deposited %llu = reserves %llu + earnings %llu: %s"),R.Deposited,R.Remaining,R.Earnings,R.bConserved?TEXT("conserved"):TEXT("CONSERVATION FAILED")),
        X,Y+42*S,.42f*S,R.bConserved?V.Frame.Teal:FLinearColor(1.f,.2f,.15f));
    V.HUD.Label(TEXT("死亡ごとに倒れた者の初期入金の 10% が移る決まりだが、入金 0 のため何も移っていない。台帳には何も書き込まない。"),X,Y+72*S,.36f*S,V.Frame.Ivory);
    if(V.bEnglish) V.HUD.Label(TEXT("Each death moves 10% of the victim's initial bond; with zero bonds nothing moved, and nothing is written to any ledger."),X,Y+100*S,.32f*S,V.Frame.Muted);
    Pair(V,TEXT("ENTER もう一度   ESC メニュー"),TEXT("Enter: play again   Esc: menu"),X,V.H-50*S,.5f*S,V.Frame.Ivory);
}
}

void SoraHUDPanels::DrawPractice(const FSoraHUDFrame& Frame)
{
    const ASoraGameMode& Mode=Frame.Mode;
    const UArenaKernelSubsystem* Kernel=Mode.Kernel();
    const USoraPracticeDirector* Director=Mode.Practice();
    if(!Mode.bDeterministicPractice||!Kernel||!Director||!Kernel->PracticeActive()||Kernel->PracticePlayers.IsEmpty()) return;
    const FPracticeView V{Frame,Frame.HUD,Mode,*Kernel,*Director,Frame.W,Frame.H,Frame.S,Mode.bEnglishSubtitles,SoraPractice::IsTeamMode(Director->Config.Mode)};
    if(Kernel->PracticeTerminal&&Director->Results().bValid) { DrawResults(V,Director->Results()); return; }
    DrawMarkers(V);
    DrawScores(V);
    DrawObjectiveStatus(V);
    DrawFeed(V);
    const FSoraPracticePlayer& Me=Kernel->PracticePlayers[0];
    if(!Me.Alive) DrawRespawn(V,Me);
}
