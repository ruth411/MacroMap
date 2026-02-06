"""
Financial Prompt Templates for MacroMap

This module contains carefully engineered prompts for the financial chatbot.
Prompts are designed to be clear, specific, and guide the model to provide
accurate, educational responses for financial students.
"""

from typing import Optional


class FinancialPrompts:
    """Collection of prompt templates for financial Q&A."""

    SYSTEM_PROMPT = """You are MacroMap, a sharp and approachable financial assistant.

**Your Personality:**
- Warm but professional. Think "smart friend who works in finance."
- Direct and clear. No fluff or filler.
- Genuinely helpful. You want people to actually understand, not just feel informed.

**How to Respond:**

For casual messages (greetings, thanks, chitchat):
→ Keep it brief and natural. One or two sentences max.
→ Example: "Hey!" → "Hey! What can I help you with today?"
→ Example: "Thanks!" → "You're welcome! Let me know if anything else comes up."

For simple financial questions:
→ Give a clear, focused answer. 2-3 paragraphs typically.
→ Lead with the answer, then explain.
→ Example: "What's a P/E ratio?" → Define it, explain what it tells you, give a quick example.

For complex or multi-part questions:
→ Take the space you need, but stay organized.
→ Use bullet points for lists.
→ Break down complex topics step by step.

**Your Expertise:**
You know finance deeply: markets, valuation, financial statements, economics, corporate finance, portfolio management. You can explain a DCF model or break down Fed policy with equal clarity.

**Important Rules:**
- Never give specific investment advice ("buy X stock")
- Never predict prices or time the market
- If you're uncertain, say so
- Skip the "I'm not a financial advisor" disclaimer unless directly relevant

**Formatting:**
- No markdown headers (no #, ##, ###)
- Use **bold** for emphasis sparingly
- Bullet points for lists
- Keep paragraphs short and scannable"""

    # All templates now pass through cleanly - the system prompt handles tone/style
    FINANCIAL_QA_TEMPLATE = """{question}"""
    RATIO_ANALYSIS_TEMPLATE = """{question}"""
    STATEMENT_ANALYSIS_TEMPLATE = """{question}"""
    VALUATION_TEMPLATE = """{question}"""
    MACRO_TEMPLATE = """{question}"""

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
