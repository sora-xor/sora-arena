#pragma once
#include <array>
#include <cmath>

// Presentation only: fixed-size samples of a slack lead. These positions
// never feed horse movement, collision, steering, fear or interaction rules.
namespace SoraLeadRopeRules
{
constexpr int Segments = 12;
struct FPoint { double X=0, Y=0, Z=0; };
struct FLine { std::array<FPoint,Segments+1> Points{}; bool Visible=false; };
inline bool Finite(FPoint P) { return std::isfinite(P.X)&&std::isfinite(P.Y)&&std::isfinite(P.Z); }
inline double Distance(FPoint A,FPoint B)
{
    return std::hypot(std::hypot(B.X-A.X,B.Y-A.Y),B.Z-A.Z);
}
inline FLine Sample(FPoint Start,FPoint End,double Sag)
{
    FLine Line;
    Line.Visible=true;
    for(int N=0;N<=Segments;++N)
    {
        const double T=double(N)/Segments;
        Line.Points[N]={Start.X+(End.X-Start.X)*T,Start.Y+(End.Y-Start.Y)*T,
            Start.Z+(End.Z-Start.Z)*T-4*Sag*T*(1-T)};
    }
    // Keep exact attachments, including at large world coordinates.
    Line.Points.front()=Start; Line.Points.back()=End;
    return Line;
}
inline double Length(const FLine& Line)
{
    double Total=0;
    for(int N=0;N<Segments;++N) Total+=Distance(Line.Points[N],Line.Points[N+1]);
    return Total;
}
inline FLine Curve(FPoint Start,FPoint End,double NominalLengthCm)
{
    if(!Finite(Start)||!Finite(End)||!std::isfinite(NominalLengthCm)||NominalLengthCm<=0) return {};
    const double Span=Distance(Start,End);
    if(!std::isfinite(Span)||Span<.001) return {};
    // Existing following can temporarily separate the horses farther than
    // the lead's nominal length. Show the connection taut; never pull them.
    if(Span>=NominalLengthCm) return Sample(Start,End,0);
    double Low=0,High=NominalLengthCm*.5;
    for(int Iteration=0;Iteration<32;++Iteration)
    {
        const double Mid=(Low+High)*.5;
        if(Length(Sample(Start,End,Mid))<NominalLengthCm) Low=Mid;
        else High=Mid;
    }
    return Sample(Start,End,(Low+High)*.5);
}
}
