#pragma once

// Continuous, bounded deck travel. Work is in milliturns, not the HUD's
// rounded permille, so idle decay also moves the deck continuously.
namespace SoraLiftRules
{
constexpr double BottomCm=2700.0, TopCm=14200.0, TravelCm=TopCm-BottomCm;
constexpr double SizeCm=600.0, GalleryWidthCm=1000.0, GalleryLengthCm=4000.0;
constexpr double Speed(int Turns,int MinTurnMs)
{
    return Turns>0&&MinTurnMs>0?TravelCm*1000.0/(Turns*MinTurnMs):0.0;
}
constexpr double Height(int Work,int Goal)
{
    return BottomCm+TravelCm*(Goal>0?(Work<0?0.0:Work>Goal?1.0:double(Work)/Goal):0.0);
}
constexpr double Gantry(int Quarter) { return BottomCm+TravelCm*Quarter/4.0; }
constexpr double Advance(double Current,double Target,double CmPerSecond,double Seconds)
{
    const double Step=CmPerSecond>0.0&&Seconds>0.0?CmPerSecond*Seconds:0.0;
    return Current<Target?(Current+Step<Target?Current+Step:Target):(Current-Step>Target?Current-Step:Target);
}
constexpr bool At(double Current,double Target,double Tolerance=.1)
{
    return Current>=Target-Tolerance&&Current<=Target+Tolerance;
}
}
