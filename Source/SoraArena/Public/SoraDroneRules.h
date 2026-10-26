#pragma once

namespace SoraDroneRules
{
// The inventory disc is authored in centimetres at actor scale one. Its
// movement sphere contains the mesh; precision hits use the imported UCX
// hulls instead. The ledger's ceiling and flight height are unchanged.
constexpr float MovementRadiusCm=38.f;
constexpr float VisualRadiusLimitCm=36.5f;
constexpr int ScalePermille=1000;
}
