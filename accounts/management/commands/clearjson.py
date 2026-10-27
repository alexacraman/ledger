import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Null journal_entry foreign keys in a fixture so it can be reloaded without accounting data present."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="banking/fixtures/202526.json",
            help="Path to the fixture JSON file to clean.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            raise CommandError(f"Fixture file not found: {file_path}")

        try:
            with file_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {file_path}: {exc}") from exc

        if not isinstance(data, list):
            raise CommandError("Fixture must be a list of JSON objects.")

        updated = 0

        for entry in data:
            if entry.get("model") != "banking.banktransaction":
                continue

            fields = entry.get("fields", {})
            if "journal_entry" in fields and fields["journal_entry"] is not None:
                fields["journal_entry"] = None
                fields["reconciled"] = False
                updated += 1

        with file_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4)
            fh.write("\n")

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {updated} bank transaction records in {file_path}."
            )
        )