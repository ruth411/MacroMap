"""SEC EDGAR API client with rate limiting."""

import asyncio
import time
import logging
from typing import Optional

import httpx

from app.core.config import settings
from .models import FilingMetadata, FilingType

logger = logging.getLogger(__name__)


class EdgarAPIError(Exception):
    """Base exception for EDGAR API errors."""
    pass


class RateLimitError(EdgarAPIError):
    """SEC rate limit exceeded."""
    pass


class FilingNotFoundError(EdgarAPIError):
    """Requested filing does not exist."""
    pass


class EdgarClient:
    """
    Async HTTP client for SEC EDGAR API with rate limiting.

    Handles:
    - CIK lookup from ticker symbols
    - Fetching company submissions metadata
    - Downloading raw filing documents
    - Automatic rate limiting (10 req/sec max)
    """

    SEC_BASE_URL = "https://data.sec.gov"
    SEC_SUBMISSIONS_URL = f"{SEC_BASE_URL}/submissions"
    SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    def __init__(self):
        self.user_agent = settings.sec_user_agent
        self.rate_limit = settings.sec_rate_limit  # Minimum seconds between requests
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()
        self._ticker_cache: dict[str, str] = {}  # ticker -> CIK cache

    def _get_headers(self) -> dict[str, str]:
        """Get headers required by SEC EDGAR."""
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

    async def _rate_limited_request(
        self,
        url: str,
        timeout: float = 30.0
    ) -> httpx.Response:
        """
        Make a rate-limited HTTP request.

        Ensures minimum delay between requests to comply with SEC rate limits.
        """
        async with self._lock:
            # Enforce rate limiting
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit:
                await asyncio.sleep(self.rate_limit - elapsed)

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    headers = self._get_headers()
                    response = await client.get(url, headers=headers)
                    self._last_request_time = time.time()

                    if response.status_code == 429:
                        raise RateLimitError("SEC rate limit exceeded")

                    return response
            except httpx.TimeoutException as e:
                raise EdgarAPIError(f"Request timeout: {url}") from e
            except httpx.HTTPError as e:
                raise EdgarAPIError(f"HTTP error: {e}") from e

    async def _request_with_retry(
        self,
        url: str,
        max_retries: int = 3
    ) -> httpx.Response:
        """Make a request with retry logic and exponential backoff."""
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                response = await self._rate_limited_request(url)
                response.raise_for_status()
                return response
            except RateLimitError:
                wait_time = 2 ** attempt
                logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
                last_error = RateLimitError("Rate limit exceeded after retries")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise FilingNotFoundError(f"Not found: {url}")
                last_error = EdgarAPIError(f"HTTP {e.response.status_code}: {url}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except EdgarAPIError as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

        raise last_error or EdgarAPIError("Request failed after retries")

    async def _load_ticker_map(self) -> None:
        """Load the SEC company tickers mapping."""
        if self._ticker_cache:
            return

        try:
            response = await self._request_with_retry(self.COMPANY_TICKERS_URL)
            data = response.json()

            # SEC returns dict with numeric keys
            for entry in data.values():
                ticker = entry.get("ticker", "").upper()
                cik = str(entry.get("cik_str", "")).zfill(10)
                if ticker and cik:
                    self._ticker_cache[ticker] = cik

            logger.info(f"Loaded {len(self._ticker_cache)} ticker mappings")
        except Exception as e:
            logger.error(f"Failed to load ticker map: {e}")
            raise EdgarAPIError("Failed to load SEC ticker mappings") from e

    async def get_cik(self, ticker: str) -> str:
        """
        Get CIK (Central Index Key) for a ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")

        Returns:
            10-digit CIK string (zero-padded)

        Raises:
            EdgarAPIError: If ticker not found
        """
        await self._load_ticker_map()

        ticker_upper = ticker.upper()
        if ticker_upper not in self._ticker_cache:
            raise EdgarAPIError(f"Ticker not found: {ticker}")

        return self._ticker_cache[ticker_upper]

    async def get_submissions(self, cik: str) -> dict:
        """
        Get company submissions (filing history) from SEC.

        Args:
            cik: 10-digit CIK (zero-padded)

        Returns:
            Dictionary with company info and filing history
        """
        url = f"{self.SEC_SUBMISSIONS_URL}/CIK{cik}.json"
        response = await self._request_with_retry(url)
        return response.json()

    async def get_company_filings(
        self,
        ticker: str,
        filing_types: list[str],
        years: int = 3,
    ) -> list[FilingMetadata]:
        """
        Get list of filings for a company.

        Args:
            ticker: Stock ticker symbol
            filing_types: List of filing types (e.g., ["10-K", "10-Q"])
            years: Number of years of filings to retrieve

        Returns:
            List of FilingMetadata objects
        """
        cik = await self.get_cik(ticker)
        submissions = await self.get_submissions(cik)

        company_name = submissions.get("name", ticker)
        recent_filings = submissions.get("filings", {}).get("recent", {})

        # Extract filing data arrays
        forms = recent_filings.get("form", [])
        filing_dates = recent_filings.get("filingDate", [])
        accession_numbers = recent_filings.get("accessionNumber", [])
        primary_documents = recent_filings.get("primaryDocument", [])

        # Filter by type and date
        from datetime import date, timedelta
        cutoff_date = date.today() - timedelta(days=years * 365)

        filings: list[FilingMetadata] = []
        normalized_types = [t.upper().replace(" ", "").replace("_", "-") for t in filing_types]

        for i, form in enumerate(forms):
            if form not in normalized_types:
                continue

            try:
                filing_date = date.fromisoformat(filing_dates[i])
                if filing_date < cutoff_date:
                    continue

                filings.append(FilingMetadata(
                    cik=cik,
                    ticker=ticker.upper(),
                    company_name=company_name,
                    filing_type=FilingType.from_string(form),
                    filing_date=filing_date,
                    accession_number=accession_numbers[i],
                    primary_document=primary_documents[i],
                ))
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping filing due to parse error: {e}")
                continue

        logger.info(f"Found {len(filings)} filings for {ticker}")
        return filings

    async def get_filing_document(self, filing: FilingMetadata) -> str:
        """
        Download the raw filing document.

        Args:
            filing: FilingMetadata object

        Returns:
            Raw HTML content of the filing
        """
        # Construct document URL
        # Format: https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}
        accession_no_dashes = filing.accession_number.replace("-", "")
        url = (
            f"{self.SEC_ARCHIVES_URL}/"
            f"{filing.cik.lstrip('0')}/"
            f"{accession_no_dashes}/"
            f"{filing.primary_document}"
        )

        logger.info(f"Downloading filing from: {url}")
        response = await self._request_with_retry(url)
        return response.text

    async def health_check(self) -> bool:
        """Check if SEC EDGAR API is accessible."""
        try:
            response = await self._rate_limited_request(
                f"{self.SEC_BASE_URL}/submissions/CIK0000320193.json"  # Apple's CIK
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"EDGAR health check failed: {e}")
            return False


# Singleton instance
_edgar_client: Optional[EdgarClient] = None


def get_edgar_client() -> EdgarClient:
    """Get singleton EdgarClient instance."""
    global _edgar_client
    if _edgar_client is None:
        _edgar_client = EdgarClient()
    return _edgar_client
