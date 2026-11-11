resource "azurerm_databricks_workspace" "this" {
  name                = var.workspace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku

  parameters = {}
}

# Optionally create a user-assigned identity for Databricks workloads (example)
resource "azurerm_user_assigned_identity" "databricks_uai" {
  count               = var.create_user_assigned_identity ? 1 : 0
  name                = "${var.workspace_name}-uai"
  resource_group_name = var.resource_group_name
  location            = var.location
}

output "workspace_id" {
  value = azurerm_databricks_workspace.this.id
}

output "workspace_url" {
  value = azurerm_databricks_workspace.this.workspace_url
}

