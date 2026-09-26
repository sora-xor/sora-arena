#pragma once
#include "CoreMinimal.h"
#include "ArenaWalletSubsystem.h"
#include "SoraText.h"

// Each wallet and transaction state in both languages. The wallet writes its
// own Japanese status line, which can carry a reason; the screen shows that
// line when there is one, with the state's English beneath.
namespace SoraUI
{
inline SoraText::FLine WalletStateText(EArenaWalletState State)
{
    switch (State)
    {
    case EArenaWalletState::Idle: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.Idle", "未接続。"));
    case EArenaWalletState::CreatingSession: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.CreatingSession", "接続用のセッションを作成中……"));
    case EArenaWalletState::Connecting: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.Connecting", "中継に接続中……"));
    case EArenaWalletState::AwaitingApproval: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.AwaitingApproval", "QR コードを読み取るかウォレットを開き、承認してほしい。"));
    case EArenaWalletState::Approved: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.Approved", "接続済み。署名の依頼はすべて、先に正確な条件を示す。"));
    case EArenaWalletState::AwaitingSignature: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.AwaitingSignature", "ウォレットでの署名を待っている。"));
    case EArenaWalletState::Signed: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.Signed", "ウォレットで署名済み。まだ送信していない。"));
    case EArenaWalletState::Disconnected: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.Disconnected", "接続を解除した。"));
    case EArenaWalletState::Unavailable: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.Unavailable", "この版では IrohaConnect を使えない。"));
    case EArenaWalletState::Error: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "State.Error", "ウォレットのエラー。理由は日本語の行にある。"));
    }
    return SoraText::FLine();
}

inline SoraText::FLine TransactionStateText(EArenaTransactionState State)
{
    switch (State)
    {
    case EArenaTransactionState::AwaitingSignature: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.AwaitingSignature", "署名待ち。条件と手数料を確かめてほしい。"));
    case EArenaTransactionState::Signed: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.Signed", "この端末で署名済み。未送信。"));
    case EArenaTransactionState::Submitting: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.Submitting", "隔離された試験ネットワークへ送信中。"));
    case EArenaTransactionState::Pending: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.Pending", "台帳での確定を待っている。"));
    case EArenaTransactionState::Uncertain: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.Uncertain", "状態が分からない。再送しないでほしい。"));
    case EArenaTransactionState::Finalized: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.Finalized", "Torii は適用済みと報告した。試合への参加は別。"));
    case EArenaTransactionState::Rejected: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.Rejected", "台帳で拒否されたか、期限が切れた。"));
    case EArenaTransactionState::Cancelled: return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.Cancelled", "送信前に取り消した。"));
    case EArenaTransactionState::None: break;
    }
    return SoraText::Line(NSLOCTEXT("SoraArena.Wallet", "Transaction.None", "取引の状態は分からない。"));
}
}
