"""Small atomic JSON store for the demo's shared school-map annotations."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from app.models.map_annotations import MapAnnotations


class MapStateStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = RLock()

    def _read(self) -> dict:
        if not self.path.exists():
            return {"activePlaceId": None, "annotations": {}}
        with self.path.open(encoding="utf-8") as state_file:
            data = json.load(state_file)
        if not isinstance(data, dict) or not isinstance(data.get("annotations", {}), dict):
            raise ValueError("Map state file has an invalid structure.")
        data.setdefault("activePlaceId", None)
        data.setdefault("annotations", {})
        return data

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as state_file:
                temporary_path = state_file.name
                json.dump(data, state_file, ensure_ascii=False, separators=(",", ":"))
                state_file.flush()
                os.fsync(state_file.fileno())
            os.replace(temporary_path, self.path)
        except OSError:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise

    def get_active_place(self) -> str | None:
        with self._lock:
            return self._read()["activePlaceId"]

    def set_active_place(self, place_id: str) -> str:
        with self._lock:
            data = self._read()
            data["activePlaceId"] = place_id
            self._write(data)
        return place_id

    def get_annotations(self, place_id: str, storage_key: str | None = None) -> MapAnnotations:
        with self._lock:
            data = self._read()
            raw = data["annotations"].get(storage_key or place_id)
        if raw is None:
            return MapAnnotations(placeId=place_id)
        return MapAnnotations.model_validate(raw)

    def save_annotations(self, annotations: MapAnnotations, storage_key: str | None = None) -> MapAnnotations:
        with self._lock:
            data = self._read()
            data["annotations"][storage_key or annotations.placeId] = annotations.model_dump(mode="json")
            self._write(data)
        return annotations
