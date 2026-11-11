resource "azurerm_storage_account" "datalake" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
  allow_blob_public_access = false
  min_tls_version          = "TLS1_2"
  identity {
    type = "SystemAssigned"
  }
}

# Create containers (raw/processed/serving) for ADLS Gen2
resource "azurerm_storage_container" "containers" {
  for_each            = toset(var.containers)
  name                = each.value
  storage_account_name = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Optional: apply network rules when provided
resource "azurerm_storage_account_network_rules" "rules" {
  storage_account_id = azurerm_storage_account.datalake.id
  default_action     = var.network_rules.default_action

  dynamic "ip_rules" {
    for_each = var.network_rules.ip_rules
    content {
      ip_address_or_range = ip_rules.value
    }
  }

  bypass = var.network_rules.bypass
}

resource "azurerm_storage_account_customer_managed_key" "cmk" {
  count = 0
  # Placeholder: enable customer-managed keys if needed
}

resource "azurerm_monitor_diagnostic_setting" "storage_diagnostics" {
  name               = "datalake-diagnostics"
  target_resource_id = azurerm_storage_account.datalake.id
  # Common logs/metrics to route to a Log Analytics workspace or Storage account.
  # left as placeholders for production configuration.
  depends_on = [azurerm_storage_container.containers]
}
