#pragma once
class FJsonObject;
struct FSoraBeat;
struct FSoraSpace;
namespace SoraCatalogTerminalCharge
{ bool Read(const FJsonObject& Object,FSoraBeat& Beat,const FSoraSpace& Space); }
