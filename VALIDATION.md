# Verification notes

Created 2026-09-29. Tested with Python 3.12.14 and the package versions in requirements.txt.

- Notebook validated against the Jupyter notebook v4 schema.
- All notebook code cells parsed successfully.
- Executed every cell in sequence with an in-process IPython shell, in a fresh folder, using the standalone embedded assets.
- Untouched workbook: 48 unfinished checks skipped as intended.
- Completed verification copy: all 48 exercise check groups passed with private reference implementations.
- 22 companion assets verified against recorded SHA-256 digests after extraction.
- Boundary checks include invalid dates, duplicate join keys, retries, stale updates, transaction rollback, partition replay and checkpoint failures.
- Checked Markdown fence/hint structure and supplied example totals.

A separate Jupyter kernel could not be launched in the authoring environment because socket binding is disabled. Cell execution was verified with IPython without those kernel sockets. The reference implementations and executed verification copies are not part of this workbook.

Checks establish the documented example/boundary behavior. They do not establish performance at production scale, every possible malformed input, or distributed exactly-once processing.
