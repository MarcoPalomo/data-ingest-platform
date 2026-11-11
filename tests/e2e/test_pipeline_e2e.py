import pytest
from pyspark.sql import SparkSession

from src.pipeline.etl import transform_customers_df, transform_events_df, create_customer_360_df


@pytest.fixture(scope="session")
def spark():
    spark = SparkSession.builder.master("local[2]") \
        .appName("dip-e2e-test") \
        .config("spark.ui.showConsoleProgress", "false") \
        .getOrCreate()
    yield spark
    spark.stop()


@pytest.mark.e2e
def test_pipeline_end_to_end(spark):
    # Sample customers
    customers = [
        (1, "Alice", "ALICE@EXAMPLE.COM", "2023-01-01 10:00:00"),
        (2, "Bob", "bob@example.com", "2023-01-02 11:00:00"),
        (3, "Charlie", "charlie@example.com", "2023-01-03 12:00:00"),
    ]
    customers_cols = ["customer_id", "name", "email", "created_at"]
    customers_df = spark.createDataFrame(customers, schema=customers_cols)

    # Sample events
    events = [
        (101, 1, "click", 0.0, "2023-01-01 10:05:00"),
        (102, 1, "purchase", 99.99, "2023-01-01 10:10:00"),
        (103, 2, "view", 0.0, "2023-01-02 11:05:00"),
    ]
    events_cols = ["event_id", "customer_id", "event_type", "amount", "created_at"]
    events_df = spark.createDataFrame(events, schema=events_cols)

    # Run transforms
    customers_silver = transform_customers_df(customers_df)
    events_silver = transform_events_df(events_df)

    # Create customer 360
    df_360 = create_customer_360_df(customers_silver, events_silver)

    # Assertions
    assert df_360.count() == 3
    cols = set(df_360.columns)
    assert "total_events" in cols and "total_spend" in cols

    # Validate aggregated values for customer 1
    row = df_360.filter(df_360.customer_id == 1).select("total_events", "total_spend").collect()[0]
    assert row[0] == 2
    assert abs(row[1] - 99.99) < 0.001
