from __future__ import annotations

import argparse

from flight_price_alert.config import load_config
from flight_price_alert.emailer import send_email
from flight_price_alert.runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track flight prices and send alerts.")
    parser.add_argument("--config", default="config/queries.yaml", help="Path to YAML config file.")
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--dry-run", action="store_true", help="Do not send email or persist state.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    subject, body, changed, should_send = run(config, args.mode, dry_run=args.dry_run)
    print(subject)
    print(body)

    if not args.dry_run and should_send:
        send_email(subject, body)

    if changed:
        print("State updated.")
    if not should_send and args.mode == "daily":
        print("No qualifying daily alert to send.")
    return 0
