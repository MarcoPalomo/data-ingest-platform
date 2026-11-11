# Databricks notebook source
# Databricks Notebook: Data Quality Validation (Great Expectations)
# Validates the bronze (raw) zone before silver runs. Raises on failure so the job / ADF activity fails
# and downstream layers are not executed.
# Suites are the JSON files from great_expectations/expectations/, uploaded by CD to DBFS.
# GX is pinned to 0.18: the code below uses the 0.18 Fluent API (removed in GX 1.x).

# COMMAND ----------

# MAGIC %pip install great-expectations==0.18.21

# COMMAND ----------

import great_expectations as gx
from great_expectations.core.expectation_configuration import ExpectationConfiguration
from great_expectations.data_context.types.base import DataContextConfig, InMemoryStoreBackendDefaults
import json
import logging
import os
from datetime import datetime

# COMMAND ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

# Configuration
dbutils.widgets.text("suites_dir", "/dbfs/FileStore/data-platform/great_expectations/expectations")
SUITES_DIR = dbutils.widgets.get("suites_dir")

STORAGE_ACCOUNT = dbutils.secrets.get(scope="dip-secrets", key="storage_account")
CONTAINER = "raw"

# Explicit in-memory context: datasource and suites are defined at runtime, nothing to deploy besides the
# suite JSON, and no great_expectations.yml found on disk is picked up by accident.
context = gx.get_context(
    project_config=DataContextConfig(store_backend_defaults=InMemoryStoreBackendDefaults())
)
datasource = context.sources.add_or_update_spark(name="spark_adls")

# COMMAND ----------

def load_suite(suite_name):
    """Register the suite from <SUITES_DIR>/<suite_name>.json in the context."""
    with open(os.path.join(SUITES_DIR, f"{suite_name}.json")) as f:
        suite_def = json.load(f)

    suite = context.add_or_update_expectation_suite(expectation_suite_name=suite_name)
    for exp in suite_def["expectations"]:
        suite.add_expectation(ExpectationConfiguration(
            expectation_type=exp["expectation_type"],
            kwargs=exp["kwargs"],
            meta=exp.get("meta", {}),
        ))
    context.add_or_update_expectation_suite(expectation_suite=suite)

# COMMAND ----------

def run_validation(df, suite_name, data_asset_name):
    """
    Validate a PySpark DataFrame using Great Expectations.

    Args:
        df: PySpark DataFrame to validate
        suite_name: Name of the expectation suite (e.g., 'customers_suite')
        data_asset_name: Name of the data asset for tracking

    Returns:
        dict: validation results with success status and details
    """
    try:
        logger.info(f"Starting validation for {data_asset_name} with suite {suite_name}")

        load_suite(suite_name)

        try:
            asset = datasource.get_asset(data_asset_name)
        except LookupError:
            asset = datasource.add_dataframe_asset(name=data_asset_name)
        batch_request = asset.build_batch_request(dataframe=df)

        validator = context.get_validator(
            batch_request=batch_request,
            expectation_suite_name=suite_name
        )

        validation_result = validator.validate()

        success = validation_result.success
        num_expectations = len(validation_result.results)
        num_passed = sum(1 for r in validation_result.results if r.success)
        num_failed = num_expectations - num_passed

        logger.info(f"Validation complete: {num_passed}/{num_expectations} passed, {num_failed} failed")

        failures = []
        for result in validation_result.results:
            if not result.success:
                details = result.result or {}
                failures.append({
                    "expectation_type": result.expectation_config.expectation_type,
                    "kwargs": result.expectation_config.kwargs,
                    "unexpected_count": details.get("unexpected_count"),
                    "partial_unexpected_list": details.get("partial_unexpected_list"),
                    "exception": (result.exception_info or {}).get("exception_message"),
                })

        return {
            "success": success,
            "data_asset": data_asset_name,
            "suite_name": suite_name,
            "timestamp": datetime.now().isoformat(),
            "total_expectations": num_expectations,
            "passed": num_passed,
            "failed": num_failed,
            "failures": failures,
        }

    except Exception as e:
        logger.exception(f"Validation error for {data_asset_name}")
        return {
            "success": False,
            "data_asset": data_asset_name,
            "suite_name": suite_name,
            "timestamp": datetime.now().isoformat(),
            "failures": [],
            "error": str(e),
        }

# COMMAND ----------

def validate_customers():
    """Validate bronze customer data against customers_suite."""
    bronze_path = f"abfss://{CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/customers"
    df = spark.read.format("delta").load(bronze_path)
    return run_validation(df, "customers_suite", "customers")

# COMMAND ----------

def validate_events():
    """Validate bronze event data against events_suite."""
    bronze_path = f"abfss://{CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/api/events"
    df = spark.read.format("delta").load(bronze_path)
    return run_validation(df, "events_suite", "events")

# COMMAND ----------

# Main entry point: run every validation, report, then fail the run if any failed
if __name__ == "__main__":
    logger.info("Starting data quality validation...")
    results = [validate_customers(), validate_events()]

    for r in results:
        print(f"\n{r['data_asset']}: {'PASS' if r['success'] else 'FAIL'}")
        if r.get("error"):
            print(f"  Error: {r['error']}")
        else:
            print(f"  Passed: {r['passed']}/{r['total_expectations']}")
        for f in r["failures"]:
            print(f"    - {f['expectation_type']} {f['kwargs']}: "
                  f"unexpected={f['unexpected_count']} sample={f['partial_unexpected_list']} {f['exception'] or ''}")

    failed = [r["data_asset"] for r in results if not r["success"]]
    if failed:
        # raise (not dbutils.notebook.exit) so the Databricks run and the ADF activity are marked Failed
        raise Exception(f"Data quality check failed for: {', '.join(failed)}")

    logger.info("All validations passed ✅")
