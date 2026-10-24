import unittest
from app.planner import validate_offsets, validate_zone_assignments, search_plans

VALID_OFFSETS = {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0, "G6": 0}
VALID_ZONES = {"car": "Z3", "two_wheeler": "Z1", "auto_van": "Z2", "bus": "Z4"}

class PlannerTests(unittest.TestCase):
    def test_g1_cannot_move(self):
        offsets = {**VALID_OFFSETS, "G1": 5}
        self.assertTrue(validate_offsets(offsets))

    def test_g6_cannot_shift_beyond_five(self):
        offsets = {**VALID_OFFSETS, "G6": 10}
        self.assertTrue(validate_offsets(offsets))

    def test_sibling_groups_must_match(self):
        offsets = {**VALID_OFFSETS, "G3": 5, "G4": 0}
        self.assertTrue(validate_offsets(offsets))

    def test_zone_vehicle_compatibility(self):
        zones = {**VALID_ZONES, "bus": "Z3"}
        self.assertTrue(validate_zone_assignments(zones))

    def test_unknown_zone_rejected(self):
        zones = {**VALID_ZONES, "car": "UNKNOWN"}
        self.assertTrue(validate_zone_assignments(zones))

    def test_search_is_repeatable(self):
        first = search_plans(limit=10)
        second = search_plans(limit=10)
        self.assertEqual(first, second)

if __name__ == "__main__":
    unittest.main(verbosity=2)
