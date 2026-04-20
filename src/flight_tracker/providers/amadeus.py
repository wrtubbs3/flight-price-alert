from __future__ import annotations

import os
from datetime import datetime

import httpx

from flight_tracker.models import FlightLeg, FlightSegment, Itinerary, SearchTask
from flight_tracker.providers.base import FlightProvider


class AmadeusProvider(FlightProvider):
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = "https://api.amadeus.com",
        timeout: float = 60.0,
    ) -> None:
        self.client_id = client_id or os.environ.get("AMADEUS_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("AMADEUS_CLIENT_SECRET")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._token: str | None = None

        if not self.client_id or not self.client_secret:
            raise ValueError("Amadeus credentials are required")

    def search(self, task: SearchTask, *, max_results: int) -> list[Itinerary]:
        payload = self._build_payload(task, max_results=max_results)
        response = self._request(
            "POST",
            "/v2/shopping/flight-offers",
            json=payload,
        )
        offers = response.json().get("data", [])
        return [self._parse_offer(task, offer) for offer in offers]

    def _build_payload(self, task: SearchTask, *, max_results: int) -> dict:
        origin_destinations = []
        for index, (origin, destination, departure_date) in enumerate(task.legs, start=1):
            origin_destinations.append(
                {
                    "id": str(index),
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDateTimeRange": {"date": departure_date},
                }
            )

        return {
            "currencyCode": "USD",
            "originDestinations": origin_destinations,
            "travelers": task.travelers,
            "sources": ["GDS"],
            "searchCriteria": {
                "maxFlightOffers": max_results,
                "flightFilters": {
                    "cabinRestrictions": [
                        {
                            "cabin": _map_cabin(task.cabin),
                            "coverage": "MOST_SEGMENTS",
                            "originDestinationIds": [leg["id"] for leg in origin_destinations],
                        }
                    ]
                },
            },
        }

    def _parse_offer(self, task: SearchTask, offer: dict) -> Itinerary:
        legs: list[FlightLeg] = []
        for itinerary in offer.get("itineraries", []):
            segments = []
            for segment in itinerary.get("segments", []):
                departure_at = _parse_dt(segment["departure"]["at"])
                arrival_at = _parse_dt(segment["arrival"]["at"])
                segments.append(
                    FlightSegment(
                        origin=segment["departure"]["iataCode"],
                        destination=segment["arrival"]["iataCode"],
                        departure_at=departure_at,
                        arrival_at=arrival_at,
                        marketing_carrier=segment.get("carrierCode", ""),
                        operating_carrier=segment.get("operating", {}).get("carrierCode"),
                        flight_number=segment.get("number"),
                        duration_minutes=_duration_minutes(segment.get("duration")),
                    )
                )
            legs.append(
                FlightLeg(
                    segments=segments,
                    duration_minutes=_duration_minutes(itinerary.get("duration")),
                )
            )

        price = offer.get("price", {})
        return Itinerary(
            provider="amadeus",
            query_id=task.query_id,
            query_name=task.query_name,
            airport_pair_key=task.airport_pair_key,
            total_price=float(price.get("grandTotal") or price.get("total")),
            currency=price.get("currency", "USD"),
            cabin_label=task.cabin,
            fare_label=_infer_fare_label(offer),
            validating_carrier=(offer.get("validatingAirlineCodes") or [None])[0],
            total_duration_minutes=sum(leg.duration_minutes for leg in legs),
            legs=legs,
            raw_reference=offer.get("id", ""),
            stopover_label=task.stopover_label,
            metadata={
                "oneWay": offer.get("oneWay"),
                "instantTicketingRequired": offer.get("instantTicketingRequired"),
                "lastTicketingDate": offer.get("lastTicketingDate"),
            },
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        token = self._get_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"

        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response

    def _get_token(self) -> str:
        if self._token:
            return self._token

        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.post(
                "/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token


def _map_cabin(cabin: str) -> str:
    return {
        "economy": "ECONOMY",
        "premium_economy": "PREMIUM_ECONOMY",
        "business": "BUSINESS",
        "first": "FIRST",
    }[cabin]


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _duration_minutes(value: str | None) -> int:
    if not value:
        return 0
    raw = value.removeprefix("PT")
    hours = 0
    minutes = 0
    if "H" in raw:
        left, raw = raw.split("H", 1)
        hours = int(left)
    if "M" in raw:
        minutes = int(raw.removesuffix("M"))
    return hours * 60 + minutes


def _infer_fare_label(offer: dict) -> str:
    traveler_pricings = offer.get("travelerPricings", [])
    fare_details = []
    for pricing in traveler_pricings:
        fare_details.extend(pricing.get("fareDetailsBySegment", []))
    branded = {detail.get("brandedFare") for detail in fare_details if detail.get("brandedFare")}
    cabins = {detail.get("cabin") for detail in fare_details if detail.get("cabin")}
    if branded:
        return ", ".join(sorted(branded))
    if len(cabins) > 1:
        return "mixed-cabin"
    return "standard"
