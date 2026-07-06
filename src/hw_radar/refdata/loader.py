"""Seed-document loader — MS-1c's whole "fetch+parse" stage (plan decision D1:
curated in-repo documents; a live datasheet fetcher would replace THIS seam).
Seeds ship inside the package so deploy (rsync, ADR-0006) carries them."""

from __future__ import annotations

from pathlib import Path

from hw_radar.refdata.contracts import SeedDocument

SEED_DIR = Path(__file__).resolve().parent / "seeds"


def load_seed_documents(seed_dir: Path | None = None) -> list[SeedDocument]:
    directory = seed_dir if seed_dir is not None else SEED_DIR
    paths = sorted(directory.glob("*.json"))
    if not paths:
        msg = f"no seed documents found in {directory}"
        raise FileNotFoundError(msg)
    return [SeedDocument.model_validate_json(path.read_text(encoding="utf-8")) for path in paths]
