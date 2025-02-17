from setuptools import setup, find_packages

setup(
    name="thedata-dagster",
    version="0.1.0",
    description="theData.io Dagster pipelines",
    author="theData.io",
    packages=find_packages(),
    install_requires=[
        "dagster",
        "dagster-postgres",
        "clickhouse-connect",
        "psycopg2-binary",
        "questdb",
        "nats-py",
    ],
) 