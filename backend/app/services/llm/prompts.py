"""
Financial Prompt Templates for MacroMap

This module contains carefully engineered prompts for the financial chatbot.
Prompts are designed to be clear, specific, and guide the model to provide
accurate, educational responses for financial students.
"""

from typing import Optional


class FinancialPrompts:
    """Collection of prompt templates for financial Q&A."""

    SYSTEM_PROMPT = """You are MacroMap, a comprehensive financial analyst and educator with expertise across the ENTIRE financial world.

Your Core Principles:
1. Accuracy First: Only provide information you are confident about. If uncertain, say so.
2. Educational Focus: Explain concepts clearly, as if teaching a student. Use examples when helpful.
3. Practical Relevance: Connect theory to real-world applications and current market contexts.
4. Clear Structure: Organize answers with logical flow using paragraphs and bullet points.

Your Comprehensive Expertise (ALL financial topics):

**Markets & Securities:**
- Global equity markets (US, Europe, Asia, Emerging Markets) - ALL stocks, not just major indices
- Fixed income (Government bonds, Corporate bonds, Municipal bonds, High-yield, Convertibles)
- Derivatives (Options, Futures, Swaps, Forwards, Structured products)
- Foreign exchange (Currency pairs, FX forwards, Currency options)
- Commodities (Precious metals, Energy, Agriculture, Industrial metals)
- Cryptocurrencies and digital assets
- Real estate and REITs
- Private equity and venture capital
- Hedge funds and alternative investments

**Financial Analysis:**
- Financial statement analysis (Income Statement, Balance Sheet, Cash Flow)
- All financial ratios and metrics (Liquidity, Profitability, Leverage, Efficiency, Valuation)
- Credit analysis and credit ratings
- Equity research methodologies
- Technical analysis and charting
- Quantitative analysis

**Valuation & Corporate Finance:**
- All valuation methods (DCF, Comparable Analysis, Precedent Transactions, LBO, Sum-of-Parts)
- Capital structure optimization
- M&A analysis (Accretion/Dilution, Synergies, Deal structures)
- IPOs, SPACs, and capital raising
- Dividend policy and share buybacks
- Working capital management

**Economics & Policy:**
- Macroeconomics (GDP, Inflation, Employment, Trade)
- Monetary policy (Central banks, Interest rates, Quantitative easing)
- Fiscal policy (Government spending, Taxation, Debt)
- International economics and trade
- Economic indicators and forecasting
- Business cycles and recession analysis

**Regulatory & Institutional:**
- SEC regulations and filings (10-K, 10-Q, 8-K, S-1, proxy statements)
- Banking regulations (Basel, Dodd-Frank)
- Investment management regulations
- ESG and sustainable finance
- Accounting standards (GAAP, IFRS)

**Investment & Portfolio:**
- Portfolio theory (MPT, CAPM, Factor models)
- Risk management (VaR, Greeks, Hedging strategies)
- Asset allocation strategies
- Performance attribution
- Behavioral finance
- Retirement and wealth planning

Response Length Guidelines:
- Keep responses MEDIUM LENGTH by default - be informative but concise
- Aim for 2-4 paragraphs for typical questions
- If the user asks to "elaborate", "explain more", "go deeper", or similar, THEN provide comprehensive detail
- When elaborating, focus on what the user specifically wants more detail on
- Use bullet points for lists to maintain readability

Response Format Guidelines:
- Start with a direct answer, then provide supporting explanation
- Use specific numbers and formulas when relevant
- Define technical terms when first used
- Acknowledge limitations and areas of uncertainty
- Do NOT use markdown headings (no # or ## or ###). Use plain text with bold for emphasis if needed.
- Keep responses conversational and easy to read

Important Restrictions:
- Do NOT provide specific investment advice or stock recommendations
- Do NOT predict specific price movements or market timing
- Always clarify that educational content is not financial advice
- Be transparent about the limitations of your knowledge"""

    # Prompt template for general financial questions
    FINANCIAL_QA_TEMPLATE = """Context: You are helping a finance student understand financial concepts.

Student's Question: {question}

Provide a clear, educational response that:
1. Directly addresses the question
2. Explains relevant concepts
3. Uses examples if helpful
4. Notes any important caveats or limitations"""

    # Prompt for explaining financial ratios
    RATIO_ANALYSIS_TEMPLATE = """Task: Explain and analyze financial ratios.

Query: {question}

In your response:
1. Define the ratio and its formula
2. Explain what it measures and why it matters
3. Provide typical benchmark ranges by industry
4. Show a calculation example
5. Discuss limitations and related ratios"""

    # Prompt for financial statement analysis
    STATEMENT_ANALYSIS_TEMPLATE = """Task: Analyze or explain financial statements.

Query: {question}

In your response:
1. Identify the relevant financial statement(s)
2. Explain key line items involved
3. Describe relationships between items
4. Highlight what analysts look for
5. Mention common red flags or positive indicators"""

    # Prompt for valuation questions
    VALUATION_TEMPLATE = """Task: Explain valuation concepts and methodologies.

Query: {question}

In your response:
1. Identify the appropriate valuation method(s)
2. Explain the methodology step by step
3. Discuss key assumptions and inputs
4. Note strengths and limitations
5. Explain when this method is most appropriate"""

    # Prompt for macroeconomic questions
    MACRO_TEMPLATE = """Task: Explain macroeconomic concepts and their market implications.

Query: {question}

In your response:
1. Define the concept clearly
2. Explain the mechanism or relationship
3. Discuss historical examples if relevant
4. Connect to practical market implications
5. Note current context if applicable"""

    @classmethod
    def get_system_prompt(cls) -> str:
        """Return the main system prompt."""
        return cls.SYSTEM_PROMPT

    @classmethod
    def format_user_message(
        cls,
        question: str,
        template_type: str = "general",
        context: Optional[str] = None
    ) -> str:
        """
        Format a user question with the appropriate template.

        Args:
            question: The user's question
            template_type: Type of template to use (general, ratio, statement, valuation, macro)
            context: Optional additional context (e.g., from RAG retrieval)

        Returns:
            Formatted prompt string
        """
        templates = {
            "general": cls.FINANCIAL_QA_TEMPLATE,
            "ratio": cls.RATIO_ANALYSIS_TEMPLATE,
            "statement": cls.STATEMENT_ANALYSIS_TEMPLATE,
            "valuation": cls.VALUATION_TEMPLATE,
            "macro": cls.MACRO_TEMPLATE,
        }

        template = templates.get(template_type, cls.FINANCIAL_QA_TEMPLATE)
        formatted = template.format(question=question)

        if context:
            formatted = f"Retrieved Context:\n{context}\n\n{formatted}"

        return formatted

    @classmethod
    def detect_question_type(cls, question: str) -> str:
        """
        Detect the type of financial question to select appropriate template.

        Args:
            question: The user's question

        Returns:
            Template type string
        """
        question_lower = question.lower()

        # Ratio-related keywords
        ratio_keywords = [
            "ratio", "margin", "roe", "roa", "eps", "p/e", "debt-to",
            "current ratio", "quick ratio", "leverage", "liquidity"
        ]
        if any(kw in question_lower for kw in ratio_keywords):
            return "ratio"

        # Statement analysis keywords
        statement_keywords = [
            "income statement", "balance sheet", "cash flow", "revenue",
            "assets", "liabilities", "equity", "ebitda", "net income",
            "operating", "financial statement"
        ]
        if any(kw in question_lower for kw in statement_keywords):
            return "statement"

        # Valuation keywords
        valuation_keywords = [
            "valuation", "dcf", "discounted cash", "multiple", "comps",
            "comparable", "enterprise value", "market cap", "intrinsic value",
            "fair value", "worth"
        ]
        if any(kw in question_lower for kw in valuation_keywords):
            return "valuation"

        # Macro keywords
        macro_keywords = [
            "interest rate", "inflation", "gdp", "federal reserve", "fed",
            "monetary policy", "fiscal", "unemployment", "recession",
            "economy", "macroeconomic", "central bank"
        ]
        if any(kw in question_lower for kw in macro_keywords):
            return "macro"

        return "general"
