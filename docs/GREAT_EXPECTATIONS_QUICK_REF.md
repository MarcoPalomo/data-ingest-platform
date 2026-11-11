# Data Quality with Great Expectations & PySpark: Quick Reference

## The Flow

```
Bronze Delta (raw/customers, raw/api/events)
   → spark.read.format("delta").load(...)
   → GX 0.18 ephemeral context, Spark dataframe asset
   → suite JSON (great_expectations/expectations/*.json)
   → Pass: silver runs | Fail: exception → ADF ValidateBronze Failed, silver/gold skipped
```

## Minimal Example (GX 0.18, as in `dq/validate_data_quality.py`)

```python
import json
import great_expectations as gx
from great_expectations.core.expectation_configuration import ExpectationConfiguration

df = spark.read.format("delta").load("abfss://raw@<storage>.dfs.core.windows.net/customers")

context = gx.get_context()                                   # ephemeral, no config to deploy
datasource = context.sources.add_or_update_spark(name="spark_adls")
asset = datasource.add_dataframe_asset(name="customers")

suite_def = json.load(open("/dbfs/FileStore/data-platform/great_expectations/expectations/customers_suite.json"))
suite = context.add_or_update_expectation_suite(expectation_suite_name="customers_suite")
for e in suite_def["expectations"]:
    suite.add_expectation(ExpectationConfiguration(expectation_type=e["expectation_type"], kwargs=e["kwargs"]))
context.add_or_update_expectation_suite(expectation_suite=suite)

validator = context.get_validator(
    batch_request=asset.build_batch_request(dataframe=df),
    expectation_suite_name="customers_suite",
)
result = validator.validate()
if not result.success:
    raise Exception("Data quality check failed")   # not dbutils.notebook.exit: that marks the run as succeeded
```

## Suite Rules of Thumb

| Topic | Rule |
|-------|------|
| Types | Spark names: `IntegerType`, `LongType`, `TimestampType`… (not `int64`) |
| Columns | `expect_table_columns_to_match_set` with `"exact_match": false`, because bronze has the extra columns `_ingested_at` and `_source` |
| Version | `great-expectations==0.18.21` in both `pyproject.toml` and the notebook `%pip` cell |

## Files in This Project

| File | Purpose |
|------|---------|
| `great_expectations/expectations/customers_suite.json` | Customer validation rules |
| `great_expectations/expectations/events_suite.json` | Event validation rules |
| `databricks/notebooks/dq/validate_data_quality.py` | Validation notebook (widget `suites_dir`) |
| `databricks/jobs/data_quality_validation_job.json` | Standalone job definition |
| `datafactory/pipelines/orchestrator_master.json` | `ValidateBronze` step between ingestion and silver |
| `.github/workflows/cd.yml` | Uploads suites to `dbfs:/FileStore/data-platform/great_expectations/expectations` |
| `tests/integration/test_data_quality.py` | CI tests with sample data (`uv run pytest tests/integration`) |

See `docs/great_expectations_integration.md` for full details.
