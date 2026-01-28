#!/usr/bin/env python3
"""
S&P 500 Ingestion Script for MacroMap

Ingests SEC filings (10-K, 10-Q) for all S&P 500 companies.
Supports resumption if interrupted.

Usage:
    python scripts/ingest_sp500.py [--years 3] [--workers 5] [--resume]
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.edgar.service import EdgarService
from app.services.retrieval.service import RetrievalService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# S&P 500 Companies (as of 2024)
SP500_TICKERS = [
    # Technology
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "CSCO", "ACN", "ADBE", "IBM",
    "INTC", "AMD", "QCOM", "TXN", "AMAT", "NOW", "INTU", "ADI", "LRCX", "MU",
    "KLAC", "SNPS", "CDNS", "MCHP", "APH", "MSI", "TEL", "FTNT", "KEYS", "ON",
    "NXPI", "MPWR", "FSLR", "TDY", "ZBRA", "TRMB", "TER", "SWKS", "JNPR", "FFIV",
    "QRVO", "AKAM", "NTAP", "WDC", "STX", "GEN", "ENPH", "SEDG", "CTSH", "HPQ",
    "HPE", "EPAM", "IT", "GDDY", "PAYC", "ANSS", "PTC", "VRSN", "CDW", "FICO",

    # Communication Services
    "GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "EA",
    "TTWO", "WBD", "PARA", "OMC", "IPG", "LYV", "MTCH", "NWSA", "NWS", "FOXA",
    "FOX", "DISH",

    # Consumer Discretionary
    "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "ORLY",
    "MAR", "AZO", "CMG", "DHI", "HLT", "YUM", "ROST", "LEN", "GM", "F",
    "EBAY", "APTV", "PHM", "GRMN", "DRI", "POOL", "BBY", "ULTA", "MGM", "WYNN",
    "CZR", "RCL", "CCL", "NCLH", "LVS", "BWA", "EXPE", "NVR", "TSCO", "KMX",
    "GPC", "DPZ", "ETSY", "TPR", "HAS", "WHR", "MHK", "VFC", "PVH", "RL",

    # Consumer Staples
    "WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "MDLZ", "CL", "EL",
    "KMB", "GIS", "KDP", "STZ", "SYY", "HSY", "KHC", "ADM", "MKC", "K",
    "TSN", "CAG", "HRL", "CPB", "SJM", "CLX", "CHD", "TAP", "BG", "LW",
    "KR", "WBA", "TGT", "DG", "DLTR",

    # Healthcare
    "LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "ABT", "PFE", "DHR", "BMY",
    "AMGN", "ISRG", "ELV", "GILD", "VRTX", "MDT", "CI", "CVS", "REGN", "SYK",
    "BSX", "ZTS", "BDX", "MCK", "HUM", "HCA", "GEHC", "EW", "IDXX", "IQV",
    "DXCM", "A", "RMD", "MTD", "WAT", "COO", "HOLX", "ALGN", "PODD", "WST",
    "TECH", "MOH", "CNC", "BAX", "ZBH", "CAH", "VTRS", "HSIC", "DGX", "LH",
    "BIIB", "ILMN", "INCY", "MRNA", "RVTY", "CRL", "PKI", "TFX", "BIO", "XRAY",

    # Financials
    "BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK",
    "C", "AXP", "SCHW", "PGR", "CB", "MMC", "CME", "ICE", "AON", "USB",
    "PNC", "TFC", "AJG", "MET", "AIG", "AFL", "PRU", "TRV", "ALL", "ACGL",
    "MCO", "MSCI", "FIS", "AMP", "COF", "BK", "TROW", "STT", "NDAQ", "FITB",
    "FRC", "SIVB", "HBAN", "RF", "CFG", "MTB", "KEY", "NTRS", "DFS", "SYF",
    "WRB", "RJF", "CBOE", "CINF", "L", "AIZ", "GL", "BEN", "IVZ", "MKTX",

    # Industrials
    "CAT", "GE", "RTX", "HON", "UNP", "BA", "UPS", "DE", "LMT", "ADP",
    "ETN", "WM", "ITW", "EMR", "GD", "NOC", "FDX", "CSX", "NSC", "PH",
    "CTAS", "TT", "PCAR", "CPRT", "CARR", "AME", "FAST", "ODFL", "JCI", "RSG",
    "CMI", "OTIS", "ROK", "GWW", "VRSK", "IR", "DOV", "XYL", "HWM", "PWR",
    "WAB", "LHX", "TDG", "LDOS", "FTV", "DAL", "UAL", "LUV", "AAL", "ALK",
    "J", "EXPD", "JBHT", "CHRW", "NDSN", "SNA", "PNR", "AOS", "IEX", "RHI",

    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "PXD", "OXY",
    "WMB", "KMI", "HES", "HAL", "DVN", "FANG", "BKR", "CTRA", "OKE", "TRGP",
    "MRO", "APA",

    # Materials
    "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "DOW", "DD", "PPG",
    "VMC", "MLM", "CTVA", "ALB", "FMC", "CE", "EMN", "IFF", "LYB", "BALL",
    "AVY", "PKG", "IP", "CF", "MOS", "AMCR", "SEE", "WRK",

    # Utilities
    "NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PCG", "EXC", "XEL",
    "ED", "EIX", "WEC", "AWK", "DTE", "ES", "PPL", "ETR", "FE", "AEE",
    "CMS", "CNP", "EVRG", "ATO", "NI", "PNW", "NRG", "LNT", "AES", "PEG",

    # Real Estate
    "PLD", "AMT", "EQIX", "CCI", "PSA", "O", "SPG", "WELL", "DLR", "VICI",
    "AVB", "EQR", "SBAC", "WY", "ARE", "VTR", "MAA", "EXR", "CBRE", "IRM",
    "UDR", "ESS", "INVH", "HST", "CPT", "KIM", "REG", "BXP", "FRT", "VNO",
    "AIV", "PEAK", "DOC",
]

# Progress tracking file
PROGRESS_FILE = Path("data/ingestion_progress.json")


def load_progress() -> dict:
    """Load ingestion progress from file."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"completed": [], "failed": [], "started_at": None}


def save_progress(progress: dict) -> None:
    """Save ingestion progress to file."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


async def ingest_company(
    ticker: str,
    edgar_service: EdgarService,
    retrieval_service: RetrievalService,
    years: int = 3,
    filing_types: list[str] = None,
) -> tuple[bool, str]:
    """
    Ingest a single company's filings.

    Returns:
        Tuple of (success: bool, message: str)
    """
    if filing_types is None:
        filing_types = ["10-K", "10-Q"]

    try:
        logger.info(f"Ingesting {ticker}...")

        # Fetch and parse filings
        parsed_filings, chunks = await edgar_service.ingest_company(
            ticker=ticker,
            filing_types=filing_types,
            years=years,
        )

        if not chunks:
            return True, f"{ticker}: No chunks generated (may have no filings)"

        # Index chunks into vector store
        count = await retrieval_service.index_chunks(chunks)

        return True, f"{ticker}: Indexed {count} chunks from {len(parsed_filings)} filings"

    except Exception as e:
        error_msg = f"{ticker}: Error - {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def run_ingestion(
    tickers: list[str],
    years: int = 3,
    max_workers: int = 3,
    resume: bool = True,
) -> None:
    """
    Run ingestion for multiple companies.

    Args:
        tickers: List of ticker symbols
        years: Number of years of filings to fetch
        max_workers: Number of concurrent workers (be nice to SEC API)
        resume: Whether to skip already completed tickers
    """
    # Load progress
    progress = load_progress() if resume else {"completed": [], "failed": [], "started_at": None}

    if not progress["started_at"]:
        progress["started_at"] = datetime.now().isoformat()

    # Filter out already completed tickers
    if resume:
        remaining = [t for t in tickers if t not in progress["completed"]]
        logger.info(f"Resuming: {len(progress['completed'])} done, {len(remaining)} remaining")
    else:
        remaining = tickers
        # Clear old data
        logger.info("Starting fresh ingestion...")

    if not remaining:
        logger.info("All tickers already completed!")
        return

    # Initialize services
    edgar_service = EdgarService()
    retrieval_service = RetrievalService()

    # Process in batches to control concurrency
    semaphore = asyncio.Semaphore(max_workers)

    async def process_with_semaphore(ticker: str) -> tuple[str, bool, str]:
        async with semaphore:
            # Add delay to be nice to SEC API (10 req/sec limit)
            await asyncio.sleep(0.5)
            success, message = await ingest_company(
                ticker=ticker,
                edgar_service=edgar_service,
                retrieval_service=retrieval_service,
                years=years,
            )
            return ticker, success, message

    # Process all tickers
    total = len(remaining)
    completed_count = len(progress["completed"])

    for i, ticker in enumerate(remaining):
        ticker, success, message = await process_with_semaphore(ticker)

        if success:
            progress["completed"].append(ticker)
            logger.info(f"[{completed_count + i + 1}/{completed_count + total}] {message}")
        else:
            progress["failed"].append({"ticker": ticker, "error": message})
            logger.error(f"[{completed_count + i + 1}/{completed_count + total}] {message}")

        # Save progress after each company
        save_progress(progress)

    # Final summary
    progress["completed_at"] = datetime.now().isoformat()
    save_progress(progress)

    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"  Successful: {len(progress['completed'])}")
    logger.info(f"  Failed: {len(progress['failed'])}")
    if progress["failed"]:
        logger.info("  Failed tickers:")
        for f in progress["failed"]:
            logger.info(f"    - {f['ticker']}: {f['error']}")


async def clear_index() -> None:
    """Clear the existing vector store index."""
    logger.info("Clearing existing vector store...")

    chroma_dir = settings.chroma_dir
    if chroma_dir.exists():
        import shutil
        shutil.rmtree(chroma_dir)
        logger.info(f"Deleted {chroma_dir}")

    chroma_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Vector store cleared")


def main():
    parser = argparse.ArgumentParser(description="Ingest S&P 500 SEC filings")
    parser.add_argument(
        "--years", type=int, default=3,
        help="Number of years of filings to fetch (default: 3)"
    )
    parser.add_argument(
        "--workers", type=int, default=3,
        help="Number of concurrent workers (default: 3, max recommended: 5)"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from previous progress"
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear existing index before starting"
    )
    parser.add_argument(
        "--tickers", type=str, nargs="+",
        help="Specific tickers to ingest (default: all S&P 500)"
    )
    parser.add_argument(
        "--limit", type=int,
        help="Limit number of companies to ingest (for testing)"
    )

    args = parser.parse_args()

    # Select tickers
    tickers = args.tickers if args.tickers else SP500_TICKERS
    if args.limit:
        tickers = tickers[:args.limit]

    logger.info(f"MacroMap S&P 500 Ingestion")
    logger.info(f"  Tickers: {len(tickers)}")
    logger.info(f"  Years: {args.years}")
    logger.info(f"  Workers: {args.workers}")
    logger.info(f"  Resume: {args.resume}")

    # Clear index if requested
    if args.clear:
        asyncio.run(clear_index())

    # Run ingestion
    asyncio.run(run_ingestion(
        tickers=tickers,
        years=args.years,
        max_workers=args.workers,
        resume=args.resume,
    ))


if __name__ == "__main__":
    main()
