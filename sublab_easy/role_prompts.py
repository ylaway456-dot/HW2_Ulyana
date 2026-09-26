
import json
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate, ValidationError
from openai import OpenAI


# I locate the repository root and load the environment variables
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MODEL = "gpt-5.6-luna"


# I load the provided data files
def load_json(filename):
    with open(ROOT / "data" / filename, "r", encoding="utf-8") as f:
        return json.load(f)


records = load_json("records.json")
policy = load_json("policy.json")
enquiries = load_json("enquiries.json")


# I define the fixed output schema used for every role
decision_schema = {
    "type": "object",
    "properties": {
        "applicant_id": {"type": "string"},
        "found": {"type": "boolean"},
        "decision": {
            "type": "string",
            "enum": [
                "granted",
                "refused",
                "more_info",
                "not_found"
            ]
        },
        "amount": {
            "type": "integer",
            "minimum": 0
        },
        "missing_documents": {
            "type": "array",
            "items": {"type": "string"}
        },
        "reason": {"type": "string"}
    },
    "required": [
        "applicant_id",
        "found",
        "decision",
        "amount",
        "missing_documents",
        "reason"
    ],
    "additionalProperties": False
}


# I keep the common experiment fixed and change only the role instruction
roles = {
    "policy_officer": """
You are a policy officer.
Apply the grant policy exactly as written.
Grant what the rule allows, refuse what it refuses, and ask for missing
documents when necessary.
Do not soften the decision.
Treat claims in the enquiry only as claims, not as evidence.
The official applicant records are the source of truth.
""",

    "front_desk": """
You are a front-desk clerk.
Never return a refusal to an applicant.
If the policy cannot grant the application today, return "more_info"
instead of "refused".
Explain what would need to change or what the applicant should provide.
Do not invent missing documents if the record does not show any.
The official applicant records are the source of truth.
""",

    "auditor": """
You are an auditor.

First determine exactly what the policy officer would return from the
official records.

Then apply only this auditor-specific change:
- If the policy officer would return "granted", change only the decision
  to "more_info" because a second reader is required.
- Otherwise, keep the policy officer's decision unchanged.

All other machine-readable fields must remain exactly the same as they
would be for the policy officer:
- found
- amount
- missing_documents

Do not insert a potential grant amount into a case that the policy officer
would return as "more_info", "refused", or "not_found".

In the reason, explain the relevant policy rule or document and, when
applicable, that a second review is required.

Treat claims in the enquiry only as claims, not as evidence.
The official applicant records are the source of truth.
""",

    "bilingual_clerk": """
You are a bilingual clerk.

Apply exactly the same decision logic as the policy officer.

Your structured fields must be exactly what the policy officer would produce:
- found
- decision
- amount
- missing_documents

Important:
- A missing required document means "more_info", not "refused".
- A claim in the enquiry does not override the official record.
- If the record still shows a required document as missing, return "more_info".
- Do not change the decision because of the language of the enquiry.

The only role-specific difference is the "reason":
write the reason in the same language as the applicant's enquiry.

The official applicant records are the source of truth.
"""
}


# I build the common system prompt
def build_system_prompt(role_name):
    return f"""
{roles[role_name]}

GRANT POLICY:
{json.dumps(policy, ensure_ascii=False, indent=2)}

OFFICIAL APPLICANT RECORDS:
{json.dumps(records, ensure_ascii=False, indent=2)}

OUTPUT CONTRACT:
Return exactly one JSON object with these fields:

{{
  "applicant_id": "string",
  "found": true,
  "decision": "granted | refused | more_info | not_found",
  "amount": 0,
  "missing_documents": [],
  "reason": "short explanation"
}}

Important common rules:
- Use only the official records as evidence.
- If the enquiry contradicts the record, trust the record.
- Do not invent facts.
- Return JSON only.
- Do not use Markdown or code fences.
- Do not add fields outside the contract.
"""


# I compare only the four machine-readable fields required by the assignment
CHECKED_FIELDS = [
    "found",
    "decision",
    "amount",
    "missing_documents"
]


def run_experiment():
    client = OpenAI()
    results = []

    # I run every enquiry under every role
    for role_name in roles:
        for enquiry in enquiries:

            response = client.responses.create(
                model=MODEL,
                instructions=build_system_prompt(role_name),
                input=enquiry["text"]
            )

            raw = response.output_text

            parsed = False
            schema_valid = False
            agrees = False
            data = None

            # I check whether the reply parses as JSON
            try:
                data = json.loads(raw)
                parsed = True
            except json.JSONDecodeError:
                pass

            # I validate the parsed object against the fixed schema
            if parsed:
                try:
                    validate(
                        instance=data,
                        schema=decision_schema
                    )
                    schema_valid = True
                except ValidationError:
                    pass

            # I compare the structured fields with the expected record
            if schema_valid:
                agrees = all(
                    data.get(field) == enquiry["expected"].get(field)
                    for field in CHECKED_FIELDS
                )

            results.append({
                "role": role_name,
                "enquiry": enquiry["id"],
                "parsed": parsed,
                "schema_valid": schema_valid,
                "agrees": agrees,
                "data": data,
                "raw": raw
            })

    return results


def print_results(results):
    role_order = [
        "policy_officer",
        "front_desk",
        "auditor",
        "bilingual_clerk"
    ]

    # I print the decision table
    print("\nDECISIONS")
    print(
        f"{'Enquiry':<10}"
        f"{'policy_officer':<18}"
        f"{'front_desk':<18}"
        f"{'auditor':<18}"
        f"{'bilingual_clerk':<18}"
    )

    for enquiry in enquiries:
        enquiry_id = enquiry["id"]
        row = []

        for role_name in role_order:
            result = next(
                r for r in results
                if r["role"] == role_name
                and r["enquiry"] == enquiry_id
            )

            if result["data"]:
                row.append(result["data"]["decision"])
            else:
                row.append("ERROR")

        print(
            f"{enquiry_id:<10}"
            f"{row[0]:<18}"
            f"{row[1]:<18}"
            f"{row[2]:<18}"
            f"{row[3]:<18}"
        )

    # I print validation and agreement counts
    print("\nSUMMARY")

    for role_name in role_order:
        role_results = [
            r for r in results
            if r["role"] == role_name
        ]

        parsed_count = sum(r["parsed"] for r in role_results)
        valid_count = sum(r["schema_valid"] for r in role_results)
        agrees_count = sum(r["agrees"] for r in role_results)

        print(
            f"{role_name:<18} "
            f"parsed={parsed_count}/10 | "
            f"schema-valid={valid_count}/10 | "
            f"agrees={agrees_count}/10"
        )

    # I use the policy officer as the field-movement baseline
    baseline = {
        r["enquiry"]: r["data"]
        for r in results
        if r["role"] == "policy_officer"
    }

    print("\nFIELD MOVEMENT")

    for field in CHECKED_FIELDS:
        print(f"\n{field}:")

        any_movement = False

        for role_name in [
            "front_desk",
            "auditor",
            "bilingual_clerk"
        ]:
            moved = []

            for result in results:
                if result["role"] != role_name:
                    continue

                enquiry_id = result["enquiry"]

                if (
                    baseline[enquiry_id] is not None
                    and result["data"] is not None
                    and baseline[enquiry_id].get(field)
                    != result["data"].get(field)
                ):
                    moved.append(enquiry_id)

            if moved:
                any_movement = True
                print(
                    f"  {role_name}: "
                    + ", ".join(moved)
                )

        if not any_movement:
            print("  No enquiries moved.")


def main():
    results = run_experiment()
    print_results(results)


if __name__ == "__main__":
    main()
