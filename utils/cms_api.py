"""
CMS Coverage API Integration
==============================
Fetches real NCD (National Coverage Determination) references from
the CMS Coverage API (api.coverage.cms.gov).

Includes:
- Session-level LRU cache to avoid repeated API calls
- Retry logic with exponential backoff
- Timeout fallback to curated local references
"""

import requests
import time
from functools import lru_cache

CMS_COVERAGE_API = "https://api.coverage.cms.gov/v1"
CMS_BASE_URL     = "https://www.cms.gov/medicare-coverage-database"

# Tighter keywords — specific to avoid false matches
CPT_KEYWORDS = {
    "99215": ["evaluation and management", "office and outpatient"],
    "99213": ["evaluation and management", "office and outpatient"],
    "99223": ["hospital", "inpatient care"],
    "99397": ["preventive medicine", "annual wellness"],
    "72148": ["magnetic resonance imaging", "lumbar", "spine mri"],
    "70553": ["magnetic resonance imaging", "brain"],
    "93306": ["echocardiograph"],
    "93000": ["electrocardiograph"],
    "27447": ["knee", "arthroplasty", "osteoarthritic knee"],
    "97001": ["physical therapy", "occupational therapy"],
    "85025": ["complete blood count", "blood count"],
    "80053": ["metabolic panel", "comprehensive metabolic"],
    "36415": ["venipuncture", "phlebotomy"]
}

# Curated fallback references per CPT when no NCD match found
CPT_FALLBACK_REFS = {
    "99215": {"title": "E/M Services Guide", "url": f"{CMS_BASE_URL}/view/article.aspx?articleid=52972"},
    "99213": {"title": "E/M Services Guide", "url": f"{CMS_BASE_URL}/view/article.aspx?articleid=52972"},
    "99223": {"title": "E/M Services Guide", "url": f"{CMS_BASE_URL}/view/article.aspx?articleid=52972"},
    "99397": {"title": "Preventive Services", "url": "https://www.cms.gov/medicare/coverage/preventive-and-screening-services"},
    "72148": {"title": "MRI Coverage Policy NCD 220.2", "url": f"{CMS_BASE_URL}/view/ncd.aspx?ncdid=177"},
    "70553": {"title": "MRI Coverage Policy NCD 220.2", "url": f"{CMS_BASE_URL}/view/ncd.aspx?ncdid=177"},
    "93306": {"title": "Echocardiography NCD 20.7", "url": f"{CMS_BASE_URL}/view/ncd.aspx?ncdid=98"},
    "93000": {"title": "Electrocardiograph NCD 20.15", "url": f"{CMS_BASE_URL}/view/ncd.aspx?ncdid=100"},
    "27447": {"title": "Knee Arthroplasty LCD", "url": f"{CMS_BASE_URL}/view/lcd.aspx?lcdid=38548"},
    "97001": {"title": "Physical Therapy LCD", "url": f"{CMS_BASE_URL}/view/lcd.aspx?lcdid=33865"},
    "85025": {"title": "Lab Services Coverage", "url": "https://www.cms.gov/medicare/coverage/clinical-laboratory-services"},
    "80053": {"title": "Lab Services Coverage", "url": "https://www.cms.gov/medicare/coverage/clinical-laboratory-services"},
    "36415": {"title": "Lab Services Coverage", "url": "https://www.cms.gov/medicare/coverage/clinical-laboratory-services"},
    "64483": {"title": "Epidural Steroid Injection", "url": f"{CMS_BASE_URL}/view/lcd.aspx?lcdid=33935"},
    "73721": {"title": "MRI Extremity Coverage", "url": f"{CMS_BASE_URL}/view/ncd.aspx?ncdid=177"},
    "94640": {"title": "Nebulizer Treatment Coverage", "url": "https://www.cms.gov/medicare/coverage/durable-medical-equipment"},
}


@lru_cache(maxsize=1)
def fetch_ncd_list_cached() -> tuple:
    """
    Fetch NCD list with session-level caching.
    Returns tuple (for hashability with lru_cache) of NCD dicts.
    Includes retry logic with exponential backoff.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"{CMS_COVERAGE_API}/reports/national-coverage-ncd",
                timeout=8
            )
            if response.status_code == 200:
                data = response.json().get("data", [])
                return tuple(data)  # tuple for lru_cache hashability
        except requests.Timeout:
            print(f"[CMS API] Timeout on attempt {attempt+1}/{max_retries}")
        except requests.RequestException as e:
            print(f"[CMS API] Error on attempt {attempt+1}: {e}")

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s

    print("[CMS API] All retries failed, using fallback references")
    return tuple()


def find_ncd_for_cpt(cpt_code: str, ncd_list: tuple) -> list:
    """Find matching NCDs for a CPT code using strict keyword matching."""
    keywords = CPT_KEYWORDS.get(cpt_code, [])
    if not keywords:
        return []

    matches = []
    for doc in ncd_list:
        title = doc.get("title", "").lower()
        for kw in keywords:
            kw_words = kw.lower().split()
            if all(w in title for w in kw_words):
                url = doc.get("url", "")
                full_url = (
                    f"{CMS_BASE_URL}{url}"
                    if url.startswith("/")
                    else url or CMS_BASE_URL
                )
                matches.append({
                    "title":               doc.get("title", "Unknown"),
                    "document_display_id": doc.get("document_display_id", "N/A"),
                    "last_updated":        doc.get("last_updated", "N/A"),
                    "url":                 full_url
                })
                break

    return matches[:1]


def get_cms_context_for_claim(cpt_codes: list) -> dict:
    """
    Main function: fetches real CMS NCD references for all CPT codes.
    Uses session-level cache — API called at most once per session.
    Falls back to curated references if no NCD match found.
    """
    ncd_list = fetch_ncd_list_cached()
    results  = {}

    for code in cpt_codes:
        matches = find_ncd_for_cpt(code, ncd_list)

        if not matches and code in CPT_FALLBACK_REFS:
            fallback = CPT_FALLBACK_REFS[code]
            matches = [{
                "title":               fallback["title"],
                "document_display_id": "See URL",
                "last_updated":        "Current",
                "url":                 fallback["url"]
            }]

        results[code] = matches

    return results