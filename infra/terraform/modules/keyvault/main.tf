resource "azurerm_key_vault" "this" {
  name                        = var.name
  location                    = var.location
  resource_group_name         = var.resource_group_name
  tenant_id                   = var.tenant_id
  sku_name                    = var.sku_name
  purge_protection_enabled    = false
  soft_delete_enabled         = true
  soft_delete_retention_days  = 90

  access_policy {
    tenant_id = var.tenant_id
    object_id = var.admin_object_id

    secret_permissions = [
      "get",
      "list",
      "set",
      "delete"
    ]
  }
}

resource "azurerm_key_vault_access_policy" "example" {
  count                = 0
  key_vault_id         = azurerm_key_vault.this.id
  tenant_id            = var.tenant_id
  object_id            = var.admin_object_id
  secret_permissions   = ["get", "list"]
}
