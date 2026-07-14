# TODO_NEXT_M07 — Milestone M07 (RSS Collector)

## Planned steps

1. Inspect existing project patterns for collectors/scheduler integration.
2. Implement M07 RSS collector:
   - RSS registry loading (parsing RSS_REGISTRY.md)
   - Download RSS XML (with dry_run support)
   - Validate XML (basic structural checks)
   - Extract RSS items (GUID/link/title/pubDate)
   - Compute duplicate key and persist duplicate index
   - Save raw XML snapshots and metadata.json
   - Generate scheduler jobs for new items
3. Add unit tests for M07 (dry_run + idempotency + duplicate detection).
4. Run pytest.
5. Self-review changes.
6. Update README_IMPLEMENTATION.md milestone status for M07.
7. Update TODO.md progress checkboxes.
