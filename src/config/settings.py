import os

ENV = os.getenv('ENV', 'dev')

# Storage and service endpoints (override via env or Key Vault)
STORAGE_ACCOUNT = os.getenv('STORAGE_ACCOUNT', 'mydatalakestorage')
