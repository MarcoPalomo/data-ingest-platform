# Deployment & CI/CD Guide

This document explains how to set up and deploy the Data Ingestion Platform using GitHub Actions, Azure OIDC, and Terraform in a GitOps fashion.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       GitHub Repository                         │
│                                                                 │
│  ┌──────────────────┐       ┌──────────────────┐               │
│  │  Pull Request    │       │  Push to main    │               │
│  │  (CI workflow)   │       │  (CD workflow)   │               │
│  └────────┬─────────┘       └────────┬─────────┘               │
│           │                          │                          │
│      Lint & Test              Terraform Plan                    │
│      (no deploy)              Databricks Deploy                 │
│                               ADF Deploy                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ↓
        ┌───────────────────────────────────────┐
        │     Azure OIDC (short-lived token)    │
        │  (no secrets stored in GitHub)        │
        └───────────────┬───────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ↓              ↓              ↓
   ┌──────────┐   ┌──────────┐  ┌──────────┐
   │Terraform │   │Databricks│  │Data      │
   │Deploy    │   │Deploy    │  │Factory   │
   │Infra     │   │Notebooks │  │Pipelines │
   └──────────┘   └──────────┘  └──────────┘
```

## Prerequisites

1. **Azure Setup:**
   - Azure subscription with contributor or custom role privileges.
   - An existing storage account for Terraform state (one per environment).
   - Service Principal or Azure AD app for OIDC federation.

2. **GitHub Setup:**
   - Repository with branch protection on `main` (require PR reviews before merge).
   - GitHub Organization or user with ability to create secrets and environments.

3. **Tools (local development):**
   - Terraform >= 1.2
   - Azure CLI (`az` command)
   - [uv](https://docs.astral.sh/uv/) — manages Python, all Python dependencies and the Databricks CLI (see [Python Dependencies (uv)](#python-dependencies-uv))
   - Python 3.10 (installed automatically by uv from `.python-version`)

## Python Dependencies (uv)

All Python dependencies are declared in `pyproject.toml` and pinned in `uv.lock`. There is no `requirements.txt` and no `pip install` in the workflows anymore.

| Section | Content | Used by |
|---------|---------|---------|
| `[project] dependencies` | `requests`, `pyodbc`, `pyspark` 3.3.x, `pandas` < 2, `great-expectations==0.18.21` | Local dev, CI tests, smoke tests |
| `[dependency-groups] dev` (installed by default) | `pytest`, `pytest-spark`, `pre-commit` | Local dev, CI |
| `[dependency-groups] deploy` | `databricks-cli==0.18.0` (legacy Python CLI) | CD `databricks-deploy` job |

Versions are aligned with the Databricks cluster runtime (`12.2.x-scala2.12` = Python 3.9 / Spark 3.3.2): `pyspark` 3.3 and `pandas` < 2 (pandas 2 breaks PySpark 3.3).

Common commands:

```bash
uv sync                          # create .venv with runtime + dev deps (from uv.lock)
uv run pytest -q                 # run tests
uv run pre-commit run --all-files
uv sync --only-group deploy      # only the Databricks CLI (what CD does)
uv run --only-group deploy databricks --version

uv add <package>                 # add a runtime dependency (updates pyproject.toml + uv.lock)
uv add --group dev <package>     # add a dev-only dependency
uv lock --upgrade-package <pkg>  # bump one package
```

Rules:
- Always commit `pyproject.toml` **and** `uv.lock` together. CI and CD run `uv sync --frozen`, which fails if the lock is out of date.
- `great-expectations` is pinned twice, in `pyproject.toml` and in the `%pip install` cell of `databricks/notebooks/dq/validate_data_quality.py` (the cluster does not use `uv.lock`). Change both together.

## GitHub Secrets Configuration

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

### Azure OIDC (Recommended for Production)

```
AZURE_CLIENT_ID         # Service principal/app client ID
AZURE_TENANT_ID         # Azure AD tenant ID
AZURE_SUBSCRIPTION_ID   # Azure subscription ID
```

Also, add environment-specific repository secrets:

```
# For dev environment
TFSTATE_RG_dev
TFSTATE_SA_dev
TFSTATE_CONTAINER_dev
KEYVAULT_NAME_dev

# For staging environment
TFSTATE_RG_staging
TFSTATE_SA_staging
TFSTATE_CONTAINER_staging
KEYVAULT_NAME_staging

# For prod environment (requires manual approval)
TFSTATE_RG_prod
TFSTATE_SA_prod
TFSTATE_CONTAINER_prod
KEYVAULT_NAME_prod
```

Also add `SNYK_TOKEN` for security scanning:

```
SNYK_TOKEN              # Snyk API token
```

## Setting Up Azure OIDC (GitHub → Azure Passwordless Auth)

Instead of storing long-lived secrets, use OIDC to mint short-lived tokens:

1. **Create Azure AD App and Federated Credentials:**

```bash
# Create app registration
APP=$(az ad app create --display-name "github-oidc-dip" --query appId -o tsv)

# Create service principal
SP=$(az ad sp create --id "$APP" --query id -o tsv)

# Create federated credential for GitHub
az ad app federated-credential create \
  --id "$APP" \
  --parameters '{
    "name": "github-dip",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/data-ingestion-platform:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Grant the service principal access (e.g., Contributor role)
az role assignment create \
  --assignee "$SP" \
  --role "Contributor" \
  --subscription "YOUR_SUBSCRIPTION_ID"
```

2. **Add GitHub Secrets (for OIDC):**

Get the IDs:

```bash
az account show --query tenantId -o tsv          # AZURE_TENANT_ID
az account show --query id -o tsv                # AZURE_SUBSCRIPTION_ID
echo "$APP"                                        # AZURE_CLIENT_ID
```

Then add to GitHub Secrets:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

## GitHub Environments (for gating)

Create environments for each target:

1. Go to **Settings → Environments**.
2. Create `terraform-dev`, `terraform-staging`, `terraform-prod`.
3. For `terraform-prod`, add deployment reviewers under "Required reviewers".

This ensures prod deployments require manual approval.

## Workflow Triggers

### CI Workflow (`.github/workflows/ci.yml`)

Runs on every push and PR:
- Installs dependencies with `astral-sh/setup-uv` + `uv sync --frozen`
- Lint (black, isort, flake8) via `uv run pre-commit run --all-files` (non-blocking for now)
- Unit tests via `uv run pytest -q`
- E2E tests (`pytest -m e2e`) inside the `jupyter/pyspark-notebook` image, also installed with `uv sync --frozen`

The Snyk scan runs in a separate workflow (`.github/workflows/security-scan.yml`).

### CD Workflow (`.github/workflows/cd.yml`)

**On push to `main`:**
- Auto-deploys to `dev` environment.
- Skips `staging` and `prod` (manual trigger only).

**On manual workflow dispatch (Actions → Run workflow):**
- Choose environment (dev/staging/prod).
- Deploys Terraform, Databricks, and Data Factory.
- Prod deployments require approval (environment gate).

## Deployment Flow

### 1. Developer Opens a PR

```
PR pushed → CI workflow triggers
   ├── Lint & format checks
   ├── Unit tests
   └── Snyk security scan
   
If all pass → ready for review
If any fail → PR shows failures, developer fixes
```

### 2. Code Review & Merge

Once approved and merged to `main`:

```
Merge to main → CD workflow triggers automatically
   ├── Terraform init (from tfstate backend)
   ├── Terraform plan -var-file=envs/dev.tfvars
   ├── Terraform apply (auto-approved for dev)
   ├── Databricks deploy
   │     ├── uv sync --frozen --only-group deploy   (Databricks CLI)
   │     ├── notebooks  → /Shared/data-platform/notebooks/{bronze,silver,gold,dq}/
   │     ├── GX suites  → dbfs:/FileStore/data-platform/great_expectations/expectations/
   │     └── jobs       (databricks/jobs/*.json)
   ├── ADF pipelines deploy
   └── Post-deploy smoke tests (uv sync --frozen && uv run pytest -k "not integration")
```

## Databricks Artifacts & Data Pipeline

### Notebook paths

The CD imports each notebook to `/Shared/data-platform/notebooks/<layer>/<notebook>`. The same path is used in **three places**, keep them in sync:

| Where | Field |
|-------|-------|
| `.github/workflows/cd.yml` | `NOTEBOOK_ROOT` |
| `databricks/jobs/*.json` | `notebook_task.notebook_path` |
| `datafactory/pipelines/*.json` | `typeProperties.notebookPath` |

Notebooks must keep `# Databricks notebook source` as first line and `# COMMAND ----------` between cells. Otherwise the import creates a single cell and magics such as `%pip` break. Magic commands are written as `# MAGIC %pip ...`.

### Pipeline order (`datafactory/pipelines/orchestrator_master.json`)

```
IngestSQL (customers) ─┐
                       ├─→ ValidateBronze (GX) ─┬─→ TransformSilverCustomers ─┐
IngestAPI (events)  ───┘                        └─→ TransformSilverEvents  ───┴─→ CreateGold
```

- `ExecutePipeline` activities use `waitOnCompletion: true`. Without it, ADF starts the next step before ingestion is finished.
- `ValidateBronze` raises an exception when an expectation fails, so the activity is **Failed** and silver/gold do not run.

### Storage layout (ADLS Gen2, Delta)

| Layer | Path | Written by | Read by |
|-------|------|-----------|---------|
| Bronze | `raw/customers` | `bronze/ingest_sql` | `dq/validate_data_quality`, `silver/transform_customers` |
| Bronze | `raw/api/events` | `bronze/ingest_unstructured` | `dq/validate_data_quality`, `silver/transform_events` |
| Silver | `processed/customers` | `silver/transform_customers` | `gold/customer_360_model` |
| Silver | `processed/events` | `silver/transform_events` | `gold/customer_360_model` |
| Gold | `serving/customer_360` | `gold/customer_360_model` | BI / APIs |

Each run overwrites the table at a **fixed path** (`overwriteSchema` enabled). Earlier runs stay available through Delta time travel (`VERSION AS OF` / `TIMESTAMP AS OF`). Bronze tables carry `_ingested_at` and `_source` columns. Events come from the API only; the SQL notebook ingests `customers` only.

### 3. Manual Promotion to Staging/Prod

```
Go to Actions → Select CD workflow → Run workflow
   ├── Choose environment (staging or prod)
   ├── Terraform plan & apply
   ├── Databricks & ADF deploy
   └── (Prod requires approval before apply)
```

## Environment Variables & Secrets in Terraform

Create environment-specific `.tfvars` files (e.g., `envs/dev.tfvars`):

```hcl
subscription_id         = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
resource_group_name     = "rg-dip-dev"
location                = "eastus"
storage_account_name    = "dipdevelopla"
workspace_name          = "dip-db-dev"
datafactory_name        = "dip-adf-dev"
keyvault_name           = "dip-kv-dev"
tenant_id               = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
admin_object_id         = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

tags = {
  Environment = "dev"
  Owner       = "data-platform"
  Project     = "data-ingestion-platform"
}
```

**Note:** Do not commit secret values to `.tfvars` files. Instead:
- Use GitHub Secrets for sensitive data.
- Reference them in GitHub Actions environment variables.
- Pass them to Terraform via command-line `-var` flags (if needed).

## Databricks Token Management

The Databricks token is fetched from Azure Key Vault at deploy time:

```yaml
# From cd.yml: Deploy Databricks assets step
az keyvault secret show \
  --vault-name "$KV_NAME" \
  --name "databricks-token" \
  --query value -o tsv
```

**To add the token to Key Vault (one-time setup):**

```bash
# Get a Databricks PAT from the workspace admin
DATABRICKS_TOKEN="dapi1234567890abcdef"

az keyvault secret set \
  --vault-name "dip-kv-dev" \
  --name "databricks-token" \
  --value "$DATABRICKS_TOKEN"
```

## Local Testing

To test Terraform locally:

```bash
cd infra/terraform

# Initialize backend
terraform init \
  -backend-config="resource_group_name=rg-tfstate" \
  -backend-config="storage_account_name=mystgaccount" \
  -backend-config="container_name=tfstate"

# Plan with dev variables
terraform plan -var-file=envs/dev.tfvars -out=tfplan

# Apply (use caution in shared environments)
terraform apply tfplan
```

## Monitoring & Alerts

After deployment, monitor:

1. **Azure Portal:**
   - Resource group status and costs.
   - Data Factory pipeline runs.
   - Databricks workspace and job runs.

2. **GitHub Actions:**
   - Workflow run history and logs.
   - PR status checks.

3. **Application-level:**
   - Databricks job logs and metrics.
   - ADF monitoring and alerts.
   - Key Vault access logs (in Log Analytics).

## Troubleshooting

### Terraform plan fails: "backend initialization"

```
Error: error reading Azure credentials from environment or Azure CLI
```

**Solution:** Ensure Azure CLI is authenticated:

```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### Databricks CLI: "authentication failed"

```
Error: INVALID_PARAMETER_VALUE: unable to configure client: missing token
```

**Solution:** Ensure `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are set, then use the CLI from the uv `deploy` group:

```bash
export DATABRICKS_HOST="https://adb-1234567890.azuredatabricks.net"
export DATABRICKS_TOKEN="dapi1234567890abcdef"
uv run --only-group deploy databricks workspace ls /Shared/data-platform/notebooks
```

### `uv sync --frozen` fails in CI: "lockfile needs to be updated"

`pyproject.toml` was changed without regenerating the lock. Run `uv lock` locally and commit `uv.lock`.

### `uv lock` is slow the first time

`pyspark` 3.3.x is only published as a ~280 MB source distribution, which uv downloads to read its metadata. Later runs use the uv cache (`enable-cache: true` in the workflows).

### Tests fail with `NoSuchMethodException: java.nio.DirectByteBuffer.<init>(long,int)` or `getSubject is not supported`

PySpark 3.3 supports Java 8, 11 and 17 only. These errors mean a newer JDK is in use: the first appears on Java 21, the second on Java 23 and later. In CI, the jobs that run pytest on the runner pin Java 17 with `actions/setup-java`. Locally, point `JAVA_HOME` to a JDK 17:

```bash
export JAVA_HOME=/usr/lib/jvm/temurin-17-jdk-amd64 PATH=/usr/lib/jvm/temurin-17-jdk-amd64/bin:$PATH
uv run pytest -q
```

### Databricks job: "Notebook not found"

The `notebook_path` in the job JSON or ADF pipeline does not match the import path in `cd.yml`. See [Notebook paths](#notebook-paths).

### Data quality job fails

The run output of `dq/validate_data_quality` lists every failed expectation with `unexpected_count` and a sample of bad values. Either fix the source data, or adjust the suite in `great_expectations/expectations/` and redeploy (the CD uploads the suites to DBFS). See `docs/great_expectations_integration.md`.

### ADF deployment: "linked service already exists"

The workflow contains a catch-all `|| echo "Linked service may already exist"`. To force an update, use the `az datafactory linked-service update` command or delete the old one first.

## Next Steps

1. Customize `envs/staging.tfvars` and `envs/prod.tfvars` for production environments.
2. Add Log Analytics workspace to Terraform and configure diagnostic settings for monitoring.
3. Integrate with notification systems (Teams, Slack) to alert on deployment failures.
4. Add automated rollback or canary deployment strategies as your platform matures.
