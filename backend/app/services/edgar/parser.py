"""SEC filing HTML parser for extracting structured sections."""

import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

from .models import FilingMetadata, Section, ParsedFiling, FilingType

logger = logging.getLogger(__name__)


# Section definitions for 10-K filings
SECTIONS_10K = [
    ("1", "Business", r"item\s*1[.\s\-\u2013\u2014]+business"),
    ("1A", "Risk Factors", r"item\s*1a[.\s\-\u2013\u2014]+risk\s*factors"),
    ("1B", "Unresolved Staff Comments", r"item\s*1b[.\s\-\u2013\u2014]+unresolved"),
    ("2", "Properties", r"item\s*2[.\s\-\u2013\u2014]+properties"),
    ("3", "Legal Proceedings", r"item\s*3[.\s\-\u2013\u2014]+legal"),
    ("4", "Mine Safety", r"item\s*4[.\s\-\u2013\u2014]+mine"),
    ("5", "Market", r"item\s*5[.\s\-\u2013\u2014]+market"),
    ("6", "Reserved", r"item\s*6[.\s\-\u2013\u2014]+reserved"),
    ("7", "Management's Discussion and Analysis", r"item\s*7[.\s\-\u2013\u2014]+management"),
    ("7A", "Quantitative and Qualitative Disclosures", r"item\s*7a[.\s\-\u2013\u2014]+quantitative"),
    ("8", "Financial Statements", r"item\s*8[.\s\-\u2013\u2014]+financial\s*statements"),
    ("9", "Changes in Accountants", r"item\s*9[.\s\-\u2013\u2014]+changes"),
    ("9A", "Controls and Procedures", r"item\s*9a[.\s\-\u2013\u2014]+controls"),
    ("9B", "Other Information", r"item\s*9b[.\s\-\u2013\u2014]+other"),
]

# Section definitions for 10-Q filings
SECTIONS_10Q = [
    ("1", "Financial Statements", r"item\s*1[.\s\-\u2013\u2014]+financial\s*statements"),
    ("2", "Management's Discussion and Analysis", r"item\s*2[.\s\-\u2013\u2014]+management"),
    ("3", "Quantitative and Qualitative Disclosures", r"item\s*3[.\s\-\u2013\u2014]+quantitative"),
    ("4", "Controls and Procedures", r"item\s*4[.\s\-\u2013\u2014]+controls"),
    ("1A", "Risk Factors", r"item\s*1a[.\s\-\u2013\u2014]+risk\s*factors"),
    ("2_II", "Unregistered Sales", r"item\s*2[.\s\-\u2013\u2014]+unregistered"),
    ("5", "Other Information", r"item\s*5[.\s\-\u2013\u2014]+other"),
    ("6", "Exhibits", r"item\s*6[.\s\-\u2013\u2014]+exhibits"),
]


class FilingParser:
    """
    Parses SEC filing HTML documents to extract structured sections.

    Uses a more robust approach that:
    - Finds all occurrences of section headers
    - Uses the last substantive occurrence (skipping table of contents)
    - Extracts content between sections
    """

    def parse(self, html_content: str, metadata: FilingMetadata) -> ParsedFiling:
        """Parse a filing based on its type."""
        if metadata.filing_type == FilingType.FORM_10K:
            return self._parse_structured(html_content, metadata, SECTIONS_10K)
        elif metadata.filing_type == FilingType.FORM_10Q:
            return self._parse_structured(html_content, metadata, SECTIONS_10Q)
        elif metadata.filing_type == FilingType.FORM_8K:
            return self._parse_8k(html_content, metadata)
        else:
            return self._parse_generic(html_content, metadata)

    def _parse_structured(
        self,
        html_content: str,
        metadata: FilingMetadata,
        section_defs: list[tuple[str, str, str]]
    ) -> ParsedFiling:
        """Parse filing with defined section structure."""
        soup = BeautifulSoup(html_content, "lxml")

        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()

        # Get text content
        full_text = soup.get_text(separator="\n")
        raw_text = self._clean_text(full_text)

        sections: dict[str, Section] = {}
        parse_errors: list[str] = []

        # Find all section positions
        section_positions = []
        for item_num, title, pattern in section_defs:
            positions = self._find_section_positions(raw_text, pattern)
            for pos in positions:
                section_positions.append((pos, item_num, title, pattern))

        # Sort by position
        section_positions.sort(key=lambda x: x[0])

        # Extract content between sections
        # Use the LAST occurrence of each section header (skip TOC entries)
        seen_items = {}
        for i, (pos, item_num, title, pattern) in enumerate(section_positions):
            # Find end position (start of next section or end of document)
            end_pos = len(raw_text)
            if i + 1 < len(section_positions):
                end_pos = section_positions[i + 1][0]

            content = raw_text[pos:end_pos]
            cleaned_content = self._clean_section_content(content)

            # Keep track of the best (longest) content for each section
            if len(cleaned_content) > 500:  # Minimum threshold for real content
                if item_num not in seen_items or len(cleaned_content) > len(seen_items[item_num][1]):
                    seen_items[item_num] = (title, cleaned_content)

        # Build sections from best matches
        for item_num, (title, content) in seen_items.items():
            sections[item_num] = Section(
                item_number=item_num,
                title=title,
                content=content,
            )
            logger.info(f"Extracted Item {item_num} ({title}): {len(content)} chars")

        # Report missing sections
        for item_num, title, pattern in section_defs:
            if item_num not in sections:
                # Only report for key sections
                if item_num in ["1", "1A", "7", "7A", "8"]:
                    parse_errors.append(f"Item {item_num} ({title}): Not found or too short")

        return ParsedFiling(
            metadata=metadata,
            sections=sections,
            raw_text=raw_text,
            parse_errors=parse_errors,
        )

    def _find_section_positions(self, text: str, pattern: str) -> list[int]:
        """Find all positions where a section pattern matches."""
        positions = []
        for match in re.finditer(pattern, text, re.IGNORECASE):
            positions.append(match.start())
        return positions

    def _clean_section_content(self, content: str) -> str:
        """Clean section content, removing header and excess whitespace."""
        # Skip the first line (section header)
        lines = content.split("\n")
        if lines:
            lines = lines[1:]  # Remove header line

        content = "\n".join(lines)
        return self._clean_text(content)

    def _parse_8k(self, html_content: str, metadata: FilingMetadata) -> ParsedFiling:
        """Parse an 8-K current report."""
        soup = BeautifulSoup(html_content, "lxml")

        for element in soup(["script", "style"]):
            element.decompose()

        raw_text = self._clean_text(soup.get_text(separator="\n"))

        return ParsedFiling(
            metadata=metadata,
            sections={
                "full": Section(
                    item_number="full",
                    title="Full Document",
                    content=raw_text,
                )
            },
            raw_text=raw_text,
        )

    def _parse_generic(self, html_content: str, metadata: FilingMetadata) -> ParsedFiling:
        """Generic parsing for unknown filing types."""
        soup = BeautifulSoup(html_content, "lxml")

        for element in soup(["script", "style"]):
            element.decompose()

        raw_text = self._clean_text(soup.get_text(separator="\n"))

        return ParsedFiling(
            metadata=metadata,
            sections={
                "full": Section(
                    item_number="full",
                    title="Full Document",
                    content=raw_text,
                )
            },
            raw_text=raw_text,
        )

    def _clean_text(self, text: str) -> str:
        """Clean extracted text content."""
        # Replace multiple spaces/tabs with single space
        text = re.sub(r"[ \t]+", " ", text)

        # Normalize line breaks
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\r", "\n", text)

        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split("\n")]

        # Remove empty lines that are adjacent to other empty lines
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            is_empty = len(line) == 0
            if is_empty and prev_empty:
                continue
            cleaned_lines.append(line)
            prev_empty = is_empty

        return "\n".join(cleaned_lines).strip()


# Singleton instance
_filing_parser: Optional[FilingParser] = None


def get_filing_parser() -> FilingParser:
    """Get singleton FilingParser instance."""
    global _filing_parser
    if _filing_parser is None:
        _filing_parser = FilingParser()
    return _filing_parser
