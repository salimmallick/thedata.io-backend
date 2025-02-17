import asyncio
import httpx
import time
import sys
import psycopg2
import redis

CLICKHOUSE_URL = "http://clickhouse-test:8123/ping"
QUESTDB_URL = "http://questdb-test:9000"
MATERIALIZE_URL = "http://materialize-test:6875/status"
NATS_URL = "http://nats-test:8222/healthz"

async def check_services():
    services = {
        'ClickHouse': CLICKHOUSE_URL,
        'QuestDB': QUESTDB_URL,
        'Materialize': MATERIALIZE_URL,
        'NATS': NATS_URL
    }
    
    for name, url in services.items():
        print(f'Checking {name}...')
        for attempt in range(60):
            try:
                print(f'Attempt {attempt + 1} for {name} at {url}')
                async with httpx.AsyncClient() as client:
                    print(f'Making request to {url}...')
                    r = await client.get(url)
                    print(f'Got response from {name}: status={r.status_code}, content={r.text}')
                    if r.status_code == 200:
                        print(f'{name} is ready')
                        break
            except Exception as e:
                print(f'Attempt {attempt + 1} failed for {name}: {str(e)}')
                print(f'Error type: {type(e).__name__}')
                await asyncio.sleep(1)
        else:
            print(f'{name} failed to start after 60 attempts')
            sys.exit(1)
    
    # Check PostgreSQL
    for _ in range(60):
        try:
            conn = psycopg2.connect(
                dbname='testdb',
                user='test',
                password='test',
                host='postgres-test',
                port=5432
            )
            conn.close()
            print('PostgreSQL is ready')
            break
        except Exception as e:
            print(f'Waiting for PostgreSQL: {str(e)}')
            time.sleep(1)
    else:
        print('PostgreSQL failed to start')
        sys.exit(1)
    
    # Check Redis
    for _ in range(60):
        try:
            redis_client = redis.Redis(
                host='redis-test',
                port=6379
            )
            redis_client.ping()
            print('Redis is ready')
            break
        except Exception as e:
            print(f'Waiting for Redis: {str(e)}')
            time.sleep(1)
    else:
        print('Redis failed to start')
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(check_services()) 