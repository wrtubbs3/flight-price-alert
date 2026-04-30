from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from flight_price_alert.models import CabinClass, StopoverDirection


class DefaultsConfig(BaseModel):
    provider: str = "amadeus"
    currency: str = "USD"
    alert_threshold_usd: float = 10.0
    max_results_per_search: int = 20


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.end < self.start:
            raise ValueError("end must be on or after start")
        return self


class RangeDays(BaseModel):
    min: int
    max: int

    @model_validator(mode="after")
    def validate_order(self) -> "RangeDays":
        if self.max < self.min:
            raise ValueError("max must be >= min")
        return self


class PassengerConfig(BaseModel):
    type: Literal["adult", "child", "infant"]
    count: int = 1
    age: int | None = None

    @model_validator(mode="after")
    def validate_age(self) -> "PassengerConfig":
        if self.type == "child" and self.age is None:
            raise ValueError("child passengers must define an age")
        if self.type == "adult" and self.age is not None:
            raise ValueError("adult passengers should not define an age")
        return self


class LayoverConfig(BaseModel):
    default_min_minutes: int = 60
    default_max_minutes: int = 360
    domestic_min_minutes: int | None = None
    domestic_max_minutes: int | None = None
    international_min_minutes: int | None = None
    international_max_minutes: int | None = None


class StopoverConfig(BaseModel):
    allowed_on: StopoverDirection = "none"
    airports: list[str] = Field(default_factory=list)
    min_days: int = 1
    max_days: int = 3

    @field_validator("airports")
    @classmethod
    def uppercase_airports(cls, value: list[str]) -> list[str]:
        return [airport.upper() for airport in value]

    @model_validator(mode="after")
    def validate_stopovers(self) -> "StopoverConfig":
        if self.allowed_on != "none" and not self.airports:
            raise ValueError("stopover airports are required when stopovers are enabled")
        return self


class ConstraintsConfig(BaseModel):
    cabin: CabinClass = "economy"
    max_stops_per_leg: int = 1
    max_additional_stops_with_stopover: int = 0
    max_total_duration_hours_per_leg: int | None = None
    layovers: LayoverConfig = Field(default_factory=LayoverConfig)
    stopovers: StopoverConfig = Field(default_factory=StopoverConfig)


class QueryConfig(BaseModel):
    id: str
    name: str
    origins: list[str]
    destinations: list[str]
    passengers: list[PassengerConfig]
    outbound_date_range: DateRange
    return_arrival_date_range: DateRange
    trip_length_days: RangeDays
    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    provider: str | None = None
    currency: str | None = None
    alert_threshold_usd: float | None = None
    max_results_per_search: int | None = None

    @field_validator("origins", "destinations")
    @classmethod
    def uppercase_airports(cls, value: list[str]) -> list[str]:
        return [airport.upper() for airport in value]


class AppConfig(BaseModel):
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    queries: list[QueryConfig]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(payload)
