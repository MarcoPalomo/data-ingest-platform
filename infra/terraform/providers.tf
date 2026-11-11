terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = ">= 1.0"
    }
  }
}

provider "azurerm" {
  features = {}
  subscription_id = var.subscription_id
}

# Databricks provider configuration is intentionally left to CI/deploy-time
# because it often requires a workspace URL and token. We allow override
# via environment variables or provider aliasing in CI pipelines.
provider "databricks" {
  # host and token should be provided via environment variables or provider config
  # e.g. DATabrICKS_HOST / DATABRICKS_TOKEN or via provider alias
}
