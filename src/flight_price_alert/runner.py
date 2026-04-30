from __future__ import annotations

from collections import defaultdict

from flight_price_alert.config import AppConfig
from flight_price_alert.filtering import filter_itineraries
from flight_price_alert.models import Itinerary, QueryMode
from flight_price_alert.planner import build_search_tasks
from flight_price_alert.providers import AmadeusProvider, FlightProvider
from flight_price_alert.reporting import build_daily_email, build_weekly_email
from flight_price_alert.state import StateStore


def run(config: AppConfig, mode: QueryMode, *, dry_run: bool = False) -> tuple[str, str, bool, bool]:
    providers = _build_providers(config)
    tasks = build_search_tasks(config)
    thresholds = {f"{query.id}:{origin}-{destination}": (query.alert_threshold_usd or config.defaults.alert_threshold_usd)
                  for query in config.queries
                  for origin in query.origins
                  for destination in query.destinations}

    results_by_query: dict[str, list[Itinerary]] = defaultdict(list)
    for task in tasks:
        provider = providers[task.provider]
        query = next(query for query in config.queries if query.id == task.query_id)
        max_results = query.max_results_per_search or config.defaults.max_results_per_search
        try:
            itineraries = provider.search(task, max_results=max_results)
        except Exception as exc:
            print(f"Search failed for {task.query_id} {task.legs}: {exc}")
            continue
        filtered = filter_itineraries(query, itineraries)
        results_by_query[task.query_id].extend(filtered)

    flattened = []
    for query_id, itineraries in results_by_query.items():
        flattened.extend(_dedupe_itineraries(itineraries))

    state = StateStore()
    changed = False
    should_send = True
    if mode == "daily":
        lowest_by_pair = _lowest_by_pair(flattened)
        drops = state.detect_price_drops(lowest_by_pair, thresholds)
        changed = state.update_best_prices(lowest_by_pair)
        subject, body = build_daily_email(drops)
        should_send = bool(drops)
    else:
        changed = state.update_best_prices(_lowest_by_pair(flattened))
        subject, body = build_weekly_email(flattened)

    if changed and not dry_run:
        state.save()

    return subject, body, changed, should_send


def _build_providers(config: AppConfig) -> dict[str, FlightProvider]:
    names = {query.provider or config.defaults.provider for query in config.queries}
    providers: dict[str, FlightProvider] = {}
    for name in names:
        if name == "amadeus":
            providers[name] = AmadeusProvider()
        else:
            raise ValueError(f"Unsupported provider: {name}")
    return providers


def _dedupe_itineraries(itineraries: list[Itinerary]) -> list[Itinerary]:
    deduped: dict[str, Itinerary] = {}
    for itinerary in itineraries:
        key = f"{itinerary.raw_reference}:{itinerary.total_price}"
        deduped[key] = itinerary
    return list(deduped.values())


def _lowest_by_pair(itineraries: list[Itinerary]) -> list[Itinerary]:
    lowest: dict[str, Itinerary] = {}
    for itinerary in itineraries:
        current = lowest.get(itinerary.cheapest_key)
        if current is None or itinerary.total_price < current.total_price:
            lowest[itinerary.cheapest_key] = itinerary
    return list(lowest.values())
