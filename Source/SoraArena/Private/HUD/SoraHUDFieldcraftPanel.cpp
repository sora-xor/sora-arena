#include "HUD/SoraHUDPanels.h"
#include "SoraArmsRules.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraFieldcraft.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"

// The campaign's arms wheel and group keys (SoraArmsRules.h), and what the
// beat's fieldcraft (USoraFieldcraft) asks of the hero: the work his hand can
// do here and how far a held piece of it has come, his breath in the water
// and grip on the wall, the stones he carries, the candle, the signal his
// escorted party answers, the volley ranks' ring and loading (and Easy's
// auto-order), seizure nets and the time before a netted load is hauled off,
// a searchlight's spot on him, guttered cook-fires, a ladder in reach, the
// League's charge, and where the downed lie. Every line is Japanese
// with its English beside or beneath it while subtitles are on, and every
// key is the player's own on the device in hand.
namespace
{
SoraText::FLine Keyed(const ASoraHUD& HUD, const FText& Pattern, const TCHAR* Action)
{
    return SoraText::Format(Pattern, {{TEXT("Key"), SoraUI::ActionKey(&HUD, Action)}});
}

void Bar(ASoraHUD& HUD, float X, float Y, float Width, float S, float Fraction, const FLinearColor& Color)
{
    HUD.Panel(X, Y, Width, 4 * S, FLinearColor(.12f, .19f, .21f));
    HUD.Panel(X, Y, Width * FMath::Clamp(Fraction, 0.f, 1.f), 4 * S, Color);
}

SoraText::FLine ArmName(int32 WeaponId)
{
    const FSoraWeapon& Weapon = FSoraCatalog::Get().Weapon(WeaponId);
    return {Weapon.Name, Weapon.NameEnglish};
}
}

void SoraHUDPanels::DrawArmsWheel(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero)
{
    ASoraHUD& HUD = Frame.HUD;
    const ASoraGameMode& G = Frame.Mode;
    const float W = Frame.W, H = Frame.H, S = Frame.S;
    const bool bEnglish = G.bEnglishSubtitles;
    const ASoraPlayerCharacter::FArmsWheel& Wheel = Hero.ArmsWheel();
    if (!Wheel.bOpen)
    {
        DrawArmsNotice(Frame,Hero);
        return;
    }
    const float CX = W * .5f, CY = H * .5f, Radius = FMath::Min(300.f * S, H * .34f);
    HUD.Panel(0, 0, W, H, FLinearColor(0.f, 0.f, 0.f, .45f));
    const SoraText::FLine Title = Keyed(HUD, NSLOCTEXT("SoraArena.Arms", "WheelTitle", "武器の輪　視点を向けて選び、{Key} を離して持ち替える"), TEXT("ArmsWheel"));
    HUD.Label(Title.Japanese, CX - HUD.LabelWidth(Title.Japanese, .5f * S) * .5f, CY - Radius - 110 * S, .5f * S, Frame.Ivory);
    if (bEnglish) HUD.Label(Title.English, CX - HUD.LabelWidth(Title.English, .36f * S) * .5f, CY - Radius - 80 * S, .36f * S, Frame.Muted);
    const int32 Count = Wheel.Arms.Num();
    for (int32 Index = 0; Index < Count; ++Index)
    {
        const float Angle = 2.f * PI * Index / Count;
        const float X = CX + FMath::Sin(Angle) * Radius, Y = CY - FMath::Cos(Angle) * Radius;
        const bool bChoice = Index == Wheel.Choice, bHeld = Wheel.Arms[Index] == Hero.WeaponId;
        const SoraText::FLine Name = ArmName(Wheel.Arms[Index]);
        const float BoxW = 150 * S, BoxH = bEnglish ? 50 * S : 32 * S;
        HUD.Panel(X - BoxW * .5f, Y - BoxH * .5f, BoxW, BoxH,
            bChoice ? FLinearColor(.35f, .22f, .05f, .95f) : FLinearColor(.015f, .035f, .05f, .9f));
        if (bHeld) HUD.Panel(X - BoxW * .5f, Y + BoxH * .5f - 3 * S, BoxW, 3 * S, Frame.Teal);
        HUD.Label(Name.Japanese, X - HUD.LabelWidth(Name.Japanese, .42f * S) * .5f, Y - BoxH * .5f + 3 * S, .42f * S,
            bChoice ? Frame.Gold : Frame.Ivory);
        if (bEnglish) HUD.Label(Name.English, X - HUD.LabelWidth(Name.English, .3f * S) * .5f, Y - BoxH * .5f + 27 * S, .3f * S, Frame.Muted);
    }
    // The cursor's direction, and the arm under it named at the centre.
    const FVector2D Cursor = Wheel.Cursor.GetClampedToMaxSize(1.f);
    HUD.DrawLine(CX, CY, CX + Cursor.X * Radius * .55f, CY - Cursor.Y * Radius * .55f, Frame.Gold, 2.f);
    if (Wheel.Arms.IsValidIndex(Wheel.Choice))
    {
        const int32 Arm = Wheel.Arms[Wheel.Choice];
        const SoraText::FLine Group = SoraText::Line(SoraUI::ArmsGroupName(SoraArmsRules::GroupOf(Arm)));
        const SoraText::FLine Name = ArmName(Arm);
        HUD.Label(Group.Japanese, CX - HUD.LabelWidth(Group.Japanese, .42f * S) * .5f, CY - 52 * S, .42f * S, Frame.Teal);
        HUD.Label(Name.Japanese, CX - HUD.LabelWidth(Name.Japanese, .8f * S) * .5f, CY - 26 * S, .8f * S, Frame.Gold);
        if (bEnglish)
            HUD.Label(Group.English + TEXT(" / ") + Name.English,
                CX - HUD.LabelWidth(Group.English + TEXT(" / ") + Name.English, .36f * S) * .5f, CY + 20 * S, .36f * S, Frame.Muted);
    }
}

void SoraHUDPanels::DrawFieldcraft(const FSoraHUDFrame& Frame, const ASoraPlayerCharacter& Hero)
{
    ASoraHUD& HUD = Frame.HUD;
    const ASoraGameMode& G = Frame.Mode;
    const USoraFieldcraft* Fieldcraft = G.bCampaign && !G.bDeterministicPractice ? USoraFieldcraft::Get(&Hero) : nullptr;
    if (!Fieldcraft || Hero.ArmsWheel().bOpen) return;
    const float W = Frame.W, H = Frame.H, S = Frame.S;
    const float PromptX = W * .5f - 170 * S;
    struct FPromptRow { SoraText::FLine Line; FLinearColor Color; float Fraction=-1.f; };
    TArray<FPromptRow> Prompts;
    const auto Prompt = [&](const SoraText::FLine& Line, const FLinearColor& Color)
    {
        Prompts.Add({Line,Color,-1.f});
    };
    const auto DrawPrompts = [&]()
    {
        float Height=0;
        for(const FPromptRow& Row:Prompts) Height+=(Row.Fraction>=0.f?38:30)*S;
        float Y=FMath::Min(H*.5f+100*S,GameplayStoryTop(Frame)-6*S-Height);
        for(const FPromptRow& Row:Prompts)
        {
            Frame.LabelWithEnglish(Row.Line,PromptX,Y,.5f*S,Row.Color);
            if(Row.Fraction>=0.f) Bar(HUD,PromptX,Y+26*S,300*S,S,Row.Fraction,Frame.Gold);
            Y+=(Row.Fraction>=0.f?38:30)*S;
        }
    };
    // Work held at a point: a load hoisted on the well's 釣瓶 (it waits while a
    // guard watches), or an objective worked with Interact held.
    if (const USoraCampaignDirector* Campaign = G.Campaign(); Campaign && Campaign->HeldWorkProgress() >= 0.f)
    {
        const FText Pattern = Campaign->IsHeldWorkWatched() ? NSLOCTEXT("SoraArena.Fieldcraft", "HoistWatched", "見られている　{Key} を押さえたまま待て")
            : Campaign->IsRecoveringEquipment() ? NSLOCTEXT("SoraArena.Fieldcraft", "StringBow", "{Key} 長押し：弓に弦を張る")
            : Campaign->IsHoisting() ? NSLOCTEXT("SoraArena.Fieldcraft", "Hoist", "{Key} 長押し：釣瓶で引き上げる")
            : NSLOCTEXT("SoraArena.Fieldcraft", "HeldWork", "{Key} を押さえたまま仕事を続ける");
        Prompt(Keyed(HUD, Pattern, TEXT("Interact")), Campaign->IsHeldWorkWatched() ? FLinearColor(.95f, .35f, .2f) : Frame.Gold);
        Prompts.Last().Fraction=Campaign->HeldWorkProgress();
    }
    const FSoraFieldcraftReadout R = Fieldcraft->Readout(Hero);
    if (!R.bActive) { DrawPrompts(); return; }
    // What the hero's hand can do here, and how far a held piece of it has come.
    using EHold = FSoraFieldcraftReadout::EHold;
    const EHold Work = R.Holding != EHold::None ? R.Holding : R.HoldHere;
    if (Work != EHold::None)
    {
        const FText Pattern = Work == EHold::Snuff ? NSLOCTEXT("SoraArena.Fieldcraft", "Snuff", "{Key} 長押し：灯りを消す")
            : Work == EHold::Revive ? NSLOCTEXT("SoraArena.Fieldcraft", "Revive", "{Key} 長押し：助け起こす")
            : Work == EHold::Free ? NSLOCTEXT("SoraArena.Fieldcraft", "Free", "{Key} 長押し：首輪を断つ")
            : Work == EHold::NetCut ? NSLOCTEXT("SoraArena.Fieldcraft", "NetCut", "{Key} 長押し：網を切る")
            : Work == EHold::Relight ? NSLOCTEXT("SoraArena.Fieldcraft", "Relight", "{Key} 長押し：竈の火を点け直す")
            : NSLOCTEXT("SoraArena.Fieldcraft", "Release", "{Key} 長押し：牢の戸を開ける");
        Prompt(Keyed(HUD, Pattern, TEXT("Interact")), Frame.Gold);
        if (R.Holding != EHold::None)
        {
            Prompts.Last().Fraction=R.HoldProgress;
        }
    }
    if (R.bAtPile) Prompt(Keyed(HUD, NSLOCTEXT("SoraArena.Fieldcraft", "TakeStones", "{Key}：礫を拾う"), TEXT("Interact")), Frame.Gold);
    if (R.bAtFace) Prompt(Keyed(HUD, NSLOCTEXT("SoraArena.Fieldcraft", "StartClimb", "{Key}：手掛かりへ取り付く"), TEXT("Jump")), Frame.Gold);
    if (R.bAtLadder) Prompt(Keyed(HUD, NSLOCTEXT("SoraArena.Fieldcraft", "Ladder", "{Key}：梯子を使う"), TEXT("Jump")), Frame.Gold);
    DrawPrompts();
    // The left column above the health panel: breath, grip, stones, the candle, the signal.
    float Y = FMath::Min(H - 150 * S,GameplayStoryTop(Frame)-6*S);
    const float X = 30 * S;
    const auto Status = [&](const SoraText::FLine& Line, const FLinearColor& Color, float Fraction)
    {
        Y -= Fraction >= 0.f ? 38 * S : 30 * S;
        Frame.LabelWithEnglish(Line, X, Y, .42f * S, Color);
        if (Fraction >= 0.f) Bar(HUD, X, Y + 26 * S, 260 * S, S, Fraction, Fraction < .25f ? FLinearColor(.85f, .2f, .12f) : Frame.Teal);
    };
    if (R.bSwimming)
        Status(Keyed(HUD, R.bDiving ? NSLOCTEXT("SoraArena.Fieldcraft", "Diving", "潜水中　息　{Key} で浮かぶ")
            : NSLOCTEXT("SoraArena.Fieldcraft", "Swimming", "泳いでいる　息　{Key} で潜る"), TEXT("Crouch")), Frame.Ivory, R.Breath);
    if(R.bFloodPassage)
        Status(Keyed(HUD,R.bFloodAirShaft
            ?NSLOCTEXT("SoraArena.Fieldcraft","FloodAirShaft","頭上に空気　{Key} で浮かび、息を整えろ")
            :NSLOCTEXT("SoraArena.Fieldcraft","FloodDeepPassage","{Key} で潜れ　途中の明るい縦穴で息継ぎ"),TEXT("Crouch")),Frame.Teal,-1.f);
    if (R.bClimbing)
        Status(Keyed(HUD, R.bLedge ? NSLOCTEXT("SoraArena.Fieldcraft", "Ledge", "足場で握力が戻る　{Key} で手を離す")
            : NSLOCTEXT("SoraArena.Fieldcraft", "Climbing", "握力　前後で登り降り　{Key} で手を離す"), TEXT("Jump")), Frame.Ivory, R.Grip);
    if (R.bStones)
        Status(SoraText::Format(NSLOCTEXT("SoraArena.Fieldcraft", "Stones", "礫 {Count} / {Max}　{Key} で投げる"),
            {{TEXT("Count"), R.Stones}, {TEXT("Max"), R.StonesMax}, {TEXT("Key"), SoraUI::ActionKey(&HUD, TEXT("Ability"))}}), Frame.Ivory, -1.f);
    if (R.bCandle)
        Status(Keyed(HUD, R.bCupped ? NSLOCTEXT("SoraArena.Fieldcraft", "Cupped", "手燭を覆っている　写しは半速")
            : NSLOCTEXT("SoraArena.Fieldcraft", "Candle", "手燭が目立つ　{Key} 長押しで覆う"), TEXT("Block")), R.bCupped ? Frame.Teal : Frame.Gold, -1.f);
    if (R.bSignal)
        Status(Keyed(HUD, R.bPartyHidden ? NSLOCTEXT("SoraArena.Fieldcraft", "SignalGo", "仲間は伏せている　{Key}：進めの合図")
            : NSLOCTEXT("SoraArena.Fieldcraft", "SignalHide", "{Key}：伏せろの合図"), TEXT("Ability")), R.bPartyHidden ? Frame.Gold : Frame.Ivory, -1.f);
    // 輪番撃ち: each rank's loading, the front one marked, and the ring held.
    if (R.bVolley)
    {
        Status(Keyed(HUD, R.bMarking ? NSLOCTEXT("SoraArena.Fieldcraft", "VolleyMarking", "的を示している　{Key} を離して放て")
            : NSLOCTEXT("SoraArena.Fieldcraft", "Volley", "輪番撃ち　{Key} 長押し：的を示す"), TEXT("Ability")), Frame.Ivory, -1.f);
        // A pip for each rank above it: its letter and gunners standing, and its loading.
        static const TCHAR* const Letters[] = {TEXT("A"), TEXT("B"), TEXT("C"), TEXT("D")};
        Y -= 34 * S;
        for (int32 Rank = 0; Rank < R.Ranks; ++Rank)
        {
            const float PipX = X + Rank * 70 * S;
            HUD.Label(FString::Printf(TEXT("%s %d"), Letters[Rank], R.RankStanding[Rank]), PipX, Y, .36f * S,
                Rank == R.FrontRank ? Frame.Gold : Frame.Muted);
            Bar(HUD, PipX, Y + 22 * S, 58 * S, S, R.RankLoaded[Rank], R.RankLoaded[Rank] >= 1.f ? Frame.Gold : Frame.Teal);
        }
        if (R.bMarking && R.bMarkValid)
        {
            const FVector Eye = Hero.GetCamera()->GetComponentLocation();
            const FVector Forward = Hero.GetCamera()->GetForwardVector();
            constexpr int32 Segments = 36;
            for (int32 Segment = 0; Segment < Segments; ++Segment)
            {
                const auto Point = [&](int32 Index)
                {
                    const float Angle = 2.f * PI * Index / Segments;
                    return R.MarkAt + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * R.RingRadius + FVector(0.f, 0.f, 8.f);
                };
                const FVector A = Point(Segment), B = Point(Segment + 1);
                if (FVector::DotProduct(A - Eye, Forward) <= 10.f || FVector::DotProduct(B - Eye, Forward) <= 10.f) continue;
                const FVector SA = HUD.Project(A), SB = HUD.Project(B);
                HUD.DrawLine(SA.X, SA.Y, SB.X, SB.Y, Frame.Gold, 2.f * S);
            }
        }
    }
    // Seizure nets: how many are netted, and the time before the first is hauled off.
    if (R.NetsHeld > 0 || R.NetsLocking > 0)
        Status(SoraText::Format(NSLOCTEXT("SoraArena.Fieldcraft", "Nets", "差押網 {Held}　網を切るか、吊る目録を落とせ"),
            {{TEXT("Held"), R.NetsHeld}}), FLinearColor(.95f, .35f, .2f), R.NetsHeld > 0 ? R.HaulLeft : -1.f);
    // A searchlight's spot on him, filling toward the alarm.
    if (R.bInLight)
        Status(SoraText::Line(NSLOCTEXT("SoraArena.Fieldcraft", "InLight", "探照灯に照らされている　潜れ")), FLinearColor(.95f, .35f, .2f),
            1.f - R.LightExposure);
    if (R.FiresOut > 0)
        Status(Keyed(HUD, NSLOCTEXT("SoraArena.Fieldcraft", "FireOut", "竈の火が消えた　{Key} 長押しで点け直すまで炊き出しは止まる"), TEXT("Interact")),
            Frame.Gold, -1.f);
    if (R.bAutoOrder)
        Status(SoraText::Line(NSLOCTEXT("SoraArena.Fieldcraft", "AutoOrder", "自動号令：込め終えた組が一番近い敵へ放つ")), Frame.Muted, -1.f);
    if (R.Riders > 0)
        Status(SoraText::Format(NSLOCTEXT("SoraArena.Fieldcraft", "Charge", "騎馬 {Riders}　差押え杭 残り {Stakes}"),
            {{TEXT("Riders"), R.Riders}, {TEXT("Stakes"), R.StakesStanding}}), Frame.Ivory, -1.f);
    // Where the downed lie, so the hero can reach them in time.
    const SoraText::FLine Down = SoraText::Line(NSLOCTEXT("SoraArena.Fieldcraft", "Downed", "倒れている"));
    for (const FVector& At : R.Downed)
    {
        if (FVector::DotProduct(At - Hero.GetActorLocation(), Hero.GetActorForwardVector()) <= 0.f) continue;
        const FVector Screen = HUD.Project(At + FVector(0.f, 0.f, 120.f));
        if (Screen.X < 0 || Screen.X > W || Screen.Y < 170 * S || Screen.Y > H - 120 * S) continue;
        Frame.LabelWithEnglish(Down, Screen.X - 40 * S, Screen.Y, .42f * S, FLinearColor(.95f, .35f, .2f));
    }
}
