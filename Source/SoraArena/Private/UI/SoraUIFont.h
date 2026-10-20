#pragma once

class UObject;
class UFont;

namespace SoraUI
{
// Shared by the live HUD/menu and the Slate readability fixtures.
UFont* CreateUIFont(UObject* Outer);
}
