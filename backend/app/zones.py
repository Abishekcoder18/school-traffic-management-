ZONES = {
    "Z1": {
        "name": "Main gate kerb",
        "capacity": 10,
        "allowed": ["car", "two_wheeler"],
    },
    "Z2": {
        "name": "Side lane",
        "capacity": 3,
        "allowed": ["car", "two_wheeler", "auto_van"],
    },
    "Z3": {
        "name": "Rear lot",
        "capacity": 12,
        "allowed": ["car", "two_wheeler", "auto_van"],
    },
    "Z4": {
        "name": "Bus bay",
        "capacity": 4,
        "allowed": ["bus"],
    },
}

VEHICLE_OCCUPANCY = {
    "car": 1.5,
    "two_wheeler": 1,
    "auto_van": 5,
    "bus": 30,
}

DWELL_SECONDS = {
    "car": 90,
    "two_wheeler": 45,
    "auto_van": 120,
    "bus": 180,
}
