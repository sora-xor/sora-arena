//! The single canonical outcome-state encoder (docs/combat-rules.md §12).
//! Both exported bytes and the replay digest consume this stream. Exhaustive
//! destructuring makes every newly added state field an explicit review point.
use super::abilities::Entity;
use super::{Config, Player, Projectile, Winner, World};
use crate::{economy::Account, math::Vec3, simulation::DamageRecord};

pub(super) fn encode(world: &World, mut emit: impl FnMut(&[u8])) {
    let World {
        config,
        tick,
        players,
        accounts,
        projectiles,
        entities,
        // These are the last step's presentation output, never future inputs.
        removed_entities: _,
        events: _,
        next_entity_id,
        damage_history,
        terminal,
        score,
        control_owner,
        control_progress,
        overtime,
        payload_progress,
        payload_checkpoints,
        payload_idle,
        winner,
    } = world;
    assert_eq!(
        players.len(),
        accounts.len(),
        "canonical state requires one account per permanent player slot"
    );
    let Config {
        mode,
        map,
        max_ticks,
        base_bond,
        offline,
    } = config;

    emit(b"sora-arena:reference-state:v2\0");
    emit(crate::RULES_VERSION.as_bytes());
    emit(&[*mode as u8, *map, *offline as u8]);
    emit(&max_ticks.to_le_bytes());
    emit(&base_bond.to_le_bytes());
    emit(&tick.to_le_bytes());
    emit(&[*terminal as u8]);
    emit(&world.arena().map_digest());
    emit(&(players.len() as u32).to_le_bytes());
    for (player, account) in players.iter().zip(accounts) {
        let Player {
            team,
            class,
            weapon,
            position,
            velocity_z,
            yaw,
            pitch,
            health,
            stamina,
            alive,
            respawn_ticks,
            attack_cooldown,
            ability_cooldown,
            charge,
            charge_weapon,
            ammo,
            reload_ticks,
            guarding,
            guard_ticks,
            spawn_protection,
            admitted_special,
            pending_loadout,
            stance_ticks,
            marked_ticks,
        } = player;
        let Account {
            initial,
            remaining,
            earnings,
            kills,
            deaths,
            paid_deaths,
        } = account;
        let (pending_class, pending_weapon) = pending_loadout.unwrap_or((255, 255));
        emit(&[
            *team,
            *class,
            *weapon,
            *alive as u8,
            *guarding as u8,
            admitted_special.unwrap_or(255),
            pending_class,
            pending_weapon,
        ]);
        let Vec3 { x, y, z } = position;
        for value in [x, y, z, velocity_z, health, stamina] {
            emit(&value.to_le_bytes());
        }
        emit(&yaw.to_le_bytes());
        emit(&pitch.to_le_bytes());
        emit(&respawn_ticks.to_le_bytes());
        emit(&[*charge_weapon]);
        for value in [
            attack_cooldown,
            ability_cooldown,
            charge,
            ammo,
            reload_ticks,
            guard_ticks,
            spawn_protection,
            stance_ticks,
            marked_ticks,
        ] {
            emit(&value.to_le_bytes());
        }
        for value in [initial, remaining, earnings] {
            emit(&value.to_le_bytes());
        }
        for value in [kills, deaths, paid_deaths] {
            emit(&value.to_le_bytes());
        }
    }
    emit(&(projectiles.len() as u32).to_le_bytes());
    for projectile in projectiles {
        let Projectile {
            id,
            owner,
            position,
            velocity,
            weapon,
            traveled,
            age,
        } = projectile;
        emit(&id.to_le_bytes());
        emit(&(*owner as u32).to_le_bytes());
        emit(&[*weapon]);
        let Vec3 { x, y, z } = position;
        let Vec3 {
            x: vx,
            y: vy,
            z: vz,
        } = velocity;
        for value in [x, y, z, vx, vy, vz, traveled] {
            emit(&value.to_le_bytes());
        }
        emit(&age.to_le_bytes());
    }
    emit(&(entities.len() as u32).to_le_bytes());
    for entity in entities {
        let Entity {
            id,
            kind,
            owner,
            team,
            position,
            yaw,
            health,
            age,
            half_x,
            half_y,
        } = entity;
        emit(&id.to_le_bytes());
        emit(&[*kind as u8]);
        emit(&(*owner as u32).to_le_bytes());
        emit(&[*team]);
        let Vec3 { x, y, z } = position;
        for value in [x, y, z] {
            emit(&value.to_le_bytes());
        }
        emit(&yaw.to_le_bytes());
        emit(&health.to_le_bytes());
        emit(&age.to_le_bytes());
        for value in [half_x, half_y] {
            emit(&value.to_le_bytes());
        }
    }
    emit(&next_entity_id.to_le_bytes());
    emit(&(damage_history.len() as u32).to_le_bytes());
    for record in damage_history {
        let DamageRecord {
            tick,
            attacker,
            victim,
            damage,
        } = record;
        for value in [*tick, *attacker as u32, *victim as u32, *damage] {
            emit(&value.to_le_bytes());
        }
    }
    for value in score {
        emit(&value.to_le_bytes());
    }
    emit(&[control_owner.unwrap_or(255)]);
    emit(&control_progress.to_le_bytes());
    emit(&[*overtime as u8]);
    emit(&payload_progress.to_le_bytes());
    emit(&[*payload_checkpoints]);
    emit(&payload_idle.to_le_bytes());
    let (tag, value) = match winner {
        None => (0u8, 0u32),
        Some(Winner::Team(team)) => (1, u32::from(*team)),
        Some(Winner::Slot(slot)) => (2, *slot as u32),
        Some(Winner::Draw) => (3, 0),
    };
    emit(&[tag]);
    emit(&value.to_le_bytes());
}
