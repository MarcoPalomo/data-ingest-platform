import pytest
import great_expectations as ge
from great_expectations.core.batch import RuntimeBatchRequest
import pandas as pd
from pyspark.sql import SparkSession


@pytest.fixture
def spark():
    """Fixture to create a Spark session for tests."""
    return SparkSession.builder \
        .master("local") \
        .appName("test-ge-validation") \
        .getOrCreate()


@pytest.fixture
def sample_customers_df(spark):
    """Create sample customer data."""
    data = [
        (1, "Alice", "alice@example.com", "2023-01-01 10:00:00"),
        (2, "Bob", "bob@example.com", "2023-01-02 11:00:00"),
        (3, "Charlie", "charlie@example.com", "2023-01-03 12:00:00"),
    ]
    columns = ["customer_id", "name", "email", "created_at"]
    return spark.createDataFrame(data, schema=columns)


@pytest.fixture
def sample_events_df(spark):
    """Create sample event data."""
    data = [
        (101, 1, "click", 0.0, "2023-01-01 10:05:00"),
        (102, 1, "purchase", 99.99, "2023-01-01 10:10:00"),
        (103, 2, "view", 0.0, "2023-01-02 11:05:00"),
    ]
    columns = ["event_id", "customer_id", "event_type", "amount", "created_at"]
    return spark.createDataFrame(data, schema=columns)


def test_customer_data_not_empty(sample_customers_df):
    """Test that customer DataFrame is not empty."""
    assert sample_customers_df.count() > 0


def test_customer_schema(sample_customers_df):
    """Test that customer data has expected columns."""
    expected_cols = {"customer_id", "name", "email", "created_at"}
    actual_cols = set(sample_customers_df.columns)
    assert expected_cols.issubset(actual_cols), f"Missing columns: {expected_cols - actual_cols}"


def test_customer_data_quality(sample_customers_df):
    """Test basic data quality checks on customer data (without GE context)."""
    # Check no null customer_ids
    null_count = sample_customers_df.filter(
        sample_customers_df.customer_id.isNull()
    ).count()
    assert null_count == 0, "Found null customer_ids"
    
    # Check no null emails
    null_emails = sample_customers_df.filter(
        sample_customers_df.email.isNull()
    ).count()
    assert null_emails == 0, "Found null emails"


def test_event_data_not_empty(sample_events_df):
    """Test that event DataFrame is not empty."""
    assert sample_events_df.count() > 0


def test_event_schema(sample_events_df):
    """Test that event data has expected columns."""
    expected_cols = {"event_id", "customer_id", "event_type", "amount", "created_at"}
    actual_cols = set(sample_events_df.columns)
    assert expected_cols.issubset(actual_cols), f"Missing columns: {expected_cols - actual_cols}"


def test_event_types_valid(sample_events_df):
    """Test that event types are in valid set."""
    valid_types = {"click", "view", "purchase", "review", "add_to_cart", "remove_from_cart"}
    
    actual_types = set(
        sample_events_df.select("event_type").distinct().rdd.flatMap(lambda x: x).collect()
    )
    
    invalid_types = actual_types - valid_types
    assert len(invalid_types) == 0, f"Found invalid event types: {invalid_types}"


def test_event_amounts_non_negative(sample_events_df):
    """Test that event amounts are non-negative."""
    negative_count = sample_events_df.filter(
        sample_events_df.amount < 0
    ).count()
    assert negative_count == 0, "Found negative amounts"


def test_event_amounts_within_bounds(sample_events_df):
    """Test that event amounts are within acceptable bounds."""
    out_of_bounds = sample_events_df.filter(
        (sample_events_df.amount < 0) | (sample_events_df.amount > 999999.99)
    ).count()
    assert out_of_bounds == 0, "Found amounts outside acceptable bounds"
