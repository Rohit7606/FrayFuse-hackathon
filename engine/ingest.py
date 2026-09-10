"""Ingestion — an uploaded zip of collection CSVs to a validated NetworkInput.

Admitted to scope in AGENTS.md §1.5 for the judged demo, and bounded there:
this reads a file the user hands it and nothing else.  No scraping, no lookups,
no network egress, no LLM.  §1.4 is untouched — the repo still never goes and
fetches anything.

It is deliberately thin.  `engine/transform.py` is already "the only place that
knows about CSVs" (§7), so this module does exactly three things transform
cannot do for itself:

  1. unpack an archive without trusting it,
  2. work out which member is which collection CSV, tolerating a renamed file,
  3. stage those members under the canonical names transform expects.

Then it calls `transform()` and gets out of the way.  There is no second
CSV→network path here, and if one ever appears in this file it is a bug.

Determinism (§3.1).  Zip member order is not guaranteed by the format, so every
walk over the archive is sorted.  Extraction writes into a caller-supplied
directory and never into the repo tree.  Nothing here reads the clock:
`meta.generated_at` comes from `config.TRANSFORM_GENERATED_AT` and the deep
tier is seeded, so the same zip produces a byte-identical network every time.
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine import config
from engine.transform import TransformError, transform, validate


class IngestError(ValueError):
    """The upload cannot produce a valid network.

    Always carries a message naming the file and, where it is known, the field
    — the API turns this into a 422 and a judge reads it off the screen, so
    "malformed archive" is not an acceptable message (SCHEMA.md §5.6).
    """


# The files transform() reads, and a signature that identifies each one from
# its header alone.  Filename is tried first; the signature is the fallback for
# a judge's slightly-renamed file.
#
# Each signature is the smallest set of columns that is unique across the
# collection set.  `company_id` + `fy` alone would match both financials.csv
# and backtest_panel.csv, so financials is pinned by a disclosure column that
# only it carries.
CANONICAL_FILES: dict[str, frozenset[str]] = {
    "companies.csv": frozenset({"company_id", "name", "tier_role"}),
    "financials.csv": frozenset({"company_id", "fy", "msme_not_due"}),
    "edges.csv": frozenset({"edge_id", "from_company_id", "to_company_id"}),
    "entity_pool.csv": frozenset({"name", "source", "location", "product_category"}),
    "distress_events.csv": frozenset({"company_id", "event_date", "event_type"}),
}

# transform() cannot run without these three.  entity_pool.csv is optional but
# its absence costs the demo the deep tier, so it is warned about loudly.
REQUIRED_FILES = ("companies.csv", "financials.csv", "edges.csv")


@dataclass
class IngestReport:
    """What the upload contained and what was made of it.

    A demo asset, not debug output.  It is what lets someone say "we read 43
    filings and 37 of them disclosed nothing usable" while pointing at a screen,
    so every field here is meant to be shown.
    """

    files_seen: list[str] = field(default_factory=list)
    files_used: dict[str, str] = field(default_factory=dict)
    files_ignored: list[str] = field(default_factory=list)
    rows_parsed: dict[str, int] = field(default_factory=dict)
    companies_read: int = 0
    nodes_built: int = 0
    edges_built: int = 0
    generated_nodes: int = 0
    observable_nodes: int = 0
    fields_present: int = 0
    fields_null: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "files_seen": list(self.files_seen),
            "files_used": dict(self.files_used),
            "files_ignored": list(self.files_ignored),
            "rows_parsed": dict(self.rows_parsed),
            "companies_read": self.companies_read,
            "nodes_built": self.nodes_built,
            "edges_built": self.edges_built,
            "generated_nodes": self.generated_nodes,
            "observable_nodes": self.observable_nodes,
            "fields_present": self.fields_present,
            "fields_null": self.fields_null,
            "warnings": list(self.warnings),
        }


def _safe_member_path(root: Path, member_name: str) -> Path | None:
    """Resolve an archive member under `root`, or None if it tries to escape.

    Zip-slip defence.  A member may name an absolute path, a Windows drive, or
    any number of `..` segments, and `Path.resolve()` on the joined path is the
    only reliable way to find out where it would actually land — string
    inspection of the member name misses `a/../../b` and mixed separators.
    Directory entries and anything that is not a regular file are skipped.
    """
    if member_name.endswith("/"):
        return None

    candidate = Path(member_name)
    if candidate.is_absolute() or candidate.drive:
        return None

    resolved = (root / candidate).resolve()
    root_resolved = root.resolve()
    if resolved == root_resolved or root_resolved not in resolved.parents:
        return None
    return resolved


def _classify(path: Path, header: list[str]) -> str | None:
    """Which canonical CSV this member is, by name first and header second."""
    lowered = path.name.lower()
    if lowered in CANONICAL_FILES:
        return lowered

    columns = {column.strip().lower() for column in header}
    for canonical, signature in sorted(CANONICAL_FILES.items()):
        if signature <= columns:
            return canonical
    return None


def _read_header(path: Path) -> list[str]:
    """First row of a CSV, or an empty list if it has none.

    utf-8-sig because a CSV exported from a spreadsheet on Windows carries a
    byte-order mark, and a BOM glued to the first column name would defeat
    every header signature in this module.
    """
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return next(csv.reader(handle), [])
    except (UnicodeDecodeError, OSError):
        return []


def _count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _extract(data: bytes, workdir: Path, report: IngestReport) -> Path:
    """Unpack the archive into `workdir/raw`, refusing anything hostile."""
    raw = workdir / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise IngestError(f"not a readable zip archive: {exc}") from exc

    with archive:
        # Sorted, because zip member order is not guaranteed and an unsorted
        # walk would make classification order-dependent.
        names = sorted(archive.namelist())

        if len(names) > config.INGEST_MAX_MEMBERS:
            raise IngestError(
                f"archive holds {len(names)} members, more than the "
                f"{config.INGEST_MAX_MEMBERS} allowed"
            )

        # Declared sizes are checked before a single byte is written, which is
        # the only point at which a zip bomb can still be refused cheaply.
        total = sum(info.file_size for info in archive.infolist())
        if total > config.INGEST_MAX_UNCOMPRESSED_BYTES:
            raise IngestError(
                f"archive expands to {total / 1_048_576:.1f} MB, more than the "
                f"{config.INGEST_MAX_UNCOMPRESSED_BYTES / 1_048_576:.0f} MB allowed"
            )

        for name in names:
            info = archive.getinfo(name)
            report.files_seen.append(name)

            target = _safe_member_path(raw, name)
            if target is None:
                if not name.endswith("/"):
                    raise IngestError(
                        f"archive member {name!r} resolves outside the extraction "
                        "directory and was refused"
                    )
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as sink:
                sink.write(source.read())

    return raw


def _stage(raw: Path, report: IngestReport) -> Path:
    """Copy the recognised members under the names transform() expects."""
    staged = raw.parent / "staged"
    staged.mkdir(parents=True, exist_ok=True)

    # Sorted for determinism: two members could both classify as the same
    # canonical file, and which one wins must not depend on filesystem order.
    for path in sorted(raw.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(raw).as_posix()

        if path.suffix.lower() != ".csv":
            # Markdown, JSON and anything else ride along harmlessly. The whole
            # data/real directory is a realistic upload and it contains a data
            # dictionary and a findings note; refusing the archive over those
            # would be absurd.
            report.files_ignored.append(relative)
            continue

        canonical = _classify(path, _read_header(path))
        if canonical is None:
            report.files_ignored.append(relative)
            continue

        if canonical in report.files_used:
            report.warnings.append(
                f"{relative} also looks like {canonical}; kept "
                f"{report.files_used[canonical]} and ignored this one"
            )
            report.files_ignored.append(relative)
            continue

        (staged / canonical).write_bytes(path.read_bytes())
        report.files_used[canonical] = relative
        report.rows_parsed[canonical] = _count_rows(path)

    missing = [name for name in REQUIRED_FILES if name not in report.files_used]
    if missing:
        seen = ", ".join(sorted(report.files_seen)[:8]) or "nothing"
        raise IngestError(
            f"no file in the archive matched {', '.join(missing)}. "
            f"Members seen: {seen}. Expected the collection CSVs described in "
            "data/real/DATA_DICTIONARY.md, matched by filename or by header."
        )

    if "entity_pool.csv" not in report.files_used:
        report.warnings.append(
            "entity_pool.csv absent - no synthetic deep tier will be generated, "
            "so the graph bottoms out at the real companies and nothing propagates"
        )

    return staged


def _measure_disclosure(network: dict[str, Any], report: IngestReport) -> None:
    """Count what the filings actually disclosed, and what they left blank.

    The null count is the point, not a diagnostic: most of this network being
    dark is the product's own thesis, and the report is where that becomes a
    number somebody can say out loud.
    """
    present = 0
    null = 0
    for signal in network.get("stress_signals", []):
        for key, value in sorted(signal.items()):
            if key in ("node_id", "fy", "basis", "data_source", "ageing_basis"):
                continue
            if value is None:
                null += 1
            else:
                present += 1

    report.fields_present = present
    report.fields_null = null
    report.nodes_built = len(network["nodes"])
    report.edges_built = len(network["edges"])
    report.observable_nodes = sum(1 for node in network["nodes"] if node["is_observable"])
    report.generated_nodes = sum(
        1 for node in network["nodes"] if node.get("data_source") != "real"
    )
    report.companies_read = report.rows_parsed.get("companies.csv", 0)


def ingest_zip(data: bytes, workdir: Path) -> tuple[dict[str, Any], IngestReport]:
    """An uploaded zip to a validated NetworkInput, with a report of what happened.

    `workdir` is supplied by the caller and must be a temporary directory the
    caller owns — never a path inside the repo.  Nothing is written outside it.

    Raises IngestError, with a message naming the offending file, for anything
    the upload got wrong.  The caller turns that into a 422; it must never
    become a 500 (SCHEMA.md §5.6).
    """
    report = IngestReport()

    raw = _extract(data, workdir, report)
    staged = _stage(raw, report)

    try:
        network, excluded = transform(staged)
    except TransformError as exc:
        raise IngestError(f"the collection CSVs could not be transformed: {exc}") from exc
    except KeyError as exc:
        # A missing column surfaces from transform as a KeyError on the row
        # dict. Name it rather than letting it become a 500.
        raise IngestError(
            f"a required column is missing from the uploaded CSVs: {exc}"
        ) from exc

    report.warnings.extend(excluded)

    try:
        validate(network)
    except Exception as exc:  # jsonschema.ValidationError, kept loose on purpose
        raise IngestError(
            f"the network built from this upload does not satisfy schema.json: {exc}"
        ) from exc

    _measure_disclosure(network, report)
    return network, report
