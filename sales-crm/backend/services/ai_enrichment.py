"""
AI enrichment service — uses Claude to analyse a LinkedIn profile and
automatically populate stakeholder CRM fields.

Requires ANTHROPIC_API_KEY environment variable.

Returns a structured dict with:
  - role                    (decision-maker | influencer | champion | user | unknown)
  - influence_level         (high | medium | low)
  - sentiment               (positive | neutral | negative)
  - ai_summary              one-paragraph profile summary
  - approach_recommendation personalised outreach advice
  - buying_signals          list of signals detected from the profile
"""

import os
import json
from typing import Dict

import anthropic
from pydantic import BaseModel
from typing import List


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ── Pydantic schema for structured output ──────────────────────────────────────

class StakeholderInsights(BaseModel):
    role: str
    influence_level: str
    sentiment: str
    ai_summary: str
    approach_recommendation: str
    buying_signals: List[str]


# ── Public interface ───────────────────────────────────────────────────────────

async def enrich_from_linkedin(profile: Dict) -> Dict:
    """
    Send a LinkedIn profile dict to Claude and get back structured
    stakeholder insights.

    Falls back gracefully if no API key is set or the call fails.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_insights(profile)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    profile_text = _format_profile(profile)

    prompt = f"""You are an expert B2B sales strategist. Analyse the following LinkedIn profile
and return structured insights to help a sales team engage with this person.

LinkedIn Profile:
{profile_text}

Return your analysis as JSON matching this exact schema:
{{
  "role": "<one of: decision-maker | influencer | champion | user | unknown>",
  "influence_level": "<one of: high | medium | low>",
  "sentiment": "<one of: positive | neutral | negative>  (inferred from their background and likely attitude toward vendors)",
  "ai_summary": "<2-3 sentence summary of who this person is and why they matter to this deal>",
  "approach_recommendation": "<specific, actionable advice on how to engage this person — tone, topics to raise, what to avoid>",
  "buying_signals": ["<signal 1>", "<signal 2>", ...]
}}

Buying signals are concrete indicators from their profile (job title, tenure, skills, company growth,
recent role change, etc.) that suggest they are likely to be involved in a purchasing decision.
Return only valid JSON, no markdown fences."""

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract the text block (thinking blocks are separate)
        text = next(
            (b.text for b in response.content if b.type == "text"), "{}"
        )
        data = json.loads(text)

        # Validate and coerce via Pydantic
        insights = StakeholderInsights(**data)
        return insights.model_dump()

    except Exception as exc:
        # Return fallback so the scan still succeeds
        result = _fallback_insights(profile)
        result["ai_summary"] = f"[AI enrichment failed: {exc}] " + result["ai_summary"]
        return result


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format_profile(profile: Dict) -> str:
    lines = []
    if profile.get("full_name"):
        lines.append(f"Name: {profile['full_name']}")
    if profile.get("headline"):
        lines.append(f"Headline: {profile['headline']}")
    if profile.get("current_company"):
        lines.append(f"Company: {profile['current_company']}")
    if profile.get("location"):
        lines.append(f"Location: {profile['location']}")
    if profile.get("summary"):
        lines.append(f"Summary: {profile['summary']}")
    if profile.get("skills"):
        lines.append(f"Skills: {', '.join(profile['skills'])}")
    if profile.get("connections"):
        lines.append(f"Connections: {profile['connections']}")
    return "\n".join(lines) if lines else "No profile data available."


def _fallback_insights(profile: Dict) -> Dict:
    """Return sensible defaults when Claude is unavailable."""
    headline = profile.get("headline", "").lower()
    role = "decision-maker" if any(
        w in headline for w in ["ceo", "cto", "cfo", "coo", "vp", "director", "head", "chief"]
    ) else "influencer" if any(
        w in headline for w in ["manager", "lead", "senior", "principal"]
    ) else "unknown"

    return {
        "role": role,
        "influence_level": "high" if role == "decision-maker" else "medium",
        "sentiment": "neutral",
        "ai_summary": (
            f"{profile.get('full_name', 'This person')} is a "
            f"{profile.get('headline', 'professional')} at "
            f"{profile.get('current_company', 'their company')}."
        ),
        "approach_recommendation": (
            "Review their LinkedIn profile in detail before reaching out. "
            "Set ANTHROPIC_API_KEY for AI-powered personalised recommendations."
        ),
        "buying_signals": [],
    }
