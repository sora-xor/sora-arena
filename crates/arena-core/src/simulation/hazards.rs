//! Environmental hazards (docs/combat-rules.md §9): arena floor volumes that
//! pulse damage. They never block movement, rays, projectiles or sight.
use super::{DamageKind, PendingDamage, Source, World};
use crate::{maps::Hazard, math::Vec3};

/// A position stands in a hazard when its x and y lie in the volume's closed
/// rectangle and its z is within the volume's height.
pub(super) fn inside(hazard: &Hazard, position: Vec3) -> bool {
    let v = hazard.volume;
    (v.min.x..=v.max.x).contains(&position.x)
        && (v.min.y..=v.max.y).contains(&position.y)
        && (v.min.z..=v.max.z).contains(&position.z)
}

impl World {
    /// §2 phase 8: on ticks where `tick % period == 0`, every living player
    /// without spawn protection inside a hazard takes its damage, in slot
    /// order and then hazard order. Hazard hits have no origin.
    pub(super) fn hazard_phase(&self, damage: &mut Vec<PendingDamage>) {
        let hazards = self.arena().hazards;
        for (slot, p) in self.players.iter().enumerate() {
            if !p.alive || p.spawn_protection > 0 {
                continue;
            }
            for (index, hazard) in hazards.iter().enumerate() {
                if self.tick.is_multiple_of(u32::from(hazard.period)) && inside(hazard, p.position)
                {
                    damage.push(PendingDamage {
                        source: Source::Hazard(index as u8),
                        victim: slot,
                        amount: hazard.damage,
                        weapon: 255,
                        origin: None,
                        kind: DamageKind::Hazard,
                        penetrating: false,
                    });
                }
            }
        }
    }
}
