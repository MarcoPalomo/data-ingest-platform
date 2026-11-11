# Implementation status — repo vs diagram

This document summarizes how the repository maps to the architecture diagram in `docs/architecture.md`, calls out differences, and lists optional next steps.

What I inspected
- `infra/terraform` (root and modules for datalake, databricks, datafactory, keyvault)
- `datafactory/` (pipeline, dataset, linked-service JSON artifacts)
- `databricks/` (notebooks, jobs, cluster configs)
- `great_expectations/` (config and expectation suites)
- `.github/workflows/` (CI, CD, security scan)

Implemented (matches diagram)
- GitHub Actions / CI: CI, security scans, and a CD workflow are present and configured to deploy artifacts and infrastructure.
- Orchestration (ADF): ADF JSON pipeline artifacts exist and `modules/datafactory` provisions an `azurerm_data_factory` resource.
- Raw Data Storage (ADLS Gen2 / Bronze): `modules/datalake` provisions an ADLS Gen2-enabled storage account (HNS) and containers.
- Databricks: Notebooks and job definitions are present; `modules/databricks` provisions an Azure Databricks workspace. Notebooks are written for Databricks runtime and Delta Lake.
- Data Quality: Great Expectations suites (`customers_suite`, `events_suite`) are validated against bronze by `dq/validate_data_quality`. In ADF this runs as the `ValidateBronze` step, which blocks silver/gold on failure.
- Python dependencies: managed with uv (`pyproject.toml` + `uv.lock`); CI and CD install with `uv sync --frozen`.
- Key Vault: A Key Vault module is present and ADF/other artifacts reference Key Vault linked-services.

Differences / gaps (what the diagram mentions but the repo does not fully provision)
- IaC tool: Diagram references ARM/Bicep for ADF; the repository uses **Terraform** to provision cloud resources and relies on CI to deploy pipeline JSON artifacts.
- Delta Live Tables (DLT): The diagram mentions DLT; the repo currently provides standard Databricks notebooks and job definitions, not DLT pipelines.
- MLflow: Not provisioned by default. If MLflow is required, a tracking server or Databricks-managed MLflow would need explicit setup.
- Monitoring & Logs: Terraform modules include diagnostic setting placeholders (e.g., `azurerm_monitor_diagnostic_setting`) but do not automatically wire a Log Analytics workspace or storage sink—these are left for environment-specific configuration.
- Production hardening: Items such as private endpoints, fine-grained role assignments, and managed-identity bindings are scaffolded or commented as examples but are not fully configured for production out-of-the-box.
- Analytics services: The repository includes connector examples (e.g., Azure SQL linked service), but does not provision Power BI or Synapse resources automatically.

Recommended next steps (pick one)
- Update `docs/architecture.md` to reflect the repo implementation (swap ARM/Bicep mention to Terraform, add a short 'Implemented vs diagram' section). This keeps the single source-of-truth in one file.
- Wire monitoring diagnostics to a Log Analytics workspace in Terraform (I can scaffold a small example module and tfvars). This reduces operational friction.
- Scaffold a DLT example or an MLflow provisioning example if you want the diagram to more closely match the repo.

If you want, I will update `docs/architecture.md` in-place to include a short summary (same content as this file), or I can implement one of the recommended next steps above.
