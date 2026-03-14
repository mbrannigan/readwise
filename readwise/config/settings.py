"""
User settings: persisted as JSON in the platform app data directory.
"""
from __future__ import annotations

import json
from pathlib import Path

from readwise.db.database import get_app_data_dir

SETTINGS_FILE = get_app_data_dir() / "settings.json"

DEFAULTS: dict = {
    "calibre_library_path": "",
    "obsidian_vault_path": "",
    "default_chunk_strategy": "CHAPTERS",
    "default_chunk_size": 1,
    "words_per_minute": 250,
    "card_progress_style": "bar",   # bar | bar_pct | pct
    "theme": "light",               # light | dark | sepia
    "daily_reminder_enabled": False,
    "daily_reminder_time": "20:00",
}


class Settings:
    _instance: "Settings | None" = None

    def __init__(self) -> None:
        self._data: dict = dict(DEFAULTS)
        self._load()

    @classmethod
    def get(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance

    def _load(self) -> None:
        if SETTINGS_FILE.exists():
            try:
                stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        SETTINGS_FILE.write_text(
            json.dumps(self._data, indent=2), encoding="utf-8"
        )

    def __getattr__(self, key: str):
        if key.startswith("_"):
            raise AttributeError(key)
        if key in self._data:
            return self._data[key]
        raise AttributeError(f"Unknown setting: {key}")

    def __setattr__(self, key: str, value) -> None:
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value
            self.save()

    def get_value(self, key: str, default=None):
        return self._data.get(key, default)
