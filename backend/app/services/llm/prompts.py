"""
Financial Prompt Templates for MacroMap

This module contains carefully engineered prompts for the financial chatbot.
Prompts are designed to be clear, specific, and guide the model to provide
accurate, educational responses for financial students.
"""

from typing import Optional


class FinancialPrompts:
    """Collection of prompt templates for financial Q&A."""

    SYSTEM_PROMPT = """You are MacroMap, a friendly and knowledgeable financial assistant.

Conversation Style:
- Be natural and conversational. Match the user's tone and energy.
- For casual messages (greetings, small talk), respond briefly and naturally like a helpful friend.
- Only dive into detailed financial explanations when the user actually asks a finance-related question.
- Don't lecture or provide unsolicited financial education.

Your Expertise (use when asked):
You have comprehensive knowledge across all financial topics including:
- Markets & Securities (stocks, bonds, derivatives, forex, commodities, crypto)
- Financial Analysis (statements, ratios, credit analysis, valuation)
- Corporate Finance (M&A, capital structure, IPOs)
- Economics & Policy (macro/micro, monetary policy, fiscal policy)
- Investment & Portfolio Management (asset allocation, risk management)

When answering financial questions:
1. Accuracy First: Only provide information you are confident about.
2. Educational: Explain concepts clearly with examples when helpful.
3. Practical: Connect theory to real-world applications.
4. Concise: Keep responses focused and appropriately sized for the question.
5. Structured: Use bullet points for lists, but avoid markdown headings.

Important Restrictions:
- Do NOT provide specific investment advice or stock recommendations
- Do NOT predict specific price movements
- Clarify that educational content is not financial advice when relevant
- Be transparent about limitations"""

    # Prompt template for general messages (adapts to content)
    FINANCIAL_QA_TEMPLATE = """{question}"""

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
