# Architecture

High level architecture for the data ingestion platform. Replace this with `docs/architecture.png` as needed.



                                 ┌────────────────────────────────────────┐
                                 │               Developers               │
                                 │    (push PRs, update pipelines, etc.)  │
                                 └────────────────────────────────────────┘
                                                  │
                                                  ▼
                               ┌──────────────────────────────────────────────┐
                               │               GitHub Actions                 │
                               │----------------------------------------------│
                               │ • CI: Lint, test, validate configs           │
                               │ • Data quality tests (Great Expectations)    │
                               │ • Schema validation                          │
                               │ • Build & push Databricks notebooks/artifacts│
                               │ • CD: deploy ADF pipelines (ARM/Bicep)       │
                               └──────────────────────────────────────────────┘
                                                  │
                                                  ▼
                      ┌────────────────────────────────────────────────────────────┐
                      │                    Azure Data Factory (ADF)                │
                      │------------------------------------------------------------│
                      │ Orchestration Layer:                                       │
                      │  • Scheduled triggers                                      │
                      │  • Pipeline orchestration                                  │
                      │  • Data movement (Copy Data)                               │
                      │  • Calls Databricks notebooks / Jobs API                   │
                      └────────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼
       ┌──────────────────────────────┬────────────────────────────────────────────────────┬──────────────────────────┐
       │                              │                                                    │                          │
       ▼                              ▼                                                    ▼                          ▼
┌───────────────┐            ┌──────────────────────────┐                       ┌──────────────────────┐    ┌────────────────────────┐
│ External APIs │            │   Raw Data Storage       │                       │   Semi-Structured    │    │   Structured DBs       │
│ (REST, SaaS)  │───────────▶│  ADLS Gen2 (Bronze)      │◀────────────────────▶ │   JSON / Parquet     │    │  Azure SQL / Synapse   │
└──────────────┘             └──────────────────────────┘                       └──────────────────────┘    └────────────────────────┘
                                           │
                                           ▼
                           ┌────────────────────────────────────────────────┐
                           │            Databricks (ETL/ELT)                │
                           │------------------------------------------------│
                           │ • Notebooks / Jobs                             │
                           │ • Delta Lake processing (Bronze→Silver→Gold)   │
                           │ • Integrates with MLflow if needed             │
                           │ • Reads/writes ADLS, Synapse, APIs             │
                           └────────────────────────────────────────────────┘
                                           │
                                           ▼
                        ┌──────────────────────────────────────────────┐
                        │   Data Quality & Validation Layer            │
                        │----------------------------------------------│
                        │ • Great Expectations (Databricks integration)│
                        │ • Delta Live Tables expectations             │
                        │ • Schema validation (Pydantic/Custom checks) │
                        └──────────────────────────────────────────────┘
                                           │
                                           ▼
                    ┌────────────────────────────┬────────────────────────────┐
                    ▼                            ▼                            ▼

           ┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
           │ Curated Storage (Gold) │   │   Analytics / BI       │   │ Monitoring & Logs      │
           │   Delta Lake           │   │   Power BI / Synapse   │   │   Azure Monitor/Log    │
           └────────────────────────┘   └────────────────────────┘   │   Analytics            │
                                                                     └────────────────────────┘
