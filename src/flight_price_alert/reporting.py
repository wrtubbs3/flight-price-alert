from __future__ import annotations

from collections import defaultdict

from flight_price_alert.models import Itinerary
from flight_price_alert.state import PriceDrop


def build_daily_email(price_drops: list[PriceDrop]) -> tuple[str, str]:
    if not price_drops:
        return ("Flight Price Alert: no qualifying price drops", "No tracked itinerary dropped beyond its configured threshold today.")

    lines = ["The following tracked itineraries dropped beyond threshold:", ""]
    for drop in sorted(price_drops, key=lambda item: item.current_price):
        itinerary = drop.itinerary
        lines.extend(
            [
                f"- {itinerary.query_name} [{itinerary.airport_pair_key}]",
                f"  Previous: ${drop.previous_price:,.2f}",
                f"  New: ${drop.current_price:,.2f}",
                f"  Fare: {itinerary.fare_label}",
                f"  Depart: {itinerary.first_departure.isoformat()}",
                f"  Return arrival: {itinerary.final_arrival.isoformat()}",
                f"  Stopover: {itinerary.stopover_label or 'none'}",
                "",
            ]
        )
    return ("Flight Price Alert: price drops detected", "\n".join(lines).strip())


def build_weekly_email(itineraries: list[Itinerary]) -> tuple[str, str]:
    grouped: dict[str, list[Itinerary]] = defaultdict(list)
    for itinerary in itineraries:
        grouped[itinerary.cheapest_key].append(itinerary)

    lines = ["Weekly top itineraries by airport pair", ""]
    for key in sorted(grouped):
        sample = grouped[key][0]
        lines.append(f"{sample.query_name} [{sample.airport_pair_key}]")
        for index, itinerary in enumerate(sorted(grouped[key], key=lambda item: item.total_price)[:5], start=1):
            lines.append(
                f"{index}. ${itinerary.total_price:,.2f} | "
                f"{itinerary.first_departure.isoformat()} -> {itinerary.final_arrival.isoformat()} | "
                f"fare={itinerary.fare_label} | stopover={itinerary.stopover_label or 'none'}"
            )
        lines.append("")
    return ("Flight Price Alert: weekly summary", "\n".join(lines).strip())
