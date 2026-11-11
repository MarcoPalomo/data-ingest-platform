import pyodbc


def ingest_sql(conn_str: str, query: str):
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        for row in cursor.fetchall():
            yield dict(zip(cols, row))
