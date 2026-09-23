#include "ArenaTransactionRecoveryRecord.h"

#include <cstdlib>
#include <iostream>
#include <string>

namespace R = ArenaTransactionRecovery;

static void Check(bool Condition, const char* Name)
{
    if (!Condition)
    {
        std::cerr << "FAIL: " << Name << '\n';
        std::exit(1);
    }
}

int main()
{
    const std::string Origin = "http://127.0.0.1:8080";
    const std::string Network = "hash:0000000000000000000000000000000000000000000000000000000000000001#C50E";
    const std::string Hash(63, '0');
    const R::Record Identity{Origin, Network, Hash + '1', Hash + '3'};
    std::string Encoded;
    Check(R::Encode(Identity, Origin, Network, Encoded), "encode exact identity");
    Check(Encoded.find("SORA_ARENA_PENDING_TX_V1\n") == 0, "versioned record");
    Check(Encoded.find("iroha://") == std::string::npos, "no pairing URI");
    R::Record Restored;
    Check(R::Decode(Encoded, Origin, Network, Restored), "decode exact identity");
    Check(Restored.Origin == Identity.Origin && Restored.NetworkId == Identity.NetworkId
        && Restored.TransactionHash == Identity.TransactionHash
        && Restored.EntrypointHash == Identity.EntrypointHash, "round-trip all bindings");
    Check(!R::Decode(Encoded, "http://localhost:8080", Network, Restored), "origin substitution");
    Check(!R::Decode(Encoded, Origin, Network + "x", Restored), "network substitution");
    Check(!R::Decode(Encoded.substr(0, Encoded.size() - 1), Origin, Network, Restored), "truncated record");
    Check(!R::Decode(Encoded + "signed_bytes=secret\n", Origin, Network, Restored), "extra field rejected");
    Check(!R::Decode(Encoded + "\n", Origin, Network, Restored), "extra empty field rejected");
    Check(!R::Decode(std::string(R::MaxRecordBytes + 1, 'A'), Origin, Network, Restored), "oversize rejected");
    std::string Modified = Encoded;
    Modified.replace(0, R::Schema.size(), "SORA_ARENA_PENDING_TX_V0");
    Check(!R::Decode(Modified, Origin, Network, Restored), "no legacy record format");
    Modified = Encoded;
    Modified.replace(Modified.find(Network), Network.size(), Network.substr(0, 73) + "F");
    Check(!R::Decode(Modified, Origin, Network, Restored), "network checksum mutation");
    Modified = Encoded;
    Modified.replace(Modified.find(Identity.TransactionHash), 64, Hash + '0');
    Check(!R::Decode(Modified, Origin, Network, Restored), "noncanonical transaction hash");
    Modified = Encoded;
    Modified.replace(Modified.find(Identity.EntrypointHash), 64, Hash + '0');
    Check(!R::Decode(Modified, Origin, Network, Restored), "noncanonical entrypoint hash");
    Modified = Encoded;
    Modified.replace(Modified.find(Origin), Origin.size(), "http://localhost.evil:8080");
    Check(!R::Decode(Modified, Origin, Network, Restored), "remote origin rejected");
    Modified = Encoded;
    Modified.replace(Modified.find(Origin), Origin.size(), "https://127.0.0.1:8080");
    Check(!R::Decode(Modified, Origin, Network, Restored), "HTTPS cannot bypass isolated loopback rule");
    Modified = Encoded;
    Modified.insert(Modified.find(Origin) + Origin.size(), "\riroha://connect?secret");
    Check(!R::Decode(Modified, Origin, Network, Restored), "control and URI injection");
    Check(R::LoopbackHttpOrigin("http://[::1]:65535"), "IPv6 loopback");
    Check(!R::LoopbackHttpOrigin("http://[::1]:65536"), "invalid port");
    Check(!R::LoopbackHttpOrigin("http://localhost.evil"), "lookalike host");
    Check(!R::LoopbackHttpOrigin("http://127.0.0.1/path"), "origin path");
    Check(!R::Encode({"http://torii.example", Network, Hash + '1', Hash + '3'},
        "http://torii.example", Network, Encoded), "remote HTTP encoding forbidden");
    Check(Encoded.empty(), "invalid encode leaves no record");
    std::cout << "transaction recovery codec: 23 checks passed\n";
    return 0;
}
