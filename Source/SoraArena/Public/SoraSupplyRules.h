#pragma once

// No reserve-stock amount is authored for the League cache. Each explicit
// use fills existing magazines to catalog caps; repeated full use does nothing.
namespace SoraSupplyRules
{
inline int Restock(int* Stored,const int* Caps,int Count,unsigned Unlocked,int Held,int& Ammo)
{
    int Changed=0;
    for(int Id=0;Id<Count&&Id<32;++Id)
    {
        if((Unlocked&(1u<<Id))==0||Caps[Id]<=0) continue;
        // The currently held count is authoritative: firing and reload update
        // Ammo, while the stored copy normally catches up on weapon switch.
        const int Before=Id==Held?Ammo:Stored[Id];
        if(Before<Caps[Id]) ++Changed;
        Stored[Id]=Caps[Id];
        if(Id==Held) Ammo=Caps[Id];
    }
    return Changed;
}
}
