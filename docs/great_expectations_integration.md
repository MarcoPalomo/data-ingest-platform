# Great Expectations Integration Guide

Great Expectations (GX) validates the bronze (raw) Delta tables before the silver layer runs. This guide describes how the integration works in this repository and how to change it.

## Architecture

```
IngestSQL (raw/customers) ─┐
                           ├─→ ValidateBronze: dq/validate_data_quality ─┬─ Pass → silver → gold
IngestAPI (raw/api/events) ┘   (GX 0.18, customers_suite + events_suite) └─ Fail → ADF activity Failed,
                                                                                     silver/gold not run
```

The `ValidateBronze` activity is in `datafactory/pipelines/orchestrator_master.json`. The notebook can also run on its own as the `data_quality_validation` job (`databricks/jobs/data_quality_validation_job.json`).

## Version

GX is pinned to **0.18.21**. The notebook uses the 0.18 Fluent API (`context.sources.add_or_update_spark`, `add_dataframe_asset`, `get_validator`), which was removed in GX 1.x.

The pin lives in two places, keep them in sync:

| Where | Why |
|-------|-----|
| `pyproject.toml` / `uv.lock` | Local dev, CI |
| `# MAGIC %pip install great-expectations==0.18.21` in `databricks/notebooks/dq/validate_data_quality.py` | Databricks cluster (does not use `uv.lock`) |

## How the Validation Notebook Works

`databricks/notebooks/dq/validate_data_quality.py`:

1. Installs GX on the cluster (`%pip`).
2. Creates an **ephemeral** context with a Spark datasource named `spark_adls`. Nothing has to be deployed besides the suite JSON files. `great_expectations/great_expectations.yml` is not used at runtime.
3. For each dataset:
   - reads the bronze Delta table (`raw/customers`, `raw/api/events`);
   - loads the suite from `<suites_dir>/<suite_name>.json`;
   - validates the DataFrame.
4. Prints every failed expectation with `unexpected_count`, `partial_unexpected_list` and the exception message, if any.
5. Runs **all** validations, then raises an exception if any failed. The Databricks run and the ADF activity are then marked **Failed**. It does not use `dbutils.notebook.exit`, which would mark the run as succeeded.

Widget:

| Name | Default | Purpose |
|------|---------|---------|
| `suites_dir` | `/dbfs/FileStore/data-platform/great_expectations/expectations` | Folder containing the suite JSON files |

The CD uploads `great_expectations/expectations/` to that folder:

```bash
databricks fs cp -r --overwrite great_expectations/expectations dbfs:/FileStore/data-platform/great_expectations/expectations
```

## Expectation Suites

| Suite | Dataset | Main rules |
|-------|---------|-----------|
| `great_expectations/expectations/customers_suite.json` | `raw/customers` | required columns, ≥ 1 row, `customer_id` not null / unique / `IntegerType` or `LongType`, valid `email`, `name` not null, `created_at` is a timestamp/date |
| `great_expectations/expectations/events_suite.json` | `raw/api/events` | required columns, `event_id` not null / unique, `event_type` in the allowed set, `amount` not null and in `[0, 999999.99]` |

Things to know when editing suites:

- **Spark type names:** type expectations run on Spark DataFrames, so use Spark type names (`IntegerType`, `LongType`, `StringType`, `TimestampType`…), not pandas names like `int64`.
- **Extra columns:** `expect_table_columns_to_match_set` uses `"exact_match": false`, because bronze tables have the extra columns `_ingested_at` and `_source`. Only the listed columns are required.
- **Suites are for bronze:** silver tables add columns and are already cleaned. Create separate suites if you want to validate silver.

### Adding an expectation or a suite

1. Edit or add `great_expectations/expectations/<name>.json`. The format is `{"expectation_suite_name": ..., "expectations": [{"expectation_type": ..., "kwargs": {...}}]}`.
2. For a new dataset, add a `validate_<dataset>()` function in the notebook that reads the table and calls `run_validation(df, "<name>", "<dataset>")`, and add it to the `results` list.
3. Merge to `main`. The CD re-uploads the suites and the notebook.

## Running It Manually

- **Databricks UI:** run the `data_quality_validation` job, or open `/Shared/data-platform/notebooks/dq/validate_data_quality` and run all cells.
- **Other suite location:** set the `suites_dir` widget, for example to a Workspace Files path.

## Tests

`tests/integration/test_data_quality.py` checks the same rules on sample DataFrames with plain PySpark assertions:

```bash
uv run pytest tests/integration -q
```

## Possible Extensions

- **Alerting:** post the failure list printed by the notebook to Teams or Slack, or use an ADF failure path on `ValidateBronze`.
- **Quarantine:** write failing rows (`partial_unexpected_list` or a filter on the failing rule) to a `quarantine/` container instead of only blocking.
- **Data Docs:** persist validation results with a file-backed context and publish Data Docs to ADLS.
- **Silver suites:** add suites for `processed/*` and a validation step before gold.
