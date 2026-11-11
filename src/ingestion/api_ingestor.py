import requests


def ingest_api(url: str, params: dict = None) -> dict:
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()
