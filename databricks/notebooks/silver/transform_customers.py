# Databricks notebook source
# Databricks Notebook: Silver Layer - Customer Transformation
# This notebook applies transformations to the raw customer data for analytics.
# Input: raw/customers  ->  Output: processed/customers (Delta, full refresh)

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, trim, current_timestamp
import logging

# COMMAND ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

STORAGE_ACCOUNT = dbutils.secrets.get(scope="dip-secrets", key="storage_account")
RAW_CONTAINER = "raw"
PROCESSED_CONTAINER = "processed"

# COMMAND ----------

def transform_customers():
    """
    Transform raw customer data:
    - Lowercase and trim columns
    - Remove duplicates
    - Add processing timestamp
    """
    try:
        spark = SparkSession.builder.appName("silver_customers_transform").getOrCreate()

        # Read latest raw data
        bronze_path = f"abfss://{RAW_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/customers"
        df = spark.read.format("delta").load(bronze_path)

        # Apply transformations
        df_transformed = df \
            .withColumn("name", lower(trim(col("name")))) \
            .withColumn("email", lower(trim(col("email")))) \
            .dropDuplicates(["customer_id"]) \
            .withColumn("processed_at", current_timestamp())

        # Write to silver (processed) zone, fixed path read by gold
        output_path = f"abfss://{PROCESSED_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/customers"

        df_transformed.write.mode("overwrite").option("overwriteSchema", "true").format("delta").save(output_path)

        logger.info(f"Transformed {df.count()} customers to {output_path}")

    except Exception as e:
        logger.error(f"Error transforming customers: {e}")
        raise

# COMMAND ----------

if __name__ == "__main__":
    transform_customers()
