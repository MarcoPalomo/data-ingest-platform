# Databricks notebook source
# Databricks Notebook: Bronze Layer - SQL Ingestion
# This notebook ingests data from Azure SQL into ADLS Gen2 in bronze (raw) format.
# Output: raw/<table_name> (Delta, full snapshot overwritten on each run; history kept by Delta time travel)

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit
import logging

# COMMAND ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

# Configuration (normally from widgets or secrets)
STORAGE_ACCOUNT = dbutils.secrets.get(scope="dip-secrets", key="storage_account")
CONTAINER = "raw"

# COMMAND ----------

def ingest_sql_table(table_name: str, query: str = None) -> None:
    """
    Ingest a table from Azure SQL to ADLS Gen2 (bronze).

    Args:
        table_name: Name of the SQL table
        query: Optional custom SQL query; if None, SELECT * FROM table_name
    """
    try:
        spark = SparkSession.builder.appName("bronze_sql_ingest").getOrCreate()

        sql = query or f"SELECT * FROM {table_name}"

        # Read from Azure SQL
        df = spark.read \
            .format("sqlserver") \
            .option("host", "your-sql-server.database.windows.net") \
            .option("port", "1433") \
            .option("database", "your_database") \
            .option("query", sql) \
            .option("user", dbutils.secrets.get(scope="dip-secrets", key="sql_user")) \
            .option("password", dbutils.secrets.get(scope="dip-secrets", key="sql_password")) \
            .load() \
            .withColumn("_ingested_at", current_timestamp()) \
            .withColumn("_source", lit(f"azure_sql.{table_name}"))

        # Fixed path read by DQ and silver; ingestion time is tracked in _ingested_at
        output_path = f"abfss://{CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net/{table_name}"

        df.write.mode("overwrite").option("overwriteSchema", "true").format("delta").save(output_path)

        logger.info(f"Successfully ingested {table_name} to {output_path}")

    except Exception as e:
        logger.error(f"Error ingesting {table_name}: {e}")
        raise

# COMMAND ----------

# Main entry point
# Events come from the API (see ingest_unstructured), not from SQL.
if __name__ == "__main__":
    ingest_sql_table("customers")
