#include "HUD/SoraHUDPanels.h"
#include "Combat/SoraStealth.h"
#include "SoraGameMode.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "Camera/CameraComponent.h"

namespace
{
using EState=SoraStealthRules::EState;
struct FStealthText { const TCHAR* Japanese; const TCHAR* English; };
FStealthText StateText(EState State)
{
    switch(State)
    {
    case EState::Unaware: return {TEXT("気付かれていない"),TEXT("UNSEEN")};
    case EState::Suspicious: return {TEXT("不審"),TEXT("SUSPICIOUS")};
    case EState::Search: return {TEXT("捜索中"),TEXT("SEARCHING")};
    case EState::Alert: return {TEXT("警戒"),TEXT("ALERT")};
    case EState::Combat: return {TEXT("交戦"),TEXT("COMBAT")};
    case EState::Retreat: return {TEXT("後退"),TEXT("FALLING BACK")};
    }
    return {TEXT(""),TEXT("")};
}
// Calm teal, amber while a guard wonders or searches, red once one knows.
// Every state also has its own words and glyph, so colour is never the only cue.
FLinearColor StateTint(EState State,const FSoraHUDFrame& Frame)
{
    switch(State)
    {
    case EState::Unaware: return Frame.Teal;
    case EState::Suspicious: return Frame.Gold;
    case EState::Search: return FLinearColor(.86f,.52f,.18f);
    case EState::Alert: return FLinearColor(.95f,.34f,.12f);
    case EState::Combat:
    case EState::Retreat: return FLinearColor(.92f,.13f,.10f);
    }
    return Frame.Ivory;
}
const TCHAR* Glyph(EState State)
{
    return State==EState::Unaware||State==EState::Suspicious||State==EState::Search?TEXT("？"):TEXT("！");
}
void CenteredLabel(ASoraHUD& HUD,const FString& Text,float X,float Y,float Scale,FLinearColor Color)
{
    HUD.Label(Text,X-HUD.LabelWidth(Text,Scale)*.5f,Y,Scale,Color);
}
}

TArray<FBox2D> SoraHUDPanels::StealthPanelBounds(const FSoraHUDFrame& F,const ASoraPlayerCharacter& Hero)
{
    const auto* Stealth=USoraStealth::Get(&Hero);
    if(!Stealth||!Stealth->IsZoneActive()||F.Mode.bDeterministicPractice) return {};
    const float S=F.S,Width=340*S,X=F.W-Width-25*S,Y=87*S,Height=(F.Mode.bEnglishSubtitles?104:84)*S;
    TArray<FBox2D> Bounds={FBox2D({X,Y},{X+Width,Y+Height})};
    if(Stealth->Readout(Hero).bAlarm)
        Bounds.Add(FBox2D({X,Y+Height+4*S},{X+Width,Y+Height+4*S+(F.Mode.bEnglishSubtitles?48:32)*S}));
    return Bounds;
}

void SoraHUDPanels::DrawStealth(const FSoraHUDFrame& Frame,const ASoraPlayerCharacter& Hero)
{
    const USoraStealth* Stealth=USoraStealth::Get(&Hero);
    if(!Stealth||!Stealth->IsZoneActive()||Frame.Mode.bDeterministicPractice) return;
    const FSoraStealthReadout Readout=Stealth->Readout(Hero);
    ASoraHUD& HUD=Frame.HUD;
    const float W=Frame.W,H=Frame.H,S=Frame.S;
    const bool bEnglish=Frame.Mode.bEnglishSubtitles;
    const FLinearColor Track(.12f,.19f,.21f),Back(.013f,.027f,.033f,.86f);

    // The detection meter, top right: the most alarmed guard's state and fill,
    // then the hero's stance and how lit he stands, his carried light included.
    const auto Panels=StealthPanelBounds(Frame,Hero);
    const float PW=Panels[0].GetSize().X,PX=Panels[0].Min.X,PY=Panels[0].Min.Y,PH=Panels[0].GetSize().Y;
    const FLinearColor Tint=StateTint(Readout.Worst,Frame);
    const FStealthText Text=StateText(Readout.Worst);
    HUD.Panel(PX,PY,PW,PH,Back);
    HUD.Label(TEXT("気配"),PX+16*S,PY+9*S,.40*S,Frame.Muted);
    HUD.Label(Text.Japanese,PX+68*S,PY+4*S,.54*S,Tint);
    if(bEnglish) HUD.Label(Text.English,PX+PW-16*S-HUD.LabelWidth(Text.English,.32*S),PY+12*S,.32*S,Frame.Muted);
    HUD.Panel(PX+16*S,PY+40*S,PW-32*S,6*S,Track);
    HUD.Panel(PX+16*S,PY+40*S,(PW-32*S)*Readout.MeterPermille/1000.f,6*S,Tint);
    const int32 Lit=FMath::Clamp(Readout.LightPermille*Readout.VisibilityPermille/1000,0,1000);
    HUD.Label(Readout.bCrouched?TEXT("しゃがみ"):TEXT("立ち"),PX+16*S,PY+54*S,.40*S,Frame.Ivory);
    HUD.Label(TEXT("明るさ"),PX+128*S,PY+54*S,.40*S,Frame.Muted);
    HUD.Panel(PX+205*S,PY+65*S,PW-221*S,4*S,Track);
    HUD.Panel(PX+205*S,PY+65*S,(PW-221*S)*Lit/1000.f,4*S,Lit>=500?Frame.Gold:Frame.Teal);
    if(bEnglish)
        HUD.Label(FString::Printf(TEXT("%s  /  LIGHT"),Readout.bCrouched?TEXT("CROUCHED"):TEXT("STANDING")),PX+16*S,PY+80*S,.30*S,Frame.Muted);
    if(Readout.bAlarm)
    {
        const FLinearColor Red=StateTint(EState::Combat,Frame);
        HUD.Panel(Panels[1].Min.X,Panels[1].Min.Y,Panels[1].GetSize().X,Panels[1].GetSize().Y,FLinearColor(.20f,.02f,.02f,.88f));
        HUD.Label(TEXT("警報発令"),PX+16*S,PY+PH+7*S,.46*S,Red);
        if(bEnglish) HUD.Label(TEXT("ALARM RAISED"),PX+16*S,PY+PH+32*S,.30*S,Frame.Ivory);
    }

    // Marks: over each guard whose meter fills or who is alarmed, its glyph and
    // meter; a guard out of view shows as a pointer on a ring around the
    // crosshair, turned toward it.
    const UCameraComponent* Camera=Hero.GetCamera();
    const FVector From=Camera->GetComponentLocation();
    const FVector Forward=Camera->GetForwardVector(),Right=Camera->GetRightVector();
    const float CX=W*.5f,CY=H*.5f,Ring=FMath::Min(W,H)*.3f;
    for(const FSoraStealthMark& Mark:Readout.Marks)
    {
        const FLinearColor Color=StateTint(Mark.State,Frame);
        const FVector To=Mark.Head-From;
        if(FVector::DotProduct(To,Forward)>0.f)
        {
            const FVector Screen=HUD.Project(Mark.Head);
            if(Screen.X>=0.f&&Screen.X<=W&&Screen.Y>=0.f&&Screen.Y<=H)
            {
                HUD.Label(Glyph(Mark.State),Screen.X-10*S,Screen.Y-34*S,.62*S,Color);
                HUD.Panel(Screen.X-24*S,Screen.Y,48*S,5*S,Track);
                HUD.Panel(Screen.X-24*S,Screen.Y,48*S*Mark.MeterPermille/1000.f,5*S,Color);
                continue;
            }
        }
        const float Angle=FMath::Atan2(FVector::DotProduct(To,Right),FVector::DotProduct(To,Forward));
        const FVector2D Direction(FMath::Sin(Angle),-FMath::Cos(Angle));
        const FVector2D Side(-Direction.Y,Direction.X);
        const FVector2D Base=FVector2D(CX,CY)+Direction*Ring;
        const FVector2D Tip=Base+Direction*16*S,A=Base+Side*11*S,B=Base-Side*11*S;
        HUD.DrawLine(A.X,A.Y,Tip.X,Tip.Y,Color,3*S); HUD.DrawLine(B.X,B.Y,Tip.X,Tip.Y,Color,3*S); HUD.DrawLine(A.X,A.Y,B.X,B.Y,Color,2*S);
        const FVector2D Beyond=Tip+Direction*16*S;
        HUD.Label(Glyph(Mark.State),Beyond.X-9*S,Beyond.Y-14*S,.44*S,Color);
    }

    // What the hero can do here, under the crosshair.
    FString Japanese,English;
    if(Readout.bDragging)
    {
        Japanese=TEXT("引きずっている ― ［調べる］を離して置く");
        English=TEXT("Dragging a body: release [Interact] to set it down.");
    }
    else if(Readout.bTakedown)
    {
        if(Readout.bTakedownSubdues)
        {
            Japanese=TEXT("背後から［近接］：峰打ち（殺さない）");
            English=TEXT("From behind, [Melee]: strike with the blade's back. Non-lethal.");
        }
        else if(Readout.bLethalDefault)
        {
            Japanese=TEXT("背後から［近接］：不意討ち　長押し：当て身（殺さない）");
            English=TEXT("Rear takedown: [Melee], lethal. Hold: non-lethal.");
        }
        else
        {
            Japanese=TEXT("背後から当て身：［近接］（殺さない）　長押し：斬る");
            English=TEXT("Rear takedown: [Melee]. Non-lethal. Hold: lethal.");
        }
    }
    else if(Readout.bDrag)
    {
        Japanese=TEXT("倒れた者を引きずる：［調べる］長押し");
        English=TEXT("Drag a body: hold [Interact].");
    }
    if(Japanese.IsEmpty()) return;
    CenteredLabel(HUD,Japanese,CX,CY+92*S,.50*S,Frame.Gold);
    if(bEnglish) CenteredLabel(HUD,English,CX,CY+122*S,.36*S,Frame.Ivory);
}
