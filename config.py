from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

OIL_LIMIT = 0.1
MOISTURE_LIMIT = 89.0
PARTICLE_LIMITS = {
    "0.5": {"A": 23, "B": 627, "C": 23402, "D": 141390},
    "5.0": {"A": 4, "B": 13, "C": 1540, "D": 8183},
}

TEST_TYPES = {
    "oil": {
        "label": "Oil Content Measurement",
        "filename": "Oil Content Measurement Log (유분 측정 일지).xlsx",
    },
    "moisture": {
        "label": "Moisture Content Measurement",
        "filename": "Moisture Content Measurement Log (수분 측정 일지).xlsx",
    },
    "airborne": {
        "label": "Airborne Particle Measurement",
        "filename": "Airborne Particle Measurement Log (부유입자 측정 일지).xlsx",
    },
}
