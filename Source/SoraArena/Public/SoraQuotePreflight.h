#pragma once

// Host-testable comparison rules for a future, authenticated Arena quote.
// These structs are deliberately not a source of chain state or a wallet
// authorization decision. Join/Buy signing remains blocked in the subsystem.
#include <cstdint>
#include <string_view>

namespace SoraQuotePreflight
{
using Text = std::string_view;

enum class EResult
{
    MatchesSuppliedSnapshot,
    Incomplete,
    Stale,
    DifferentTerms,
    InvalidBond,
    UnavailableNft,
};

inline Text JapaneseCopy(EResult Result)
{
    switch (Result)
    {
    case EResult::MatchesSuppliedSnapshot:
        return "照合用データは一致しました。台帳認証・手数料確認・署名は未実施です。";
    case EResult::Incomplete: return "照合する条件が不足しています。";
    case EResult::Stale: return "条件が期限切れか、台帳状態が変わりました。";
    case EResult::DifferentTerms: return "申請と照合用データの条件が一致しません。";
    case EResult::InvalidBond: return "入金額と死亡時の固定損失額が一致しません。";
    case EResult::UnavailableNft: return "NFT の所有者または予約状態を確認できません。";
    }
    return "条件を確認できません。";
}

inline Text EnglishSubtitle(EResult Result)
{
    switch (Result)
    {
    case EResult::MatchesSuppliedSnapshot:
        return "Supplied terms match. Chain authentication, fee review, and signing remain unavailable.";
    case EResult::Incomplete: return "Terms are incomplete.";
    case EResult::Stale: return "Terms expired or chain state changed.";
    case EResult::DifferentTerms: return "Requested and supplied terms differ.";
    case EResult::InvalidBond: return "Bond and fixed death loss differ.";
    case EResult::UnavailableNft: return "NFT ownership or reservation is unavailable.";
    }
    return "Terms could not be checked.";
}

inline bool Bounded(Text Value)
{
    if (Value.empty() || Value.size() > 256) return false;
    for (const unsigned char Character : Value)
        if (Character < 0x20 || Character > 0x7e) return false;
    return true;
}

inline bool Atomic(Text Value)
{
    if (Value.empty() || Value.size() > 39 || (Value.size() > 1 && Value.front() == '0'))
        return false;
    for (const char Character : Value)
        if (Character < '0' || Character > '9') return false;
    return true;
}

inline bool TenEqualLosses(Text Total, Text PerDeath)
{
    return Atomic(Total) && Atomic(PerDeath) && Total != "0" &&
        Total.size() > 1 && Total.back() == '0' &&
        Total.substr(0, Total.size() - 1) == PerDeath;
}

// The bond and loss fields must eventually come from a verified Arena profile
// applied to an authenticated session read; generic GameSessionRecordV1 alone
// supplies only a minimum stake for VerifiedAllocations.
struct FJoinIntent
{
    Text Network, Account, SessionId, ManifestHash, AssetId, TotalBondAtomic;
    Text NftId, NftMetadataHash, NftRoleId;
    std::uint64_t QuotedSessionRevision;
};

struct FArenaSessionQuote
{
    Text Network, SessionId, ManifestHash, AssetId, TotalBondAtomic;
    Text PerDeathLossAtomic, MaximumLossAtomic;
    std::uint64_t Revision, ObservedHeight, JoinDeadlineHeight;
    bool AcceptingJoins;
};

struct FEquipmentRead
{
    Text NftId, MetadataHash, RoleId, OwnerAccount;
    bool AvailableForReservation;
};

inline EResult CheckJoin(const FJoinIntent& Intent, const FArenaSessionQuote& Quote,
                        const FEquipmentRead& Equipment)
{
    if (!Bounded(Intent.Network) || !Bounded(Intent.Account) ||
        !Bounded(Intent.SessionId) || !Bounded(Intent.ManifestHash) ||
        !Bounded(Intent.AssetId) || !Atomic(Intent.TotalBondAtomic) ||
        !Bounded(Quote.Network) || !Bounded(Quote.SessionId) ||
        !Bounded(Quote.ManifestHash) || !Bounded(Quote.AssetId) ||
        !Atomic(Quote.TotalBondAtomic) || !Atomic(Quote.PerDeathLossAtomic) ||
        !Atomic(Quote.MaximumLossAtomic)) return EResult::Incomplete;
    if (!Quote.AcceptingJoins || Quote.ObservedHeight > Quote.JoinDeadlineHeight ||
        Intent.QuotedSessionRevision != Quote.Revision) return EResult::Stale;
    if (Intent.Network != Quote.Network || Intent.SessionId != Quote.SessionId ||
        Intent.ManifestHash != Quote.ManifestHash || Intent.AssetId != Quote.AssetId ||
        Intent.TotalBondAtomic != Quote.TotalBondAtomic) return EResult::DifferentTerms;
    if (!TenEqualLosses(Quote.TotalBondAtomic, Quote.PerDeathLossAtomic) ||
        Quote.MaximumLossAtomic != Quote.TotalBondAtomic) return EResult::InvalidBond;
    if (Intent.NftId.empty())
        return Intent.NftMetadataHash.empty() && Intent.NftRoleId.empty()
            ? EResult::MatchesSuppliedSnapshot : EResult::Incomplete;
    if (!Bounded(Intent.NftId) || !Bounded(Intent.NftMetadataHash) ||
        !Bounded(Intent.NftRoleId)) return EResult::Incomplete;
    if (!Equipment.AvailableForReservation ||
        Equipment.NftId != Intent.NftId ||
        Equipment.MetadataHash != Intent.NftMetadataHash ||
        Equipment.RoleId != Intent.NftRoleId ||
        Equipment.OwnerAccount != Intent.Account) return EResult::UnavailableNft;
    return EResult::MatchesSuppliedSnapshot;
}

// These fields mirror the immutable NftSaleOfferV1 plus its retained native
// commitment. The source must separately authenticate NftSaleRecordV1 and
// current consensus height before calling this comparison.
struct FOfferTerms
{
    Text Network, OfferId, NftId, Seller, PaymentAsset, PriceAtomic;
    Text ReservedBuyer, MetadataHash, OfferCommitment;
    std::uint64_t ExpiresAtHeight;
};

struct FBuyIntent
{
    FOfferTerms Offer;
    Text Buyer;
};

struct FOfferRead
{
    FOfferTerms Offer;
    std::uint64_t ObservedHeight;
    bool Open, HeldInSaleCustody;
};

inline bool SameOffer(const FOfferTerms& Left, const FOfferTerms& Right)
{
    return Left.Network == Right.Network && Left.OfferId == Right.OfferId &&
        Left.NftId == Right.NftId && Left.Seller == Right.Seller &&
        Left.PaymentAsset == Right.PaymentAsset && Left.PriceAtomic == Right.PriceAtomic &&
        Left.ReservedBuyer == Right.ReservedBuyer &&
        Left.MetadataHash == Right.MetadataHash &&
        Left.OfferCommitment == Right.OfferCommitment &&
        Left.ExpiresAtHeight == Right.ExpiresAtHeight;
}

inline EResult CheckBuy(const FBuyIntent& Intent, const FOfferRead& Read)
{
    const FOfferTerms& Offer = Intent.Offer;
    if (!Bounded(Intent.Buyer) || !Bounded(Offer.Network) ||
        !Bounded(Offer.OfferId) || !Bounded(Offer.NftId) ||
        !Bounded(Offer.Seller) || !Bounded(Offer.PaymentAsset) ||
        !Atomic(Offer.PriceAtomic) || Offer.PriceAtomic == "0" ||
        !Bounded(Offer.MetadataHash) || !Bounded(Offer.OfferCommitment))
        return EResult::Incomplete;
    if (!Read.Open || !Read.HeldInSaleCustody ||
        Read.ObservedHeight > Read.Offer.ExpiresAtHeight) return EResult::Stale;
    if (!SameOffer(Offer, Read.Offer)) return EResult::DifferentTerms;
    if (!Offer.ReservedBuyer.empty() && Offer.ReservedBuyer != Intent.Buyer)
        return EResult::UnavailableNft;
    return EResult::MatchesSuppliedSnapshot;
}
} // namespace SoraQuotePreflight
