# Dataset dictionary

All records are fictional. Raw source files are immutable practice inputs.

## Batch 1: Courier billing CSV

One raw row is one shipment update. Key: shipment_id; updated_at chooses the current version. Columns: shipment_id, carrier, destination, packages, unit_fee (currency units per package), updated_at, status. All raw values are strings. The file has 11 rows and 7 columns.

## Batch 2: Retail order updates and settlements

order_updates.csv: one row per order update (10 rows); one product per order in this simplified source. Composite version identification is order_id + updated_at, with a later-input tie rule. products.csv: one row per product (3 rows). settlements.csv: one row per settlement date (4 rows). All money is integer cents. Dates are business calendar dates; updated_at represents a UTC instant.

## Batch 3: Paginated support-ticket API

ticket_pages.json has three pages. Each page has results (list) and next_cursor (string or null). A ticket has id, customer{id,country?}, tags (list/null), priority, updated_at. Six delivered versions represent five ticket IDs. All API examples use an injected offline session.

## Batch 4: Korean apartment transactions

apartment_sales.xml contains 8 sale versions. Fields: sale_id, district, apartment, contract_date (YYYY-MM-DD), price_manwon (integer text with commas), area_m2 (decimal text), floor (integer text), cancelled (Y/N), updated_at (ISO timestamp). Default namespace urn:practice:sales. Each sale is a direct child of the root. This exercise supplies a stable sale_id; do not assume real public feeds do.

## Batch 5: Clickstream JSON Lines

events.jsonl has 16 physical lines: 1 blank, 2 parse/schema rejects, and 13 object rows. Each event object has event_id, user_id (int), event_type (view/cart/purchase), product_id, timestamp. One object has an invalid timestamp and E2 is delivered twice. Event timestamps represent instants.

## Batch 6: Warehouse stock changes

inventory grain: one current stock state per (sku, warehouse), with qty>=0, version>0, is_deleted in {0,1}. load_audit: run_id primary key and rows_loaded>=0. checkpoint: pipeline primary key and last_change_id. source_changes: change_id primary key plus sku, warehouse, qty, version, is_deleted. The stock checkpoint starts at 0 and there are six source changes.

## Batch 7: Sensor readings in Parquet

sensors.parquet: device_id string, site string, timestamp Arrow timestamp(us, UTC), temperature_c double nullable. One row is one observation; 10 observations are split across four row groups. There are no duplicate observation keys in this batch. Operational valid range is [-20,50] Celsius.

## Batch 8: Object-storage ingestion manifest

s3_listing.json uses S3 field names Key, ETag, Size. The normalized objects list uses key, etag, size. previous_manifest.json maps each processed key to etag and size. a changed, b is unchanged, c is new, and an old key is absent. Local object files contain tiny fictional records {id,value}. No account, secrets, paid services or live endpoints are involved.

## Handoff fixtures
`handoffs/fixtures.json` holds typed canonical inputs for later exercises. Special JSON tags restore Decimal/date/datetime/DataFrame/Arrow types. They are data, not implementations. `handoffs/expected.json` holds output snapshots used by checks. You may inspect them after an attempt.
