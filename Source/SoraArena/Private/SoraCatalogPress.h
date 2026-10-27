#pragma once
class FJsonObject;
struct FSoraBeat;
struct FSoraSpace;
namespace SoraCatalogPress { bool Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space); }
