
import json
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate, ValidationError
from openai import OpenAI


# I locate the repository root and load my environment variables
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MODEL = "gpt-5.6-luna"


# I load the official scoring rubric
with open(
    ROOT / "data" / "candidate_rubric.json",
    "r",
    encoding="utf-8"
) as f:
    candidate_rubric = json.load(f)


# I load all six candidate stories
candidate_files = sorted(
    (ROOT / "data" / "candidates").glob("story-*.md")
)

stories = {
    path.stem: path.read_text(encoding="utf-8")
    for path in candidate_files
}


# I define the structured record expected from extraction
candidate_schema = {
    "type": "object",
    "properties": {
        "candidate_id": {
            "type": "string"
        },
        "full_name": {
            "type": ["string", "null"]
        },
        "degree": {
            "type": ["string", "null"]
        },
        "graduation_year": {
            "type": ["integer", "null"]
        },
        "gpa_original_value": {
            "type": ["number", "null"]
        },
        "gpa_original_scale": {
            "type": ["number", "null"]
        },
        "gpa_4_scale": {
            "type": ["number", "null"]
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "published_peer_reviewed_outputs": {
            "type": "integer",
            "minimum": 0
        },
        "non_published_outputs": {
            "type": "array",
            "items": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "object"}
                ]
            }
        },
        "relevant_experience_months": {
            "type": ["integer", "null"],
            "minimum": 0
        },
        "uncountable_experience": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "ambiguities": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "evidence": {
            "type": "object"
        }
    },
    "required": [
        "candidate_id",
        "full_name",
        "degree",
        "graduation_year",
        "gpa_original_value",
        "gpa_original_scale",
        "gpa_4_scale",
        "languages",
        "published_peer_reviewed_outputs",
        "non_published_outputs",
        "relevant_experience_months",
        "uncountable_experience",
        "ambiguities",
        "evidence"
    ],
    "additionalProperties": False
}


# I define the three scoring fields returned by the model
score_schema = {
    "type": "object",
    "properties": {
        "academic": {
            "type": "number",
            "minimum": 0,
            "maximum": 5
        },
        "research": {
            "type": "number",
            "minimum": 0,
            "maximum": 5
        },
        "experience": {
            "type": "number",
            "minimum": 0,
            "maximum": 5
        }
    },
    "required": [
        "academic",
        "research",
        "experience"
    ],
    "additionalProperties": False
}


# I place the assignment extraction rules directly in the prompt
EXTRACTION_PROMPT = """
You extract structured scholarship candidate data from one written story.

Return exactly one JSON object and nothing else.

Follow these rules strictly:

1. UNKNOWN FACTS
If the story does not explicitly state a fact, return null for that field.
Never estimate or infer a missing GPA, graduation year, degree, or experience.

2. GPA CONVERSION
If the GPA is stated on a scale other than 4.0, convert it proportionally to
a 4.0 scale using:

gpa_4_scale = original_gpa / original_scale * 4.0

Round the converted GPA to two decimal places.
Always preserve the original GPA value and original scale.

If no GPA is stated, all GPA value fields must be null.

3. PUBLICATIONS
Count a peer-reviewed output as published only if the story explicitly says
it is published or accepted.

Do NOT count:
- submitted
- under review
- in preparation
- in press
- planned

Record those separately in non_published_outputs.
Prefer plain strings in non_published_outputs, for example:
"Second paper — under review".
Do not invent any metadata that is not present in the story.

4. CONTRADICTIONS
If the story contradicts itself about a field, do not choose one value and
do not average the values.

Return null for the contradicted field and describe the contradiction in
ambiguities.

5. EXPERIENCE
Count months of relevant work or internship.
If periods overlap, count overlapping months only once.
If a period has no countable duration, record it in uncountable_experience.

6. EVIDENCE
For every non-null or non-empty extracted field, include a short evidence
quote or evidence phrase from the story in the evidence object.

Use exactly this JSON structure:

{
  "candidate_id": "story-01",
  "full_name": "string or null",
  "degree": "string or null",
  "graduation_year": 2025,
  "gpa_original_value": 3.8,
  "gpa_original_scale": 4.0,
  "gpa_4_scale": 3.8,
  "languages": [],
  "published_peer_reviewed_outputs": 0,
  "non_published_outputs": [],
  "relevant_experience_months": 0,
  "uncountable_experience": [],
  "ambiguities": [],
  "evidence": {}
}

Do not add fields outside this structure.
"""


# I use the same official rubric for every candidate
SCORING_PROMPT = f"""
Score one scholarship candidate using the official rubric below.

OFFICIAL RUBRIC:
{json.dumps(candidate_rubric, ensure_ascii=False, indent=2)}

Return exactly one JSON object with only these fields:

{{
  "academic": 0,
  "research": 0,
  "experience": 0
}}

Rules:
- Each score must be between 0 and 5.
- Follow the rubric and its counting rules.
- Use only the structured candidate record provided.
- Do not invent missing information.
- If GPA is missing, follow the rubric rule that academic scores 0.
- If a field is null because of a contradiction, do not resolve or average it.
- Use remaining valid evidence when the rubric has no explicit intermediate anchor.
- Do not calculate the weighted total.
- Do not choose a winner.
- Do not provide explanations.
- Return JSON only.
"""


def extract_candidate(client, story_id, story_text):
    # I ask the model to extract one structured candidate record
    response = client.responses.create(
        model=MODEL,
        instructions=EXTRACTION_PROMPT,
        input=(
            f"CANDIDATE ID: {story_id}\n\n"
            f"STORY:\n{story_text}"
        )
    )

    raw = response.output_text

    parsed = False
    schema_valid = False
    data = None
    error = None

    # I parse the model response as JSON
    try:
        data = json.loads(raw)
        parsed = True
    except json.JSONDecodeError as e:
        error = str(e)

    # I validate the extracted candidate
    if parsed:
        try:
            validate(
                instance=data,
                schema=candidate_schema
            )
            schema_valid = True
        except ValidationError as e:
            error = e.message

    return {
        "story": story_id,
        "parsed": parsed,
        "schema_valid": schema_valid,
        "data": data,
        "raw": raw,
        "error": error
    }


def score_candidate(client, candidate):
    # I ask the model only for the three rubric scores
    response = client.responses.create(
        model=MODEL,
        instructions=SCORING_PROMPT,
        input=json.dumps(
            candidate,
            ensure_ascii=False,
            indent=2
        )
    )

    raw = response.output_text

    parsed = False
    schema_valid = False
    data = None
    error = None

    try:
        data = json.loads(raw)
        parsed = True
    except json.JSONDecodeError as e:
        error = str(e)

    if parsed:
        try:
            validate(
                instance=data,
                schema=score_schema
            )
            schema_valid = True
        except ValidationError as e:
            error = e.message

    return {
        "parsed": parsed,
        "schema_valid": schema_valid,
        "data": data,
        "raw": raw,
        "error": error
    }


def weighted_total(scores):
    # I calculate the official weighted total in Python
    return round(
        0.5 * scores["academic"]
        + 0.3 * scores["research"]
        + 0.2 * scores["experience"],
        2
    )


def prose_ranking(client, candidates):
    # I make a separate prose ranking call only for comparison
    prompt = f"""
Here are six structured scholarship candidate records and the official rubric.

OFFICIAL RUBRIC:
{json.dumps(candidate_rubric, ensure_ascii=False, indent=2)}

CANDIDATES:
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Which candidate should win the scholarship?

Answer in prose.
Name the candidate and briefly explain your reasoning.

Do not use or refer to Python weighted totals.
"""

    response = client.responses.create(
        model=MODEL,
        input=prompt
    )

    return response.output_text


def main():
    client = OpenAI()

    extracted_candidates = {}
    extraction_results = []

    print("EXTRACTION")
    print()

    # I extract and validate all six candidate records
    for story_id in sorted(stories.keys()):

        result = extract_candidate(
            client,
            story_id,
            stories[story_id]
        )

        extraction_results.append(result)

        print(
            f"{story_id} | "
            f"parsed={result['parsed']} | "
            f"schema-valid={result['schema_valid']}"
        )

        if result["schema_valid"]:
            extracted_candidates[story_id] = result["data"]

        else:
            print(
                "  ERROR:",
                result["error"]
            )

    print()

    # I stop scoring if an extraction did not validate
    if len(extracted_candidates) != len(stories):
        print(
            "Not all candidates produced valid structured records. "
            "Ranking was not performed."
        )
        return

    print("EXTRACTION SUMMARY")
    print()

    for story_id in sorted(extracted_candidates.keys()):

        candidate = extracted_candidates[story_id]

        print(
            f"{story_id} | "
            f"name={candidate['full_name']} | "
            f"GPA={candidate['gpa_4_scale']} | "
            f"published={candidate['published_peer_reviewed_outputs']} | "
            f"experience={candidate['relevant_experience_months']}"
        )

        if candidate["ambiguities"]:
            print(
                "  ambiguities:",
                candidate["ambiguities"]
            )

    print()
    print("STORY-06 FULL EXTRACTION")
    print()

    print(
        json.dumps(
            extracted_candidates["story-06"],
            indent=2,
            ensure_ascii=False
        )
    )

    print()
    print("SCORING")
    print()

    ranking = []

    # I obtain the model scores and compute totals myself
    for story_id in sorted(extracted_candidates.keys()):

        result = score_candidate(
            client,
            extracted_candidates[story_id]
        )

        if not result["schema_valid"]:
            print(
                f"{story_id} | scoring failed | "
                f"{result['error']}"
            )
            return

        scores = result["data"]

        total = weighted_total(scores)

        ranking.append({
            "candidate": story_id,
            "academic": scores["academic"],
            "research": scores["research"],
            "experience": scores["experience"],
            "weighted_total": total
        })

        print(
            f"{story_id} | "
            f"academic={scores['academic']} | "
            f"research={scores['research']} | "
            f"experience={scores['experience']} | "
            f"total={total:.2f}"
        )

    # I sort only after the deterministic totals are computed
    ranking.sort(
        key=lambda row: row["weighted_total"],
        reverse=True
    )

    print()
    print("RANKING")
    print()

    for position, row in enumerate(ranking, start=1):
        print(
            f"{position}. "
            f"{row['candidate']} | "
            f"{row['weighted_total']:.2f}"
        )

    winner = ranking[0]

    print()
    print(
        "Winner computed by Python:",
        winner["candidate"]
    )

    print(
        "Weighted total:",
        f"{winner['weighted_total']:.2f}"
    )

    # I ask separately for a prose judgement
    prose_answer = prose_ranking(
        client,
        extracted_candidates
    )

    print()
    print("SEPARATE PROSE RANKING")
    print()
    print(prose_answer)


if __name__ == "__main__":
    main()
