// Top-level Terraform that pulls modules for datalake, databricks, datafactory

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

module "datalake" {
  source              = "./modules/datalake"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  storage_account_name = var.storage_account_name
  containers          = var.datalake_containers
  tags                = var.tags
}

module "databricks" {
  source              = "./modules/databricks"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_name      = var.workspace_name
  sku                 = var.databricks_sku
  tags                = var.tags
}

module "datafactory" {
  source              = "./modules/datafactory"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name                = var.datafactory_name
  tags                = var.tags
}

module "keyvault" {
  source              = "./modules/keyvault"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  name                = var.keyvault_name
  tenant_id           = var.tenant_id
  admin_object_id     = var.admin_object_id
  tags                = var.tags
}

# Example role assignment (commented) - replace principal_id with a known object id
# resource "azurerm_role_assignment" "example_storage_owner" {
#   scope                = module.datalake.storage_account_id
#   role_definition_name = "Storage Blob Data Owner"
#   principal_id         = var.storage_owner_principal_id
# }
