import os
from openai import OpenAI
from dotenv import load_dotenv
from utils.prompts import FWA_AGENT_PROMPT
from data.cms_guidelines import get_relevant_guidelines

load_dotenv()

def run_fwa_agent(case: dict, clinical_summary: str) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    cms_context = get_relevant_guidelines(case["submitted_cpt_codes"])
    
    prompt = FWA_AGENT_PROMPT.format(
        clinical_summary=clinical_summary,
        cms_guidelines=cms_context,
        provider_name=case["provider_name"],
        provider_specialty=case["provider_specialty"],
        cpt_codes=", ".join(case["submitted_cpt_codes"]),
        icd_codes=", ".join(case["submitted_icd_codes"]),
        billed_amount=case["billed_amount"]
    )
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an FWA detection specialist. Always cite specific CMS guidelines when flagging codes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1024
    )
    return response.choices[0].message.content