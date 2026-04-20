# Flight Price Tracker

Python app for tracking flexible-date flight searches, alerting on meaningful price drops, and sending weekly summary emails. The project is designed for free scheduled runs on GitHub Actions with provider credentials and mail credentials stored as GitHub Actions secrets.

## Current Status

This first version provides:

- A pluggable provider interface
- An initial `AmadeusProvider`
- Flexible date expansion for round-trip searches
- Optional explicit stopover generation for outbound, return, or both
- Filtering for stops, trip length, total duration, and layover windows
- Stateful price-drop alerts with configurable thresholds
- Weekly top-5 summaries per airport pair
- SMTP email output
- GitHub Actions scheduled workflow

This first version does **not** fully solve every travel-search nuance yet. In particular:

- Domestic vs. international layover rules are modeled in config, but the current provider response is not yet enriched enough to classify every connection reliably.
- Fare-brand labeling is best-effort and depends on what the provider returns.
- Multi-city stopover generation is supported structurally, but should be treated as a controlled first pass rather than a complete fare-construction engine.
- Amadeus does not cover every airline and fare source.

## Quick Start

1. Create a virtual environment and install dependencies.
2. Edit `config/queries.yaml` with your searches.
3. Set environment variables:

```powershell
$env:AMADEUS_CLIENT_ID="..."
$env:AMADEUS_CLIENT_SECRET="..."
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="your-address@gmail.com"
$env:SMTP_PASSWORD="your-app-password"
$env:EMAIL_FROM="your-address@gmail.com"
$env:EMAIL_TO="your-address@gmail.com"
```

4. Run a dry summary:

```powershell
python -m flight_tracker --config config/queries.yaml --mode daily --dry-run
```

5. Send emails for real:

```powershell
python -m flight_tracker --config config/queries.yaml --mode daily
python -m flight_tracker --config config/queries.yaml --mode weekly
```

## GitHub Actions Secrets

Store these as repository secrets:

- `AMADEUS_CLIENT_ID`
- `AMADEUS_CLIENT_SECRET`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_TO`

The repo can be public while these remain private. GitHub Actions secrets are encrypted and only exposed to workflow runtime.

## Config Model

The main config file is `config/queries.yaml`. Each query can define:

- multiple origin airports
- multiple destination airports
- passengers with adult/child age details
- outbound date range
- return-home-arrival date range
- trip length range
- stop and layover rules
- stopover rules for outbound-only, return-only, or both
- total duration caps
- price-drop alert threshold

See `config/queries.example.yaml`.

## Architecture

- `src/flight_tracker/config.py`: config models and loading
- `src/flight_tracker/planner.py`: expands flexible rules into provider search tasks
- `src/flight_tracker/providers/`: provider interface and Amadeus implementation
- `src/flight_tracker/filtering.py`: itinerary filtering and normalization
- `src/flight_tracker/state.py`: state persistence
- `src/flight_tracker/reporting.py`: daily and weekly email rendering
- `src/flight_tracker/emailer.py`: SMTP delivery
- `.github/workflows/flight-tracker.yml`: scheduled runs

## Running in GitHub Actions

The workflow is scheduled twice:

- daily alert run
- weekly summary run

State is written to `data/state.json`. The workflow commits state changes back to the repository using the default `GITHUB_TOKEN`.

## Known Next Steps

- enrich airport metadata to properly distinguish domestic vs. international layovers
- broaden provider coverage with additional provider implementations
- improve stopover search generation heuristics and quota management
- add tests around date expansion and filtering
