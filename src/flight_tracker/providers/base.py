from __future__ import annotations

from abc import ABC, abstractmethod

from flight_tracker.models import Itinerary, SearchTask


class FlightProvider(ABC):
    @abstractmethod
    def search(self, task: SearchTask, *, max_results: int) -> list[Itinerary]:
        raise NotImplementedError
