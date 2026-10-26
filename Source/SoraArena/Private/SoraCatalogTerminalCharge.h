#pragma once
class FJsonObject;
struct FSoraBeat;
struct FSoraSpace;
struct FSoraZone;
namespace SoraCatalogTerminalCharge
{
bool IsSquare(const FSoraZone& Zone);
bool Read(const FJsonObject& Object,FSoraBeat& Beat,const FSoraSpace& Space);
}
