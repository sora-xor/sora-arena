#include "ArenaWalletSubsystem.h"
#include "ArenaTransactionRecoveryRecord.h"

#include "Async/Async.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/Texture2D.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/PlatformTime.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "IWebSocket.h"
#include "Misc/Base64.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "TextureResource.h"
#include "WebSocketsModule.h"
#include "ThirdParty/QrCodeGen/qrcodegen.h"
#include <atomic>
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#endif

namespace ArenaConnect
{
constexpr int32 MaxFrameBytes = 1024 * 1024;
constexpr int32 MaxSessionJsonBytes = 32 * 1024;
constexpr int32 MaxTransactionStatusJsonBytes = 4096;
constexpr int32 MaxTransactionPolls = 90;
constexpr uint32 BridgeAbi = 23;
enum class EChainObservation : uint8 { Invalid, Absent, InFlight, Applied, Rejected };
struct FIngressBudget
{
    std::atomic<int32> Bytes{0};
    std::atomic<int32> Fragments{0};
    std::atomic<bool> Stopped{false};
};
const FString Permissions = TEXT("{\"methods\":[\"SIGN_REQUEST_TX\"],\"events\":[],\"resources\":null}");

void Erase(TArray<uint8>& Bytes)
{
    volatile uint8* Data = Bytes.GetData();
    for (int32 I = 0; I < Bytes.Num(); ++I) Data[I] = 0;
    Bytes.Empty();
}

void Erase(FString& Text)
{
    volatile TCHAR* Data = Text.GetCharArray().GetData();
    for (int32 I = 0; I < Text.GetCharArray().Num(); ++I) Data[I] = 0;
    Text.Empty();
}

TArray<uint8> Utf8(const FString& Text)
{
    FTCHARToUTF8 Encoded(*Text);
    TArray<uint8> Out;
    Out.Append(reinterpret_cast<const uint8*>(Encoded.Get()), Encoded.Length());
    return Out;
}

FString Text(const uint8* Data, int32 Size)
{
    if (!Data || Size == 0) return FString();
    FUTF8ToTCHAR Decoded(reinterpret_cast<const ANSICHAR*>(Data), Size);
    return FString(Decoded.Length(), Decoded.Get());
}

FString Base64Url(const TArray<uint8>& Bytes)
{
    return FBase64::Encode(Bytes).Replace(TEXT("+"), TEXT("-")).Replace(TEXT("/"), TEXT("_")).Replace(TEXT("="), TEXT(""));
}

bool DecodeBase64Url(const FString& Encoded, int32 Size, TArray<uint8>& Out)
{
    if (Encoded.Len() != (Size * 8 + 5) / 6) return false;
    FString Standard = Encoded.Replace(TEXT("-"), TEXT("+")).Replace(TEXT("_"), TEXT("/"));
    while (Standard.Len() % 4) Standard += TEXT("=");
    return FBase64::Decode(Standard, Out) && Out.Num() == Size && Base64Url(Out) == Encoded;
}

bool DecodeHex(const FString& Hex, int32 Size, TArray<uint8>& Out, bool UpperOnly = false)
{
    if (Hex.Len() != Size * 2) return false;
    Out.SetNumUninitialized(Size);
    auto Nibble = [UpperOnly](TCHAR C) -> int32 {
        if (C >= '0' && C <= '9') return C - '0';
        if (C >= 'A' && C <= 'F') return C - 'A' + 10;
        if (!UpperOnly && C >= 'a' && C <= 'f') return C - 'a' + 10;
        return -1;
    };
    for (int32 I = 0; I < Size; ++I)
    {
        int32 A = Nibble(Hex[2 * I]), B = Nibble(Hex[2 * I + 1]);
        if (A < 0 || B < 0) { Out.Empty(); return false; }
        Out[I] = static_cast<uint8>((A << 4) | B);
    }
    return true;
}

bool ParseNetworkId(const FString& Literal, TArray<uint8>& Out)
{
    if (Literal.Len() != 74 || !Literal.StartsWith(TEXT("hash:"), ESearchCase::CaseSensitive) || Literal[69] != '#') return false;
    if (!DecodeHex(Literal.Mid(5, 64), 32, Out, true) || !(Out.Last() & 1)) return false;
    uint16 Crc = 0xFFFF;
    for (int32 I = 0; I < 69; ++I)
    {
        Crc ^= static_cast<uint16>(Literal[I]) << 8;
        for (int32 Bit = 0; Bit < 8; ++Bit) Crc = static_cast<uint16>((Crc & 0x8000) ? ((Crc << 1) ^ 0x1021) : (Crc << 1));
    }
    return Literal.Right(4) == FString::Printf(TEXT("%04X"), Crc);
}

bool NormalizeOrigin(const FString& Input, FString& Out)
{
    Out = Input;
    if (Out.EndsWith(TEXT("/"))) Out.LeftChopInline(1);
    bool Https = Out.StartsWith(TEXT("https://"), ESearchCase::CaseSensitive);
    bool Http = Out.StartsWith(TEXT("http://"), ESearchCase::CaseSensitive);
    if (!Https && !Http) return false;
    FString Authority = Out.Mid(Https ? 8 : 7);
    if (Authority.IsEmpty() || Authority.Len() > 260) return false;
    for (TCHAR C : Authority)
    {
        if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '-' || C == '.' || C == ':' || C == '[' || C == ']')) return false;
    }
    FString Host = Authority, Port;
    if (Authority.StartsWith(TEXT("[")))
    {
        int32 End = INDEX_NONE;
        if (!Authority.FindChar(']', End) || Authority.Left(End + 1) != TEXT("[::1]")) return false;
        Host = Authority.Left(End + 1);
        if (Authority.Len() > End + 1)
        {
            if (Authority[End + 1] != ':') return false;
            Port = Authority.Mid(End + 2);
            if (Port.IsEmpty()) return false;
        }
    }
    else if (Authority.Contains(TEXT(":")))
    {
        if (!Authority.Split(TEXT(":"), &Host, &Port) || Host.IsEmpty() || Port.IsEmpty() || Host.Contains(TEXT("[")) || Host.Contains(TEXT("]"))) return false;
    }
    if (Host.IsEmpty() || Host.Contains(TEXT("[")) != (Host == TEXT("[::1]")) || Host.Contains(TEXT("]")) != (Host == TEXT("[::1]"))) return false;
    if (!Port.IsEmpty())
    {
        if (Port.Len() > 5) return false;
        for (TCHAR C : Port) if (C < '0' || C > '9') return false;
        int32 Number = FCString::Atoi(*Port);
        if (Number < 1 || Number > 65535) return false;
    }
    return Https || Host == TEXT("127.0.0.1") || Host == TEXT("localhost") || Host == TEXT("[::1]");
}

bool ParseObject(const uint8* Data, int32 Size, TSharedPtr<FJsonObject>& Out)
{
    const auto Reader = TJsonReaderFactory<>::Create(Text(Data, Size));
    return FJsonSerializer::Deserialize(Reader, Out) && Out.IsValid();
}

bool CanonicalHash(const FString& Hash)
{
    if (Hash.Len() != 64) return false;
    for (TCHAR C : Hash) if (!((C >= '0' && C <= '9') || (C >= 'a' && C <= 'f'))) return false;
    const TCHAR Marker = Hash[63];
    return (Marker >= '0' && Marker <= '9' && (Marker - '0') % 2 == 1)
        || Marker == 'b' || Marker == 'd' || Marker == 'f';
}

bool JsonContentType(const FString& ContentType)
{
    return ContentType.Equals(TEXT("application/json"), ESearchCase::IgnoreCase)
        || ContentType.StartsWith(TEXT("application/json;"), ESearchCase::IgnoreCase);
}

EChainObservation ReadExactStatus(int32 HttpCode, const FString& ContentType, const TArray<uint8>& Body, const FString& Hash)
{
    if ((HttpCode != 200 && HttpCode != 404) || !JsonContentType(ContentType)
        || Body.IsEmpty() || Body.Num() > MaxTransactionStatusJsonBytes || !CanonicalHash(Hash)) return EChainObservation::Invalid;
    TSharedPtr<FJsonObject> Root;
    if (!ParseObject(Body.GetData(), Body.Num(), Root)) return EChainObservation::Invalid;
    FString ObservedHash, Scope;
    if (HttpCode == 404)
    {
        FString Code;
        const TSharedPtr<FJsonObject>* Details = nullptr;
        const TSharedPtr<FJsonObject>* Absence = nullptr;
        if (Root->Values.Num() != 3 || !Root->TryGetStringField(TEXT("code"), Code) || Code != TEXT("pipeline_transaction_status_not_found")
            || !Root->TryGetObjectField(TEXT("details"), Details)
            || (*Details)->Values.Num() != 1
            || !(*Details)->TryGetObjectField(TEXT("pipeline_transaction_status_not_found"), Absence)
            || (*Absence)->Values.Num() != 2
            || !(*Absence)->TryGetStringField(TEXT("hash"), ObservedHash)
            || !(*Absence)->TryGetStringField(TEXT("scope"), Scope)) return EChainObservation::Invalid;
        return ObservedHash == Hash && Scope == TEXT("global") ? EChainObservation::Absent : EChainObservation::Invalid;
    }
    FString Source;
    const TSharedPtr<FJsonObject>* Status = nullptr;
    if (Root->Values.Num() != 4 || !Root->TryGetStringField(TEXT("hash"), ObservedHash)
        || ObservedHash != Hash || !Root->TryGetStringField(TEXT("scope"), Scope) || Scope != TEXT("global")
        || !Root->TryGetStringField(TEXT("resolved_from"), Source)
        || (Source != TEXT("cache") && Source != TEXT("queue") && Source != TEXT("state"))
        || !Root->TryGetObjectField(TEXT("status"), Status)
        || ((*Status)->Values.Num() != 1 && (*Status)->Values.Num() != 2)) return EChainObservation::Invalid;
    if ((*Status)->Values.Num() == 2)
    {
        double Height = 0;
        if (!(*Status)->TryGetNumberField(TEXT("block_height"), Height) || Height < 0 || Height > 9007199254740991.0 || FMath::FloorToDouble(Height) != Height) return EChainObservation::Invalid;
    }
    FString Kind;
    if (!(*Status)->TryGetStringField(TEXT("kind"), Kind)) return EChainObservation::Invalid;
    if (Kind == TEXT("Applied") && Source == TEXT("state")) return EChainObservation::Applied;
    if ((Kind == TEXT("Rejected") || Kind == TEXT("Expired")) && Source == TEXT("state")) return EChainObservation::Rejected;
    if (Kind == TEXT("Queued") || Kind == TEXT("Approved") || Kind == TEXT("Committed")
        || Kind == TEXT("Applied") || Kind == TEXT("Rejected") || Kind == TEXT("Expired")) return EChainObservation::InFlight;
    return EChainObservation::Invalid;
}

bool MatchLaunchUri(const FString& Uri, const TMap<FString, FString>& Expected)
{
    const FString Prefix = TEXT("iroha://connect?");
    if (!Uri.StartsWith(Prefix, ESearchCase::CaseSensitive) || Uri.Contains(TEXT("#"))) return false;
    TArray<FString> Parts;
    Uri.Mid(Prefix.Len()).ParseIntoArray(Parts, TEXT("&"), false);
    if (Parts.Num() != Expected.Num()) return false;
    TSet<FString> Seen;
    for (const FString& Part : Parts)
    {
        FString Key, Value;
        if (!Part.Split(TEXT("="), &Key, &Value)) return false;
        Key = FGenericPlatformHttp::UrlDecode(Key);
        Value = FGenericPlatformHttp::UrlDecode(Value);
        const FString* Wanted = Expected.Find(Key);
        if (!Wanted || Seen.Contains(Key) || *Wanted != Value) return false;
        Seen.Add(Key);
    }
    return true;
}

bool IsAllowedInstruction(const FString& Name)
{
    // Arena equipment is returnable. NFT wagering is intentionally not an Arena action.
    static const TSet<FString> Allowed = {TEXT("OpenGameSessionV1"), TEXT("JoinGameSessionV1"), TEXT("ClaimGamePayoutV1"), TEXT("OfferNftV1"), TEXT("BuyNftV1"), TEXT("CancelNftOfferV1")};
    return Allowed.Contains(Name);
}

bool RequiresQualifiedTermsReview(const FString& Name)
{
    // Neither a typed scaffold nor a wallet approval proves the live game/offer terms.
    return Name == TEXT("JoinGameSessionV1") || Name == TEXT("BuyNftV1");
}

std::string Utf8String(const FString& Value)
{
    const FTCHARToUTF8 Encoded(*Value);
    return std::string(Encoded.Get(), Encoded.Length());
}

bool ReadIsolatedTestConfig(FString& OutOrigin, FString& OutNetwork)
{
#if UE_BUILD_SHIPPING
    return false;
#else
    if (!GConfig) return false;
    bool bEnabled = false;
    GConfig->GetBool(TEXT("Arena.Connect"), TEXT("bEnableIsolatedTestTransactions"), bEnabled, GGameIni);
    GConfig->GetString(TEXT("Arena.Connect"), TEXT("IsolatedTestToriiOrigin"), OutOrigin, GGameIni);
    GConfig->GetString(TEXT("Arena.Connect"), TEXT("IsolatedTestNetworkId"), OutNetwork, GGameIni);
    FString Normalized;
    TArray<uint8> NetworkBytes;
    return bEnabled && OutOrigin.StartsWith(TEXT("http://"), ESearchCase::CaseSensitive)
        && NormalizeOrigin(OutOrigin, Normalized) && Normalized == OutOrigin
        && ParseNetworkId(OutNetwork, NetworkBytes)
        && ArenaTransactionRecovery::LoopbackHttpOrigin(Utf8String(OutOrigin));
#endif
}

FString RecoveryDirectory()
{
    return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("ArenaConnect"), TEXT("Recovery"));
}

FString RecoveryPath(const FString& Hash)
{
    return FPaths::Combine(RecoveryDirectory(), TEXT("pending-") + Hash + TEXT(".v1"));
}

void RecoveryFiles(TArray<FString>& Out)
{
    IFileManager::Get().FindFiles(Out, *FPaths::Combine(RecoveryDirectory(), TEXT("pending-*")), true, false);
}

enum class ERecoveryRead : uint8 { Missing, Valid, Invalid };

ERecoveryRead ReadRecovery(const FString& ExpectedOrigin, const FString& ExpectedNetwork,
    ArenaTransactionRecovery::Record& Out)
{
    TArray<FString> Files;
    RecoveryFiles(Files);
    if (Files.IsEmpty()) return ERecoveryRead::Missing;
    if (Files.Num() != 1) return ERecoveryRead::Invalid;
    const FString& Name = Files[0];
    if (!Name.StartsWith(TEXT("pending-")) || !Name.EndsWith(TEXT(".v1"))) return ERecoveryRead::Invalid;
    const FString FilenameHash = Name.Mid(8, Name.Len() - 11);
    if (!CanonicalHash(FilenameHash)) return ERecoveryRead::Invalid;
    const FString Path = FPaths::Combine(RecoveryDirectory(), Name);
    TUniquePtr<IFileHandle> Handle(FPlatformFileManager::Get().GetPlatformFile().OpenRead(*Path, false));
    if (!Handle.IsValid()) return ERecoveryRead::Invalid;
    const int64 FileSize = Handle->Size();
    if (FileSize <= 0 || FileSize > static_cast<int64>(ArenaTransactionRecovery::MaxRecordBytes)) return ERecoveryRead::Invalid;
    TArray<uint8> Bytes;
    Bytes.SetNumUninitialized(static_cast<int32>(FileSize));
    if (!Handle->Read(Bytes.GetData(), FileSize) || Handle->Size() != FileSize) return ERecoveryRead::Invalid;
    const std::string_view Encoded(reinterpret_cast<const char*>(Bytes.GetData()), static_cast<size_t>(Bytes.Num()));
    if (!ArenaTransactionRecovery::Decode(Encoded, Utf8String(ExpectedOrigin), Utf8String(ExpectedNetwork), Out)
        || Out.TransactionHash != Utf8String(FilenameHash)) return ERecoveryRead::Invalid;
    return ERecoveryRead::Valid;
}

bool PersistRecovery(const ArenaTransactionRecovery::Record& Identity,
    const FString& ExpectedOrigin, const FString& ExpectedNetwork)
{
    std::string Encoded;
    if (!ArenaTransactionRecovery::Encode(Identity, Utf8String(ExpectedOrigin), Utf8String(ExpectedNetwork), Encoded)) return false;
    TArray<FString> Existing;
    RecoveryFiles(Existing);
    if (!Existing.IsEmpty()) return false;
    IPlatformFile& File = FPlatformFileManager::Get().GetPlatformFile();
    const FString Directory = RecoveryDirectory();
    if (!File.CreateDirectoryTree(*Directory)) return false;
    const FString Hash = UTF8_TO_TCHAR(Identity.TransactionHash.c_str());
    const FString Destination = RecoveryPath(Hash);
    const FString Staging = FPaths::Combine(Directory, TEXT("staging-") + Hash + TEXT("-")
        + FGuid::NewGuid().ToString(EGuidFormats::Digits) + TEXT(".tmp"));
    bool bWritten = false;
    {
        TUniquePtr<IFileHandle> Handle(File.OpenWrite(*Staging, false, false));
        bWritten = Handle.IsValid() && Handle->Write(reinterpret_cast<const uint8*>(Encoded.data()), static_cast<int64>(Encoded.size()))
            && Handle->Flush(true);
    }
    if (!bWritten || !IFileManager::Get().Move(*Destination, *Staging, false, false))
    {
        File.DeleteFile(*Staging);
        return false;
    }
    ArenaTransactionRecovery::Record ReadBack;
    return ReadRecovery(ExpectedOrigin, ExpectedNetwork, ReadBack) == ERecoveryRead::Valid
        && ReadBack.TransactionHash == Identity.TransactionHash
        && ReadBack.EntrypointHash == Identity.EntrypointHash;
}

bool ForgetRecovery(const ArenaTransactionRecovery::Record& Identity,
    const FString& ExpectedOrigin, const FString& ExpectedNetwork)
{
    ArenaTransactionRecovery::Record Stored;
    if (ReadRecovery(ExpectedOrigin, ExpectedNetwork, Stored) != ERecoveryRead::Valid
        || Stored.TransactionHash != Identity.TransactionHash
        || Stored.EntrypointHash != Identity.EntrypointHash) return false;
    return IFileManager::Get().Delete(*RecoveryPath(UTF8_TO_TCHAR(Identity.TransactionHash.c_str())), false, true);
}
}

    /** Exact C signatures use unsigned long: it is 32-bit on Win64 and 64-bit on macOS. */
struct FArenaConnectNative
{
    using FBlob = int32 (*)(const uint8*, unsigned long, uint8**, unsigned long*);
    void* Handle = nullptr;
    uint32 (*Abi)() = nullptr;
    void (*Free)(uint8*) = nullptr;
    int32 (*CanonicalJson)(const uint8*, unsigned long, uint8**, unsigned long*, uint8*, unsigned long) = nullptr;
    int32 (*KeyPair)(uint8*, uint8*) = nullptr;
    int32 (*DeriveSid)(const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, uint8*, unsigned long) = nullptr;
    int32 (*Open)(const uint8*, uint8, uint64, const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, uint8**, unsigned long*) = nullptr;
    int32 (*FrameKind)(const uint8*, unsigned long, uint8*, uint8*, uint64*, uint16*) = nullptr;
    int32 (*DecodePing)(const uint8*, unsigned long, uint64*) = nullptr;
    int32 (*EncodePong)(const uint8*, uint8, uint64, uint64, uint8**, unsigned long*) = nullptr;
    int32 (*ApprovePublic)(const uint8*, unsigned long, uint8*) = nullptr;
    int32 (*ApproveSignature)(const uint8*, unsigned long, uint8*) = nullptr;
    FBlob ApproveAccount = nullptr, ApprovePermissions = nullptr, ApproveProof = nullptr;
    FBlob Hash = nullptr, InspectTransaction = nullptr, JoinTermsInspect = nullptr, DecodeEnvelopeJson = nullptr;
    int32 (*VerifyApproval)(const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, const char*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, const char*, unsigned long, const char*, unsigned long, const uint8*, unsigned long) = nullptr;
    int32 (*DeriveKeys)(const uint8*, const uint8*, const uint8*, uint8*, uint8*) = nullptr;
    int32 (*SignRequest)(uint64, const uint8*, unsigned long, uint8**, unsigned long*) = nullptr;
    int32 (*Encrypt)(const uint8*, const uint8*, uint8, const uint8*, unsigned long, uint8**, unsigned long*) = nullptr;
    int32 (*Decrypt)(const uint8*, const uint8*, unsigned long, uint8**, unsigned long*) = nullptr;
    int32 (*EnvelopeKind)(const uint8*, unsigned long, uint64*, uint16*) = nullptr;
    int32 (*Finalize)(const uint8*, unsigned long, const uint8*, unsigned long, const uint8*, unsigned long, uint8**, unsigned long*, uint8**, unsigned long*) = nullptr;
    int32 (*BuildTransaction)(const uint8*, unsigned long, uint8**, unsigned long*, uint8**, unsigned long*) = nullptr;

    ~FArenaConnectNative() { if (Handle) FPlatformProcess::FreeDllHandle(Handle); }
    template <typename T> bool Bind(T& Fn, const TCHAR* Name)
    {
        Fn = reinterpret_cast<T>(FPlatformProcess::GetDllExport(Handle, Name));
        return Fn != nullptr;
    }
    bool Load(const FString& Path)
    {
        Handle = FPlatformProcess::GetDllHandle(*Path);
        if (!Handle || !Bind(Abi, TEXT("connect_norito_bridge_abi_version")) || Abi() != ArenaConnect::BridgeAbi) return false;
#define ARENA_BIND(Field, Symbol) if (!Bind(Field, TEXT(Symbol))) return false
        ARENA_BIND(Free, "connect_norito_free");
        ARENA_BIND(CanonicalJson, "connect_norito_canonical_json_blake3_v1");
        ARENA_BIND(KeyPair, "connect_norito_connect_generate_keypair");
        ARENA_BIND(DeriveSid, "connect_norito_connect_derive_session_id");
        ARENA_BIND(Open, "connect_norito_encode_control_open_ext");
        ARENA_BIND(FrameKind, "connect_norito_decode_control_kind");
        ARENA_BIND(DecodePing, "connect_norito_decode_control_ping");
        ARENA_BIND(EncodePong, "connect_norito_encode_control_pong");
        ARENA_BIND(ApprovePublic, "connect_norito_decode_control_approve_pub");
        ARENA_BIND(ApproveSignature, "connect_norito_decode_control_approve_sig");
        ARENA_BIND(ApproveAccount, "connect_norito_decode_control_approve_account");
        ARENA_BIND(ApprovePermissions, "connect_norito_decode_control_approve_permissions_json");
        ARENA_BIND(ApproveProof, "connect_norito_decode_control_approve_proof_json");
        ARENA_BIND(VerifyApproval, "connect_norito_connect_verify_approval");
        ARENA_BIND(DeriveKeys, "connect_norito_connect_derive_keys");
        ARENA_BIND(Hash, "connect_norito_blake3_hash");
        ARENA_BIND(InspectTransaction, "connect_norito_detached_transaction_scaffold_inspect_v1");
        ARENA_BIND(SignRequest, "connect_norito_encode_envelope_sign_request_tx");
        ARENA_BIND(Encrypt, "connect_norito_connect_encrypt_envelope");
        ARENA_BIND(Decrypt, "connect_norito_connect_decrypt_ciphertext");
        ARENA_BIND(EnvelopeKind, "connect_norito_decode_envelope_kind");
        ARENA_BIND(DecodeEnvelopeJson, "connect_norito_decode_envelope_json");
        ARENA_BIND(Finalize, "connect_norito_detached_transaction_scaffold_finalize_ed25519_v1");
#undef ARENA_BIND
        Bind(BuildTransaction, TEXT("connect_norito_native_transaction_scaffold_build_v1"));
        // Optional research inspector; ABI 23 alone does not prove this symbol is present.
        Bind(JoinTermsInspect, TEXT("connect_norito_arena_join_terms_inspect_v1"));
        return true;
    }
};

namespace
{
struct FNativeBytes
{
    FArenaConnectNative& Api;
    uint8* Data = nullptr;
    unsigned long Size = 0;
    explicit FNativeBytes(FArenaConnectNative& InApi) : Api(InApi) {}
    ~FNativeBytes() { if (Data) Api.Free(Data); }
    FNativeBytes(const FNativeBytes&) = delete;
    FNativeBytes& operator=(const FNativeBytes&) = delete;
    bool Bounded(int32 Limit = ArenaConnect::MaxFrameBytes) const { return Data && Size > 0 && Size <= static_cast<unsigned long>(Limit); }
};
}

UArenaWalletSubsystem::UArenaWalletSubsystem() = default;
UArenaWalletSubsystem::~UArenaWalletSubsystem() = default;

void UArenaWalletSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    StatusText = TEXT("ウォレット未接続。シングルプレイは接続不要です。");
    TransactionStatusText = TEXT("取引はありません。");
    RestorePendingTransactionIdentity();
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UArenaWalletSubsystem::TickSession));
}

void UArenaWalletSubsystem::Deinitialize()
{
    FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
    ClearSubmissionRequests();
    ClearTransport();
    Native.Reset();
    Super::Deinitialize();
}

void UArenaWalletSubsystem::SetState(EArenaWalletState NewState, const FString& Message)
{
    State = NewState;
    StatusText = Message;
    OnStateChanged.Broadcast();
}

void UArenaWalletSubsystem::SetTransactionState(EArenaTransactionState NewState, const FString& Message)
{
    TransactionState = NewState;
    TransactionStatusText = Message;
    OnTransactionStateChanged.Broadcast();
}

void UArenaWalletSubsystem::RestorePendingTransactionIdentity()
{
    TArray<FString> Files;
    ArenaConnect::RecoveryFiles(Files);
    if (Files.IsEmpty()) return;
    FString PinnedOrigin, PinnedNetwork;
    ArenaTransactionRecovery::Record Identity;
    if (!ArenaConnect::ReadIsolatedTestConfig(PinnedOrigin, PinnedNetwork)
        || ArenaConnect::ReadRecovery(PinnedOrigin, PinnedNetwork, Identity) != ArenaConnect::ERecoveryRead::Valid)
    {
        bRecoveryBlocked = true;
        SetTransactionState(EArenaTransactionState::Uncertain,
            TEXT("保存された取引IDまたは隔離テスト網の設定が一致しません。送信と照会を停止しました。"));
        return;
    }
    SubmissionOrigin = UTF8_TO_TCHAR(Identity.Origin.c_str());
    SubmissionNetworkLiteral = UTF8_TO_TCHAR(Identity.NetworkId.c_str());
    LastSignedTransactionHash = UTF8_TO_TCHAR(Identity.TransactionHash.c_str());
    LastEntrypointHash = UTF8_TO_TCHAR(Identity.EntrypointHash.c_str());
    ArenaConnect::Erase(LastSignedTransactionBase64);
    // The pre-dispatch record also covers a crash before Torii sees the POST.
    // Restored acceptance is therefore unknown until a fresh exact-hash query.
    SetTransactionState(EArenaTransactionState::Uncertain,
        TEXT("隔離テスト網の取引IDを復元しました。再送せず、取引IDから状態を照会できます。"));
}

bool UArenaWalletSubsystem::IsRecoveryIdentityCurrent() const
{
    FString PinnedOrigin, PinnedNetwork;
    if (bRecoveryBlocked || !ArenaConnect::ReadIsolatedTestConfig(PinnedOrigin, PinnedNetwork)
        || SubmissionOrigin != PinnedOrigin || SubmissionNetworkLiteral != PinnedNetwork
        || !ArenaConnect::CanonicalHash(LastSignedTransactionHash)
        || !ArenaConnect::CanonicalHash(LastEntrypointHash)) return false;
    ArenaTransactionRecovery::Record Identity;
    return ArenaConnect::ReadRecovery(PinnedOrigin, PinnedNetwork, Identity) == ArenaConnect::ERecoveryRead::Valid
        && Identity.TransactionHash == ArenaConnect::Utf8String(LastSignedTransactionHash)
        && Identity.EntrypointHash == ArenaConnect::Utf8String(LastEntrypointHash);
}

void UArenaWalletSubsystem::ClearSubmissionRequests()
{
    ++TransactionGeneration;
    NextStatusPollAt = 0;
    for (TSharedPtr<IHttpRequest, ESPMode::ThreadSafe>* Request : {&SubmissionRequest, &StatusRequest})
    {
        if (!Request->IsValid()) continue;
        (*Request)->OnProcessRequestComplete().Unbind();
        (*Request)->OnRequestProgress().Unbind();
        (*Request)->CancelRequest();
        Request->Reset();
    }
}

void UArenaWalletSubsystem::ClearTransport()
{
    ++Generation;
    Deadline = 0;
    if (SessionRequest.IsValid())
    {
        SessionRequest->OnProcessRequestComplete().Unbind();
        SessionRequest->OnRequestProgress().Unbind();
        SessionRequest->CancelRequest();
        SessionRequest.Reset();
    }
    if (Socket.IsValid())
    {
        Socket->OnConnected().Clear();
        Socket->OnConnectionError().Clear();
        Socket->OnClosed().Clear();
        Socket->OnRawMessage().Clear();
        Socket->OnMessage().Clear();
        Socket->Close(1000, TEXT("Session ended"));
        Socket.Reset();
    }
    ArenaConnect::Erase(AppPrivateKey);
    ArenaConnect::Erase(AppDirectionKey);
    ArenaConnect::Erase(WalletDirectionKey);
    ArenaConnect::Erase(RelayToken);
    ArenaConnect::Erase(WalletLaunchUri);
    ClearWalletQr();
    ArenaConnect::Erase(PendingScaffold);
    ArenaConnect::Erase(PendingSignatory);
    bIgnoreCancelledSignatureResult = false;
    IncomingFrame.Empty();
    SessionId.Empty();
    AppPublicKey.Empty();
    Nonce.Empty();
    ApprovedAccount.Empty();
    PendingTransactionSummary.Empty();
    ArenaConnect::Erase(LastSignedTransactionBase64);
    if (TransactionState == EArenaTransactionState::AwaitingSignature || TransactionState == EArenaTransactionState::Signed)
    {
        LastSignedTransactionHash.Empty();
        LastEntrypointHash.Empty();
        SubmissionOrigin.Empty();
        SubmissionNetworkLiteral.Empty();
        SetTransactionState(EArenaTransactionState::Cancelled, TEXT("ウォレット接続の終了により未送信の取引を破棄しました。"));
    }
    AppSequence = WalletSequence = 1;
}

void UArenaWalletSubsystem::Fail(const FString& Message, EArenaWalletState FailureState)
{
    ClearTransport();
    SetState(FailureState, Message);
}

bool UArenaWalletSubsystem::TickSession(float DeltaTime)
{
    if (Deadline > 0 && FPlatformTime::Seconds() > Deadline)
        Fail(TEXT("接続または署名の待ち時間を超えました。再接続してください。"));
    if (NextStatusPollAt > 0 && FPlatformTime::Seconds() >= NextStatusPollAt)
    {
        NextStatusPollAt = 0;
        PollTransactionStatus();
    }
    return true;
}

bool UArenaWalletSubsystem::LoadNativeBridge()
{
    if (Native) return true;
    FString Path = FPlatformMisc::GetEnvironmentVariable(TEXT("SORA_CONNECT_BRIDGE"));
    if (Path.IsEmpty())
    {
#if PLATFORM_MAC
        Path = FPaths::Combine(FPaths::ProjectDir(), TEXT("Binaries/Mac/libconnect_norito_bridge.dylib"));
#elif PLATFORM_WINDOWS
        Path = FPaths::Combine(FPaths::ProjectDir(), TEXT("Binaries/Win64/connect_norito_bridge.dll"));
#elif PLATFORM_LINUX
        Path = FPaths::Combine(FPaths::ProjectDir(), TEXT("Binaries/Linux/libconnect_norito_bridge.so"));
#else
        Fail(TEXT("この環境ではウォレット接続を利用できません。"), EArenaWalletState::Unavailable);
        return false;
#endif
    }
    auto Candidate = MakeUnique<FArenaConnectNative>();
    if (!Candidate->Load(FPaths::ConvertRelativePathToFull(Path)))
    {
        Fail(TEXT("署名検証用のネイティブライブラリがありません。オンライン決済は利用できません。"), EArenaWalletState::Unavailable);
        return false;
    }
    Native = MoveTemp(Candidate);
    return true;
}

void UArenaWalletSubsystem::BeginPairingFromConfig()
{
    FString Torii, Network, Account;
    GConfig->GetString(TEXT("Arena.Connect"), TEXT("ToriiOrigin"), Torii, GGameIni);
    GConfig->GetString(TEXT("Arena.Connect"), TEXT("NetworkId"), Network, GGameIni);
    GConfig->GetString(TEXT("Arena.Connect"), TEXT("ExpectedAccount"), Account, GGameIni);
    BeginPairing(Torii, Network, Account);
}

void UArenaWalletSubsystem::BeginPairing(const FString& ToriiOrigin, const FString& CanonicalNetworkId, const FString& ExpectedAccount)
{
    ClearTransport();
    if (!ArenaConnect::NormalizeOrigin(ToriiOrigin, Origin) || !ArenaConnect::ParseNetworkId(CanonicalNetworkId, NetworkBytes))
    {
        Fail(TEXT("接続先とネットワーク識別子を設定してください。公開接続には HTTPS が必要です。"));
        return;
    }
    NetworkLiteral = CanonicalNetworkId;
    ExpectedAccountLiteral = ExpectedAccount;
    if (!LoadNativeBridge()) return;
    AppPublicKey.SetNumZeroed(32);
    AppPrivateKey.SetNumZeroed(32);
    SessionId.SetNumZeroed(32);
    TArray<uint8> EntropyPublic, EntropyPrivate;
    EntropyPublic.SetNumZeroed(32);
    EntropyPrivate.SetNumZeroed(32);
    if (Native->KeyPair(AppPublicKey.GetData(), AppPrivateKey.GetData()) != 0 || Native->KeyPair(EntropyPublic.GetData(), EntropyPrivate.GetData()) != 0)
    {
        ArenaConnect::Erase(EntropyPrivate);
        Fail(TEXT("安全な接続鍵を作成できませんでした。")); return;
    }
    // Independent OS-random bridge key material, hashed before taking a 16-byte launch nonce.
    FNativeBytes NonceHash(*Native);
    const int32 HashResult = Native->Hash(EntropyPrivate.GetData(), 32, &NonceHash.Data, &NonceHash.Size);
    ArenaConnect::Erase(EntropyPrivate);
    if (HashResult != 0 || NonceHash.Size != 32 || !NonceHash.Data)
    { Fail(TEXT("接続識別子を作成できませんでした。")); return; }
    Nonce.Append(NonceHash.Data, 16);
    if (Native->DeriveSid(NetworkBytes.GetData(), 32, AppPublicKey.GetData(), 32, Nonce.GetData(), 16, SessionId.GetData(), 32) != 0)
    { Fail(TEXT("ネットワーク識別子を検証できませんでした。")); return; }

    auto Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("sid"), ArenaConnect::Base64Url(SessionId));
    Body->SetStringField(TEXT("network_id"), NetworkLiteral);
    Body->SetStringField(TEXT("app_pk"), ArenaConnect::Base64Url(AppPublicKey));
    Body->SetStringField(TEXT("nonce"), ArenaConnect::Base64Url(Nonce));
    Body->SetStringField(TEXT("node"), Origin);
    FString BodyText;
    FJsonSerializer::Serialize(Body, TJsonWriterFactory<>::Create(&BodyText));
    SessionRequest = FHttpModule::Get().CreateRequest();
    SessionRequest->SetURL(Origin + TEXT("/v1/connect/session"));
    SessionRequest->SetVerb(TEXT("POST"));
    SessionRequest->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    SessionRequest->SetHeader(TEXT("Accept"), TEXT("application/json"));
    SessionRequest->SetContentAsString(BodyText);
    SessionRequest->SetTimeout(20.0f);
    const uint64 Attempt = Generation;
    TWeakObjectPtr<UArenaWalletSubsystem> Weak(this);
    SessionRequest->OnRequestProgress().BindLambda([Weak, Attempt](FHttpRequestPtr Request, int32, int32 Received)
    {
        if (Received <= ArenaConnect::MaxSessionJsonBytes) return;
        Request->CancelRequest();
        AsyncTask(ENamedThreads::GameThread, [Weak, Attempt]()
        { if (Weak.IsValid() && Weak->Generation == Attempt) Weak->Fail(TEXT("接続応答が上限を超えました。")); });
    });
    SessionRequest->OnProcessRequestComplete().BindLambda([Weak, Attempt](FHttpRequestPtr Request, FHttpResponsePtr Response, bool Success)
    {
        AsyncTask(ENamedThreads::GameThread, [Weak, Attempt, Request, Response, Success]()
        {
            if (!Weak.IsValid() || Weak->Generation != Attempt) return;
            if (!Success || !Response.IsValid() || Response->GetResponseCode() != 200 || Response->GetURL() != Request->GetURL() || Response->GetContent().Num() > ArenaConnect::MaxSessionJsonBytes)
            { Weak->Fail(TEXT("接続サービスから有効な応答を受信できませんでした。")); return; }
            // Do not retain the HTTP response and its launch tokens for the session lifetime.
            Weak->SessionRequest.Reset();
            Weak->AcceptSessionResponse(Response->GetContent());
        });
    });
    Deadline = FPlatformTime::Seconds() + 120;
    SetState(EArenaWalletState::CreatingSession, TEXT("ウォレット接続を準備しています…"));
    if (Generation != Attempt || !SessionRequest.IsValid()) return;
    if (!SessionRequest->ProcessRequest()) Fail(TEXT("接続リクエストを開始できませんでした。"));
}

void UArenaWalletSubsystem::AcceptSessionResponse(const TArray<uint8>& JsonBytes)
{
    if (State != EArenaWalletState::CreatingSession || !Native || JsonBytes.IsEmpty()) return;
    FNativeBytes Canonical(*Native);
    uint8 Digest[32] = {};
    TSharedPtr<FJsonObject> Json;
    if (Native->CanonicalJson(JsonBytes.GetData(), JsonBytes.Num(), &Canonical.Data, &Canonical.Size, Digest, 32) != 0 || !Canonical.Bounded(ArenaConnect::MaxSessionJsonBytes) || !ArenaConnect::ParseObject(Canonical.Data, Canonical.Size, Json) || Json->Values.Num() != 10)
    { Fail(TEXT("接続応答の形式を検証できませんでした。")); return; }
    const TCHAR* Fields[] = {TEXT("sid"), TEXT("network_id"), TEXT("app_pk"), TEXT("nonce"), TEXT("wallet_uri"), TEXT("app_uri"), TEXT("token_app"), TEXT("token_wallet"), TEXT("token_management"), TEXT("token_relay")};
    TMap<FString, FString> Values;
    for (const TCHAR* Field : Fields)
    {
        FString Value;
        if (!Json->TryGetStringField(Field, Value)) { Fail(TEXT("接続応答に必要な情報がありません。")); return; }
        Values.Add(Field, Value);
    }
    if (Values[TEXT("sid")] != ArenaConnect::Base64Url(SessionId) || Values[TEXT("network_id")] != NetworkLiteral || Values[TEXT("app_pk")] != ArenaConnect::Base64Url(AppPublicKey) || Values[TEXT("nonce")] != ArenaConnect::Base64Url(Nonce))
    { Fail(TEXT("接続先がセッション識別子を書き換えました。接続を中止しました。")); return; }
    for (const TCHAR* Key : {TEXT("token_app"), TEXT("token_wallet"), TEXT("token_management"), TEXT("token_relay")})
    {
        TArray<uint8> Decoded;
        if (!ArenaConnect::DecodeBase64Url(Values[Key], 32, Decoded)) { Fail(TEXT("接続トークンの形式が不正です。")); return; }
        ArenaConnect::Erase(Decoded);
    }
    TMap<FString, FString> Expected = {{TEXT("sid"), Values[TEXT("sid")]}, {TEXT("network_id"), NetworkLiteral}, {TEXT("app_pk"), Values[TEXT("app_pk")]}, {TEXT("nonce"), Values[TEXT("nonce")]}, {TEXT("node"), Origin}, {TEXT("v"), TEXT("1")}, {TEXT("role"), TEXT("wallet")}, {TEXT("token"), Values[TEXT("token_wallet")]}, {TEXT("relay"), Values[TEXT("token_relay")]}};
    if (!ArenaConnect::MatchLaunchUri(Values[TEXT("wallet_uri")], Expected)) { Fail(TEXT("ウォレット起動リンクの内容が一致しません。")); return; }
    Expected[TEXT("role")] = TEXT("app");
    Expected[TEXT("token")] = Values[TEXT("token_app")];
    if (!ArenaConnect::MatchLaunchUri(Values[TEXT("app_uri")], Expected)) { Fail(TEXT("アプリ起動リンクの内容が一致しません。")); return; }
    WalletLaunchUri = Values[TEXT("wallet_uri")];
    BuildWalletQr();
    RelayToken = Values[TEXT("token_relay")];
    FString WsOrigin = Origin.StartsWith(TEXT("https://")) ? TEXT("wss://") + Origin.Mid(8) : TEXT("ws://") + Origin.Mid(7);
    TMap<FString, FString> Headers = {{TEXT("Authorization"), TEXT("Bearer ") + Values[TEXT("token_app")]}};
    Socket = FWebSocketsModule::Get().CreateWebSocket(WsOrigin + TEXT("/v1/connect/ws?sid=") + Values[TEXT("sid")] + TEXT("&role=app"), FString(), Headers);
    const uint64 Attempt = Generation;
    TWeakObjectPtr<UArenaWalletSubsystem> Weak(this);
    Socket->OnConnected().AddLambda([Weak, Attempt]() { AsyncTask(ENamedThreads::GameThread, [Weak, Attempt]() { if (Weak.IsValid() && Weak->Generation == Attempt) Weak->SendOpen(); }); });
    Socket->OnConnectionError().AddLambda([Weak, Attempt](const FString&) { AsyncTask(ENamedThreads::GameThread, [Weak, Attempt]() { if (Weak.IsValid() && Weak->Generation == Attempt) Weak->Fail(TEXT("ウォレット通信を開始できませんでした。")); }); });
    Socket->OnClosed().AddLambda([Weak, Attempt](int32, const FString&, bool) { AsyncTask(ENamedThreads::GameThread, [Weak, Attempt]() { if (Weak.IsValid() && Weak->Generation == Attempt) Weak->Fail(TEXT("ウォレットとの接続が閉じられました。"), EArenaWalletState::Disconnected); }); });
    Socket->SetTextMessageMemoryLimit(1024);
    Socket->OnMessage().AddLambda([Weak, Attempt](const FString&) { AsyncTask(ENamedThreads::GameThread, [Weak, Attempt]() { if (Weak.IsValid() && Weak->Generation == Attempt) Weak->Fail(TEXT("未対応のウォレット通信を受信しました。")); }); });
    const auto Ingress = MakeShared<ArenaConnect::FIngressBudget, ESPMode::ThreadSafe>();
    Socket->OnRawMessage().AddLambda([Weak, Attempt, Ingress](const void* Data, SIZE_T Size, SIZE_T Remaining)
    {
        if (Ingress->Stopped.load()) return;
        auto Stop = [&]()
        {
            if (!Ingress->Stopped.exchange(true))
                AsyncTask(ENamedThreads::GameThread, [Weak, Attempt]() { if (Weak.IsValid() && Weak->Generation == Attempt) Weak->Fail(TEXT("ウォレット通信が上限を超えました。")); });
        };
        if (Size > ArenaConnect::MaxFrameBytes || Remaining > ArenaConnect::MaxFrameBytes || Size + Remaining > ArenaConnect::MaxFrameBytes)
        { Stop(); return; }
        const int32 Count = static_cast<int32>(Size);
        const int32 PreviousBytes = Ingress->Bytes.fetch_add(Count);
        const int32 PreviousFragments = Ingress->Fragments.fetch_add(1);
        if (PreviousBytes > 2 * ArenaConnect::MaxFrameBytes - Count || PreviousFragments >= 256)
        {
            Ingress->Bytes.fetch_sub(Count);
            Ingress->Fragments.fetch_sub(1);
            Stop(); return;
        }
        TArray<uint8> Copy;
        Copy.Append(static_cast<const uint8*>(Data), Count);
        AsyncTask(ENamedThreads::GameThread, [Weak, Attempt, Ingress, Copy = MoveTemp(Copy), Count, Remaining]() mutable
        {
            Ingress->Bytes.fetch_sub(Count);
            Ingress->Fragments.fetch_sub(1);
            if (!Ingress->Stopped.load() && Weak.IsValid() && Weak->Generation == Attempt) Weak->ReceiveFragment(MoveTemp(Copy), Remaining);
        });
    });
    SetState(EArenaWalletState::Connecting, TEXT("ウォレットとの暗号化接続を開いています…"));
    if (Generation != Attempt || !Socket.IsValid()) return;
    Socket->Connect();
}

void UArenaWalletSubsystem::SendOpen()
{
    if (State != EArenaWalletState::Connecting || !Native || !Socket.IsValid()) return;
    auto Metadata = ArenaConnect::Utf8(TEXT("{\"name\":\"SORA Arena\",\"url\":null,\"icon_hash\":null}"));
    auto Permissions = ArenaConnect::Utf8(ArenaConnect::Permissions);
    FNativeBytes Frame(*Native);
    if (Native->Open(SessionId.GetData(), 0, AppSequence, AppPublicKey.GetData(), 32, Nonce.GetData(), 16, Metadata.GetData(), Metadata.Num(), NetworkBytes.GetData(), 32, Permissions.GetData(), Permissions.Num(), &Frame.Data, &Frame.Size) != 0 || !Frame.Bounded())
    { Fail(TEXT("ウォレット接続メッセージを作成できませんでした。")); return; }
    ++AppSequence;
    const uint64 Attempt = Generation;
    SetState(EArenaWalletState::AwaitingApproval, TEXT("ウォレットで接続内容を確認してください。接続だけでは XOR は移動しません。"));
    if (Generation != Attempt || !Socket.IsValid()) return;
    Socket->Send(Frame.Data, Frame.Size, true);
}

void UArenaWalletSubsystem::LaunchWallet()
{
    if (State != EArenaWalletState::AwaitingApproval || WalletLaunchUri.IsEmpty()) return;
    FString Error;
    FPlatformProcess::LaunchURL(*WalletLaunchUri, nullptr, &Error);
    if (!Error.IsEmpty()) SetState(State, TEXT("対応ウォレットを開けません。ウォレットをインストールして再度お試しください。"));
}

void UArenaWalletSubsystem::BuildWalletQr()
{
    ClearWalletQr();
    // Called only after every Torii launch-URI field has been validated.
    if (WalletLaunchUri.IsEmpty()) return;
    FTCHARToUTF8 Text(*WalletLaunchUri);
    if (Text.Length() > 2048) return;
    TArray<uint8> Scratch, Code;
    Scratch.SetNumZeroed(qrcodegen_BUFFER_LEN_MAX);
    Code.SetNumZeroed(qrcodegen_BUFFER_LEN_MAX);
    const bool Encoded = qrcodegen_encodeText(Text.Get(), Scratch.GetData(), Code.GetData(), qrcodegen_Ecc_MEDIUM,
        qrcodegen_VERSION_MIN, qrcodegen_VERSION_MAX, qrcodegen_Mask_AUTO, true);
    ArenaConnect::Erase(Scratch);
    if (!Encoded) { ArenaConnect::Erase(Code); return; }
    const int32 Modules = qrcodegen_getSize(Code.GetData());
    constexpr int32 Border = 4; // Required quiet zone, included in the texture.
    const int32 Side = Modules + Border * 2;
    UTexture2D* Texture = UTexture2D::CreateTransient(Side, Side, PF_B8G8R8A8);
    if (!Texture) { ArenaConnect::Erase(Code); return; }
    Texture->Filter = TF_Nearest;
    Texture->SRGB = false;
    Texture->NeverStream = true;
    Texture->AddressX = Texture->AddressY = TA_Clamp;
    FTexture2DMipMap& Mip = Texture->GetPlatformData()->Mips[0];
    FColor* Pixels = static_cast<FColor*>(Mip.BulkData.Lock(LOCK_READ_WRITE));
    for (int32 Y = 0; Y < Side; ++Y)
        for (int32 X = 0; X < Side; ++X)
        {
            const bool Dark = X >= Border && Y >= Border && X < Border + Modules && Y < Border + Modules && qrcodegen_getModule(Code.GetData(), X - Border, Y - Border);
            Pixels[Y * Side + X] = Dark ? FColor::Black : FColor::White;
        }
    Mip.BulkData.Unlock();
    ArenaConnect::Erase(Code);
    WalletQrTexture = Texture;
    Texture->UpdateResource();
}

void UArenaWalletSubsystem::ClearWalletQr()
{
    if (WalletQrTexture && WalletQrTexture->GetPlatformData() && !WalletQrTexture->GetPlatformData()->Mips.IsEmpty())
    {
        FTexture2DMipMap& Mip = WalletQrTexture->GetPlatformData()->Mips[0];
        void* Pixels = Mip.BulkData.Lock(LOCK_READ_WRITE);
        FMemory::Memset(Pixels, 255, static_cast<SIZE_T>(Mip.BulkData.GetBulkDataSize()));
        Mip.BulkData.Unlock();
        WalletQrTexture->UpdateResource();
    }
    WalletQrTexture = nullptr;
}

void UArenaWalletSubsystem::DisconnectWallet()
{
    ClearTransport();
    SetState(EArenaWalletState::Disconnected, TEXT("ウォレットを切断しました。"));
}

void UArenaWalletSubsystem::ReceiveFragment(TArray<uint8> Bytes, SIZE_T BytesRemaining)
{
    if (IncomingFrame.Num() + Bytes.Num() > ArenaConnect::MaxFrameBytes || BytesRemaining > static_cast<SIZE_T>(ArenaConnect::MaxFrameBytes - IncomingFrame.Num() - Bytes.Num()))
    { Fail(TEXT("ウォレット通信が上限を超えました。")); return; }
    IncomingFrame.Append(Bytes);
    if (BytesRemaining == 0)
    {
        TArray<uint8> Frame = MoveTemp(IncomingFrame);
        IncomingFrame.Empty();
        ReceiveFrame(Frame);
    }
}

void UArenaWalletSubsystem::ReceiveFrame(const TArray<uint8>& Frame)
{
    if (!Native || Frame.IsEmpty()) { Fail(TEXT("ウォレット通信が不正です。")); return; }
    uint8 Sid[32] = {}, Direction = 255;
    uint64 Sequence = 0;
    uint16 Kind = 0;
    if (Native->FrameKind(Frame.GetData(), Frame.Num(), Sid, &Direction, &Sequence, &Kind) != 0 || SessionId.Num() != 32 || FMemory::Memcmp(Sid, SessionId.GetData(), 32) != 0 || Direction != 1)
    { Fail(TEXT("別セッションまたは不正なウォレット通信を拒否しました。")); return; }
    if (Kind == 7) return; // Relay server events are not wallet approvals or finality evidence.
    if (Sequence != WalletSequence || WalletSequence == MAX_uint64)
    { Fail(TEXT("重複または順序の異なるウォレット通信を拒否しました。")); return; }
    if (Kind == 5 && (State == EArenaWalletState::AwaitingApproval || State == EArenaWalletState::Approved || State == EArenaWalletState::AwaitingSignature || State == EArenaWalletState::Signed))
    {
        uint64 PingNonce = 0;
        FNativeBytes Pong(*Native);
        if (AppSequence == MAX_uint64 || !Socket.IsValid() || Native->DecodePing(Frame.GetData(), Frame.Num(), &PingNonce) != 0 || Native->EncodePong(SessionId.GetData(), 0, AppSequence, PingNonce, &Pong.Data, &Pong.Size) != 0 || !Pong.Bounded())
        { Fail(TEXT("接続確認メッセージが不正です。")); return; }
        ++WalletSequence;
        ++AppSequence;
        Socket->Send(Pong.Data, Pong.Size, true);
        return;
    }
    if (Kind == 2 && State == EArenaWalletState::AwaitingApproval) { AcceptApproval(Frame); return; }
    if ((Kind == 3 || Kind == 4) && State == EArenaWalletState::AwaitingApproval)
    { Fail(TEXT("ウォレットで接続が拒否または終了されました。"), EArenaWalletState::Disconnected); return; }
    if (Kind == 100 && (State == EArenaWalletState::Approved || State == EArenaWalletState::AwaitingSignature || State == EArenaWalletState::Signed))
    { ReceiveEncrypted(Frame, Sequence); return; }
    Fail(TEXT("現在の接続状態では受け付けられない通信です。"));
}

void UArenaWalletSubsystem::AcceptApproval(const TArray<uint8>& Frame)
{
    FNativeBytes Account(*Native), Permissions(*Native), Proof(*Native);
    uint8 WalletPublic[32] = {}, Signature[64] = {};
    if (Native->ApprovePublic(Frame.GetData(), Frame.Num(), WalletPublic) != 0 || Native->ApproveSignature(Frame.GetData(), Frame.Num(), Signature) != 0 || Native->ApproveAccount(Frame.GetData(), Frame.Num(), &Account.Data, &Account.Size) != 0 || !Account.Bounded(512) || Native->ApprovePermissions(Frame.GetData(), Frame.Num(), &Permissions.Data, &Permissions.Size) != 0 || !Permissions.Bounded(4096) || Native->ApproveProof(Frame.GetData(), Frame.Num(), &Proof.Data, &Proof.Size) != 0 || !Proof.Bounded(4096))
    { Fail(TEXT("ウォレット承認を読み取れませんでした。")); return; }
    const FString AccountText = ArenaConnect::Text(Account.Data, Account.Size);
    TSharedPtr<FJsonObject> Perms, ProofObject;
    const TArray<TSharedPtr<FJsonValue>>* Methods = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Events = nullptr;
    if ((!ExpectedAccountLiteral.IsEmpty() && AccountText != ExpectedAccountLiteral) || !ArenaConnect::ParseObject(Permissions.Data, Permissions.Size, Perms) || Perms->Values.Num() != 3 || !Perms->TryGetArrayField(TEXT("methods"), Methods) || Methods->Num() != 1 || (*Methods)[0]->Type != EJson::String || (*Methods)[0]->AsString() != TEXT("SIGN_REQUEST_TX") || !Perms->TryGetArrayField(TEXT("events"), Events) || !Events->IsEmpty() || !Perms->HasTypedField<EJson::Null>(TEXT("resources")) || !ArenaConnect::ParseObject(Proof.Data, Proof.Size, ProofObject) || !ProofObject->Values.IsEmpty())
    { Fail(TEXT("ウォレットのアカウントまたは許可内容が要求と一致しません。")); return; }
    auto Relay = ArenaConnect::Utf8(RelayToken);
    const int32 Verified = Native->VerifyApproval(NetworkBytes.GetData(), 32, SessionId.GetData(), 32, AppPublicKey.GetData(), 32, Nonce.GetData(), 16, WalletPublic, 32, reinterpret_cast<const char*>(Account.Data), Account.Size, Permissions.Data, Permissions.Size, nullptr, 0, reinterpret_cast<const char*>(Relay.GetData()), Relay.Num(), "ed25519", 7, Signature, 64);
    ArenaConnect::Erase(Relay);
    if (Verified != 0) { Fail(TEXT("ウォレット承認の署名を検証できませんでした。")); return; }
    AppDirectionKey.SetNumZeroed(32);
    WalletDirectionKey.SetNumZeroed(32);
    if (Native->DeriveKeys(AppPrivateKey.GetData(), WalletPublic, SessionId.GetData(), AppDirectionKey.GetData(), WalletDirectionKey.GetData()) != 0)
    { Fail(TEXT("暗号化通信の鍵を確立できませんでした。")); return; }
    ArenaConnect::Erase(AppPrivateKey);
    ArenaConnect::Erase(RelayToken);
    ArenaConnect::Erase(WalletLaunchUri);
    ClearWalletQr();
    ApprovedAccount = AccountText;
    ++WalletSequence;
    Deadline = 0;
    SetState(EArenaWalletState::Approved, TEXT("ウォレット署名を確認しました。ボンド残高とゲーム参加は別途検証が必要です。"));
}

bool UArenaWalletSubsystem::RequestSignTransaction(const FString& ScaffoldBase64, const FString& Ed25519PublicKeyHex)
{
    if (!Native || !Socket.IsValid() || !Socket->IsConnected() || bIgnoreCancelledSignatureResult || bRecoveryBlocked
        || TransactionState == EArenaTransactionState::Submitting || TransactionState == EArenaTransactionState::Pending
        || TransactionState == EArenaTransactionState::Uncertain
        || (State != EArenaWalletState::Approved && State != EArenaWalletState::Signed)) return false;
    TArray<uint8> Scaffold, Signatory, Payload;
    if (ScaffoldBase64.Len() > ArenaConnect::MaxFrameBytes * 2 || !FBase64::Decode(ScaffoldBase64, Scaffold) || Scaffold.IsEmpty() || Scaffold.Num() > ArenaConnect::MaxFrameBytes || FBase64::Encode(Scaffold) != ScaffoldBase64 || !ArenaConnect::DecodeHex(Ed25519PublicKeyHex, 32, Signatory))
    { SetState(State, TEXT("署名対象の形式が不正です。")); return false; }
    FNativeBytes Inspected(*Native);
    TSharedPtr<FJsonObject> Json;
    if (Native->InspectTransaction(Scaffold.GetData(), Scaffold.Num(), &Inspected.Data, &Inspected.Size) != 0 || !Inspected.Bounded() || !ArenaConnect::ParseObject(Inspected.Data, Inspected.Size, Json))
    { SetState(State, TEXT("署名対象をネイティブ検証できませんでした。")); return false; }
    FString Schema, Authority, Network, PayloadBase64, Kind, Name;
    const TSharedPtr<FJsonObject>* Executable = nullptr;
    if (!Json->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("iroha.detached_transaction_scaffold.v1") || !Json->TryGetStringField(TEXT("authority"), Authority) || Authority != ApprovedAccount || !Json->TryGetStringField(TEXT("network_id"), Network) || Network != NetworkLiteral || !Json->TryGetStringField(TEXT("payload_bytes_b64"), PayloadBase64) || !FBase64::Decode(PayloadBase64, Payload) || Payload.IsEmpty() || Payload.Num() > ArenaConnect::MaxFrameBytes || FBase64::Encode(Payload) != PayloadBase64 || !Json->TryGetObjectField(TEXT("executable"), Executable) || !(*Executable)->TryGetStringField(TEXT("kind"), Kind) || Kind != TEXT("native_instruction") || !(*Executable)->TryGetStringField(TEXT("name"), Name) || !ArenaConnect::IsAllowedInstruction(Name) || AppSequence == MAX_uint64)
    { SetState(State, TEXT("アカウント・ネットワーク・取引種別が一致しないため署名を中止しました。")); return false; }
    if (ArenaConnect::RequiresQualifiedTermsReview(Name))
    {
        SetState(State, Name == TEXT("JoinGameSessionV1")
            ? TEXT("参加ボンドの条件を確認できません。対戦規則・固定損失額・装備予約・手数料を表示できるまで参加署名を停止します。")
            : TEXT("NFT の売却条件と所有状態を確認できません。購入署名を停止します。"));
        return false;
    }
    FNativeBytes Envelope(*Native), Ciphertext(*Native);
    if (Native->SignRequest(AppSequence, Payload.GetData(), Payload.Num(), &Envelope.Data, &Envelope.Size) != 0 || !Envelope.Bounded() || Native->Encrypt(AppDirectionKey.GetData(), SessionId.GetData(), 0, Envelope.Data, Envelope.Size, &Ciphertext.Data, &Ciphertext.Size) != 0 || !Ciphertext.Bounded())
    { Fail(TEXT("暗号化された署名依頼を作成できませんでした。")); return false; }
    ++AppSequence;
    ClearSubmissionRequests();
    PendingScaffold = MoveTemp(Scaffold);
    PendingSignatory = MoveTemp(Signatory);
    PendingTransactionSummary = ArenaConnect::Text(Inspected.Data, Inspected.Size);
    ArenaConnect::Erase(LastSignedTransactionBase64);
    LastSignedTransactionHash.Empty();
    LastEntrypointHash.Empty();
    SubmissionOrigin.Empty();
    SubmissionNetworkLiteral.Empty();
    Deadline = FPlatformTime::Seconds() + 90;
    const uint64 Attempt = Generation;
    SetTransactionState(EArenaTransactionState::AwaitingSignature, TEXT("ウォレットの署名を待っています。"));
    if (Generation != Attempt || TransactionState != EArenaTransactionState::AwaitingSignature) return false;
    SetState(EArenaWalletState::AwaitingSignature, TEXT("ウォレットで取引内容と XOR 数量を確認してください。署名待ちです。"));
    if (Generation != Attempt || TransactionState != EArenaTransactionState::AwaitingSignature || !Socket.IsValid()) return false;
    Socket->Send(Ciphertext.Data, Ciphertext.Size, true);
    return true;
}

bool UArenaWalletSubsystem::RequestNativeTransactionSignature(const FString& ExactRequestJson, const FString& Ed25519PublicKeyHex)
{
    if (!Native || (State != EArenaWalletState::Approved && State != EArenaWalletState::Signed)) return false;
    if (!Native->BuildTransaction)
    { SetState(State, TEXT("取引作成用のネイティブ機能がありません。接続ライブラリを更新してください。")); return false; }
    auto Request = ArenaConnect::Utf8(ExactRequestJson);
    if (Request.IsEmpty() || Request.Num() > ArenaConnect::MaxFrameBytes) return false;
    FNativeBytes Scaffold(*Native), Inspection(*Native);
    if (Native->BuildTransaction(Request.GetData(), Request.Num(), &Scaffold.Data, &Scaffold.Size, &Inspection.Data, &Inspection.Size) != 0 || !Scaffold.Bounded())
    { SetState(State, TEXT("取引条件が不足しているか不正です。署名依頼を作成しませんでした。")); return false; }
    return RequestSignTransaction(FBase64::Encode(Scaffold.Data, static_cast<uint32>(Scaffold.Size)), Ed25519PublicKeyHex);
}

void UArenaWalletSubsystem::ReceiveEncrypted(const TArray<uint8>& Frame, uint64 Sequence)
{
    FNativeBytes Envelope(*Native), JsonBytes(*Native);
    uint64 InnerSequence = 0;
    uint16 Kind = 0;
    TSharedPtr<FJsonObject> Json;
    if (WalletDirectionKey.Num() != 32 || Native->Decrypt(WalletDirectionKey.GetData(), Frame.GetData(), Frame.Num(), &Envelope.Data, &Envelope.Size) != 0 || !Envelope.Bounded() || Native->EnvelopeKind(Envelope.Data, Envelope.Size, &InnerSequence, &Kind) != 0 || InnerSequence != Sequence || Native->DecodeEnvelopeJson(Envelope.Data, Envelope.Size, &JsonBytes.Data, &JsonBytes.Size) != 0 || !JsonBytes.Bounded() || !ArenaConnect::ParseObject(JsonBytes.Data, JsonBytes.Size, Json))
    { Fail(TEXT("暗号化通信の整合性を検証できませんでした。")); return; }
    const TSharedPtr<FJsonObject>* Payload = nullptr;
    if (!Json->TryGetObjectField(TEXT("payload"), Payload)) { Fail(TEXT("署名応答が不正です。")); return; }
    if ((*Payload)->HasField(TEXT("Control"))) { Fail(TEXT("ウォレットが接続または取引を終了しました。"), EArenaWalletState::Disconnected); return; }
    if (bIgnoreCancelledSignatureResult && State == EArenaWalletState::Approved
        && ((*Payload)->HasField(TEXT("SignResultOk")) || (*Payload)->HasField(TEXT("SignResultErr"))))
    {
        ++WalletSequence;
        bIgnoreCancelledSignatureResult = false;
        return;
    }
    if (State != EArenaWalletState::AwaitingSignature || PendingScaffold.IsEmpty()) { Fail(TEXT("要求していない署名応答を拒否しました。")); return; }
    ++WalletSequence;
    Deadline = 0;
    if ((*Payload)->HasField(TEXT("SignResultErr")))
    {
        ArenaConnect::Erase(PendingScaffold);
        ArenaConnect::Erase(PendingSignatory);
        PendingTransactionSummary.Empty();
        SetTransactionState(EArenaTransactionState::Cancelled, TEXT("ウォレットで署名依頼が取り消されました。送信していません。"));
        SetState(EArenaWalletState::Approved, TEXT("ウォレットで署名が拒否されました。取引は送信していません。"));
        return;
    }
    const TSharedPtr<FJsonObject>* Result = nullptr;
    FString Algorithm, EncodedSignature;
    TArray<uint8> Signature;
    if (!(*Payload)->TryGetObjectField(TEXT("SignResultOk"), Result) || !(*Result)->TryGetStringField(TEXT("algorithm"), Algorithm) || Algorithm != TEXT("ed25519") || !(*Result)->TryGetStringField(TEXT("signature_b64"), EncodedSignature) || !FBase64::Decode(EncodedSignature, Signature) || Signature.Num() != 64 || FBase64::Encode(Signature) != EncodedSignature)
    { Fail(TEXT("署名応答の形式が不正です。")); return; }
    FNativeBytes Signed(*Native), Finalized(*Native);
    TSharedPtr<FJsonObject> Finalization;
    FString Schema, PayloadHash, SignedHash, EntrypointHash;
    if (Native->Finalize(PendingScaffold.GetData(), PendingScaffold.Num(), PendingSignatory.GetData(), PendingSignatory.Num(), Signature.GetData(), Signature.Num(), &Signed.Data, &Signed.Size, &Finalized.Data, &Finalized.Size) != 0 || !Signed.Bounded()
        || !Finalized.Bounded(1024) || !ArenaConnect::ParseObject(Finalized.Data, Finalized.Size, Finalization)
        || Finalization->Values.Num() != 4
        || !Finalization->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("iroha.detached_transaction_finalization.v1")
        || !Finalization->TryGetStringField(TEXT("payload_signing_hash_hex"), PayloadHash) || !ArenaConnect::CanonicalHash(PayloadHash)
        || !Finalization->TryGetStringField(TEXT("transaction_hash_hex"), SignedHash) || !ArenaConnect::CanonicalHash(SignedHash)
        || !Finalization->TryGetStringField(TEXT("entrypoint_hash_hex"), EntrypointHash) || !ArenaConnect::CanonicalHash(EntrypointHash))
    { Fail(TEXT("取引署名が元の取引・アカウントと一致しません。")); return; }
    LastSignedTransactionBase64 = FBase64::Encode(Signed.Data, static_cast<uint32>(Signed.Size));
    LastSignedTransactionHash = SignedHash;
    LastEntrypointHash = EntrypointHash;
    SubmissionOrigin = Origin;
    SubmissionNetworkLiteral = NetworkLiteral;
    const FString VerifiedTransaction = LastSignedTransactionBase64;
    const uint64 Attempt = Generation;
    ArenaConnect::Erase(PendingScaffold);
    ArenaConnect::Erase(PendingSignatory);
    SetTransactionState(EArenaTransactionState::Signed, TEXT("署名済み。テストネットワークへの送信は別操作です。"));
    if (Generation != Attempt || TransactionState != EArenaTransactionState::Signed) return;
    SetState(EArenaWalletState::Signed, TEXT("取引署名を検証しました。チェーンへの送信・確定はまだ行っていません。"));
    if (Generation == Attempt) OnTransactionSigned.Broadcast(VerifiedTransaction);
}

bool UArenaWalletSubsystem::SubmitSignedTestTransaction()
{
#if UE_BUILD_SHIPPING
    SetTransactionState(TransactionState, TEXT("製品ビルドでは取引送信を無効にしています。"));
    return false;
#else
    FString PinnedOrigin, PinnedNetwork;
    if (bRecoveryBlocked || !ArenaConnect::ReadIsolatedTestConfig(PinnedOrigin, PinnedNetwork)
        || PinnedOrigin != SubmissionOrigin || PinnedNetwork != SubmissionNetworkLiteral)
    {
        SetTransactionState(TransactionState, TEXT("隔離テスト網の明示設定がないため送信しません。"));
        return false;
    }
    TArray<uint8> Signed;
    if (TransactionState != EArenaTransactionState::Signed || !ArenaConnect::CanonicalHash(LastSignedTransactionHash)
        || !ArenaConnect::CanonicalHash(LastEntrypointHash) || LastSignedTransactionBase64.IsEmpty()
        || LastSignedTransactionBase64.Len() > ArenaConnect::MaxFrameBytes * 2
        || !FBase64::Decode(LastSignedTransactionBase64, Signed) || Signed.IsEmpty()
        || Signed.Num() > ArenaConnect::MaxFrameBytes || FBase64::Encode(Signed) != LastSignedTransactionBase64)
    {
        SetTransactionState(TransactionState, TEXT("検証済みの署名取引がありません。"));
        return false;
    }
    const ArenaTransactionRecovery::Record IdentityRecord{
        ArenaConnect::Utf8String(SubmissionOrigin), ArenaConnect::Utf8String(SubmissionNetworkLiteral),
        ArenaConnect::Utf8String(LastSignedTransactionHash), ArenaConnect::Utf8String(LastEntrypointHash)};
    // Persist identity before dispatch. A crash at any later point must never
    // turn an ambiguous POST into a second submission of the signed payload.
    if (!ArenaConnect::PersistRecovery(IdentityRecord, PinnedOrigin, PinnedNetwork))
    {
        ArenaConnect::Erase(Signed);
        bRecoveryBlocked = true;
        SetTransactionState(EArenaTransactionState::Signed,
            TEXT("取引IDを保存できないため送信しません。隔離テスト網の回復状態を確認してください。"));
        return false;
    }
    ClearSubmissionRequests();
    StatusPollCount = 0;
    SubmissionRequest = FHttpModule::Get().CreateRequest();
    SubmissionRequest->SetURL(SubmissionOrigin + TEXT("/v1/pipeline/transactions"));
    SubmissionRequest->SetVerb(TEXT("POST"));
    SubmissionRequest->SetHeader(TEXT("Content-Type"), TEXT("application/x-norito"));
    SubmissionRequest->SetHeader(TEXT("Accept"), TEXT("application/json"));
    SubmissionRequest->SetHeader(TEXT("Prefer"), TEXT("return=minimal"));
    SubmissionRequest->SetContent(Signed);
    SubmissionRequest->SetTimeout(20.0f);
    ArenaConnect::Erase(Signed);
    // Never resubmit after this point. The request may have reached Torii even if HTTP fails.
    ArenaConnect::Erase(LastSignedTransactionBase64);
    const uint64 Attempt = TransactionGeneration;
    const FString Identity = LastSignedTransactionHash;
    const FString Entrypoint = LastEntrypointHash;
    TWeakObjectPtr<UArenaWalletSubsystem> Weak(this);
    SubmissionRequest->OnRequestProgress().BindLambda([](FHttpRequestPtr Request, int32, int32 Received)
    { if (Received > ArenaConnect::MaxTransactionStatusJsonBytes) Request->CancelRequest(); });
    SubmissionRequest->OnProcessRequestComplete().BindLambda([Weak, Attempt, Identity, Entrypoint](FHttpRequestPtr Request, FHttpResponsePtr Response, bool Success)
    {
        AsyncTask(ENamedThreads::GameThread, [Weak, Attempt, Identity, Entrypoint, Request, Response, Success]()
        {
            if (!Weak.IsValid() || Weak->TransactionGeneration != Attempt || Weak->LastSignedTransactionHash != Identity) return;
            Weak->SubmissionRequest.Reset();
            const bool bAccepted = Success && Response.IsValid() && Response->GetURL() == Request->GetURL()
                && Response->GetResponseCode() == 202 && Response->GetContent().IsEmpty()
                && Response->GetHeader(TEXT("preference-applied")) == TEXT("return=minimal")
                && Response->GetHeader(TEXT("x-iroha-signed-transaction-hash")) == Identity
                && Response->GetHeader(TEXT("x-iroha-entrypoint-hash")) == Entrypoint;
            Weak->SetTransactionState(bAccepted ? EArenaTransactionState::Pending : EArenaTransactionState::Uncertain,
                bAccepted ? TEXT("取引を受理しました。台帳への適用を照会しています。")
                          : TEXT("送信結果が不明です。同一取引を再送せず、取引IDで照会します。"));
            if (Weak->TransactionGeneration == Attempt) Weak->PollTransactionStatus();
        });
    });
    SetTransactionState(EArenaTransactionState::Submitting, TEXT("署名済み取引を隔離テスト網へ送信しています。"));
    if (TransactionGeneration != Attempt || TransactionState != EArenaTransactionState::Submitting || !SubmissionRequest.IsValid()) return false;
    if (!SubmissionRequest->ProcessRequest())
    {
        ClearSubmissionRequests();
        SetTransactionState(EArenaTransactionState::Uncertain, TEXT("送信開始を確認できません。同一取引は再送せず、取引IDを照会します。"));
        PollTransactionStatus();
        return false;
    }
    return true;
#endif
}

bool UArenaWalletSubsystem::ReconcileTransaction()
{
    if (TransactionState != EArenaTransactionState::Pending && TransactionState != EArenaTransactionState::Uncertain)
        return false;
    if (!IsRecoveryIdentityCurrent())
    {
        bRecoveryBlocked = true;
        SetTransactionState(EArenaTransactionState::Uncertain,
            TEXT("取引IDまたは隔離テスト網の設定を確認できません。照会を停止しました。"));
        return false;
    }
    if (!LoadNativeBridge()) return false;
    StatusPollCount = 0;
    NextStatusPollAt = 0;
    PollTransactionStatus();
    return true;
}

void UArenaWalletSubsystem::PollTransactionStatus()
{
    if ((TransactionState != EArenaTransactionState::Pending && TransactionState != EArenaTransactionState::Uncertain)
        || StatusRequest.IsValid()) return;
    if (!IsRecoveryIdentityCurrent())
    {
        bRecoveryBlocked = true;
        NextStatusPollAt = 0;
        SetTransactionState(EArenaTransactionState::Uncertain,
            TEXT("取引IDまたは隔離テスト網の設定を確認できません。再送と照会を停止しました。"));
        return;
    }
    if (StatusPollCount >= ArenaConnect::MaxTransactionPolls)
    {
        SetTransactionState(EArenaTransactionState::Uncertain, TEXT("照会時間を超えました。取引IDを保持しています。後で再照会してください。"));
        return;
    }
    ++StatusPollCount;
    StatusRequest = FHttpModule::Get().CreateRequest();
    StatusRequest->SetURL(SubmissionOrigin + TEXT("/v1/pipeline/transactions/status?hash=") + LastSignedTransactionHash + TEXT("&scope=global"));
    StatusRequest->SetVerb(TEXT("GET"));
    StatusRequest->SetHeader(TEXT("Accept"), TEXT("application/json"));
    StatusRequest->SetTimeout(15.0f);
    const uint64 Attempt = TransactionGeneration;
    const FString Identity = LastSignedTransactionHash;
    TWeakObjectPtr<UArenaWalletSubsystem> Weak(this);
    StatusRequest->OnRequestProgress().BindLambda([](FHttpRequestPtr Request, int32, int32 Received)
    { if (Received > ArenaConnect::MaxTransactionStatusJsonBytes) Request->CancelRequest(); });
    StatusRequest->OnProcessRequestComplete().BindLambda([Weak, Attempt, Identity](FHttpRequestPtr Request, FHttpResponsePtr Response, bool Success)
    {
        AsyncTask(ENamedThreads::GameThread, [Weak, Attempt, Identity, Request, Response, Success]()
        {
            if (!Weak.IsValid() || Weak->TransactionGeneration != Attempt || Weak->LastSignedTransactionHash != Identity) return;
            Weak->StatusRequest.Reset();
            if (!Weak->IsRecoveryIdentityCurrent())
            {
                Weak->bRecoveryBlocked = true;
                Weak->NextStatusPollAt = 0;
                Weak->SetTransactionState(EArenaTransactionState::Uncertain,
                    TEXT("隔離テスト網の設定または回復記録が変更されました。照会を停止しました。"));
                return;
            }
            ArenaConnect::EChainObservation Observation = ArenaConnect::EChainObservation::Invalid;
            if (Success && Response.IsValid() && Response->GetURL() == Request->GetURL()
                && Weak->Native && Response->GetContent().Num() <= ArenaConnect::MaxTransactionStatusJsonBytes)
            {
                // The native canonical parser rejects duplicate keys, trailing data, and invalid UTF-8.
                FNativeBytes Canonical(*Weak->Native);
                uint8 Digest[32] = {};
                if (Weak->Native->CanonicalJson(Response->GetContent().GetData(), Response->GetContent().Num(),
                    &Canonical.Data, &Canonical.Size, Digest, 32) == 0 && Canonical.Bounded(ArenaConnect::MaxTransactionStatusJsonBytes))
                {
                    TArray<uint8> CanonicalBody;
                    CanonicalBody.Append(Canonical.Data, static_cast<int32>(Canonical.Size));
                    Observation = ArenaConnect::ReadExactStatus(Response->GetResponseCode(), Response->GetContentType(), CanonicalBody, Identity);
                }
            }
            switch (Observation)
            {
            case ArenaConnect::EChainObservation::Applied:
            case ArenaConnect::EChainObservation::Rejected:
            {
                const ArenaTransactionRecovery::Record Current{
                    ArenaConnect::Utf8String(Weak->SubmissionOrigin), ArenaConnect::Utf8String(Weak->SubmissionNetworkLiteral),
                    ArenaConnect::Utf8String(Weak->LastSignedTransactionHash), ArenaConnect::Utf8String(Weak->LastEntrypointHash)};
                if (!ArenaConnect::ForgetRecovery(Current, Weak->SubmissionOrigin, Weak->SubmissionNetworkLiteral))
                    Weak->bRecoveryBlocked = true;
                if (Observation == ArenaConnect::EChainObservation::Rejected)
                {
                    Weak->SetTransactionState(EArenaTransactionState::Rejected,
                        TEXT("Torii が台帳状態で取引の拒否または期限切れを報告しました。"));
                    return;
                }
                Weak->SetTransactionState(EArenaTransactionState::Finalized, TEXT("Torii が台帳状態で取引適用を報告しました。ゲーム参加は別途検証します。"));
                return;
            }
            case ArenaConnect::EChainObservation::InFlight:
                Weak->SetTransactionState(EArenaTransactionState::Pending, TEXT("取引は確認中です。確定を待っています。"));
                break;
            case ArenaConnect::EChainObservation::Absent:
                // Global 404 is a scoped observation, not proof of non-inclusion or permission to retry.
                if (Weak->TransactionState == EArenaTransactionState::Pending)
                    Weak->SetTransactionState(EArenaTransactionState::Pending, TEXT("取引はまだ確定していません。照会を続けます。"));
                break;
            case ArenaConnect::EChainObservation::Invalid:
                Weak->SetTransactionState(EArenaTransactionState::Uncertain, TEXT("取引状態を検証できません。同一取引は再送せず再照会します。"));
                break;
            }
            if (Weak->TransactionGeneration == Attempt
                && (Weak->TransactionState == EArenaTransactionState::Pending || Weak->TransactionState == EArenaTransactionState::Uncertain))
                Weak->NextStatusPollAt = FPlatformTime::Seconds() + 2.0;
        });
    });
    if (!StatusRequest->ProcessRequest())
    {
        ClearSubmissionRequests();
        SetTransactionState(EArenaTransactionState::Uncertain, TEXT("状態照会を開始できません。取引IDを保持します。"));
        NextStatusPollAt = FPlatformTime::Seconds() + 2.0;
    }
}

void UArenaWalletSubsystem::CancelTransactionRequest()
{
    if (TransactionState == EArenaTransactionState::AwaitingSignature)
    {
        const uint64 Attempt = Generation;
        ArenaConnect::Erase(PendingScaffold);
        ArenaConnect::Erase(PendingSignatory);
        PendingTransactionSummary.Empty();
        bIgnoreCancelledSignatureResult = true;
        Deadline = 0;
        SetTransactionState(EArenaTransactionState::Cancelled, TEXT("署名依頼を取り消しました。遅れて届く署名は使用しません。"));
        if (Generation == Attempt) SetState(EArenaWalletState::Approved, TEXT("署名依頼を取り消しました。取引は送信していません。"));
    }
    else if (TransactionState == EArenaTransactionState::Signed)
    {
        ArenaConnect::Erase(LastSignedTransactionBase64);
        LastSignedTransactionHash.Empty();
        LastEntrypointHash.Empty();
        SubmissionOrigin.Empty();
        SubmissionNetworkLiteral.Empty();
        SetTransactionState(EArenaTransactionState::Cancelled, TEXT("未送信の署名済み取引を破棄しました。"));
    }
    else if (TransactionState == EArenaTransactionState::Submitting
        || TransactionState == EArenaTransactionState::Pending || TransactionState == EArenaTransactionState::Uncertain)
    {
        ClearSubmissionRequests();
        SetTransactionState(EArenaTransactionState::Uncertain, TEXT("監視を停止しました。送信済みの取引は取り消せません。取引IDから再照会できます。"));
    }
}

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FArenaConnectBindingTest, "SoraArena.Connect.LaunchBindings", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FArenaConnectBindingTest::RunTest(const FString& Parameters)
{
    // CRC fixture independently generated with Python binascii.crc_hqx(prefix, 0xffff).
    const FString Network = TEXT("hash:0000000000000000000000000000000000000000000000000000000000000001#C50E");
    TArray<uint8> Bytes;
    TestTrue(TEXT("Canonical network identity"), ArenaConnect::ParseNetworkId(Network, Bytes));
    TestEqual(TEXT("Exact network width"), Bytes.Num(), 32);
    TestFalse(TEXT("Network checksum substitution"), ArenaConnect::ParseNetworkId(Network.Left(73) + TEXT("F"), Bytes));
    TestFalse(TEXT("Noncanonical lowercase checksum"), ArenaConnect::ParseNetworkId(Network.Left(70) + TEXT("c50e"), Bytes));
    TestFalse(TEXT("Display labels are not network identities"), ArenaConnect::ParseNetworkId(TEXT("sora-mainnet"), Bytes));

    FString Origin;
    TestTrue(TEXT("HTTPS origin"), ArenaConnect::NormalizeOrigin(TEXT("https://torii.example:443/"), Origin));
    TestEqual(TEXT("Trailing slash normalized"), Origin, FString(TEXT("https://torii.example:443")));
    TestTrue(TEXT("Explicit loopback HTTP"), ArenaConnect::NormalizeOrigin(TEXT("http://127.0.0.1:8080"), Origin));
    TestTrue(TEXT("IPv6 loopback HTTP"), ArenaConnect::NormalizeOrigin(TEXT("http://[::1]:8080"), Origin));
    for (const FString& Invalid : {FString(TEXT("http://torii.example")), FString(TEXT("https://user@torii.example")), FString(TEXT("https://torii.example/api")), FString(TEXT("https://torii.example?x=1")), FString(TEXT("https://torii.example:65536")), FString(TEXT("https://localhost.evil/path"))})
        TestFalse(TEXT("Unsafe origin rejected"), ArenaConnect::NormalizeOrigin(Invalid, Origin));

    const TMap<FString, FString> Expected = {{TEXT("sid"), TEXT("bound-session")}, {TEXT("role"), TEXT("wallet")}, {TEXT("node"), TEXT("https://torii.example")}};
    const FString Uri = TEXT("iroha://connect?sid=bound-session&role=wallet&node=https%3A%2F%2Ftorii.example");
    TestTrue(TEXT("Exact URI bindings"), ArenaConnect::MatchLaunchUri(Uri, Expected));
    TestFalse(TEXT("Session substitution"), ArenaConnect::MatchLaunchUri(Uri.Replace(TEXT("bound-session"), TEXT("other-session")), Expected));
    TestFalse(TEXT("Role substitution"), ArenaConnect::MatchLaunchUri(Uri.Replace(TEXT("role=wallet"), TEXT("role=app")), Expected));
    TestFalse(TEXT("Node substitution"), ArenaConnect::MatchLaunchUri(Uri.Replace(TEXT("torii.example"), TEXT("evil.example")), Expected));
    TestFalse(TEXT("Repeated field"), ArenaConnect::MatchLaunchUri(TEXT("iroha://connect?sid=bound-session&sid=bound-session&node=https%3A%2F%2Ftorii.example"), Expected));
    TestFalse(TEXT("Unexpected extra field"), ArenaConnect::MatchLaunchUri(Uri + TEXT("&extra=1"), Expected));
    TestFalse(TEXT("Fragment rejected"), ArenaConnect::MatchLaunchUri(Uri + TEXT("#ignored"), Expected));
    TestFalse(TEXT("Scheme substitution"), ArenaConnect::MatchLaunchUri(Uri.Replace(TEXT("iroha://"), TEXT("https://")), Expected));
    TestFalse(TEXT("NFT wagering is not an Arena action"), ArenaConnect::IsAllowedInstruction(TEXT("StakeGameItemV1")));
    TestFalse(TEXT("Unrelated transfer is not an Arena action"), ArenaConnect::IsAllowedInstruction(TEXT("Transfer")));
    TestTrue(TEXT("Funded session join is an Arena action"), ArenaConnect::IsAllowedInstruction(TEXT("JoinGameSessionV1")));
    TestTrue(TEXT("Funded join requires qualified terms review before signing"), ArenaConnect::RequiresQualifiedTermsReview(TEXT("JoinGameSessionV1")));
    TestTrue(TEXT("NFT purchase requires qualified offer review before signing"), ArenaConnect::RequiresQualifiedTermsReview(TEXT("BuyNftV1")));
    TestFalse(TEXT("Payout claim does not use join or purchase review"), ArenaConnect::RequiresQualifiedTermsReview(TEXT("ClaimGamePayoutV1")));

    const FString Hash = Network.Mid(5, 64);
    TestTrue(TEXT("Exact native signed transaction hash"), ArenaConnect::CanonicalHash(Hash));
    TestFalse(TEXT("Hash marker missing"), ArenaConnect::CanonicalHash(Hash.Left(63) + TEXT("0")));
    TestFalse(TEXT("Uppercase transaction hash"), ArenaConnect::CanonicalHash(Hash.Left(63) + TEXT("F")));
    const FString Applied = FString::Printf(TEXT("{\"hash\":\"%s\",\"scope\":\"global\",\"resolved_from\":\"state\",\"status\":{\"kind\":\"Applied\"}}"), *Hash);
    const auto AppliedBytes = ArenaConnect::Utf8(Applied);
    TestEqual(TEXT("Only state-resolved Applied is final"), static_cast<int32>(ArenaConnect::ReadExactStatus(200, TEXT("application/json"), AppliedBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::Applied));
    const auto CachedBytes = ArenaConnect::Utf8(Applied.Replace(TEXT("\"state\""), TEXT("\"cache\"")));
    TestEqual(TEXT("Cached Applied is not final"), static_cast<int32>(ArenaConnect::ReadExactStatus(200, TEXT("application/json"), CachedBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::InFlight));
    const auto RejectedBytes = ArenaConnect::Utf8(Applied.Replace(TEXT("\"Applied\""), TEXT("\"Rejected\"")));
    TestEqual(TEXT("State-resolved rejection is terminal"), static_cast<int32>(ArenaConnect::ReadExactStatus(200, TEXT("application/json"), RejectedBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::Rejected));
    const auto CachedRejectionBytes = ArenaConnect::Utf8(Applied.Replace(TEXT("\"Applied\""), TEXT("\"Rejected\"")).Replace(TEXT("\"state\""), TEXT("\"cache\"")));
    TestEqual(TEXT("Cached rejection is not terminal"), static_cast<int32>(ArenaConnect::ReadExactStatus(200, TEXT("application/json"), CachedRejectionBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::InFlight));
    const auto DifferentHashBytes = ArenaConnect::Utf8(Applied.Replace(*Hash, *(Hash.Left(63) + TEXT("3"))));
    TestEqual(TEXT("Other transaction status rejected"), static_cast<int32>(ArenaConnect::ReadExactStatus(200, TEXT("application/json"), DifferentHashBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::Invalid));
    const FString Absent = FString::Printf(TEXT("{\"code\":\"pipeline_transaction_status_not_found\",\"message\":\"not found\",\"details\":{\"pipeline_transaction_status_not_found\":{\"hash\":\"%s\",\"scope\":\"global\"}}}"), *Hash);
    const auto AbsentBytes = ArenaConnect::Utf8(Absent);
    TestEqual(TEXT("Typed global 404 remains unresolved"), static_cast<int32>(ArenaConnect::ReadExactStatus(404, TEXT("application/json"), AbsentBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::Absent));
    const auto LocalAbsenceBytes = ArenaConnect::Utf8(Absent.Replace(TEXT("\"global\""), TEXT("\"local\"")));
    TestEqual(TEXT("Local 404 cannot resolve global lookup"), static_cast<int32>(ArenaConnect::ReadExactStatus(404, TEXT("application/json"), LocalAbsenceBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::Invalid));
    TestEqual(TEXT("Untyped 404 rejected"), static_cast<int32>(ArenaConnect::ReadExactStatus(404, TEXT("application/json"), ArenaConnect::Utf8(TEXT("{}")), Hash)), static_cast<int32>(ArenaConnect::EChainObservation::Invalid));
    TestEqual(TEXT("Non-JSON status rejected"), static_cast<int32>(ArenaConnect::ReadExactStatus(200, TEXT("text/plain"), AppliedBytes, Hash)), static_cast<int32>(ArenaConnect::EChainObservation::Invalid));
    return true;
}
#endif
