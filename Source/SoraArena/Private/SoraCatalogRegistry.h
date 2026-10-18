#pragma once
class FJsonObject;
struct FSoraBeat;
namespace SoraCatalogRegistry
{
bool Read(const FJsonObject& Object, FSoraBeat& Beat);
}
