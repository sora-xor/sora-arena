#pragma once

// Chapter 3 §1.4/§2.2: world-centimetre landing, two timed flight corridors.
// Mirrored by campaign_landing.py; source parity and physical fixtures guard it.
namespace SoraLandingSpaceRules
{
struct FPoint { int X,Y; };
constexpr int MinX=-12000,MaxX=-7600,MinY=-2800,MaxY=-1200;
constexpr int ZoneMinY=-3400,ZoneMaxY=-660;
constexpr FPoint Entry{-11300,-2700};
constexpr FPoint Cargo[]={{-11250,-2300},{-10500,-1850},{-9800,-2350},{-9200,-1450},{-8600,-1800}};
constexpr FPoint Lamps[]={{-11440,-1360},{-9600,-1360},{-8300,-1780}};
constexpr FPoint Puddles[]={{-10700,-2190},{-10200,-2050},{-9700,-2170},{-9300,-2110},{-8600,-2450},{-8100,-2290}};
struct FBox { int X,Y,Width,Depth,Height; };
constexpr FBox Walls[]={{-12030,-2030,60,2860,360},{-7570,-2030,60,2860,360},
    {-9800,-3430,4400,60,360},{-9800,-630,4400,60,360}};
constexpr FPoint Eight[]={{0,0},{459,354},{849,500},{1109,354},{1200,0},{1109,-354},{849,-500},{459,-354},
    {0,0},{-459,354},{-849,500},{-1109,354},{-1200,0},{-1109,-354},{-849,-500},{-459,-354}};
constexpr int Count(int Guard) { return Guard==0?16:Guard==1?2:0; }
constexpr int Period(int Guard) { return Guard==0?40000:Guard==1?30000:0; }
constexpr int Height(int Guard) { return Guard==0?500:Guard==1?400:0; }
constexpr FPoint Point(int Guard,int Index)
{
    return Guard==0&&Index>=0&&Index<16?FPoint{Eight[Index].X-10200,Eight[Index].Y-2000}:
        Guard==1&&Index>=0&&Index<2?FPoint{Index==0?-11800:-7800,-2700}:FPoint{0,0};
}
}
