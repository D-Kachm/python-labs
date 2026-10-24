import asyncio
from typing import Any
import httpx

async def fetch_single_resource_with_retry(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
    attempts: int = 3,
    timeout: float = 5.0,
    backoff_seconds: float = 0.1,
) -> dict[str, Any] | None:
    async with semaphore:
        for attempt in range(1, attempts + 1):
            try:
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
                return {"data": payload}
            except (httpx.RequestError, httpx.HTTPStatusError):
                if attempt == attempts:
                    return None
                await asyncio.sleep(backoff_seconds * attempt)
        return None

async def fetch_resources_concurrently(
    urls: list[str],
    max_concurrency: int = 5,
    timeout: float = 10.0,
    attempts: int = 3,
    custom_client: httpx.AsyncClient | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_tasks(client: httpx.AsyncClient) -> tuple[list[dict[str, Any]], list[str]]:
        tasks = [
            asyncio.create_task(
                fetch_single_resource_with_retry(
                    client=client,
                    url=url,
                    semaphore=semaphore,
                    attempts=attempts,
                    timeout=timeout,
                )
            )
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful: list[dict[str, Any]] = []
        failed_urls: list[str] = []
        for url, result in zip(urls, results, strict=True):
            if isinstance(result, dict):
                successful.append(result)
            else:
                failed_urls.append(url)
        return successful, failed_urls

    if custom_client is not None:
        return await asyncio.wait_for(execute_tasks(custom_client), timeout=timeout)

    async with httpx.AsyncClient() as client:
        return await asyncio.wait_for(execute_tasks(client), timeout=timeout)
