#pragma once

// This identity-only codec has no Unreal dependency so it can be tested without
// an engine installation. It deliberately cannot represent a signed payload,
// wallet session, or pairing URI.
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace ArenaTransactionRecovery
{
inline constexpr std::string_view Schema = "SORA_ARENA_PENDING_TX_V1";
inline constexpr size_t MaxRecordBytes = 512;

struct Record
{
    std::string Origin;
    std::string NetworkId;
    std::string TransactionHash;
    std::string EntrypointHash;
};

inline bool CanonicalHash(std::string_view Hash)
{
    if (Hash.size() != 64) return false;
    for (char C : Hash) if (!((C >= '0' && C <= '9') || (C >= 'a' && C <= 'f'))) return false;
    const char Marker = Hash.back();
    return (Marker >= '0' && Marker <= '9' && (Marker - '0') % 2 == 1)
        || Marker == 'b' || Marker == 'd' || Marker == 'f';
}

inline bool CanonicalNetworkId(std::string_view Id)
{
    if (Id.size() != 74 || Id.substr(0, 5) != "hash:" || Id[69] != '#') return false;
    for (size_t I = 5; I < 69; ++I)
        if (!((Id[I] >= '0' && Id[I] <= '9') || (Id[I] >= 'A' && Id[I] <= 'F'))) return false;
    const char Marker = Id[68];
    if (!((Marker >= '0' && Marker <= '9' && (Marker - '0') % 2 == 1)
        || Marker == 'B' || Marker == 'D' || Marker == 'F')) return false;
    uint16_t Crc = 0xFFFF;
    for (size_t I = 0; I < 69; ++I)
    {
        Crc ^= static_cast<uint16_t>(static_cast<uint8_t>(Id[I])) << 8;
        for (int Bit = 0; Bit < 8; ++Bit)
            Crc = static_cast<uint16_t>((Crc & 0x8000) ? ((Crc << 1) ^ 0x1021) : (Crc << 1));
    }
    constexpr char Hex[] = "0123456789ABCDEF";
    for (size_t I = 0; I < 4; ++I)
        if (Id[70 + I] != Hex[(Crc >> (12 - I * 4)) & 0xF]) return false;
    return true;
}

inline bool LoopbackHttpOrigin(std::string_view Origin)
{
    constexpr std::array<std::string_view, 3> Hosts = {
        "http://127.0.0.1", "http://localhost", "http://[::1]"};
    for (std::string_view Host : Hosts)
    {
        if (Origin.substr(0, Host.size()) != Host) continue;
        if (Origin.size() == Host.size()) return true;
        if (Origin[Host.size()] != ':') return false;
        const std::string_view Port = Origin.substr(Host.size() + 1);
        if (Port.empty() || Port.size() > 5) return false;
        unsigned Number = 0;
        for (char C : Port)
        {
            if (C < '0' || C > '9') return false;
            Number = Number * 10 + static_cast<unsigned>(C - '0');
        }
        return Number >= 1 && Number <= 65535;
    }
    return false;
}

inline bool Valid(const Record& Value, std::string_view ExpectedOrigin, std::string_view ExpectedNetwork)
{
    return Value.Origin == ExpectedOrigin && Value.NetworkId == ExpectedNetwork
        && LoopbackHttpOrigin(Value.Origin) && CanonicalNetworkId(Value.NetworkId)
        && CanonicalHash(Value.TransactionHash) && CanonicalHash(Value.EntrypointHash);
}

inline bool Encode(const Record& Value, std::string_view ExpectedOrigin,
    std::string_view ExpectedNetwork, std::string& Out)
{
    Out.clear();
    if (!Valid(Value, ExpectedOrigin, ExpectedNetwork)) return false;
    std::string Candidate;
    Candidate.reserve(Schema.size() + Value.Origin.size() + Value.NetworkId.size() + 132);
    Candidate.append(Schema).append("\n").append(Value.Origin).append("\n")
        .append(Value.NetworkId).append("\n").append(Value.TransactionHash).append("\n")
        .append(Value.EntrypointHash).append("\n");
    if (Candidate.size() > MaxRecordBytes) return false;
    Out = std::move(Candidate);
    return true;
}

inline bool Decode(std::string_view Bytes, std::string_view ExpectedOrigin,
    std::string_view ExpectedNetwork, Record& Out)
{
    if (Bytes.empty() || Bytes.size() > MaxRecordBytes) return false;
    std::array<std::string_view, 5> Lines;
    size_t Begin = 0;
    for (std::string_view& Line : Lines)
    {
        const size_t End = Bytes.find('\n', Begin);
        if (End == std::string_view::npos) return false;
        Line = Bytes.substr(Begin, End - Begin);
        Begin = End + 1;
    }
    if (Begin != Bytes.size() || Lines[0] != Schema) return false;
    Record Candidate{std::string(Lines[1]), std::string(Lines[2]),
        std::string(Lines[3]), std::string(Lines[4])};
    if (!Valid(Candidate, ExpectedOrigin, ExpectedNetwork)) return false;
    Out = std::move(Candidate);
    return true;
}
}
