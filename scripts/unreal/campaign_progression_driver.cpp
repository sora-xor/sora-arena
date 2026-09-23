#include "SoraCampaignRules.h"

#include <cstdlib>
#include <iostream>

using namespace SoraCampaignRules;

struct FChapterFixture
{
    int KillsNeeded;
    FSite Sites[3];
};

#include "campaign_chapters.generated.inc"

static void Expect(bool Condition, const char* Message, int Chapter)
{
    if (!Condition)
    {
        std::cerr << "chapter " << Chapter + 1 << ": " << Message << '\n';
        std::exit(1);
    }
}

int main()
{
    static_assert(sizeof(Chapters) / sizeof(Chapters[0]) == 8, "Eight chapters are required");
    for (int Chapter = 0; Chapter < 8; ++Chapter)
    {
        const FChapterFixture& Plan = Chapters[Chapter];
        FCheckpoint State{0, 0u, false};
        Expect(CheckpointValid(State, Plan.KillsNeeded, Plan.Sites, 3), "new chapter invalid", Chapter);
        Expect(!CompleteChapter(State, Plan.KillsNeeded, 3), "exit opened before objectives", Chapter);
        Expect(!CheckpointValid({-1, 0u, false}, Plan.KillsNeeded, Plan.Sites, 3), "negative kills accepted", Chapter);
        Expect(!CheckpointValid({Plan.KillsNeeded + 1, 0u, false}, Plan.KillsNeeded, Plan.Sites, 3), "excess kills accepted", Chapter);
        Expect(!CheckpointValid({0, 8u, false}, Plan.KillsNeeded, Plan.Sites, 3), "out-of-range site accepted", Chapter);
        Expect(!CheckpointValid({0, 0u, true}, Plan.KillsNeeded, Plan.Sites, 3), "forged completion accepted", Chapter);
        Expect(!CanFinishChapter(Plan.KillsNeeded, Plan.KillsNeeded, 0u, 0), "invalid site count opened exit", Chapter);

        for (int Kills = 0; Kills <= Plan.KillsNeeded; ++Kills)
        {
            if (Kills > 0)
            {
                Expect(RecordDefeat(State, Plan.KillsNeeded), "defeat rejected", Chapter);
                Expect(State.Kills == Kills, "defeat count diverged", Chapter);
            }
            for (int Site = 0; Site < 3; ++Site)
            {
                const unsigned Bit = 1u << Site;
                const bool Eligible = (State.NodesMask & Bit) == 0 &&
                    CanRestoreSite(State.Kills, State.NodesMask, Plan.Sites[Site]);
                FCheckpoint Attempt = State;
                const bool Restored = RestoreSite(Attempt, Site, Plan.Sites[Site], 3);
                Expect(Restored == Eligible, "site gate disagrees with authored requirements", Chapter);
                if (Restored)
                    State = Attempt;
                else
                    Expect(Attempt.NodesMask == State.NodesMask, "rejected site changed state", Chapter);
            }
            // This is a host-side checkpoint value round trip. Unreal's
            // SaveGameToSlot and world reconstruction need an in-engine test.
            const FCheckpoint Saved = State;
            Expect(CheckpointValid(Saved, Plan.KillsNeeded, Plan.Sites, 3), "checkpoint rejected after objective", Chapter);
            State = {Saved.Kills, Saved.NodesMask, Saved.Complete};
            Expect(CheckpointValid(State, Plan.KillsNeeded, Plan.Sites, 3), "checkpoint reload invalid", Chapter);
            if (Kills < Plan.KillsNeeded)
                Expect(!CanFinishChapter(State.Kills, Plan.KillsNeeded, State.NodesMask, 3), "premature exit", Chapter);
            if (Chapter == 7)
            {
                const bool AtBossMilestone = Kills == Plan.KillsNeeded - 1;
                Expect(CanSpawnFinalBoss(Chapter, State.Kills, Plan.KillsNeeded - 1, Plan.KillsNeeded) == AtBossMilestone,
                    "final boss spawn gate incorrect", Chapter);
            }
            else
                Expect(!CanSpawnFinalBoss(Chapter, State.Kills, Plan.KillsNeeded - 1, Plan.KillsNeeded),
                    "boss spawned outside final chapter", Chapter);
        }
        Expect(State.NodesMask == 7u, "not all authored sites restored", Chapter);
        Expect(CompleteChapter(State, Plan.KillsNeeded, 3), "completed objectives did not open exit", Chapter);
        Expect(State.Complete && CheckpointValid(State, Plan.KillsNeeded, Plan.Sites, 3),
            "complete checkpoint invalid", Chapter);
        Expect(!RecordDefeat(State, Plan.KillsNeeded), "defeat accepted after completion", Chapter);
        Expect(!CompleteChapter(State, Plan.KillsNeeded, 3), "chapter completed twice", Chapter);
        Expect(AdvanceChapter(Chapter, 7, State.Complete) == (Chapter < 7 ? Chapter + 1 : Chapter),
            "chapter advance incorrect", Chapter);
        Expect(CampaignLiberated(Chapter, 7, State.Complete) == (Chapter == 7),
            "liberation transition incorrect", Chapter);
        std::cout << "chapter " << Chapter + 1 << ": " << Plan.KillsNeeded
                  << " defeats, three sites, checkpoint and exit gates passed\n";
    }
    std::cout << "eight-chapter offline rules acceptance passed (host-only)\n";
}
