# Databricks notebook source
# Databricks Notebook: Bronze Layer - API Ingestion
# This notebook ingests data from external APIs into ADLS Gen2 (bronze).
# Output: raw/api/<dataset_name> (Delta, full snapshot overwritten on each run)

# COMMAND ----------

import requests
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit
import logging

# COMMAND ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

STORAGE_ACCOUNT = dbutils.secrets.get(scope="dip-secrets", key="storage_account")
CONTAINER = "raw"
API_BASE_URL = "https://api.example.com"

# COMMAND ----------

def ingest_api(endpoint: str, dataset_name: str, api_key: str = None, params: dict = None) -> None:
    """
    Ingest data from REST API and write to ADLS Gen2 (bronze).

    Args:
        endpoint: API endpoint path (e.g., "/v1/events")
        dataset_name: Target folder under raw/api/ (e.g., "events"), read by DQ and silver
        api_key: Optional API key (normally from secrets)
        params: Query parameters
    """
    try:
        spark = SparkSession.builder.appName("bronze_api_ingest").getOrCreate()

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        url = f"{API_BASE_URL}{endpoint}"
        logger.info(f"Fetching from {url}")

        response = requests.get(url, headers=headers, params=params or {}, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Ensure data is a list
        if isinstance(data, dict):
            data = [data]

        if not data:
            logger.warning(f"No records returned by {endpoint}; bronze {dataset_name} left unchanged")
            return

        # Let Spark's JSON reader infer the schema: handles nested objects and mixed int/float values
        df = spark.read.json(spark.sparkContext.parallelize([json.dumps(r) for r in data])) \
            .withColumn("_ingested_at", current_timestamp()) \
            .withColumn("_source", lit(f"api{endpoint}"))

        output_path = f"abfss://{CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/api/{dataset_name}"

        df.write.mode("overwrite").option("overwriteSchema", "true").format("delta").save(output_path)

        logger.info(f"Successfully ingested {len(data)} records from {endpoint} to {output_path}")

    except Exception as e:
        logger.error(f"Error ingesting from {endpoint}: {e}")
        raise

# COMMAND ----------

# Main entry point
if __name__ == "__main__":
    api_key = dbutils.secrets.get(scope="dip-secrets", key="api_key")
    ingest_api("/v1/events", dataset_name="events", api_key=api_key)
