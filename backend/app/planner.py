from itertools import product

from app.scenario import GROUPS, OFFSET_OPTIONS, MAX_GROUP_SHIFT
from app.zones import ZONES, VEHICLE_OCCUPANCY, DWELL_SECONDS

GROUP_IDS = [g.id for g in GROUPS]
STUDENTS = {g.id: g.students for g in GROUPS}
VEHICLES = ("car", "two_wheeler", "auto_van", "bus")
BIN_MINUTES = 5
PEAK_START = -15
PEAK_END = 20


def vehicle_counts(group_id):
    n = STUDENTS[group_id]
    return {
        "car": round(n * 0.30 / VEHICLE_OCCUPANCY["car"]),
        "two_wheeler": round(n * 0.25 / VEHICLE_OCCUPANCY["two_wheeler"]),
        "auto_van": round(n * 0.15 / VEHICLE_OCCUPANCY["auto_van"]),
        "bus": round(n * 0.15 / VEHICLE_OCCUPANCY["bus"]),
    }


GROUP_VEHICLES = {g: vehicle_counts(g) for g in GROUP_IDS}


def validate_offsets(offsets):
    errors = []
    if not isinstance(offsets, dict) or set(offsets) != set(GROUP_IDS):
        return ["Offsets must be supplied for exactly G1-G6."]

    for gid in GROUP_IDS:
        value = offsets[gid]
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{gid}: offset must be an integer.")
            continue
        allowed = [
            x for x in OFFSET_OPTIONS
            if abs(x) <= MAX_GROUP_SHIFT[gid]
        ]
        if value not in allowed:
            errors.append(
                f"{gid}: offset {value} is outside allowed values {allowed}."
            )

    if all(isinstance(offsets[g], int) and not isinstance(offsets[g], bool)
           for g in ("G3", "G4")):
        if offsets["G3"] != offsets["G4"]:
            errors.append("G3 and G4 must have the same offset.")

    return errors


def validate_zone_assignments(assignments, demand=None):
    errors = []
    if not isinstance(assignments, dict) or set(assignments) != set(VEHICLES):
        return ["Assign every vehicle type to exactly one zone."]

    for vehicle, zone_id in assignments.items():
        if zone_id not in ZONES:
            errors.append(f"{vehicle}: unknown zone {zone_id}.")
        elif vehicle not in ZONES[zone_id]["allowed"]:
            errors.append(f"{vehicle}: incompatible with {zone_id}.")

    if demand is not None:
        for zone_id, zone in ZONES.items():
            used = sum(
                demand.get(vehicle, 0)
                for vehicle, assigned_zone in assignments.items()
                if assigned_zone == zone_id
            )
            if used > zone["capacity"]:
                errors.append(
                    f"{zone_id}: projected demand {used} exceeds capacity "
                    f"{zone['capacity']}."
                )

    return errors


def disruption(offsets):
    return sum(STUDENTS[g] * abs(offsets[g]) for g in GROUP_IDS)


def planning_estimate(offsets, assignments):
    errors = validate_offsets(offsets) + validate_zone_assignments(assignments)
    if errors:
        return None

    peak_queue = 0
    total_delay_vehicle_minutes = 0.0
    max_occupancy = {zone_id: 0 for zone_id in ZONES}
    capacity_violations = []

    # Each group arrival is distributed deterministically across its
    # assigned vehicle types. Walk/cycle students create no vehicles.
    for zone_id, zone in ZONES.items():
        assigned = [
            vehicle for vehicle in VEHICLES
            if assignments[vehicle] == zone_id
        ]
        if not assigned:
            continue

        occupancy = [0] * (PEAK_END - PEAK_START + 1)
        queue = [0] * len(occupancy)

        for gid in GROUP_IDS:
            arrival_minute = offsets[gid]
            index = arrival_minute - PEAK_START
            if not 0 <= index < len(occupancy):
                continue

            for vehicle in assigned:
                count = GROUP_VEHICLES[gid][vehicle]
                dwell_bins = max(
                    1, (DWELL_SECONDS[vehicle] + BIN_MINUTES * 60 - 1)
                    // (BIN_MINUTES * 60)
                )
                for step in range(index, min(index + dwell_bins, len(occupancy))):
                    occupancy[step] += count

        for i, count in enumerate(occupancy):
            max_occupancy[zone_id] = max(max_occupancy[zone_id], count)
            peak_queue = max(peak_queue, max(0, count - zone["capacity"]))
            if count > zone["capacity"]:
                capacity_violations.append({
                    "zone_id": zone_id,
                    "minute": PEAK_START + i,
                    "occupancy": count,
                    "capacity": zone["capacity"],
                })
                queue[i] = count - zone["capacity"]
            total_delay_vehicle_minutes += queue[i] * BIN_MINUTES

    return {
        "estimated_delay": round(total_delay_vehicle_minutes, 2),
        "estimated_peak_queue": peak_queue,
        "estimated_max_zone_occupancy": max_occupancy,
        "estimated_capacity_violations": capacity_violations,
        "metric_source": "Deterministic planning estimate; not SUMO output",
    }


def pareto_front(plans):
    result = []
    for candidate in plans:
        dominated = any(
            other["disruption"] <= candidate["disruption"]
            and other["estimated_delay"] <= candidate["estimated_delay"]
            and (
                other["disruption"] < candidate["disruption"]
                or other["estimated_delay"] < candidate["estimated_delay"]
            )
            for other in plans
        )
        if not dominated:
            result.append(candidate)
    return result


def search_plans(assignments=None, limit=100):
    assignments = assignments or {
        "car": "Z3",
        "two_wheeler": "Z1",
        "auto_van": "Z2",
        "bus": "Z4",
    }
    errors = validate_zone_assignments(assignments)
    if errors:
        raise ValueError("; ".join(errors))

    options = {
        "G1": (0,),
        "G2": OFFSET_OPTIONS,
        "G3": OFFSET_OPTIONS,
        "G4": OFFSET_OPTIONS,
        "G5": OFFSET_OPTIONS,
        "G6": (-5, 0, 5),
    }

    plans = []
    for values in product(*(options[g] for g in GROUP_IDS)):
        offsets = dict(zip(GROUP_IDS, values))
        if validate_offsets(offsets):
            continue
        estimate = planning_estimate(offsets, assignments)
        if estimate is None:
            continue
        plans.append({
            "offsets": offsets,
            "zone_assignments": dict(assignments),
            "disruption": disruption(offsets),
            **estimate,
        })

    front = pareto_front(plans)
    front.sort(key=lambda p: (
        p["disruption"],
        p["estimated_delay"],
        tuple(p["offsets"][g] for g in GROUP_IDS),
    ))
    return {
        "feasible_count": len(plans),
        "pareto_count": len(front),
        "plans": front[:limit],
    }
