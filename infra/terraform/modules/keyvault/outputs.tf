output "keyvault_id" {
  value = azurerm_key_vault.this.id
}

output "keyvault_uri" {
  value = azurerm_key_vault.this.vault_uri
}
