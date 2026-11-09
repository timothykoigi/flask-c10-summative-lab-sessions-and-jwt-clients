import os
from pathlib import Path

# Project root: config.py is at <root>/server/App/config.py
BASE_DIR = Path(__file__).resolve().parents[2]
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "development-only-secret-key-change-before-deploying"
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'shifts.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False