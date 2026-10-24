from dataclasses import dataclass

BASELINE_START = "08:00"
OFFSET_OPTIONS = (-15, -10, -5, 0, 5, 10, 15)
MAX_GROUP_SHIFT = {
    "G1": 0,
    "G2": 15,
    "G3": 15,
    "G4": 15,
    "G5": 15,
    "G6": 5,
}

@dataclass(frozen=True)
class StudentGroup:
    id: str
    name: str
    students: int
    sibling_pair: str | None = None

GROUPS = (
    StudentGroup("G1", "Kindergarten", 150),
    StudentGroup("G2", "Grades 1-2", 200),
    StudentGroup("G3", "Grades 3-4", 220, "SIBLING_A"),
    StudentGroup("G4", "Grades 5-6", 230, "SIBLING_A"),
    StudentGroup("G5", "Grades 7-8", 200),
    StudentGroup("G6", "Grades 9-10", 200),
)

MODE_SHARE = {
    "car": 0.30,
    "two_wheeler": 0.25,
    "auto_van": 0.15,
    "bus": 0.15,
    "walk_cycle": 0.15,
}


def validate_scenario():
    assert sum(g.students for g in GROUPS) == 1200
    assert sum(MODE_SHARE.values()) == 1.0
    assert len(GROUPS) == 6
    assert MAX_GROUP_SHIFT["G1"] == 0
    assert MAX_GROUP_SHIFT["G6"] == 5
    return True
