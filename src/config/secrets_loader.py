import os

# Placeholder secrets loader: use Azure Key Vault or GitHub OIDC in production

def get_secret(name: str) -> str:
    return os.getenv(name, '')
