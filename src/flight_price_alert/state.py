from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from flight_price_alert.models import Itinerary


@dataclass(slots=True)
class PriceDrop:
    key: str
    previous_price: float
    current_price: float
    itinerary: Itinerary


class StateStore:
    def __init__(self, path: str | Path = "data/state.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def detect_price_drops(self, itineraries: list[Itinerary], thresholds: dict[str, float]) -> list[PriceDrop]:
        drops: list[PriceDrop] = []
        for itinerary in itineraries:
            key = itinerary.cheapest_key
            current = itinerary.total_price
            previous = self._state.get("best_prices", {}).get(key)
            threshold = thresholds.get(key, 0.0)
            if previous is not None and current <= previous - threshold:
                drops.append(
                    PriceDrop(
                        key=key,
                        previous_price=float(previous),
                        current_price=current,
                        itinerary=itinerary,
                    )
                )
        return drops

    def update_best_prices(self, itineraries: list[Itinerary]) -> bool:
        best_prices = self._state.setdefault("best_prices", {})
        changed = False
        for itinerary in itineraries:
            key = itinerary.cheapest_key
            current_best = best_prices.get(key)
            if current_best is None or itinerary.total_price < current_best:
                best_prices[key] = itinerary.total_price
                changed = True
        return changed

    def save(self) -> None:
        self.path.write_text(json.dumps(self._state, indent=2, sort_keys=True), encoding="utf-8")

    def _load(self) -> dict:
        if not self.path.exists():
            return {"best_prices": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))
