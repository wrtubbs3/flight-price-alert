from __future__ import annotations

from datetime import timedelta

from flight_price_alert.config import AppConfig, QueryConfig
from flight_price_alert.models import SearchTask


def build_search_tasks(config: AppConfig) -> list[SearchTask]:
    tasks: list[SearchTask] = []
    for query in config.queries:
        tasks.extend(_build_query_tasks(query, config))
    return tasks


def _build_query_tasks(query: QueryConfig, config: AppConfig) -> list[SearchTask]:
    provider = query.provider or config.defaults.provider
    cabin = query.constraints.cabin
    threshold = query.alert_threshold_usd or config.defaults.alert_threshold_usd
    travelers = _build_travelers(query)
    tasks: list[SearchTask] = []

    outbound_days = [
        query.outbound_date_range.start + timedelta(days=offset)
        for offset in range((query.outbound_date_range.end - query.outbound_date_range.start).days + 1)
    ]

    for origin in query.origins:
        for destination in query.destinations:
            for outbound_date in outbound_days:
                for trip_days in range(query.trip_length_days.min, query.trip_length_days.max + 1):
                    return_date = outbound_date + timedelta(days=trip_days)
                    if not (
                        query.return_arrival_date_range.start
                        <= return_date
                        <= query.return_arrival_date_range.end
                    ):
                        continue

                    base_legs = [
                        (origin, destination, outbound_date.isoformat()),
                        (destination, origin, return_date.isoformat()),
                    ]
                    tasks.append(
                        SearchTask(
                            query_id=query.id,
                            query_name=query.name,
                            provider=provider,
                            origin=origin,
                            destination=destination,
                            legs=base_legs,
                            cabin=cabin,
                            travelers=travelers,
                            alert_threshold_usd=threshold,
                            airport_pair_key=f"{origin}-{destination}",
                        )
                    )

                    tasks.extend(_build_stopover_tasks(query, provider, travelers, threshold, origin, destination, outbound_date, return_date))
    return tasks


def _build_stopover_tasks(
    query: QueryConfig,
    provider: str,
    travelers: list[dict],
    threshold: float,
    origin: str,
    destination: str,
    outbound_date,
    return_date,
) -> list[SearchTask]:
    stopovers = query.constraints.stopovers
    if stopovers.allowed_on == "none":
        return []

    tasks: list[SearchTask] = []
    for airport in stopovers.airports:
        for stopover_days in range(stopovers.min_days, stopovers.max_days + 1):
            if stopovers.allowed_on in {"outbound", "both"}:
                second_departure = outbound_date + timedelta(days=stopover_days)
                tasks.append(
                    SearchTask(
                        query_id=query.id,
                        query_name=query.name,
                        provider=provider,
                        origin=origin,
                        destination=destination,
                        legs=[
                            (origin, airport, outbound_date.isoformat()),
                            (airport, destination, second_departure.isoformat()),
                            (destination, origin, return_date.isoformat()),
                        ],
                        cabin=query.constraints.cabin,
                        travelers=travelers,
                        alert_threshold_usd=threshold,
                        airport_pair_key=f"{origin}-{destination}",
                        stopover_label=f"outbound:{airport}:{stopover_days}d",
                    )
                )
            if stopovers.allowed_on in {"return", "both"}:
                second_return = return_date - timedelta(days=stopover_days)
                if second_return <= outbound_date:
                    continue
                tasks.append(
                    SearchTask(
                        query_id=query.id,
                        query_name=query.name,
                        provider=provider,
                        origin=origin,
                        destination=destination,
                        legs=[
                            (origin, destination, outbound_date.isoformat()),
                            (destination, airport, second_return.isoformat()),
                            (airport, origin, return_date.isoformat()),
                        ],
                        cabin=query.constraints.cabin,
                        travelers=travelers,
                        alert_threshold_usd=threshold,
                        airport_pair_key=f"{origin}-{destination}",
                        stopover_label=f"return:{airport}:{stopover_days}d",
                    )
                )
    return tasks


def _build_travelers(query: QueryConfig) -> list[dict]:
    travelers: list[dict] = []
    traveler_id = 1
    for passenger in query.passengers:
        traveler_type = {
            "adult": "ADULT",
            "child": "CHILD",
            "infant": "HELD_INFANT",
        }[passenger.type]
        for _ in range(passenger.count):
            traveler = {
                "id": str(traveler_id),
                "travelerType": traveler_type,
            }
            if passenger.age is not None:
                traveler["age"] = passenger.age
            travelers.append(traveler)
            traveler_id += 1
    return travelers
