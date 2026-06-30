from utils.cms_api import get_cms_context_for_claim

CMS_GUIDELINES = [
    {
        "code": "99215",
        "description": "Office visit, high complexity. Requires medically appropriate history, exam, and high complexity medical decision making OR 40-54 minutes total time. NOT appropriate for straightforward acute complaints.",
        "source": "CMS E/M Guidelines 2023"
    },
    {
        "code": "99213",
        "description": "Office visit, low-moderate complexity. Appropriate for stable chronic conditions or minor acute illness. Requires low complexity medical decision making OR 20-29 minutes.",
        "source": "CMS E/M Guidelines 2023"
    },
    {
        "code": "72148",
        "description": "MRI lumbar spine without contrast. Medically necessary only after 6 weeks of conservative treatment failure, or with red flag symptoms: neurological deficits, bladder/bowel dysfunction, suspected malignancy, fracture.",
        "source": "CMS LCD L34220 - MRI Spine"
    },
    {
        "code": "27447",
        "description": "Total knee arthroplasty. Requires documented severe osteoarthritis, failure of conservative treatment, significant functional limitation. Not appropriate without prior imaging and documented knee pathology.",
        "source": "CMS LCD L38548 - Knee Arthroplasty"
    },
    {
        "code": "93306",
        "description": "Echocardiography transthoracic with Doppler. Indicated for evaluation of cardiac structure/function, valvular disease, heart failure, or endocarditis. Not appropriate as routine screening without cardiac symptoms.",
        "source": "CMS NCD 20.7 - Echocardiography"
    },
    {
        "code": "93000",
        "description": "Electrocardiogram with interpretation. Appropriate for chest pain, palpitations, syncope, dyspnea, or cardiac risk assessment. Routine use in low-risk asymptomatic patients is not covered.",
        "source": "CMS NCD 20.15 - ECG"
    },
    {
        "code": "70553",
        "description": "MRI brain with contrast. Indicated for neurological symptoms, seizures, suspected malignancy, dementia workup, or multiple sclerosis. Not appropriate for routine wellness visits without neurological complaints.",
        "source": "CMS LCD L35062 - MRI Brain"
    },
    {
        "code": "99397",
        "description": "Preventive medicine visit, established patient age 65+. Covers comprehensive age-appropriate exam, counseling, and preventive services. Cannot be billed same day as a separate E/M visit for same complaint.",
        "source": "CMS Preventive Services Guidelines"
    },
    {
        "code": "97001",
        "description": "Physical therapy evaluation. Requires documented functional limitation, physician referral, and measurable therapy goals. Not appropriate for self-limiting acute conditions expected to resolve within days.",
        "source": "CMS LCD L33865 - Physical Therapy"
    },
    {
        "code": "85025",
        "description": "Complete blood count with differential. Appropriate for infection workup, anemia evaluation, or monitoring chronic conditions. Not indicated as routine test without clinical justification.",
        "source": "CMS Lab Guidelines"
    },
    {
        "code": "99223",
        "description": "Initial hospital inpatient care, high complexity. Requires comprehensive history/exam and high complexity MDM. Appropriate for acute presentations requiring hospital admission.",
        "source": "CMS E/M Guidelines 2023"
    },
    {
        "code": "80053",
        "description": "Comprehensive metabolic panel. Appropriate for monitoring diabetes, kidney/liver disease, or electrolyte disorders. Not appropriate as routine screening without clinical indication.",
        "source": "CMS Lab Guidelines"
    },
    {
        "code": "36415",
        "description": "Venipuncture for blood collection. Covered when clinically indicated lab tests are ordered. Not separately billable as standalone without associated lab order.",
        "source": "CMS Lab Guidelines"
    }
]


def get_relevant_guidelines(cpt_codes: list) -> str:
    """
    Enhanced RAG layer:
    1. Pulls real CMS NCD references live from api.coverage.cms.gov
    2. Combines with local policy content
    3. Returns formatted context for agent prompts
    """
    # Fetch live CMS references
    cms_context = get_cms_context_for_claim(cpt_codes)

    relevant = []
    for code in cpt_codes:
        # Find local policy content
        local = next((g for g in CMS_GUIDELINES if g["code"] == code), None)

        # Find live CMS references
        live_refs = cms_context.get(code, [])

        block = f"CPT {code}:\n"

        if local:
            block += f"  Medical Necessity Policy: {local['description']}\n"
            block += f"  Local Source: {local['source']}\n"

        if live_refs:
            block += f"  Live CMS NCD References (api.coverage.cms.gov):\n"
            for ref in live_refs:
                block += (
                    f"    - {ref['title']} "
                    f"[NCD ID: {ref['document_display_id']}] "
                    f"Last Updated: {ref['last_updated']}\n"
                    f"      URL: {ref['url']}\n"
                )
        else:
            block += f"  CMS Source: Medicare Coverage Database (cms.gov)\n"

        relevant.append(block)

    if not relevant:
        return "No specific guidelines found. Apply general Medicare medical necessity standards."

    return "\n".join(relevant)