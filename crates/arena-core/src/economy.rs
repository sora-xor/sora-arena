//! Exact bounded death transfers. The proof adapter must authenticate every event.
use crate::Error;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Account {
    pub initial: u64,
    pub remaining: u64,
    pub earnings: u64,
    pub kills: u32,
    pub deaths: u32,
    pub paid_deaths: u32,
}
impl Account {
    pub fn new(bond: u64) -> Self {
        Self {
            initial: bond,
            remaining: bond,
            earnings: 0,
            kills: 0,
            deaths: 0,
            paid_deaths: 0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Allocation {
    pub slot: usize,
    pub amount: u64,
}

/// Allocate a quantity proportionally; distribute residual atomic units by slot.
fn divide(amount: u64, weighted: &[(usize, u64)], credits: &mut [u64]) -> Result<(), Error> {
    if amount == 0 {
        return Ok(());
    }
    let sum: u128 = weighted.iter().map(|(_, w)| u128::from(*w)).sum();
    if sum == 0 {
        return Err(Error::InvalidInput("empty allocation recipients"));
    }
    let mut used = 0u64;
    for &(slot, w) in weighted {
        let value = (u128::from(amount) * u128::from(w) / sum) as u64;
        credits[slot] = credits[slot].checked_add(value).ok_or(Error::Arithmetic)?;
        used = used.checked_add(value).ok_or(Error::Arithmetic)?;
    }
    let mut remainder = amount - used;
    for &(slot, weight) in weighted {
        if remainder == 0 {
            break;
        }
        if weight > 0 {
            credits[slot] = credits[slot].checked_add(1).ok_or(Error::Arithmetic)?;
            remainder -= 1;
        }
    }
    if remainder != 0 {
        return Err(Error::Arithmetic);
    }
    Ok(())
}

/// Pure allocation calculation; sorted participant slots make rounding canonical.
pub fn death_allocations(
    amount: u64,
    killer: usize,
    assists: &[(usize, u32)],
    teammates: &[usize],
    player_count: usize,
    team_mode: bool,
) -> Result<Vec<Allocation>, Error> {
    if killer >= player_count || player_count > crate::MAX_PLAYERS {
        return Err(Error::InvalidInput("invalid killer"));
    }
    let mut assist_weights = Vec::new();
    for &(slot, damage) in assists {
        if slot >= player_count
            || slot == killer
            || damage == 0
            || assist_weights.iter().any(|&(s, _)| s == slot)
        {
            return Err(Error::InvalidInput("invalid or duplicate assist"));
        }
        assist_weights.push((slot, u64::from(damage)));
    }
    assist_weights.sort_unstable_by_key(|x| x.0);
    let mut team_weights = Vec::new();
    for &slot in teammates {
        if slot >= player_count || slot == killer || team_weights.iter().any(|&(s, _)| s == slot) {
            return Err(Error::InvalidInput("invalid or duplicate team member"));
        }
        team_weights.push((slot, 1));
    }
    team_weights.sort_unstable_by_key(|x| x.0);
    if !team_mode && !team_weights.is_empty() {
        return Err(Error::InvalidInput("FFA team allocation"));
    }
    // Combine exact rational shares before rounding. Rounding the categories
    // first would unfairly award their residual units to the killer rather
    // than the lowest eligible permanent participant slots.
    let mut groups = [
        if team_mode { 60u64 } else { 80 },
        20,
        if team_mode { 20 } else { 0 },
    ];
    if assist_weights.is_empty() {
        if team_mode {
            groups[2] += groups[1];
        } else {
            groups[0] += groups[1];
        }
        groups[1] = 0;
    }
    if team_weights.is_empty() {
        groups[0] += groups[2];
        groups[2] = 0;
    }
    let assist_sum = assist_weights.iter().map(|(_, w)| *w).sum::<u64>().max(1);
    let team_count = (team_weights.len() as u64).max(1);
    let mut weights = vec![0u64; player_count];
    weights[killer] = groups[0] * assist_sum * team_count;
    for &(slot, damage) in &assist_weights {
        weights[slot] += groups[1] * damage * team_count;
    }
    for &(slot, _) in &team_weights {
        weights[slot] += groups[2] * assist_sum;
    }
    let ordered = weights
        .into_iter()
        .enumerate()
        .filter(|(_, w)| *w > 0)
        .collect::<Vec<_>>();
    let mut credits = vec![0; player_count];
    divide(amount, &ordered, &mut credits)?;
    Ok(credits
        .into_iter()
        .enumerate()
        .filter_map(|(slot, amount)| (amount > 0).then_some(Allocation { slot, amount }))
        .collect())
}

/// Apply an execution-derived death atomically. Never an externally trusted kill API.
pub(crate) fn apply_death(
    accounts: &mut [Account],
    victim: usize,
    killer: Option<usize>,
    assists: &[(usize, u32)],
    teammates: &[usize],
    team_mode: bool,
) -> Result<Vec<Allocation>, Error> {
    if victim >= accounts.len()
        || killer == Some(victim)
        || killer.is_some_and(|k| k >= accounts.len())
    {
        return Err(Error::InvalidInput("invalid death slots"));
    }
    let mut next = accounts.to_vec();
    next[victim].deaths = next[victim]
        .deaths
        .checked_add(1)
        .ok_or(Error::Arithmetic)?;
    let Some(killer) = killer else {
        accounts.clone_from_slice(&next);
        return Ok(Vec::new());
    };
    next[killer].kills = next[killer].kills.checked_add(1).ok_or(Error::Arithmetic)?;
    let tranche = next[victim].initial / 10;
    if tranche == 0 {
        accounts.clone_from_slice(&next);
        return Ok(Vec::new());
    }
    if next[victim].remaining < tranche || next[victim].paid_deaths >= 10 {
        return Err(Error::InvalidInput("exhausted victim"));
    }
    if assists.iter().any(|(s, _)| *s == victim) || teammates.contains(&victim) {
        return Err(Error::InvalidInput(
            "victim cannot receive own death transfer",
        ));
    }
    let credits = death_allocations(tranche, killer, assists, teammates, next.len(), team_mode)?;
    next[victim].remaining -= tranche;
    next[victim].paid_deaths += 1;
    for a in &credits {
        next[a.slot].earnings = next[a.slot]
            .earnings
            .checked_add(a.amount)
            .ok_or(Error::Arithmetic)?;
    }
    if !conserved(&next) {
        return Err(Error::Arithmetic);
    }
    accounts.clone_from_slice(&next);
    Ok(credits)
}

pub fn conserved(accounts: &[Account]) -> bool {
    let initial: u128 = accounts.iter().map(|a| u128::from(a.initial)).sum();
    let final_value: u128 = accounts
        .iter()
        .map(|a| u128::from(a.remaining) + u128::from(a.earnings))
        .sum();
    initial == final_value
        && accounts
            .iter()
            .all(|a| a.remaining <= a.initial && a.paid_deaths <= 10)
}

#[cfg(test)]
#[path = "economy_reference_qualification.rs"]
mod reference_qualification;

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn residual_units_follow_permanent_slots_not_reward_category() {
        assert_eq!(
            death_allocations(1, 2, &[(0, 1)], &[], 3, false).unwrap(),
            vec![Allocation { slot: 0, amount: 1 }]
        );
    }
    #[test]
    fn split_supports_unequal_bonds_and_never_rerisks_earnings() {
        let mut a = vec![
            Account::new(1000),
            Account::new(2000),
            Account::new(1000),
            Account::new(1000),
        ];
        let awards = apply_death(&mut a, 1, Some(0), &[(2, 70)], &[2, 3], true).unwrap();
        assert_eq!(
            awards,
            vec![
                Allocation {
                    slot: 0,
                    amount: 120
                },
                Allocation {
                    slot: 2,
                    amount: 60
                },
                Allocation {
                    slot: 3,
                    amount: 20
                }
            ]
        );
        apply_death(&mut a, 0, Some(1), &[], &[], true).unwrap();
        assert_eq!(a[0].earnings, 120);
        assert_eq!(a[0].remaining, 900);
        assert!(conserved(&a));
    }
    #[test]
    fn all_atomic_amounts_are_conserved() {
        for amount in 0..2000 {
            for team in [false, true] {
                let tm = if team { vec![2, 3, 4] } else { vec![] };
                let a = death_allocations(amount, 0, &[(1, 1), (2, 17)], &tm, 6, team).unwrap();
                assert_eq!(a.iter().map(|x| x.amount).sum::<u64>(), amount);
            }
        }
    }
    #[test]
    fn missing_assists_go_to_team() {
        assert_eq!(
            death_allocations(100, 0, &[], &[1, 2], 3, true).unwrap(),
            vec![
                Allocation {
                    slot: 0,
                    amount: 60
                },
                Allocation {
                    slot: 1,
                    amount: 20
                },
                Allocation {
                    slot: 2,
                    amount: 20
                }
            ]
        );
    }
    #[test]
    fn exhausted_reserve_cannot_be_debited() {
        let mut a = vec![Account::new(100), Account::new(100)];
        for _ in 0..10 {
            apply_death(&mut a, 0, Some(1), &[], &[], false).unwrap();
        }
        let before = a.clone();
        assert!(apply_death(&mut a, 0, Some(1), &[], &[], false).is_err());
        assert_eq!(a, before);
        assert_eq!(a[1].earnings, 100);
    }
    #[test]
    fn environmental_death_does_not_move_value() {
        let mut a = vec![Account::new(100), Account::new(100)];
        apply_death(&mut a, 0, None, &[], &[], false).unwrap();
        assert_eq!(a[0].remaining, 100);
        assert_eq!(a[0].paid_deaths, 0);
    }
    #[test]
    fn duplicates_and_invalid_recipients_reject() {
        assert!(death_allocations(100, 0, &[(1, 2), (1, 3)], &[], 3, false).is_err());
        assert!(death_allocations(100, 0, &[], &[0], 3, true).is_err());
    }
}
