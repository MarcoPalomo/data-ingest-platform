# Data Ingestion Platform

Opinionated scaffold for a modern data pipeline that ingests multiple sources (API, SQL, documents),
applies automated data quality and schema validation, and deploys Azure Data Factory + Databricks via
Infrastructure-as-Code and GitHub Actions CI/CD.

**Purpose:** provide a repeatable starting point for building analytics-ready data lakes, transformation
logic in Databricks, Data Factory orchestration, and automated deployment with security and testing
considerations in place.

**Repository layout (short):**
- `infra/terraform/` : Terraform root and modules for core Azure resources (datalake, databricks, datafactory, keyvault).
- `datafactory/` : ADF JSON definitions (pipelines, datasets, linked services) for orchestrator and ingest pipelines.
- `databricks/` : Notebooks, job definitions and cluster configs for bronze/silver/gold layers.
- `great_expectations/` : Great Expectations config, expectation suites and checkpoints for DQ.
- `src/` : Reusable Python helpers and ingestion adapters (API, SQL, unstructured).
- `tests/` : Unit and lightweight integration tests plus sample data.
- `docs/` : Architecture, onboarding, and operational runbooks.

**Quick links:** `infra/terraform/README.md`, `docs/architecture.md`, `datafactory/pipelines/orchestrator_master.json`.

**Quickstart (developer)**

1. Install prerequisites (local). Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # once
uv sync                                           # creates .venv (Python from .python-version) with runtime + dev deps
```

2. Run unit tests:

```bash
uv run pytest -q
```

3. Lint and format (pre-commit):

```bash
uv run pre-commit run --all-files
```

Add a dependency with `uv add <pkg>` (or `uv add --group dev <pkg>`), and commit `pyproject.toml` and `uv.lock` together. See `docs/deployment.md#python-dependencies-uv`.

**Deploy (example, Terraform)**

1. Ensure you have an Azure subscription and the values to populate `infra/terraform/envs/dev.tfvars`.
2. Initialize and plan:

```bash
cd infra/terraform
terraform init
terraform plan -var-file=envs/dev.tfvars
```

3. Apply (recommended from CI/CD; for local testing):

```bash
terraform apply -var-file=envs/dev.tfvars
```

Notes:
- `infra/terraform/backend.tf` is configured to use an `azurerm` backend. Create the storage account/container
	used for state before running `terraform init`.
- Databricks provider requires `DATABRICKS_HOST` and `DATABRICKS_TOKEN` at deploy time; CI uses Azure OIDC or
	secrets to set these.

**Databricks & Data Factory deployment**

- Databricks notebooks live under `databricks/notebooks/{bronze,silver,gold,dq}/` as `.py` in Databricks source
	format. The CD imports them to `/Shared/data-platform/notebooks/<layer>/<notebook>`, the path used by the jobs and ADF pipelines.
- Job definitions live under `databricks/jobs/` as JSON; the CD deploys them with the Databricks CLI from the uv
	`deploy` group (`uv sync --only-group deploy`).
- Pipeline: ingest (SQL customers + API events) → Great Expectations validation of bronze → silver → gold
	(`serving/customer_360`). Paths and order are documented in `docs/deployment.md#databricks-artifacts--data-pipeline`.
- ADF JSON artifacts live under `datafactory/`; deploy them via ARM/Terraform or `az datafactory` CLI. The
	JSONs are parameterized; update linked-service parameters for production (Key Vault references, workspace IDs).

**CI/CD (GitHub Actions)**

- ` .github/workflows/ci.yml` runs lint and tests on PRs (dependencies installed with `uv sync --frozen`).
- ` .github/workflows/cd.yml` is a placeholder for deploy-on-merge. Recommended flow:
	- PR -> CI validates code and `terraform plan` (using `-destroy` disabled) -> reviewers approve
	- Merge to `main` triggers a protected CD workflow that runs `terraform apply` and deploys Databricks/ADF artifacts
		using short-lived credentials (Azure OIDC recommended).
- ` .github/workflows/security-scan.yml` runs Snyk; set the `SNYK_TOKEN` repository secret.

**Secrets & credentials**

- Development: use `./.env` (not checked-in) or `az login` + `az account set` for local testing.
- CI/Production: use GitHub Actions with Azure OIDC (no long-lived secrets) and GitHub Secrets for tokens not
	supported by OIDC (e.g., Snyk token). Use Azure Key Vault for application secrets; Terraform can create the vault
	and store initial secrets as part of deployment (but do not hard-code secrets in `.tfvars`).

**Data Quality (Great Expectations)**

- Expectation suites live under `great_expectations/expectations/` (`customers_suite`, `events_suite`). The CD uploads
	them to DBFS.
- `databricks/notebooks/dq/validate_data_quality.py` (GX 0.18.21) validates the bronze tables. It runs in ADF between
	ingestion and silver and fails the pipeline when an expectation fails. See `docs/great_expectations_integration.md`.

**Testing guidance**

- Unit tests: `pytest` under `tests/unit/`.
- Integration tests: use small sample datasets in `tests/data/` and lightweight mocks for external APIs (use `responses` or `vcrpy`).
- Static checks: `black`, `isort`, `flake8` via `.pre-commit-config.yaml`.

**Security & production hardening checklist (brief)**
- Use Azure Private Endpoints for Storage and Key Vault.
- Lock down Storage account network rules and use Firewall/Service Endpoints.
- Grant least-privilege RBAC roles to Databricks managed identity / user-assigned identity.
- Enable diagnostic logs for Storage, ADF, and Databricks to a Log Analytics workspace.
- Enable soft-delete and purge protection on Key Vault; rotate keys and secrets regularly.

**Contributing & support**

- Add a `CODEOWNERS` entry for areas of ownership.
- Follow the PR template and branch protection rules; run CI checks locally before opening PRs.

**Next steps I can help with**
- Add full `terraform` root wiring for role assignments and private endpoints.
- Add a GitHub Actions workflow that runs Terraform with Azure OIDC and performs `plan` on PRs and `apply` on merge.

License: MIT — see `LICENSE`.

