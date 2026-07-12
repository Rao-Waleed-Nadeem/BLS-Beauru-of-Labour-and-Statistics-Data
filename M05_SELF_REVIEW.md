# M05 Self-Review (Calendar Collector)

## What was implemented

- Calendar registry loader: `pipeline/collectors/calendar_registry_loader.py`
- ICS event parser: `pipeline/collectors/calendar_parser.py`
- Calendar collector: `pipeline/collectors/calendar_collector.py`
- Tests: `tests/test_calendar_collector.py`
- Exports via `pipeline/collectors/__init__.py`

## Documentation compliance

- Followed required docs for M05: calendar registry + data collection guide + validation/maintenance.
- Implemented validation outputs (`validation.json`) and diff output (`calendar_diff.json`).

## Architecture preserved

- Scheduler only manages jobs; collector generates queue items.
- Raw artifacts are written under `storage/raw/bls/calendar/`.

## Coding standards / typing

- Added type hints and dataclasses.

## Validation / failure handling

- ICS failures are isolated from HTML failures.
- Does not overwrite previous snapshot file; writes `normalized_events_prev.json`.

## Testing

- `pytest` passes: 32 passed.

## Known limitations (intended for next iteration)

- HTML parsing is best-effort and currently only downloads/saves `calendar.html` without extracting events.
- Reference period mapping from ICS is currently empty because the subset parser targets DTSTART/SUMMARY.
- Calendar-driven job collector name (`calendar_event`) is a placeholder; downstream collectors may need wiring in later milestones.
