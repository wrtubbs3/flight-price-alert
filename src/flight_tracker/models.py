from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


CabinClass = Literal["economy", "premium_economy", "business", "first"]
PassengerType = Literal["adult", "child", "infant"]
StopoverDirection = Literal["none", "outbound", "return", "both"]
QueryMode = Literal["daily", "weekly"]


@dataclass(slots=True)
class SearchTask:
    query_id: str
    query_name: str
    provider: str
    origin: str
    destination: str
    legs: list[tuple[str, str, str]]
    cabin: CabinClass
    travelers: list[dict]
    alert_threshold_usd: float
    airport_pair_key: str
    stopover_label: str | None = None


@dataclass(slots=True)
class FlightSegment:
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    marketing_carrier: str
    operating_carrier: str | None
    flight_number: str | None
    duration_minutes: int


@dataclass(slots=True)
class FlightLeg:
    segments: list[FlightSegment]
    duration_minutes: int


@dataclass(slots=True)
class Itinerary:
    provider: str
    query_id: str
    query_name: str
    airport_pair_key: str
    total_price: float
    currency: str
    cabin_label: str
    fare_label: str
    validating_carrier: str | None
    total_duration_minutes: int
    legs: list[FlightLeg]
    raw_reference: str
    stopover_label: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def cheapest_key(self) -> str:
        return f"{self.query_id}:{self.airport_pair_key}"

    @property
    def first_departure(self) -> datetime:
        return self.legs[0].segments[0].departure_at

    @property
    def final_arrival(self) -> datetime:
        return self.legs[-1].segments[-1].arrival_at
