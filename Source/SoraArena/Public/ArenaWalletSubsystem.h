#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ArenaWalletSubsystem.generated.h"

class IHttpRequest;
class IWebSocket;
class UTexture2D;
struct FArenaConnectNative;
struct FArenaCancelledSignatureGuard;

UENUM(BlueprintType)
enum class EArenaWalletState : uint8
{
    Idle, CreatingSession, Connecting, AwaitingApproval, Approved,
    AwaitingSignature, Signed, Disconnected, Unavailable, Error
};

/** Submission is independent of wallet pairing. An absent Torii status is never a rejection. */
UENUM(BlueprintType)
enum class EArenaTransactionState : uint8
{
    None, AwaitingSignature, Signed, Submitting, Pending, Uncertain,
    Finalized, Rejected, Cancelled
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnArenaWalletStateChanged);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnArenaTransactionStateChanged);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnArenaWalletTransactionSigned, const FString&, SignedTransactionBase64);

/** Native Iroha Connect transport. An authenticated wallet is not evidence of a funded bond. */
UCLASS()
class SORAARENA_API UArenaWalletSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    UArenaWalletSubsystem();
    UArenaWalletSubsystem(FVTableHelper& Helper);
    virtual ~UArenaWalletSubsystem() override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintCallable, Category="SORA|Wallet") void BeginPairingFromConfig();
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet")
    void BeginPairing(const FString& ToriiOrigin, const FString& CanonicalNetworkId, const FString& ExpectedAccount = TEXT(""));
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet") void LaunchWallet();
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet") void DisconnectWallet();
    /** Sends the inspector's canonical payload, retaining the scaffold solely for verified finalization. */
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet")
    bool RequestSignTransaction(const FString& ScaffoldBase64, const FString& Ed25519PublicKeyHex);
    /** Constructs one allowlisted typed native instruction through the bridge, then requests its signature. */
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet")
    bool RequestNativeTransactionSignature(const FString& ExactRequestJson, const FString& Ed25519PublicKeyHex);
    /** Read-only canonical join preview. Its authorization_ready flag is always false. */
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet")
    bool InspectJoinScaffold(const FString& ScaffoldBase64, FString& OutInspectionJson);
    /** Disabled by default and in shipping builds; only an explicitly configured loopback test node is eligible. */
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet") bool SubmitSignedTestTransaction();
    /** Read-only exact-hash reconciliation, including an identity restored after restart. It never resends. */
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet") bool ReconcileTransaction();
    /** Cancels an outstanding wallet request locally; dispatched submissions remain uncertain until reconciled. */
    UFUNCTION(BlueprintCallable, Category="SORA|Wallet") void CancelTransactionRequest();

    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") EArenaWalletState State = EArenaWalletState::Idle;
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") FString StatusText;
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") FString ApprovedAccount;
    /** Credential-bearing URI: display as a local QR/deep link only; never log, replicate, or persist. */
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") FString WalletLaunchUri;
    /** Local transient QR of the validated URI; never save, log, stream, or replicate. */
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") TObjectPtr<UTexture2D> WalletQrTexture;
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") FString PendingTransactionSummary;
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") FString LastSignedTransactionBase64;
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") FString LastSignedTransactionHash;
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") EArenaTransactionState TransactionState = EArenaTransactionState::None;
    UPROPERTY(BlueprintReadOnly, Category="SORA|Wallet") FString TransactionStatusText;
    /** Last read-only Join scaffold inspection, never an authenticated admission quote. */
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") bool bHasUnverifiedJoinPreview = false;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewStake;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewAsset;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewNftReservations;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewNftMetadata;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewNftRole;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewNftPolicy;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewFeePayer;
    UPROPERTY(Transient, BlueprintReadOnly, Category="SORA|Wallet") FString JoinPreviewFeeCaps;
    UPROPERTY(BlueprintAssignable, Category="SORA|Wallet") FOnArenaWalletStateChanged OnStateChanged;
    UPROPERTY(BlueprintAssignable, Category="SORA|Wallet") FOnArenaTransactionStateChanged OnTransactionStateChanged;
    UPROPERTY(BlueprintAssignable, Category="SORA|Wallet") FOnArenaWalletTransactionSigned OnTransactionSigned;

private:
    TUniquePtr<FArenaConnectNative> Native;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> SessionRequest;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> SubmissionRequest;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> StatusRequest;
    TSharedPtr<IWebSocket> Socket;
    FTSTicker::FDelegateHandle TickerHandle;
    uint64 Generation = 0;
    uint64 TransactionGeneration = 0;
    uint64 AppSequence = 1;
    uint64 WalletSequence = 1;
    double Deadline = 0;
    double NextStatusPollAt = 0;
    int32 StatusPollCount = 0;
    // Reusing a session is safe only after its cancelled result was consumed.
    // An unresolved cancellation expires by retiring the transport.
    TUniquePtr<FArenaCancelledSignatureGuard> CancelledSignature;
    bool bRecoveryBlocked = false;
    FString Origin, NetworkLiteral, ExpectedAccountLiteral, RelayToken;
    FString SubmissionOrigin, SubmissionNetworkLiteral, LastEntrypointHash;
    TArray<uint8> NetworkBytes, SessionId, AppPublicKey, AppPrivateKey, Nonce;
    TArray<uint8> AppDirectionKey, WalletDirectionKey, IncomingFrame;
    TArray<uint8> PendingScaffold, PendingSignatory;

    bool LoadNativeBridge();
    void SetState(EArenaWalletState NewState, const FString& Message);
    void SetTransactionState(EArenaTransactionState NewState, const FString& Message);
    void ClearSubmissionRequests();
    void ClearJoinPreview();
    void RestorePendingTransactionIdentity();
    bool IsRecoveryIdentityCurrent() const;
    void PollTransactionStatus();
    void Fail(const FString& Message, EArenaWalletState FailureState = EArenaWalletState::Error);
    void ClearTransport();
    void BuildWalletQr();
    void ClearWalletQr();
    bool TickSession(float DeltaTime);
    void AcceptSessionResponse(const TArray<uint8>& JsonBytes);
    void SendOpen();
    void ReceiveFragment(TArray<uint8> Bytes, SIZE_T BytesRemaining);
    void ReceiveFrame(const TArray<uint8>& Frame);
    void AcceptApproval(const TArray<uint8>& Frame);
    void ReceiveEncrypted(const TArray<uint8>& Frame, uint64 Sequence);
#if WITH_DEV_AUTOMATION_TESTS
    friend class FArenaCancelledSignatureLatchTest;
#endif
};
