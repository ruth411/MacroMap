"""
Script to index SEC filings on production Railway deployment.
Run this after deploying to populate the vector store with filing data.
"""

import httpx
import asyncio
import time

PRODUCTION_URL = "https://macromap-production.up.railway.app"

# Top 10 S&P 500 companies
COMPANIES = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "NVDA",   # NVIDIA
    "AMZN",   # Amazon
    "GOOGL",  # Alphabet
    "META",   # Meta
    "TSLA",   # Tesla
    "AVGO",   # Broadcom
    "JPM",    # JPMorgan
    "LLY",    # Eli Lilly
]


async def ingest_company(client: httpx.AsyncClient, ticker: str) -> dict:
    """Ingest a company's 10-K filing and wait for completion."""
    print(f"\n{'='*50}")
    print(f"Ingesting {ticker}...")

    try:
        # Start ingestion
        response = await client.post(
            f"{PRODUCTION_URL}/api/v1/edgar/ingest",
            json={
                "ticker": ticker,
                "filing_types": ["10-K"],
                "years": 1
            },
            timeout=60.0
        )

        if response.status_code != 200:
            print(f"  ERROR: {response.status_code} - {response.text[:200]}")
            return {"ticker": ticker, "success": False, "error": response.text}

        result = response.json()
        task_id = result.get("task_id")
        print(f"  Task ID: {task_id}")

        # Poll for completion
        max_wait = 120  # 2 minutes max
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(3)
            waited += 3

            status_response = await client.get(
                f"{PRODUCTION_URL}/api/v1/edgar/status/{task_id}",
                timeout=30.0
            )

            if status_response.status_code == 200:
                status = status_response.json()
                current_status = status.get("status")

                if current_status == "completed":
                    print(f"  Completed!")
                    print(f"  Filings: {status.get('filings_processed', 0)}")
                    print(f"  Chunks: {status.get('chunks_created', 0)}")
                    return {"ticker": ticker, "success": True, "result": status}
                elif current_status == "failed":
                    print(f"  Failed: {status.get('errors', [])}")
                    return {"ticker": ticker, "success": False, "error": status.get('errors')}
                else:
                    print(f"  Status: {current_status} (waiting...)")

        print(f"  Timeout waiting for completion")
        return {"ticker": ticker, "success": False, "error": "Timeout"}

    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return {"ticker": ticker, "success": False, "error": str(e)}


async def index_to_vector_store(client: httpx.AsyncClient, ticker: str) -> dict:
    """Index a company's chunks to the vector store for RAG."""
    print(f"  Indexing {ticker} to vector store...")

    try:
        response = await client.post(
            f"{PRODUCTION_URL}/api/v1/retrieval/index",
            json={"ticker": ticker},
            timeout=300.0
        )

        if response.status_code == 200:
            result = response.json()
            print(f"  Indexed {result.get('chunks_indexed', 0)} chunks")
            return {"ticker": ticker, "success": True, "result": result}
        else:
            print(f"  Index ERROR: {response.status_code}")
            return {"ticker": ticker, "success": False, "error": response.text}

    except Exception as e:
        print(f"  Index ERROR: {str(e)}")
        return {"ticker": ticker, "success": False, "error": str(e)}


async def check_health(client: httpx.AsyncClient) -> bool:
    """Check if the production server is healthy."""
    try:
        response = await client.get(f"{PRODUCTION_URL}/health", timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            print(f"Server Status: {data.get('status')}")
            print(f"LLM Provider: {data.get('llm_provider')}")
            return True
        return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


async def get_stats(client: httpx.AsyncClient):
    """Get current vector store stats."""
    try:
        response = await client.get(
            f"{PRODUCTION_URL}/api/v1/retrieval/stats",
            timeout=30.0
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"\nVector Store Stats:")
            print(f"  Total chunks: {stats.get('total_chunks', 0)}")
            print(f"  Tickers: {stats.get('tickers', [])}")
    except Exception as e:
        print(f"Could not get stats: {e}")


async def main():
    print("="*60)
    print("MacroMap Production Indexing Script")
    print("="*60)

    async with httpx.AsyncClient() as client:
        # Check health first
        print("\nChecking server health...")
        if not await check_health(client):
            print("Server is not healthy. Aborting.")
            return

        # Get initial stats
        await get_stats(client)

        # Process each company
        results = []
        start_time = time.time()

        for i, ticker in enumerate(COMPANIES, 1):
            print(f"\n[{i}/{len(COMPANIES)}] Processing {ticker}")

            # Step 1: Ingest from SEC EDGAR
            ingest_result = await ingest_company(client, ticker)

            if ingest_result["success"]:
                # Step 2: Index to vector store for RAG
                index_result = await index_to_vector_store(client, ticker)
                results.append({
                    "ticker": ticker,
                    "ingest": ingest_result,
                    "index": index_result
                })
            else:
                results.append({
                    "ticker": ticker,
                    "ingest": ingest_result,
                    "index": None
                })

            # Small delay between companies
            if i < len(COMPANIES):
                await asyncio.sleep(2)

        # Summary
        elapsed = time.time() - start_time
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)

        successful = sum(1 for r in results if r["ingest"]["success"])
        print(f"Successfully processed: {successful}/{len(COMPANIES)} companies")
        print(f"Total time: {elapsed:.1f} seconds")

        # Final stats
        await get_stats(client)

        # List any failures
        failures = [r for r in results if not r["ingest"]["success"]]
        if failures:
            print("\nFailed companies:")
            for f in failures:
                print(f"  - {f['ticker']}: {f['ingest'].get('error', 'Unknown error')[:100]}")


if __name__ == "__main__":
    asyncio.run(main())
