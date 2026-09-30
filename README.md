# Python Data Engineering Workbook

48 exercises across eight datasets. 16 Easy, 25 Medium, 7 Stretch.

Open **de_python_workbook.ipynb**. It includes the complete instructions, dataset schemas, starter functions, optional hints, expected checkpoints and checks. No full exercise solutions are bundled.

## Start

1. Extract this ZIP into a folder, or download just the notebook and place it in a fresh folder.
2. Use Python 3.12 and a Jupyter-capable editor (for example VS Code/Codespaces).
3. Run the notebook's first setup cell to make sure companion files exist.
4. Install dependencies once while online: `%pip install -r de_workbook_assets/requirements.txt` in a notebook, or `python -m pip install -r requirements.txt` in the extracted project folder.
5. Restart/select the matching Python kernel, run setup, then run a batch's dataset cell.
6. Write an answer, rerun its definition, then run its check. Unfinished checks say “not implemented yet”.

All exercise work runs offline after dependency installation. API responses and S3 operations are simulated; never add real credentials. Use the provided sessions/clients.

## Files

- de_python_workbook.ipynb — the workbook (also embeds its companion assets).
- de_workbook_assets/data/ — CSV, JSON, XML, JSONL, SQLite, Parquet and gzip inputs.
- de_workbook_assets/handoffs/ — canonical inputs so later questions can be attempted independently; expected-output snapshots for checks.
- de_workbook_assets/workbook_support.py — setup, data loading and offline doubles.
- de_workbook_assets/workbook_checks.py — public correctness/boundary/failure checks.
- de_workbook_assets/DATA_DICTIONARY.md — dataset grains and schemas.
- requirements.txt — exact versions used for verification.

Run outputs go to workbook_outputs/, created by notebook setup. Bootstrap never overwrites existing files. To reset source assets, open an original copy of the notebook in a new empty folder. Save your notebook and commit meaningful completed exercises plus notes.

## Learning sequence

1. Courier CSV: ingestion, exact money, validation, deduplication, streaming, pytest.
2. Retail CSVs: pandas joins, grain, grouping, calendar windows, reconciliation.
3. Ticket JSON/API: flattening, pagination, timeouts, selective retries, lookback windows.
4. Apartment XML: namespaces, unit normalization, Pydantic, late cancellations, incremental parsing.
5. Event JSONL: quarantine, timezone normalization, sessions, funnels, operational logging.
6. Stock SQLite: bound SQL, atomic writes, version-aware upserts, incremental checkpoints.
7. Sensor Parquet: schemas, projection, quality, hourly metrics, partitions, bounded batches.
8. Object manifests: boto3 pagination, gzip, fingerprints, change plans, safe checkpoint publication.

## Scope and interpretation

Difficulty is educational and not a standardized interview rating. Prepared files contain only fictional data. SQLAlchemy exercises use SQLite for a self-contained environment; no PostgreSQL server is required. S3 exercises use real boto3 interfaces behind botocore Stubber. Local file replacement and manifest publication are not distributed transaction guarantees.

Checks validate example/boundary behavior; explain complexity and operational trade-offs yourself. Source examples are deliberately small so you can inspect them.
