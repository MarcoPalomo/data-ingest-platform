from pyspark.sql import DataFrame
from pyspark.sql.functions import lower, trim, current_timestamp, col, to_timestamp, sum as spark_sum, count


def transform_customers_df(df: DataFrame) -> DataFrame:
    """
    Transform raw customer DataFrame to silver/processed form.
    Operates on an in-memory PySpark DataFrame and returns a transformed DataFrame.
    """
    df_transformed = (
        df.withColumn("name", lower(trim(col("name"))))
          .withColumn("email", lower(trim(col("email"))))
          .dropDuplicates(["customer_id"])
          .withColumn("processed_at", current_timestamp())
    )
    return df_transformed


def transform_events_df(df: DataFrame) -> DataFrame:
    """
    Transform raw events DataFrame to silver/processed form.
    - parse timestamps, remove events without critical fields, add processed_at
    """
    df_transformed = (
        df.withColumn("event_timestamp", to_timestamp(col("created_at")))
          .filter(col("event_type").isNotNull())
          .filter(col("customer_id").isNotNull())
          .withColumn("processed_at", current_timestamp())
    )
    return df_transformed


def create_customer_360_df(customers_df: DataFrame, events_df: DataFrame) -> DataFrame:
    """
    Create a 360-degree customer view by joining customers and aggregated events.
    Returns a DataFrame ready for serving.
    """
    events_agg = (
        events_df.groupBy("customer_id")
                 .agg(
                     count("event_id").alias("total_events"),
                     spark_sum("amount").alias("total_spend")
                 )
    )

    df_360 = (
        customers_df.join(events_agg, on="customer_id", how="left")
                    .fillna({"total_events": 0, "total_spend": 0.0})
                    .withColumn("updated_at", current_timestamp())
    )
    return df_360
