output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "storage_account_name" {
  value = module.datalake.storage_account_name
}

output "databricks_workspace_id" {
  value = module.databricks.workspace_id
}

output "datafactory_name" {
  value = module.datafactory.datafactory_name
}

output "keyvault_uri" {
  value = module.keyvault.keyvault_uri
}
output "datalake_storage_account" {
  value = module.datalake.storage_account_name
}
