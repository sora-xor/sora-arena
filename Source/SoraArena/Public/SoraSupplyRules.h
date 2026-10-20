#pragma once

// No reserve-stock amount is authored for the League cache. Each explicit
// use fills existing magazines to catalog caps; repeated full use does nothing.
namespace SoraSupplyRules
{
// A finite pickup adds only its declared amount to one unlocked magazine.
// Full use consumes no inventory space; the caller owns the saved claim.
inline int AddAmmo(int* Stored,const int* Caps,int Count,unsigned Unlocked,int Held,int& Ammo,int Weapon,int Amount)
{
    if(!Stored||!Caps||Weapon<0||Weapon>=Count||Weapon>=32||Amount<=0||
        (Unlocked&(1u<<Weapon))==0||Caps[Weapon]<=0) return -1;
    const int Before=Weapon==Held?Ammo:Stored[Weapon];
    if(Before<0||Before>Caps[Weapon]) return -1;
    const int Added=Amount<Caps[Weapon]-Before?Amount:Caps[Weapon]-Before;
    Stored[Weapon]=Before+Added;
    if(Weapon==Held) Ammo=Stored[Weapon];
    return Added;
}
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
