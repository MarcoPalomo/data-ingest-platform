# Databricks notebook source
# Databricks Notebook: Silver Layer - Event Transformation
# This notebook cleans and enriches event data for analytics.
# Input: raw/api/events  ->  Output: processed/events (Delta, full refresh)

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, current_timestamp
import logging

# COMMAND ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

STORAGE_ACCOUNT = dbutils.secrets.get(scope="dip-secrets", key="storage_account")
RAW_CONTAINER = "raw"
PROCESSED_CONTAINER = "processed"

# COMMAND ----------

def transform_events():
    """
    Transform raw events:
    - Parse timestamps
    - Remove nulls in critical fields
    - Deduplicate on event_id
    - Add processing metadata
    """
    try:
        spark = SparkSession.builder.appName("silver_events_transform").getOrCreate()

        # Read latest raw data
        bronze_path = f"abfss://{RAW_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/api/events"
        df = spark.read.format("delta").load(bronze_path)

        # Apply transformations
        df_transformed = df \
            .withColumn("event_timestamp", to_timestamp(col("created_at"))) \
            .withColumn("amount", col("amount").cast("double")) \
            .filter(col("event_type").isNotNull()) \
            .filter(col("customer_id").isNotNull()) \
            .dropDuplicates(["event_id"]) \
            .withColumn("processed_at", current_timestamp())

        # Write to silver, fixed path read by gold
        output_path = f"abfss://{PROCESSED_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/events"

        df_transformed.write.mode("overwrite").option("overwriteSchema", "true").format("delta").save(output_path)

        logger.info(f"Transformed {df.count()} events to {output_path}")

    except Exception as e:
        logger.error(f"Error transforming events: {e}")
        raise

# COMMAND ----------

if __name__ == "__main__":
    transform_events()
