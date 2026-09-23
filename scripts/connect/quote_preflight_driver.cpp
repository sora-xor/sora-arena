#include "SoraQuotePreflight.h"

#include <cassert>
#include <iostream>

using namespace SoraQuotePreflight;

int main()
{
    const FJoinIntent NftSpecial{
        "network-a", "cat-account", "session-7", "manifest-a", "xor-asset", "1000",
        "special-blade", 1, 1, "blade-nft", "metadata-a", "catalog-role-a", 4
    };
    const FArenaSessionQuote NftSession{
        "network-a", "session-7", "manifest-a", "xor-asset", "profile-a",
        "1000", "1000", "100", "1000", 4, 90, 100, true
    };
    const FCompiledWeaponRule SpecialRule{
        "special-blade", "profile-a", "catalog-role-a", "catalog-a", "publisher-a",
        "collection-a", true
    };
    const FPublisherCatalogRead Catalog{
        "network-a", "profile-a", "catalog-role-a", "catalog-a", "publisher-a",
        "collection-a", "blade-nft", "metadata-a", true, true, true
    };
    const FEquipmentRead Equipment{
        "blade-nft", "metadata-a", "catalog-role-a", "cat-account", true
    };
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, Catalog, Equipment) ==
           EResult::MatchesSuppliedSnapshot);

    auto NonownerSpecial = NftSpecial;
    NonownerSpecial.TotalBondAtomic = "2000";
    NonownerSpecial.NftReservationCount = 0;
    NonownerSpecial.NftId = "";
    NonownerSpecial.NftMetadataHash = "";
    NonownerSpecial.NftRoleId = "";
    auto NonownerSession = NftSession;
    NonownerSession.TotalBondAtomic = "2000";
    NonownerSession.PerDeathLossAtomic = "200";
    NonownerSession.MaximumLossAtomic = "2000";
    assert(CheckJoin(NonownerSpecial, NonownerSession, SpecialRule, Catalog, {}) ==
           EResult::MatchesSuppliedSnapshot);

    auto Ordinary = NonownerSpecial;
    Ordinary.SelectedWeaponId = "ordinary-katana";
    Ordinary.SelectedSpecialCount = 0;
    Ordinary.TotalBondAtomic = "1000";
    const FCompiledWeaponRule OrdinaryRule{
        "ordinary-katana", "profile-a", "", "", "", "", false
    };
    assert(CheckJoin(Ordinary, NftSession, OrdinaryRule, {}, {}) ==
           EResult::MatchesSuppliedSnapshot);

    auto ChangedJoin = NftSpecial;
    ChangedJoin.ManifestHash = "manifest-b";
    assert(CheckJoin(ChangedJoin, NftSession, SpecialRule, Catalog, Equipment) ==
           EResult::DifferentTerms);
    ChangedJoin = NftSpecial;
    ChangedJoin.QuotedSessionRevision = 3;
    assert(CheckJoin(ChangedJoin, NftSession, SpecialRule, Catalog, Equipment) == EResult::Stale);
    auto ChangedSession = NftSession;
    ChangedSession.ObservedHeight = 101;
    assert(CheckJoin(NftSpecial, ChangedSession, SpecialRule, Catalog, Equipment) == EResult::Stale);
    ChangedSession = NftSession;
    ChangedSession.PerDeathLossAtomic = "101";
    assert(CheckJoin(NftSpecial, ChangedSession, SpecialRule, Catalog, Equipment) ==
           EResult::InvalidBond);
    ChangedSession = NftSession;
    ChangedSession.MaximumLossAtomic = "999";
    assert(CheckJoin(NftSpecial, ChangedSession, SpecialRule, Catalog, Equipment) ==
           EResult::InvalidBond);
    ChangedSession = NftSession;
    ChangedSession.BaseBondAtomic = "5";
    assert(CheckJoin(NftSpecial, ChangedSession, SpecialRule, Catalog, Equipment) ==
           EResult::InvalidBond);
    ChangedSession = NonownerSession;
    ChangedSession.BaseBondAtomic = "340282366920938463463374607431768211450";
    assert(CheckJoin(NonownerSpecial, ChangedSession, SpecialRule, Catalog, {}) ==
           EResult::InvalidBond);

    ChangedJoin = NonownerSpecial;
    ChangedJoin.TotalBondAtomic = "1000";
    assert(CheckJoin(ChangedJoin, NftSession, SpecialRule, Catalog, {}) !=
           EResult::MatchesSuppliedSnapshot);
    ChangedJoin = NftSpecial;
    ChangedJoin.TotalBondAtomic = "2000";
    assert(CheckJoin(ChangedJoin, NonownerSession, SpecialRule, Catalog, Equipment) ==
           EResult::InvalidBond);
    auto ChangedOrdinary = Ordinary;
    ChangedOrdinary.TotalBondAtomic = "2000";
    assert(CheckJoin(ChangedOrdinary, NonownerSession, OrdinaryRule, {}, {}) ==
           EResult::InvalidBond);
    ChangedJoin = NftSpecial;
    ChangedJoin.SelectedSpecialCount = 2;
    assert(CheckJoin(ChangedJoin, NftSession, SpecialRule, Catalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedJoin = NftSpecial;
    ChangedJoin.NftReservationCount = 2;
    assert(CheckJoin(ChangedJoin, NftSession, SpecialRule, Catalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedJoin = NftSpecial;
    ChangedJoin.SelectedWeaponId = "unknown-special";
    assert(CheckJoin(ChangedJoin, NftSession, SpecialRule, Catalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedJoin = Ordinary;
    ChangedJoin.NftReservationCount = 1;
    ChangedJoin.NftId = "blade-nft";
    ChangedJoin.NftMetadataHash = "metadata-a";
    ChangedJoin.NftRoleId = "catalog-role-a";
    assert(CheckJoin(ChangedJoin, NftSession, OrdinaryRule, Catalog, Equipment) ==
           EResult::UnapprovedWeapon);

    auto ChangedCatalog = Catalog;
    ChangedCatalog.SignedGenesisApproved = false;
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, ChangedCatalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedCatalog = Catalog;
    ChangedCatalog.PublisherId = "attacker-publisher";
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, ChangedCatalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedCatalog = Catalog;
    ChangedCatalog.Published = false;
    assert(CheckJoin(NonownerSpecial, NonownerSession, SpecialRule, ChangedCatalog, {}) ==
           EResult::UnapprovedWeapon);
    ChangedCatalog = Catalog;
    ChangedCatalog.ProfileId = "other-profile";
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, ChangedCatalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedCatalog = Catalog;
    ChangedCatalog.RoleId = "attacker-role";
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, ChangedCatalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedCatalog = Catalog;
    ChangedCatalog.ReturnToOriginalOwner = false;
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, ChangedCatalog, Equipment) ==
           EResult::UnapprovedWeapon);
    ChangedCatalog = Catalog;
    ChangedCatalog.MemberMetadataHash = "attacker-metadata";
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, ChangedCatalog, Equipment) ==
           EResult::UnavailableNft);
    ChangedCatalog = Catalog;
    ChangedCatalog.MemberNftId = "attacker-nft";
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, ChangedCatalog, Equipment) ==
           EResult::UnavailableNft);
    ChangedJoin = NftSpecial;
    ChangedJoin.NftRoleId = "attacker-role";
    assert(CheckJoin(ChangedJoin, NftSession, SpecialRule, Catalog, Equipment) ==
           EResult::UnavailableNft);
    auto ChangedEquipment = Equipment;
    ChangedEquipment.OwnerAccount = "other-cat";
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, Catalog, ChangedEquipment) ==
           EResult::UnavailableNft);
    ChangedEquipment = Equipment;
    ChangedEquipment.AvailableForReservation = false;
    assert(CheckJoin(NftSpecial, NftSession, SpecialRule, Catalog, ChangedEquipment) ==
           EResult::UnavailableNft);
    ChangedJoin = NonownerSpecial;
    ChangedJoin.NftMetadataHash = "attacker-metadata";
    assert(CheckJoin(ChangedJoin, NonownerSession, SpecialRule, Catalog, {}) ==
           EResult::UnavailableNft);
    assert(!Atomic("340282366920938463463374607431768211456"));
    assert(DoubleAtomic("170141183460469231731687303715884105728").empty());

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
    std::cout << "Join bond/equipment and Buy snapshot preflight passed; no authorization\n";
}
