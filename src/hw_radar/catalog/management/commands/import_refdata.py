"""Manual entry point for ADR-0018 reference ingest. Default: import the seed
documents only. --refresh runs the full monthly loop (import + backfill-queue
reconsider + discovery scan) — the same code path as the poller job. Conflicts
exit non-zero with the full descriptor list (fail into review, D4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from hw_radar.refdata.loader import load_seed_documents
from hw_radar.refdata.persist import ImportConflictError, import_documents
from hw_radar.refdata.refresh import run_refresh


class Command(BaseCommand):
    help = "Import ADR-0018 reference seed documents (--refresh: full monthly loop)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--refresh", action="store_true", help="run the full refresh loop")
        parser.add_argument("--seed-dir", type=Path, default=None)

    def handle(self, *args: Any, **options: Any) -> None:
        seed_dir: Path | None = options["seed_dir"]
        if options["refresh"]:
            report = run_refresh(seed_dir)
            self.stdout.write(json.dumps(report.as_json(), indent=2, default=str))
            if report.conflicts:
                raise CommandError(f"{len(report.conflicts)} alias conflict(s) — see report")
            return
        docs = load_seed_documents(seed_dir)
        try:
            report = import_documents(docs)
        except ImportConflictError as exc:
            raise CommandError("import aborted:\n" + "\n".join(exc.conflicts)) from exc
        self.stdout.write(json.dumps(report.as_json(), indent=2, default=str))
