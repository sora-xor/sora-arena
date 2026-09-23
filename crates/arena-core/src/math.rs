//! Bounded integer geometry. No platform floating-point math affects outcomes.

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct Vec3 {
    pub x: i32,
    pub y: i32,
    pub z: i32,
}
impl Vec3 {
    pub const fn new(x: i32, y: i32, z: i32) -> Self {
        Self { x, y, z }
    }
    pub fn offset(self, other: Self) -> Self {
        Self::new(self.x + other.x, self.y + other.y, self.z + other.z)
    }
    pub fn delta(self, other: Self) -> Self {
        Self::new(self.x - other.x, self.y - other.y, self.z - other.z)
    }
    pub fn distance_squared(self, other: Self) -> i64 {
        let d = self.delta(other);
        i64::from(d.x) * i64::from(d.x)
            + i64::from(d.y) * i64::from(d.y)
            + i64::from(d.z) * i64::from(d.z)
    }
}

/// Fixed Bhaskara sine approximation, Q15. Defined exactly by integer division.
pub fn sin_q15(angle: u16) -> i32 {
    let angle = i64::from(angle);
    let (x, sign) = if angle > 32768 {
        (angle - 32768, -1)
    } else {
        (angle, 1)
    };
    let product = x * (32768 - x);
    (sign * 16 * product * 32767 / (5 * 32768_i64 * 32768 - 4 * product)) as i32
}
pub fn direction(yaw: u16, pitch: i16) -> Vec3 {
    let cp = i64::from(sin_q15((pitch as u16).wrapping_add(16384)));
    Vec3::new(
        (i64::from(sin_q15(yaw.wrapping_add(16384))) * cp / 32767) as i32,
        (i64::from(sin_q15(yaw)) * cp / 32767) as i32,
        sin_q15(pitch as u16),
    )
}
pub fn scale_q15(v: Vec3, length: i32) -> Vec3 {
    Vec3::new(
        (i64::from(v.x) * i64::from(length) / 32767) as i32,
        (i64::from(v.y) * i64::from(length) / 32767) as i32,
        (i64::from(v.z) * i64::from(length) / 32767) as i32,
    )
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Aabb {
    pub min: Vec3,
    pub max: Vec3,
}
impl Aabb {
    pub fn expanded(self, xy: i32, z: i32) -> Self {
        Self {
            min: Vec3::new(self.min.x - xy, self.min.y - xy, self.min.z - z),
            max: Vec3::new(self.max.x + xy, self.max.y + xy, self.max.z + z),
        }
    }
    pub fn contains(self, p: Vec3) -> bool {
        p.x >= self.min.x
            && p.x <= self.max.x
            && p.y >= self.min.y
            && p.y <= self.max.y
            && p.z >= self.min.z
            && p.z <= self.max.z
    }
    /// Nearest segment intersection as a Q20 fraction of the segment length.
    pub fn intersect(self, from: Vec3, to: Vec3) -> Option<i64> {
        let mut near = 0_i64;
        let mut far = 1_i64 << 20;
        for (start, end, min, max) in [
            (from.x, to.x, self.min.x, self.max.x),
            (from.y, to.y, self.min.y, self.max.y),
            (from.z, to.z, self.min.z, self.max.z),
        ] {
            let delta = i64::from(end) - i64::from(start);
            if delta == 0 {
                if start < min || start > max {
                    return None;
                }
                continue;
            }
            let a = ((i64::from(min) - i64::from(start)) << 20) / delta;
            let b = ((i64::from(max) - i64::from(start)) << 20) / delta;
            near = near.max(a.min(b));
            far = far.min(a.max(b));
            if near > far {
                return None;
            }
        }
        Some(near)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn cardinal_angles_are_exact() {
        assert_eq!(
            [sin_q15(0), sin_q15(16384), sin_q15(32768), sin_q15(49152)],
            [0, 32767, 0, -32767]
        );
        assert_eq!(direction(0, 0), Vec3::new(32767, 0, 0));
    }
    #[test]
    fn ray_boundaries_and_parallel_miss() {
        let a = Aabb {
            min: Vec3::new(10, -2, -2),
            max: Vec3::new(20, 2, 2),
        };
        assert_eq!(
            a.intersect(Vec3::default(), Vec3::new(40, 0, 0)),
            Some(1 << 18)
        );
        assert_eq!(a.intersect(Vec3::new(0, 4, 0), Vec3::new(40, 4, 0)), None);
        assert_eq!(
            a.intersect(Vec3::new(12, 0, 0), Vec3::new(15, 0, 0)),
            Some(0)
        );
    }
    #[test]
    fn sine_is_bounded_for_every_input() {
        for a in 0..=u16::MAX {
            assert!(sin_q15(a).abs() <= 32767);
        }
    }
}
