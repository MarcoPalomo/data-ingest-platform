# Terraform modules for Data Ingestion Platform

This folder contains a small set of opinionated Terraform modules used to provision core Azure resources used by the project:

- `modules/datalake` - ADLS Gen2 storage account and containers (raw/processed/serving)
- `modules/databricks` - Azure Databricks workspace (minimal example)
- `modules/datafactory` - Azure Data Factory instance
- `modules/keyvault` - Azure Key Vault

Usage example (from `infra/terraform`):

1. Prepare `backend.tf` with your tfstate storage values (already included).
2. Create `envs/dev.tfvars` and fill in values.
3. Run:

```bash
terraform init
terraform plan -var-file=envs/dev.tfvars
terraform apply -var-file=envs/dev.tfvars
```

Notes:
- These modules are small examples to get started. In production, split resources into smaller modules, add role assignments, network rules, private endpoints, and logging/monitoring.
- Do not commit secrets. Use Key Vault + managed identities or Azure OIDC in GitHub Actions.
