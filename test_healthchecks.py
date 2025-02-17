import httpx
import asyncio
import sys

async def check_health(url: str, name: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            print(f"{name}: {response.status_code} - {response.text[:100]}")
            return response.status_code == 200
    except Exception as e:
        print(f"{name} error: {str(e)}")
        return False

async def main():
    services = {
        "QuestDB": "http://localhost:9003/health",
        "ClickHouse": "http://localhost:8123/ping",
        "NATS": "http://localhost:8222/healthz",
        "Materialize": "http://localhost:6875/status"
    }
    
    results = await asyncio.gather(*[
        check_health(url, name) for name, url in services.items()
    ])
    
    all_healthy = all(results)
    print(f"\nAll services healthy: {all_healthy}")
    sys.exit(0 if all_healthy else 1)

if __name__ == "__main__":
    asyncio.run(main()) 