"""
LinkedIn profile scraper / enrichment service.

NOTE: Scraping LinkedIn directly violates their ToS and is rate-limited by
bot-detection.  This module provides two paths:

  1. Mock / demo mode (default) – returns realistic synthetic profile data so
     the CRM works end-to-end without credentials.
  2. RapidAPI LinkedIn proxy – set RAPIDAPI_KEY in env to enable real lookups
     via the "Fresh LinkedIn Profile Data" API on RapidAPI.

The interface is identical in both modes so the rest of the app is unaffected.
"""

import os
import json
import hashlib
import re
from typing import Dict, Optional

import httpx


RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "fresh-linkedin-profile-data.p.rapidapi.com"

# ── Mock data ──────────────────────────────────────────────────────────────────

_MOCK_TITLES = [
    "VP of Sales", "Director of Engineering", "Chief Technology Officer",
    "Head of Product", "Senior Account Executive", "Marketing Manager",
    "CEO", "COO", "CFO", "Procurement Manager", "IT Director",
]

_MOCK_COMPANIES = [
    "Acme Corp", "TechVentures Inc", "GlobalSoft", "NexGen Systems",
    "BlueSky Analytics", "DataPeak Solutions", "CloudEdge Ltd",
]

_MOCK_SKILLS = [
    ["Python", "FastAPI", "PostgreSQL", "Docker"],
    ["Sales Strategy", "CRM", "Salesforce", "HubSpot"],
    ["Product Management", "Agile", "Jira", "Roadmapping"],
    ["Cloud Architecture", "AWS", "Terraform", "Kubernetes"],
    ["Business Development", "Partnership", "Contract Negotiation"],
]

_MOCK_SUMMARIES = [
    "Results-driven professional with 10+ years of experience driving growth.",
    "Passionate about building scalable systems that solve real-world problems.",
    "Strategic thinker with a track record of delivering enterprise-level solutions.",
    "Customer-obsessed leader focused on aligning technology with business goals.",
]


def _seed(url: str) -> int:
    return int(hashlib.md5(url.encode()).hexdigest(), 16)


def _mock_profile(linkedin_url: str) -> Dict:
    """Generate a deterministic synthetic profile from the URL."""
    s = _seed(linkedin_url)
    name_slug = re.sub(r"[^a-z0-9]", " ",
                       linkedin_url.rstrip("/").split("/")[-1]).strip().title()
    parts = name_slug.split() or ["John", "Doe"]
    first = parts[0] if parts else "John"
    last  = parts[-1] if len(parts) > 1 else "Doe"

    return {
        "full_name":       f"{first} {last}",
        "first_name":      first,
        "last_name":       last,
        "headline":        _MOCK_TITLES[s % len(_MOCK_TITLES)],
        "current_company": _MOCK_COMPANIES[s % len(_MOCK_COMPANIES)],
        "location":        ["San Francisco, CA", "New York, NY", "Austin, TX",
                            "London, UK", "Berlin, DE"][s % 5],
        "summary":         _MOCK_SUMMARIES[s % len(_MOCK_SUMMARIES)],
        "skills":          _MOCK_SKILLS[s % len(_MOCK_SKILLS)],
        "connections":     300 + (s % 700),
        "profile_url":     linkedin_url,
        "source":          "mock",
    }


# ── Real RapidAPI scraper ──────────────────────────────────────────────────────

async def _rapidapi_profile(linkedin_url: str) -> Dict:
    headers = {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }
    params = {"linkedin_url": linkedin_url}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://{RAPIDAPI_HOST}/get-linkedin-profile",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    # Normalise RapidAPI response to our schema
    return {
        "full_name":       data.get("full_name", ""),
        "first_name":      data.get("first_name", ""),
        "last_name":       data.get("last_name", ""),
        "headline":        data.get("headline", ""),
        "current_company": (data.get("experiences") or [{}])[0].get("company", ""),
        "location":        data.get("city", "") + ", " + data.get("country", ""),
        "summary":         data.get("summary", ""),
        "skills":          [s.get("name") for s in (data.get("skills") or [])],
        "connections":     data.get("connections", 0),
        "profile_url":     linkedin_url,
        "source":          "rapidapi",
    }


# ── Public interface ──────────────────────────────────────────────────────────

async def scrape_profile(linkedin_url: str) -> Dict:
    """
    Fetch a LinkedIn profile.  Uses RapidAPI if RAPIDAPI_KEY is set,
    otherwise returns mock data.
    """
    linkedin_url = linkedin_url.strip().rstrip("/")
    if not linkedin_url.startswith("http"):
        linkedin_url = "https://www.linkedin.com/in/" + linkedin_url

    if RAPIDAPI_KEY:
        try:
            return await _rapidapi_profile(linkedin_url)
        except Exception as exc:
            # Fall back to mock on any error
            return {**_mock_profile(linkedin_url), "error": str(exc), "source": "mock_fallback"}

    return _mock_profile(linkedin_url)


def profile_to_json(profile: Dict) -> str:
    return json.dumps(profile, default=str)
