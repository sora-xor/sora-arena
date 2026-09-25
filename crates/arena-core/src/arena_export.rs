//! Machine-readable export of the kernel arena tables for presentation tools.
//! Unreal builds visuals on top of exactly this collision; it never supplies
//! its own. The checked-in copy is `crates/arena-core/data/arena-map-v1.json`
//! and `arena-cli arenas` prints the same bytes.
use crate::{
    RULES_VERSION,
    maps::{ARENAS, Arena, MIN_WALL_HEIGHT, Spawn},
    math::Aabb,
    simulation::{EYE_HEIGHT, HEIGHT, PAYLOAD_PUSH_RADIUS, RADIUS},
};
use std::fmt::Write;

pub const SCHEMA: &str = "sora-arena-arena-map-v1";

/// Deterministic JSON for every arena, in map id order. Labels are ASCII.
pub fn json() -> String {
    let mut out = String::new();
    out.push_str("{\n");
    field(&mut out, 1, "schema", &quoted(SCHEMA));
    field(&mut out, 1, "rules_version", &quoted(RULES_VERSION));
    field(
        &mut out,
        1,
        "units",
        &quoted(
            "millimetres, X forward, Y right, Z up; yaw in 1/65536 turns; \
             time in 60 Hz ticks",
        ),
    );
    field(
        &mut out,
        1,
        "player",
        &format!("{{\"radius\": {RADIUS}, \"height\": {HEIGHT}, \"eye_height\": {EYE_HEIGHT}}}"),
    );
    field(&mut out, 1, "min_wall_height", &MIN_WALL_HEIGHT.to_string());
    out.push_str("  \"arenas\": [\n");
    for (index, arena) in ARENAS.iter().enumerate() {
        write_arena(&mut out, arena);
        out.push_str(if index + 1 < ARENAS.len() {
            ",\n"
        } else {
            "\n"
        });
    }
    out.push_str("  ]\n}\n");
    out
}

fn write_arena(out: &mut String, a: &Arena) {
    out.push_str("    {\n");
    field(out, 3, "id", &a.id.to_string());
    field(out, 3, "slug", &quoted(a.slug));
    field(out, 3, "name", &quoted(a.name));
    field(out, 3, "map_digest", &quoted(&hex(&a.map_digest())));
    field(out, 3, "lanes_digest", &quoted(&hex(&a.lanes_digest())));
    let b = a.bounds;
    field(
        out,
        3,
        "bounds",
        &format!(
            "{{\"min_x\": {}, \"min_y\": {}, \"max_x\": {}, \"max_y\": {}}}",
            b.min_x, b.min_y, b.max_x, b.max_y
        ),
    );
    let walls = a
        .walls
        .iter()
        .enumerate()
        .map(|(index, w)| {
            format!(
                "{{\"index\": {index}, \"label\": {}, {}}}",
                quoted(w.label),
                corners(w.aabb)
            )
        })
        .collect::<Vec<_>>();
    array(out, 3, "walls", &walls, true);
    out.push_str("      \"spawns\": {\n");
    let spawns = |list: &[Spawn]| {
        list.iter()
            .map(|s| format!("{{\"x\": {}, \"y\": {}, \"yaw\": {}}}", s.x, s.y, s.yaw))
            .collect::<Vec<_>>()
    };
    array(out, 4, "team0", &spawns(&a.team_spawns[0]), true);
    array(out, 4, "team1", &spawns(&a.team_spawns[1]), true);
    array(out, 4, "ffa", &spawns(&a.ffa_spawns), false);
    out.push_str("      },\n");
    let c = a.control;
    field(
        out,
        3,
        "control",
        &format!(
            "{{\"x\": {}, \"y\": {}, \"radius\": {}}}",
            c.x, c.y, c.radius
        ),
    );
    out.push_str("      \"payload\": {\n");
    field(out, 4, "length", &a.route_length().to_string());
    field(out, 4, "push_radius", &PAYLOAD_PUSH_RADIUS.to_string());
    field(
        out,
        4,
        "checkpoints",
        &format!(
            "[{}, {}, {}]",
            a.checkpoints[0], a.checkpoints[1], a.checkpoints[2]
        ),
    );
    let route = a
        .route
        .iter()
        .map(|(x, y)| format!("[{x}, {y}]"))
        .collect::<Vec<_>>();
    array(out, 4, "route", &route, false);
    out.push_str("      },\n");
    let hazards = a
        .hazards
        .iter()
        .enumerate()
        .map(|(index, h)| {
            format!(
                "{{\"index\": {index}, \"label\": {}, \"kind\": {}, \"kind_id\": {}, {}, \
                 \"damage\": {}, \"period\": {}}}",
                quoted(h.label),
                quoted(h.kind.name()),
                h.kind as u8,
                corners(h.volume),
                h.damage,
                h.period
            )
        })
        .collect::<Vec<_>>();
    array(out, 3, "hazards", &hazards, true);
    let lanes = a
        .lanes
        .iter()
        .map(|lane| {
            let points = lane
                .points
                .iter()
                .map(|(x, y)| format!("[{x}, {y}]"))
                .collect::<Vec<_>>()
                .join(", ");
            format!(
                "{{\"name\": {}, \"points\": [{points}]}}",
                quoted(lane.name)
            )
        })
        .collect::<Vec<_>>();
    array(out, 3, "lanes", &lanes, false);
    out.push_str("    }");
}

fn corners(b: Aabb) -> String {
    format!(
        "\"min\": [{}, {}, {}], \"max\": [{}, {}, {}]",
        b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z
    )
}

fn field(out: &mut String, depth: usize, name: &str, value: &str) {
    let _ = writeln!(out, "{}\"{name}\": {value},", "  ".repeat(depth));
}

fn array(out: &mut String, depth: usize, name: &str, items: &[String], comma: bool) {
    let indent = "  ".repeat(depth);
    let _ = writeln!(out, "{indent}\"{name}\": [");
    for (index, item) in items.iter().enumerate() {
        let separator = if index + 1 < items.len() { "," } else { "" };
        let _ = writeln!(out, "{indent}  {item}{separator}");
    }
    let _ = writeln!(out, "{indent}]{}", if comma { "," } else { "" });
}

/// JSON string literal. Arena labels are printable ASCII; anything else is
/// escaped so the output stays valid.
fn quoted(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            c if (' '..='~').contains(&c) => out.push(c),
            c => {
                for unit in c.encode_utf16(&mut [0; 2]) {
                    let _ = write!(out, "\\u{unit:04x}");
                }
            }
        }
    }
    out.push('"');
    out
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}
