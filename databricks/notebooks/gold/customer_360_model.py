# Databricks notebook source
# Databricks Notebook: Gold Layer - Customer 360 Model
# This notebook creates a unified customer view for BI dashboards and APIs.
# Input: processed/customers + processed/events  ->  Output: serving/customer_360 (Delta, full refresh)

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as spark_sum, current_timestamp
import logging

# COMMAND ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

STORAGE_ACCOUNT = dbutils.secrets.get(scope="dip-secrets", key="storage_account")
PROCESSED_CONTAINER = "processed"
SERVING_CONTAINER = "serving"

# COMMAND ----------

def create_customer_360():
    """
    Create a 360-degree customer view by joining customers and events data.
    This dataset feeds BI dashboards and internal APIs.
    """
    try:
        spark = SparkSession.builder.appName("gold_customer_360").getOrCreate()

        # Read processed data
        customers_path = f"abfss://{PROCESSED_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/customers"
        events_path = f"abfss://{PROCESSED_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/events"

        df_customers = spark.read.format("delta").load(customers_path)
        df_events = spark.read.format("delta").load(events_path)

        # Aggregate events by customer
        df_events_agg = df_events.groupBy("customer_id") \
            .agg(
                count("event_id").alias("total_events"),
                spark_sum("amount").alias("total_spend")
            )

        # Join customer and event data (only the aggregates default to 0 for customers without events)
        df_360 = df_customers.join(df_events_agg, "customer_id", "left") \
            .fillna(0, subset=["total_events", "total_spend"]) \
            .withColumn("updated_at", current_timestamp())

        # Write to serving zone (exposed for dashboards and APIs), fixed path
        output_path = f"abfss://{SERVING_CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/customer_360"

        df_360.write.mode("overwrite").option("overwriteSchema", "true").format("delta").save(output_path)

        logger.info(f"Created customer 360 for {df_360.count()} customers to {output_path}")

    except Exception as e:
        logger.error(f"Error creating customer 360: {e}")
        raise

# COMMAND ----------

if __name__ == "__main__":
    create_customer_360()
