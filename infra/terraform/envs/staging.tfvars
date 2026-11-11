subscription_id         = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
resource_group_name     = "rg-dip-staging"
location                = "eastus"
storage_account_name    = "dipstagingla"
workspace_name          = "dip-db-staging"
datafactory_name        = "dip-adf-staging"
keyvault_name           = "dip-kv-staging"
tenant_id               = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
admin_object_id         = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

tags = {
  Environment = "staging"
  Owner       = "data-platform"
  Project     = "data-ingestion-platform"
}
