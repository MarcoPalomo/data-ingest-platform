variable "subscription_id" {
  type        = string
  description = "Azure subscription id used for provider configuration"
}

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group to create/use"
}

variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure region to deploy resources"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "storage_account_name" {
  type        = string
  description = "ADLS Gen2 storage account name"
}

variable "workspace_name" {
  type        = string
  description = "Databricks workspace name"
}

variable "datafactory_name" {
  type        = string
  description = "Data Factory name"
}

variable "keyvault_name" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "admin_object_id" {
  type = string
}

variable "datalake_containers" {
  type    = list(string)
  default = ["raw", "processed", "serving"]
}

variable "databricks_sku" {
  type    = string
  default = "standard"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "storage_owner_principal_id" {
  type        = string
  description = "(Optional) Principal id to give Storage Blob Data Owner role to; used for role assignment examples"
  default     = ""
}
variable "tfstate_resource_group" {
  type = string
}
variable "tfstate_storage_account" {
  type = string
}
variable "tfstate_container" {
  type = string
}
