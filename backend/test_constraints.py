from app.planner import validate_offsets, validate_zone_assignments

valid = {
    "G1": 0,
    "G2": 0,
    "G3": 5,
    "G4": 5,
    "G5": 0,
    "G6": 0,
}

tests = [
    ("Frozen G1 moved", {**valid, "G1": 5}, None, "G1"),
    ("G6 beyond limit", {**valid, "G6": 10}, None, "G6"),
    ("Sibling mismatch", {**valid, "G4": 0}, None, "G3 and G4"),
    ("Incompatible zone", valid, {"car": "Z4", "two_wheeler": "Z1", "auto_van": "Z2", "bus": "Z3"}, "incompatible"),
    ("Over-capacity zone", valid, {"car": "Z3", "two_wheeler": "Z3", "auto_van": "Z3", "bus": "Z4"}, "capacity"),
]

for name, offsets, zones, expected in tests:
    errors = validate_offsets(offsets)
    if zones:
        errors += validate_zone_assignments(zones, {"car": 20, "two_wheeler": 10, "auto_van": 5, "bus": 2})
    passed = bool(errors) and expected.lower() in " ".join(errors).lower()
    print(f"{'PASS' if passed else 'FAIL'}: {name}")
    if not passed:
        print("  Errors:", errors)
