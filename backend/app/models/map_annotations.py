"""Validated school-map annotations authored in the GateFlow demo."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GeoPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class GateMarker(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    position: GeoPoint


class PickupArea(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    vehicleType: Literal["bus", "car", "two_wheeler", "general"] = "general"
    points: list[GeoPoint] = Field(min_length=3, max_length=200)


class MapAnnotations(BaseModel):
    placeId: str = Field(min_length=1, max_length=255)
    gates: list[GateMarker] = Field(default_factory=list, max_length=50)
    pickupAreas: list[PickupArea] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def ids_are_unique(self):
        ids = [item.id for item in (*self.gates, *self.pickupAreas)]
        if len(ids) != len(set(ids)):
            raise ValueError("Gate and pickup area IDs must be unique.")
        return self


class ActivePlaceResponse(BaseModel):
    placeId: str | None


class ActivePlaceRequest(BaseModel):
    placeId: str = Field(min_length=1, max_length=255)


class MapAnnotationsResponse(MapAnnotations):
    source: str = "Administrator-authored demo annotations"
