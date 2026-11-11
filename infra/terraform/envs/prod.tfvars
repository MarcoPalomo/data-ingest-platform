subscription_id         = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
resource_group_name     = "rg-dip-prod"
location                = "eastus"
storage_account_name    = "dipproducetionla"
workspace_name          = "dip-db-prod"
datafactory_name        = "dip-adf-prod"
keyvault_name           = "dip-kv-prod"
tenant_id               = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
admin_object_id         = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

tags = {
  Environment = "prod"
  Owner       = "data-platform"
  Project     = "data-ingestion-platform"
}
