"""Query expansion for improved RAG retrieval."""

import logging
from typing import Optional

from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Expands user queries with related financial terms for better retrieval.

    Uses LLM to generate semantically related terms that might appear
    in SEC filings but not in the user's original query.
    """

    EXPANSION_PROMPT = """You are a financial search query expander. Given a user's question about SEC filings or financial data, generate 3-5 related search terms that would help find relevant information in 10-K and 10-Q filings.

Focus on:
- Synonyms and related financial terms
- SEC filing section names (e.g., "Risk Factors", "MD&A", "Business")
- Specific financial metrics mentioned implicitly
- Industry-standard terminology

User Question: {query}

Return ONLY the expanded terms, separated by commas. No explanations."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = "gpt-4o-mini"  # Fast and cheap for expansion

    async def expand(self, query: str) -> str:
        """
        Expand a query with related terms.

        Args:
            query: Original user query

        Returns:
            Expanded query string combining original + related terms
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": self.EXPANSION_PROMPT.format(query=query)}
                ],
                max_tokens=100,
                temperature=0.3,
            )

            expansion = response.choices[0].message.content.strip()
            expanded_query = f"{query} {expansion}"

            logger.debug(f"Query expanded: '{query}' -> '{expanded_query}'")
            return expanded_query

        except Exception as e:
            logger.warning(f"Query expansion failed: {e}. Using original query.")
            return query

    async def expand_with_hyde(self, query: str) -> str:
        """
        Hypothetical Document Embeddings (HyDE) expansion.

        Generates a hypothetical answer that would appear in a relevant document,
        then uses that for retrieval instead of the query.

        Args:
            query: Original user query

        Returns:
            Hypothetical document text for embedding
        """
        hyde_prompt = f"""You are a financial analyst writing a section of an SEC 10-K filing.
Write a brief paragraph (2-3 sentences) that would directly answer this question:

Question: {query}

Write as if you are the actual text from an SEC filing. Be factual and use formal financial language."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": hyde_prompt}
                ],
                max_tokens=150,
                temperature=0.5,
            )

            hypothetical_doc = response.choices[0].message.content.strip()
            logger.debug(f"HyDE generated for: '{query}'")
            return hypothetical_doc

        except Exception as e:
            logger.warning(f"HyDE generation failed: {e}. Using original query.")
            return query


# Singleton instance
_query_expander: Optional[QueryExpander] = None


def get_query_expander() -> QueryExpander:
    """Get singleton query expander."""
    global _query_expander
    if _query_expander is None:
        _query_expander = QueryExpander()
    return _query_expander
