#include "SoraQuotePreflight.h"

#include <cassert>
#include <iostream>

using namespace SoraQuotePreflight;

int main()
{
    const FJoinIntent Joined{
        "network-a", "cat-account", "session-7", "manifest-a", "xor-asset", "2000",
        "blade-nft", "metadata-a", "catalog-role-a", 4
    };
    const FArenaSessionQuote Session{
        "network-a", "session-7", "manifest-a", "xor-asset", "2000",
        "200", "2000", 4, 90, 100, true
    };
    const FEquipmentRead Equipment{
        "blade-nft", "metadata-a", "catalog-role-a", "cat-account", true
    };
    assert(CheckJoin(Joined, Session, Equipment) == EResult::MatchesSuppliedSnapshot);
    auto ChangedJoin = Joined;
    ChangedJoin.ManifestHash = "manifest-b";
    assert(CheckJoin(ChangedJoin, Session, Equipment) == EResult::DifferentTerms);
    ChangedJoin = Joined;
    ChangedJoin.QuotedSessionRevision = 3;
    assert(CheckJoin(ChangedJoin, Session, Equipment) == EResult::Stale);
    auto ChangedSession = Session;
    ChangedSession.ObservedHeight = 101;
    assert(CheckJoin(Joined, ChangedSession, Equipment) == EResult::Stale);
    ChangedSession = Session;
    ChangedSession.PerDeathLossAtomic = "201";
    assert(CheckJoin(Joined, ChangedSession, Equipment) == EResult::InvalidBond);
    ChangedSession = Session;
    ChangedSession.TotalBondAtomic = "2001";
    ChangedJoin = Joined;
    ChangedJoin.TotalBondAtomic = "2001";
    assert(CheckJoin(ChangedJoin, ChangedSession, Equipment) == EResult::InvalidBond);
    auto ChangedEquipment = Equipment;
    ChangedEquipment.OwnerAccount = "other-cat";
    assert(CheckJoin(Joined, Session, ChangedEquipment) == EResult::UnavailableNft);
    ChangedEquipment = Equipment;
    ChangedEquipment.MetadataHash = "metadata-b";
    assert(CheckJoin(Joined, Session, ChangedEquipment) == EResult::UnavailableNft);
    ChangedJoin = Joined;
    ChangedJoin.NftId = "";
    ChangedJoin.NftMetadataHash = "";
    ChangedJoin.NftRoleId = "";
    assert(CheckJoin(ChangedJoin, Session, {}) == EResult::MatchesSuppliedSnapshot);
    ChangedJoin.NftMetadataHash = "metadata-a";
    assert(CheckJoin(ChangedJoin, Session, {}) == EResult::Incomplete);

    const FOfferTerms Offer{
        "network-a", "offer-5", "blade-nft", "seller-cat", "xor-asset", "700",
        "buyer-cat", "metadata-a", "commitment-a", 120
    };
    const FBuyIntent Buy{Offer, "buyer-cat"};
    const FOfferRead Read{Offer, 110, true, true};
    assert(CheckBuy(Buy, Read) == EResult::MatchesSuppliedSnapshot);
    auto ChangedBuy = Buy;
    ChangedBuy.Offer.PriceAtomic = "701";
    assert(CheckBuy(ChangedBuy, Read) == EResult::DifferentTerms);
    ChangedBuy = Buy;
    ChangedBuy.Offer.Seller = "other-seller";
    assert(CheckBuy(ChangedBuy, Read) == EResult::DifferentTerms);
    ChangedBuy = Buy;
    ChangedBuy.Offer.MetadataHash = "metadata-b";
    assert(CheckBuy(ChangedBuy, Read) == EResult::DifferentTerms);
    ChangedBuy = Buy;
    ChangedBuy.Offer.OfferCommitment = "commitment-b";
    assert(CheckBuy(ChangedBuy, Read) == EResult::DifferentTerms);
    ChangedBuy = Buy;
    ChangedBuy.Buyer = "other-buyer";
    assert(CheckBuy(ChangedBuy, Read) == EResult::UnavailableNft);
    auto ChangedRead = Read;
    ChangedRead.ObservedHeight = 121;
    assert(CheckBuy(Buy, ChangedRead) == EResult::Stale);
    ChangedRead = Read;
    ChangedRead.Open = false;
    assert(CheckBuy(Buy, ChangedRead) == EResult::Stale);
    ChangedRead = Read;
    ChangedRead.HeldInSaleCustody = false;
    assert(CheckBuy(Buy, ChangedRead) == EResult::Stale);
    ChangedBuy = Buy;
    ChangedBuy.Offer.PriceAtomic = "0";
    assert(CheckBuy(ChangedBuy, Read) == EResult::Incomplete);
    assert(!JapaneseCopy(EResult::Stale).empty());
    assert(!EnglishSubtitle(EResult::Stale).empty());
    std::cout << "Join and Buy supplied-snapshot preflight passed; no authorization\n";
}
