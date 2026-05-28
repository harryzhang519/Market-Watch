"""
Gemini-powered market signal interpretation.

Takes ingested market data and news headlines, sends them to Gemini,
and returns a structured JSON signal (direction, confidence, severity, etc.).

Includes automatic retry with exponential backoff for rate limits,
model fallback chain, and a rule-based local fallback when all AI calls fail.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Valid values for signal fields
VALID_DIRECTIONS = {"heating", "cooling", "stable"}
VALID_CONFIDENCES = {"high", "medium", "low"}
VALID_SEVERITIES = range(1, 6)  # 1–5

# Models to try in order of preference — if the first hits quota, try the next
MODEL_FALLBACK_CHAIN = [
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 2.0
BACKOFF_MULTIPLIER = 2.0

SYSTEM_PROMPT = (
    "You are a real estate market analyst. Given housing market data and recent "
    "news for a city, you will output a structured JSON signal object.\n"
    "Return ONLY valid JSON. No preamble. No markdown."
)

USER_PROMPT_TEMPLATE = """City: {city}, {region}

Market data (past 30 days where available):
- Median listing price: {price} ({price_change_pct}% change)
- Active inventory: {inventory} listings ({inventory_change_pct}% change)
- Median days on market: {days_on_market}
- Mortgage/policy rate: {rate}% (central bank: {bank})

Recent news headlines:
{news_headlines}

Return this exact JSON structure:
{{
  "direction": "heating" | "cooling" | "stable",
  "confidence": "high" | "medium" | "low",
  "explanation": "<2 sentences>",
  "key_driver": "<single most important factor>",
  "severity": <integer 1-5>,
  "notable_event": "<major signal from news or null>"
}}"""


def _get_api_key() -> Optional[str]:
    """Retrieve the Gemini API key from environment."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        logger.warning(
            "GEMINI_API_KEY not set in environment. AI interpretation will be unavailable. "
            "Get a key at https://aistudio.google.com/app/apikey"
        )
    return key


def _format_value(value: Any, suffix: str = "") -> str:
    """Format a value for display, showing 'N/A' for None."""
    if value is None:
        return "N/A"
    return f"{value}{suffix}"


def _build_user_prompt(
    city_name: str,
    region: str,
    market_data: Optional[Dict[str, Any]],
    news_headlines: List[str],
) -> str:
    """Construct the user prompt from market data and news."""
    md = market_data or {}

    formatted_headlines = "\n".join(
        f"- {h}" for h in news_headlines
    ) if news_headlines else "- No recent news available"

    return USER_PROMPT_TEMPLATE.format(
        city=city_name,
        region=region,
        price=_format_value(md.get("price"), ""),
        price_change_pct=_format_value(md.get("price_change_pct")),
        inventory=_format_value(md.get("inventory")),
        inventory_change_pct=_format_value(md.get("inventory_change_pct")),
        days_on_market=_format_value(md.get("days_on_market")),
        rate=_format_value(md.get("rate")),
        bank=md.get("bank", "N/A"),
        news_headlines=formatted_headlines,
    )


def _validate_signal(signal: dict) -> dict:
    """Validate and sanitize the parsed signal, applying defaults for invalid fields."""
    validated = {}

    # Direction
    direction = signal.get("direction", "stable")
    validated["direction"] = direction if direction in VALID_DIRECTIONS else "stable"

    # Confidence
    confidence = signal.get("confidence", "low")
    validated["confidence"] = confidence if confidence in VALID_CONFIDENCES else "low"

    # Explanation
    explanation = signal.get("explanation", "")
    validated["explanation"] = str(explanation)[:1000] if explanation else "Analysis unavailable."

    # Key driver
    key_driver = signal.get("key_driver", "")
    validated["key_driver"] = str(key_driver)[:200] if key_driver else "Unknown"

    # Severity
    severity = signal.get("severity", 1)
    try:
        severity = int(severity)
        validated["severity"] = severity if severity in VALID_SEVERITIES else 3
    except (ValueError, TypeError):
        validated["severity"] = 3

    # Notable event (nullable)
    notable = signal.get("notable_event")
    if notable and str(notable).lower() not in ("null", "none", "n/a", ""):
        validated["notable_event"] = str(notable)[:500]
    else:
        validated["notable_event"] = None

    return validated


def _parse_gemini_response(text: str) -> Optional[dict]:
    """Parse JSON from Gemini's response text, handling common formatting issues."""
    if not text:
        return None

    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        logger.warning("Gemini returned valid JSON but not a dict: %s", type(parsed))
        return None
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini JSON response: %s\nRaw: %s", e, text[:500])
        return None


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if an exception is a Gemini 429 rate limit error."""
    error_str = str(error)
    return "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower()


# ---------------------------------------------------------------------------
# Rule-based local fallback — guarantees the sandbox NEVER returns empty
# ---------------------------------------------------------------------------

# Keywords that signal specific market directions
HEATING_KEYWORDS = [
    "cut", "cuts", "lower", "slash", "reduce", "boom", "surge", "soar",
    "record high", "bidding war", "demand", "shortage", "employer", "hiring",
    "expansion", "campus", "headquarters", "tech hub", "growth", "buy",
]
COOLING_KEYWORDS = [
    "hike", "raise", "increase rate", "spike", "layoff", "downturn",
    "recession", "slowdown", "inventory surge", "price drop", "crash",
    "bubble", "foreclosure", "bankruptcy", "shutdown", "closing",
]


def _local_fallback_interpret(
    city_name: str,
    region: str,
    market_data: Optional[Dict[str, Any]],
    news_headlines: List[str],
) -> dict:
    """Rule-based local interpretation when all Gemini models are unavailable.

    This ensures the simulation sandbox always returns a result, even during
    API outages or quota exhaustion.
    """
    md = market_data or {}
    headline = news_headlines[0] if news_headlines else ""
    headline_lower = headline.lower()

    # Score the headline for heating vs cooling signals
    heat_score = sum(1 for kw in HEATING_KEYWORDS if kw in headline_lower)
    cool_score = sum(1 for kw in COOLING_KEYWORDS if kw in headline_lower)

    # Also factor in quantitative data
    price_pct = md.get("price_change_pct")
    if price_pct is not None:
        if price_pct > 2:
            heat_score += 2
        elif price_pct < -2:
            cool_score += 2

    rate_val = md.get("rate")
    if rate_val is not None:
        if rate_val > 6.5:
            cool_score += 1
        elif rate_val < 4.0:
            heat_score += 1

    # Determine direction
    if heat_score > cool_score:
        direction = "heating"
        severity = min(5, 2 + heat_score)
        confidence = "medium" if heat_score >= 3 else "low"
    elif cool_score > heat_score:
        direction = "cooling"
        severity = min(5, 2 + cool_score)
        confidence = "medium" if cool_score >= 3 else "low"
    else:
        direction = "stable"
        severity = 2
        confidence = "low"

    # Build explanation
    price_str = f"${md['price']:,.0f}" if md.get("price") and md["price"] > 2000 else "N/A"
    rate_str = f"{md['rate']}%" if md.get("rate") else "N/A"

    if direction == "heating":
        explanation = (
            f"Based on the simulated news scenario for {city_name}, market conditions "
            f"suggest a heating signal. With median listing prices at {price_str} and "
            f"policy rates at {rate_str}, the headline indicates upward pressure on demand."
        )
        key_driver = headline[:100] if headline else "Simulated economic stimulus"
    elif direction == "cooling":
        explanation = (
            f"The simulated scenario for {city_name} indicates cooling market pressure. "
            f"With median prices at {price_str} and rates at {rate_str}, the headline "
            f"suggests headwinds for housing demand and potential price softening."
        )
        key_driver = headline[:100] if headline else "Simulated economic headwind"
    else:
        explanation = (
            f"The simulated headline for {city_name} does not strongly indicate either "
            f"heating or cooling. Current median prices sit at {price_str} with rates "
            f"at {rate_str}, suggesting a balanced or neutral market outlook."
        )
        key_driver = "Balanced market conditions"

    return {
        "direction": direction,
        "confidence": confidence,
        "explanation": explanation,
        "key_driver": key_driver,
        "severity": severity,
        "notable_event": headline if headline else None,
        "_source": "local_fallback",
    }


async def interpret_city(
    city_name: str,
    region: str,
    market_data: Optional[Dict[str, Any]],
    news_headlines: List[str],
) -> Optional[dict]:
    """Use Gemini to interpret market data and news into a structured signal.

    Includes:
    - Automatic retry with exponential backoff for 429 rate limit errors
    - Model fallback chain (tries multiple models if one is quota-exhausted)
    - Rule-based local fallback so the sandbox NEVER returns None

    Args:
        city_name: Human-readable city name.
        region: Region name (e.g., "Ohio", "Ontario").
        market_data: Dict from FRED/StatCan/CMHC ingestion, or None.
        news_headlines: List of headline strings.

    Returns:
        Validated signal dict — always returns a result, never None.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("No API key — using local fallback for %s", city_name)
        return _local_fallback_interpret(city_name, region, market_data, news_headlines)

    # Import SDK here to avoid import errors when key isn't set
    try:
        import google.generativeai as genai
    except ImportError:
        logger.error(
            "google-generativeai package not installed. "
            "Run: pip install google-generativeai"
        )
        return _local_fallback_interpret(city_name, region, market_data, news_headlines)

    genai.configure(api_key=api_key)
    user_prompt = _build_user_prompt(city_name, region, market_data, news_headlines)

    # Try each model in the fallback chain
    for model_name in MODEL_FALLBACK_CHAIN:
        last_error = None

        # Retry loop with exponential backoff for each model
        backoff = INITIAL_BACKOFF_SECONDS
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_PROMPT,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                    ),
                )

                logger.info(
                    "Gemini request for %s using %s (attempt %d/%d)",
                    city_name, model_name, attempt, MAX_RETRIES,
                )

                response = await model.generate_content_async(user_prompt)

                if not response or not response.text:
                    logger.warning("Empty response from Gemini for %s on %s", city_name, model_name)
                    last_error = "Empty response"
                    break  # Don't retry empty responses, try next model

                parsed = _parse_gemini_response(response.text)
                if not parsed:
                    last_error = "JSON parse failure"
                    break  # Don't retry parse failures, try next model

                validated = _validate_signal(parsed)
                validated["_source"] = f"gemini:{model_name}"
                logger.info(
                    "Gemini signal for %s: direction=%s, confidence=%s, severity=%d (model=%s)",
                    city_name,
                    validated["direction"],
                    validated["confidence"],
                    validated["severity"],
                    model_name,
                )
                return validated

            except Exception as e:
                last_error = str(e)
                if _is_rate_limit_error(e):
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            "Rate limit (429) on %s for %s. Retrying in %.1fs (attempt %d/%d)...",
                            model_name, city_name, backoff, attempt, MAX_RETRIES,
                        )
                        await asyncio.sleep(backoff)
                        backoff *= BACKOFF_MULTIPLIER
                    else:
                        logger.warning(
                            "Rate limit exhausted on %s for %s after %d retries. Trying next model...",
                            model_name, city_name, MAX_RETRIES,
                        )
                else:
                    # Non-rate-limit error — don't retry, try next model
                    logger.error(
                        "Non-retryable Gemini error on %s for %s: %s",
                        model_name, city_name, e,
                    )
                    break

        logger.warning(
            "Model %s failed for %s (last error: %s). Moving to next fallback...",
            model_name, city_name, last_error,
        )

    # All models exhausted — use local rule-based fallback
    logger.warning(
        "All Gemini models exhausted for %s. Using local rule-based fallback.",
        city_name,
    )
    result = _local_fallback_interpret(city_name, region, market_data, news_headlines)
    result["explanation"] = (
        f"[AI temporarily rate-limited — rule-based analysis] {result['explanation']}"
    )
    return result
