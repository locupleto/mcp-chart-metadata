#!/usr/bin/env python3
"""
MCP Server for Chart Metadata Discovery

Provides tools for discovering and validating chart studies, strategies, and signals.
Used by the Telegram Trading Bot to ensure robust parameter validation.

Tools:
- list_studies: Get all available study names
- list_strategies: Get all available strategy names
- list_bullish_signals: Get all available bullish signal names
- list_bearish_signals: Get all available bearish signal names
- validate_study: Validate study name with fuzzy matching
- validate_strategy: Validate strategy name with fuzzy matching
"""

import sys
import os
from pathlib import Path

# Add trading-lab src to path for imports
# Try environment variable first, fallback to relative path
TRADING_LAB_PATH = os.environ.get('TRADING_LAB_PATH')
if TRADING_LAB_PATH is None:
    TRADING_LAB_PATH = Path(__file__).parent.parent / "trading-lab" / "src"
else:
    TRADING_LAB_PATH = Path(TRADING_LAB_PATH)

sys.path.insert(0, str(TRADING_LAB_PATH))
print(f"[chart-metadata] Using TRADING_LAB_PATH: {TRADING_LAB_PATH}", file=sys.stderr)

from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Optional, Tuple
import difflib

# Initialize FastMCP server
mcp = FastMCP("chart-metadata")


def get_studies() -> Dict[str, str]:
    """Discover all available studies."""
    try:
        from studies.study_registry import StudyRegistry
        studies = StudyRegistry.list_studies()
        # Strip 'Study' suffix for bot compatibility
        # e.g., "MCPSimpleStudy" -> "MCPSimple"
        return {name.replace('Study', ''): name for name in studies}
    except Exception as e:
        print(f"Error discovering studies: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {}


def get_strategies() -> Dict[str, str]:
    """Discover all available strategies."""
    try:
        from strategies import StrategyFactory
        strategies = StrategyFactory.list_available()
        return {name: name for name in strategies}
    except Exception as e:
        print(f"Error discovering strategies: {e}", file=sys.stderr)
        return {}


def get_bullish_signals() -> Dict[str, str]:
    """Discover all available bullish signals."""
    try:
        from utilities.signal_discovery import discover_bullish_signals
        signals = discover_bullish_signals()
        return {name: name for name in signals.keys()}
    except Exception as e:
        print(f"Error discovering bullish signals: {e}", file=sys.stderr)
        return {}


def get_bearish_signals() -> Dict[str, str]:
    """Discover all available bearish signals."""
    try:
        from utilities.signal_discovery import discover_bearish_signals
        signals = discover_bearish_signals()
        return {name: name for name in signals.keys()}
    except Exception as e:
        print(f"Error discovering bearish signals: {e}", file=sys.stderr)
        return {}


def fuzzy_match(query: str, options: List[str], cutoff: float = 0.6) -> List[Tuple[str, float]]:
    """
    Find closest matches using fuzzy string matching.

    Args:
        query: Input string to match
        options: List of valid options
        cutoff: Minimum similarity score (0.0 to 1.0)

    Returns:
        List of (match, score) tuples sorted by score descending
    """
    matches = difflib.get_close_matches(query, options, n=5, cutoff=cutoff)
    # Get similarity scores for each match
    scored_matches = []
    for match in matches:
        score = difflib.SequenceMatcher(None, query.lower(), match.lower()).ratio()
        scored_matches.append((match, score))

    return sorted(scored_matches, key=lambda x: x[1], reverse=True)


@mcp.tool()
def list_studies() -> dict:
    """
    Get all available chart study names.

    Returns:
        Dictionary with 'studies' key containing list of study names
    """
    studies = get_studies()
    return {
        "studies": sorted(studies.keys()),
        "count": len(studies)
    }


@mcp.tool()
def list_strategies() -> dict:
    """
    Get all available trading strategy names.

    Returns:
        Dictionary with 'strategies' key containing list of strategy names
    """
    strategies = get_strategies()
    return {
        "strategies": sorted(strategies.keys()),
        "count": len(strategies)
    }


@mcp.tool()
def list_bullish_signals() -> dict:
    """
    Get all available bullish signal names.

    Returns:
        Dictionary with 'signals' key containing list of signal names
    """
    signals = get_bullish_signals()
    return {
        "signals": sorted(signals.keys()),
        "count": len(signals)
    }


@mcp.tool()
def list_bearish_signals() -> dict:
    """
    Get all available bearish signal names.

    Returns:
        Dictionary with 'signals' key containing list of signal names
    """
    signals = get_bearish_signals()
    return {
        "signals": sorted(signals.keys()),
        "count": len(signals)
    }


@mcp.tool()
def validate_study(name: str, return_closest: bool = True) -> dict:
    """
    Validate a study name and optionally return closest matches if invalid.

    Args:
        name: Study name to validate
        return_closest: If True, return fuzzy matches when exact match fails

    Returns:
        Dictionary with validation result:
        - valid: True if exact match found
        - matched_name: Exact matched name (if valid=True)
        - confidence: Match confidence score (0.0-1.0)
        - suggestions: List of similar names (if valid=False and return_closest=True)
        - message: Human-readable message
    """
    studies = get_studies()
    study_names = list(studies.keys())

    # Try exact match (case-insensitive)
    for study in study_names:
        if study.lower() == name.lower():
            return {
                "valid": True,
                "matched_name": study,
                "confidence": 1.0,
                "suggestions": [],
                "message": f"Exact match found: {study}"
            }

    # No exact match - try fuzzy matching
    if return_closest:
        matches = fuzzy_match(name, study_names, cutoff=0.5)

        if matches:
            best_match, best_score = matches[0]
            suggestions = [{"name": m, "confidence": round(s, 2)} for m, s in matches[:5]]

            # High confidence (≥70%) - treat as valid match (lenient fuzzy matching)
            if best_score >= 0.70:
                return {
                    "valid": True,
                    "matched_name": best_match,
                    "confidence": best_score,
                    "suggestions": [],  # Empty - match is confident enough
                    "message": f"Fuzzy match: '{best_match}' (confidence: {best_score:.0%})"
                }

            # Medium/Low confidence (<70%) - return suggestions for bot to handle
            if best_score >= 0.85:
                message = f"No exact match. Did you mean '{best_match}'? (confidence: {best_score:.0%})"
            else:
                message = f"No exact match. Closest matches found (best: {best_score:.0%})"

            return {
                "valid": False,
                "matched_name": None,
                "confidence": best_score,
                "suggestions": suggestions,
                "message": message
            }

    return {
        "valid": False,
        "matched_name": None,
        "confidence": 0.0,
        "suggestions": [],
        "message": f"No match found for '{name}'. Use list_studies() to see available options."
    }


@mcp.tool()
def validate_strategy(name: str, return_closest: bool = True) -> dict:
    """
    Validate a strategy name and optionally return closest matches if invalid.

    Args:
        name: Strategy name to validate
        return_closest: If True, return fuzzy matches when exact match fails

    Returns:
        Dictionary with validation result (same structure as validate_study)
    """
    strategies = get_strategies()
    strategy_names = list(strategies.keys())

    # Try exact match (case-insensitive)
    for strategy in strategy_names:
        if strategy.lower() == name.lower():
            return {
                "valid": True,
                "matched_name": strategy,
                "confidence": 1.0,
                "suggestions": [],
                "message": f"Exact match found: {strategy}"
            }

    # No exact match - try fuzzy matching
    if return_closest:
        matches = fuzzy_match(name, strategy_names, cutoff=0.5)

        if matches:
            best_match, best_score = matches[0]
            suggestions = [{"name": m, "confidence": round(s, 2)} for m, s in matches[:5]]

            # High confidence (≥70%) - treat as valid match (lenient fuzzy matching)
            if best_score >= 0.70:
                return {
                    "valid": True,
                    "matched_name": best_match,
                    "confidence": best_score,
                    "suggestions": [],  # Empty - match is confident enough
                    "message": f"Fuzzy match: '{best_match}' (confidence: {best_score:.0%})"
                }

            # Medium/Low confidence (<70%) - return suggestions for bot to handle
            if best_score >= 0.85:
                message = f"No exact match. Did you mean '{best_match}'? (confidence: {best_score:.0%})"
            else:
                message = f"No exact match. Closest matches found (best: {best_score:.0%})"

            return {
                "valid": False,
                "matched_name": None,
                "confidence": best_score,
                "suggestions": suggestions,
                "message": message
            }

    return {
        "valid": False,
        "matched_name": None,
        "confidence": 0.0,
        "suggestions": [],
        "message": f"No match found for '{name}'. Use list_strategies() to see available options."
    }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
