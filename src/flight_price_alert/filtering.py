from __future__ import annotations

from datetime import timedelta

from flight_price_alert.config import QueryConfig
from flight_price_alert.models import Itinerary


def filter_itineraries(query: QueryConfig, itineraries: list[Itinerary]) -> list[Itinerary]:
    kept: list[Itinerary] = []
    for itinerary in itineraries:
        if not _stops_allowed(query, itinerary):
            continue
        if not _trip_length_allowed(query, itinerary):
            continue
        if not _duration_allowed(query, itinerary):
            continue
        if not _layovers_allowed(query, itinerary):
            continue
        kept.append(itinerary)
    return sorted(kept, key=lambda item: item.total_price)


def _stops_allowed(query: QueryConfig, itinerary: Itinerary) -> bool:
    stopover_bonus = 0
    if itinerary.stopover_label:
        stopover_bonus = query.constraints.max_additional_stops_with_stopover

    max_stops = query.constraints.max_stops_per_leg + stopover_bonus
    return all(max(len(leg.segments) - 1, 0) <= max_stops for leg in itinerary.legs)


def _trip_length_allowed(query: QueryConfig, itinerary: Itinerary) -> bool:
    if len(itinerary.legs) < 2:
        return True
    outbound_departure = itinerary.legs[0].segments[0].departure_at.date()
    final_arrival = itinerary.legs[-1].segments[-1].arrival_at.date()
    trip_days = (final_arrival - outbound_departure).days
    return query.trip_length_days.min <= trip_days <= query.trip_length_days.max + 2


def _duration_allowed(query: QueryConfig, itinerary: Itinerary) -> bool:
    cap_hours = query.constraints.max_total_duration_hours_per_leg
    if cap_hours is None:
        return True
    max_minutes = cap_hours * 60
    return all(leg.duration_minutes <= max_minutes for leg in itinerary.legs)


def _layovers_allowed(query: QueryConfig, itinerary: Itinerary) -> bool:
    layovers = query.constraints.layovers
    min_minutes = layovers.default_min_minutes
    max_minutes = layovers.default_max_minutes

    for leg in itinerary.legs:
        if len(leg.segments) < 2:
            continue
        for current_segment, next_segment in zip(leg.segments, leg.segments[1:]):
            duration = next_segment.departure_at - current_segment.arrival_at
            minutes = int(duration / timedelta(minutes=1))
            if minutes < min_minutes or minutes > max_minutes:
                return False
    return True
