//! Test-only adapter comparing the kernel's internal death application with an
//! independent, exact-rational Python settlement model. Never accepts game input.
use super::{Account, Allocation, apply_death, conserved};
use std::{path::PathBuf, process::Command};

fn fields(line: &str) -> Vec<&str> {
    line.split('\t').collect()
}

fn csv_u64(value: &str) -> Vec<u64> {
    if value == "-" {
        return Vec::new();
    }
    value.split(',').map(|n| n.parse().unwrap()).collect()
}

fn csv_usize(value: &str) -> Vec<usize> {
    if value == "-" {
        return Vec::new();
    }
    value.split(',').map(|n| n.parse().unwrap()).collect()
}

fn csv_pairs_u32(value: &str) -> Vec<(usize, u32)> {
    if value == "-" {
        return Vec::new();
    }
    value
        .split(',')
        .map(|entry| {
            let (slot, amount) = entry.split_once(':').unwrap();
            (slot.parse().unwrap(), amount.parse().unwrap())
        })
        .collect()
}

fn csv_allocations(value: &str) -> Vec<Allocation> {
    if value == "-" {
        return Vec::new();
    }
    value
        .split(',')
        .map(|entry| {
            let (slot, amount) = entry.split_once(':').unwrap();
            Allocation {
                slot: slot.parse().unwrap(),
                amount: amount.parse().unwrap(),
            }
        })
        .collect()
}

fn account_snapshot(value: &str) -> Vec<Account> {
    value
        .split(';')
        .map(|entry| {
            let mut n = entry.split(':').map(|v| v.parse::<u64>().unwrap());
            Account {
                initial: n.next().unwrap(),
                remaining: n.next().unwrap(),
                earnings: n.next().unwrap(),
                kills: n.next().unwrap().try_into().unwrap(),
                deaths: n.next().unwrap().try_into().unwrap(),
                paid_deaths: n.next().unwrap().try_into().unwrap(),
            }
        })
        .collect()
}

#[test]
fn exact_fraction_oracle_matches_adversarial_death_transfers() {
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../scripts/qualification/payout_oracle.py");
    let output = Command::new("python3")
        .arg(&script)
        .output()
        .unwrap_or_else(|error| panic!("could not run {}: {error}", script.display()));
    assert!(
        output.status.success(),
        "independent payout oracle failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let transcript = String::from_utf8(output.stdout).unwrap();
    let mut accounts = Vec::new();
    let mut case = String::new();
    let mut events = 0usize;
    let mut cases = 0usize;
    let mut errors = 0usize;

    for line in transcript.lines() {
        let row = fields(line);
        match row.as_slice() {
            ["CASE", name, bonds] => {
                assert!(accounts.is_empty(), "previous case did not end");
                case = (*name).to_owned();
                accounts = csv_u64(bonds).into_iter().map(Account::new).collect();
                assert!(!accounts.is_empty());
                cases += 1;
            }
            [
                "EVENT",
                victim,
                killer,
                assists,
                teammates,
                mode,
                status,
                awards,
                expected,
            ] => {
                assert!(!accounts.is_empty(), "event before case");
                let victim = victim.parse().unwrap();
                let killer = (killer != &"-").then(|| killer.parse().unwrap());
                let assists = csv_pairs_u32(assists);
                let teammates = csv_usize(teammates);
                let team_mode = match *mode {
                    "T" => true,
                    "F" => false,
                    other => panic!("unknown mode: {other}"),
                };
                let before = accounts.clone();
                let got = apply_death(
                    &mut accounts,
                    victim,
                    killer,
                    &assists,
                    &teammates,
                    team_mode,
                );
                match *status {
                    "OK" => assert_eq!(
                        got.unwrap(),
                        csv_allocations(awards),
                        "allocation mismatch in {case} event {events}"
                    ),
                    "ERR" => {
                        assert!(
                            got.is_err(),
                            "invalid event accepted in {case} event {events}"
                        );
                        assert_eq!(accounts, before, "failed event mutated {case}");
                        errors += 1;
                    }
                    other => panic!("unknown status: {other}"),
                }
                assert_eq!(
                    accounts,
                    account_snapshot(expected),
                    "account mismatch in {case} event {events}"
                );
                assert!(conserved(&accounts), "kernel value leaked in {case}");
                events += 1;
            }
            ["END", refunds, earnings] => {
                assert!(!accounts.is_empty(), "end before case");
                assert_eq!(
                    accounts.iter().map(|a| a.remaining).collect::<Vec<_>>(),
                    csv_u64(refunds),
                    "reserve refund mismatch in {case}"
                );
                assert_eq!(
                    accounts.iter().map(|a| a.earnings).collect::<Vec<_>>(),
                    csv_u64(earnings),
                    "earned payout mismatch in {case}"
                );
                let deposited = accounts.iter().map(|a| u128::from(a.initial)).sum::<u128>();
                let returned = accounts
                    .iter()
                    .map(|a| u128::from(a.remaining) + u128::from(a.earnings))
                    .sum::<u128>();
                assert_eq!(deposited, returned, "final settlement mismatch in {case}");
                accounts.clear();
            }
            other => panic!("invalid oracle record: {other:?}"),
        }
    }
    assert!(accounts.is_empty(), "last case did not end");
    assert!(cases >= 50 && events >= 500 && errors >= 2);
}
