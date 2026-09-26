
import argparse
import copy
import json
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate, ValidationError
from openai import OpenAI


# I locate the repository root and load my environment variables
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MODEL = "gpt-5.6-luna"


# I load JSON files from the provided data folder
def load_json(filename):
    with open(ROOT / "data" / filename, "r", encoding="utf-8") as f:
        return json.load(f)


chat_script = load_json("chat_script.json")
memory_schema = load_json("memory_state.schema.json")
policy = load_json("policy.json")

conversation = chat_script["conversation"]
probes = chat_script["probes"]


# I use the same grant-office context in both memory modes
MEMORY_SYSTEM_PROMPT = f"""
You are a grant-office assistant helping one applicant across a conversation.

Use information stated earlier in the conversation when answering later
questions.

GRANT POLICY:
{json.dumps(policy, ensure_ascii=False, indent=2)}

Important:
- Do not invent facts.
- Remember the applicant's identity and file details.
- Preserve constraints such as available days.
- Preserve unanswered questions.
- Distinguish what the applicant stated from what has actually been confirmed.
- Use the grant policy when the applicant asks about eligibility or amount.
- Answer the current question concisely.
"""


# I define how the earlier conversation must be compressed
COMPRESSION_PROMPT = f"""
Compress the earlier conversation into exactly one JSON object.

The JSON must follow this schema:

{json.dumps(memory_schema, ensure_ascii=False, indent=2)}

Rules:
- Return JSON only.
- Do not use Markdown or code fences.
- Do not invent information.
- ALWAYS include all seven required fields:
  applicant_id, topic, facts, decisions, constraints, open_questions, language.
- Never omit a required field.
- applicant_id must contain the applicant ID if it was established.
- If no applicant ID was established, applicant_id must be null.
- facts must contain information stated by the applicant.
- decisions must contain conclusions already established in the conversation.
- constraints must contain practical restrictions or conditions.
- open_questions must contain questions that were asked but not fully resolved.
- Preserve information that may be useful later.
- Use empty arrays instead of omitting fields.
"""


def compress_history(client, history):
    # I allow one repair attempt if the first structured state is invalid
    last_raw = None
    last_error = None
    last_tokens = 0

    for attempt in range(2):

        instructions = COMPRESSION_PROMPT

        if attempt == 1:
            instructions += f"""
The previous attempt was invalid.

Validation error:
{last_error}

Previous output:
{last_raw}

Repair the output.
Return a complete JSON object with every required field.
Return JSON only.
"""

        response = client.responses.create(
            model=MODEL,
            instructions=instructions,
            input=history
        )

        raw_state = response.output_text
        input_tokens = response.usage.input_tokens
        last_tokens = input_tokens

        parsed_state = None
        parsed = False
        schema_valid = False
        error = None

        try:
            parsed_state = json.loads(raw_state)
            parsed = True
        except json.JSONDecodeError as e:
            error = str(e)

        if parsed:
            try:
                validate(
                    instance=parsed_state,
                    schema=memory_schema
                )
                schema_valid = True
            except ValidationError as e:
                error = e.message

        if schema_valid:
            return {
                "raw": raw_state,
                "state": parsed_state,
                "parsed": True,
                "schema_valid": True,
                "input_tokens": input_tokens,
                "error": None
            }

        last_raw = raw_state
        last_error = error

    # I return the failed result after both attempts
    return {
        "raw": last_raw,
        "state": None,
        "parsed": False,
        "schema_valid": False,
        "input_tokens": last_tokens,
        "error": last_error
    }


def run_uncompressed(client):
    # I keep the complete conversation history in Mode A
    history = []
    call_records = []

    for position, turn in enumerate(conversation, start=1):

        # I skip the control command in the uncompressed mode
        if turn == "<compress>":
            continue

        history.append({
            "role": "user",
            "content": turn
        })

        response = client.responses.create(
            model=MODEL,
            instructions=MEMORY_SYSTEM_PROMPT,
            input=history
        )

        answer = response.output_text
        input_tokens = response.usage.input_tokens

        call_records.append({
            "position": position,
            "input_tokens": input_tokens,
            "answer": answer
        })

        history.append({
            "role": "assistant",
            "content": answer
        })

    return history, call_records


def run_compressed(client):
    # I begin Mode B with normal full-history conversation
    history = []
    call_records = []
    generated_state = None
    compression_result = None

    for position, turn in enumerate(conversation, start=1):

        # I perform a separate compression call at the control command
        if turn == "<compress>":

            compression_result = compress_history(
                client,
                history
            )

            call_records.append({
                "position": position,
                "type": "compression",
                "input_tokens": compression_result["input_tokens"],
                "answer": compression_result["raw"]
            })

            # I replace history only after successful validation
            if compression_result["schema_valid"]:

                generated_state = compression_result["state"]

                history = [
                    {
                        "role": "assistant",
                        "content": (
                            "Structured memory from the earlier conversation:\n"
                            + json.dumps(
                                generated_state,
                                ensure_ascii=False,
                                indent=2
                            )
                        )
                    }
                ]

            # If validation fails, I deliberately keep the old history
            continue

        history.append({
            "role": "user",
            "content": turn
        })

        response = client.responses.create(
            model=MODEL,
            instructions=MEMORY_SYSTEM_PROMPT,
            input=history
        )

        answer = response.output_text
        input_tokens = response.usage.input_tokens

        call_records.append({
            "position": position,
            "type": "conversation",
            "input_tokens": input_tokens,
            "answer": answer
        })

        history.append({
            "role": "assistant",
            "content": answer
        })

    return (
        history,
        call_records,
        generated_state,
        compression_result
    )


def run_probes(client, history):
    # I use a consistent format so the provided probe strings can be checked
    probe_prompt = MEMORY_SYSTEM_PROMPT + """
For the memory probes:
- Answer in English.
- Reuse terminology from the conversation and grant policy.
- Use "id card" for the identity document.
- Write monetary amounts with comma separators, for example "150,000 KZT".
"""

    results = []

    for probe in probes:

        # I keep every probe independent from the other probes
        probe_history = copy.deepcopy(history)

        probe_history.append({
            "role": "user",
            "content": probe["question"]
        })

        response = client.responses.create(
            model=MODEL,
            instructions=probe_prompt,
            input=probe_history
        )

        answer = response.output_text
        answer_lower = answer.lower()

        retrieved = any(
            expected.lower() in answer_lower
            for expected in probe["expect_contains"]
        )

        results.append({
            "id": probe["id"],
            "retrieved": retrieved,
            "answer": answer
        })

    return results


def print_scripted_results(
    calls_a,
    calls_b,
    probes_a,
    probes_b,
    state_b,
    compression_result
):
    # I align both modes with the 12 positions in the provided script
    tokens_a = {
        record["position"]: record["input_tokens"]
        for record in calls_a
    }

    tokens_b = {
        record["position"]: record["input_tokens"]
        for record in calls_b
    }

    print("\nTOKENS PER SCRIPT POSITION")
    print(
        f"{'Position':<12}"
        f"{'Mode A':<18}"
        f"{'Mode B':<18}"
    )

    for position in range(1, 13):

        if position == 10:
            a_text = "skipped"
        else:
            a_text = str(tokens_a[position])

        b_text = str(tokens_b[position])

        print(
            f"{position:<12}"
            f"{a_text:<18}"
            f"{b_text:<18}"
        )

    peak_a = max(
        record["input_tokens"]
        for record in calls_a
    )

    total_a = sum(
        record["input_tokens"]
        for record in calls_a
    )

    peak_b = max(
        record["input_tokens"]
        for record in calls_b
    )

    total_b = sum(
        record["input_tokens"]
        for record in calls_b
    )

    print("\nSUMMARY")
    print(
        f"Mode A | calls={len(calls_a)} | "
        f"peak={peak_a} | total={total_a}"
    )
    print(
        f"Mode B | calls={len(calls_b)} | "
        f"peak={peak_b} | total={total_b}"
    )

    print("\nCOMPRESSION")
    print(
        "Parsed:",
        compression_result["parsed"]
    )
    print(
        "Schema valid:",
        compression_result["schema_valid"]
    )

    if compression_result["error"]:
        print(
            "Compression error:",
            compression_result["error"]
        )

    print("\nGENERATED MEMORY STATE")
    if state_b is None:
        print("No valid state was generated.")
    else:
        print(
            json.dumps(
                state_b,
                indent=2,
                ensure_ascii=False
            )
        )

    print("\nMEMORY PROBES")

    for a_result, b_result in zip(
        probes_a,
        probes_b
    ):
        print(
            f"{a_result['id']} | "
            f"A={'PASS' if a_result['retrieved'] else 'FAIL'} | "
            f"B={'PASS' if b_result['retrieved'] else 'FAIL'}"
        )

        print(
            "  A:",
            a_result["answer"]
        )

        print(
            "  B:",
            b_result["answer"]
        )

    retrieved_a = sum(
        result["retrieved"]
        for result in probes_a
    )

    retrieved_b = sum(
        result["retrieved"]
        for result in probes_b
    )

    print(
        f"\nRetrieved | "
        f"Mode A={retrieved_a}/5 | "
        f"Mode B={retrieved_b}/5"
    )


def run_scripted():
    client = OpenAI()

    print("Running Mode A...")
    history_a, calls_a = run_uncompressed(client)

    print("Running Mode B...")
    (
        history_b,
        calls_b,
        state_b,
        compression_result
    ) = run_compressed(client)

    print("Running Mode A probes...")
    probes_a = run_probes(
        client,
        history_a
    )

    print("Running Mode B probes...")
    probes_b = run_probes(
        client,
        history_b
    )

    print_scripted_results(
        calls_a,
        calls_b,
        probes_a,
        probes_b,
        state_b,
        compression_result
    )


def interactive_mode():
    client = OpenAI()

    history = []
    last_input_tokens = None

    print("Interactive memory chat")
    print("Commands: compress, tokens, exit")
    print()

    while True:

        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_text:
            continue

        command = user_text.lower()

        if command in {"exit", "quit"}:
            print("Exiting.")
            break

        if command == "tokens":

            if last_input_tokens is None:
                print(
                    "No model call has been made yet."
                )
            else:
                print(
                    "Last call input tokens:",
                    last_input_tokens
                )

            continue

        if command == "compress":

            if not history:
                print(
                    "There is no conversation history to compress."
                )
                continue

            result = compress_history(
                client,
                history
            )

            last_input_tokens = result["input_tokens"]

            print(
                "Compression parsed:",
                result["parsed"]
            )

            print(
                "Compression schema valid:",
                result["schema_valid"]
            )

            if result["schema_valid"]:

                history = [
                    {
                        "role": "assistant",
                        "content": (
                            "Structured memory from the earlier conversation:\n"
                            + json.dumps(
                                result["state"],
                                ensure_ascii=False,
                                indent=2
                            )
                        )
                    }
                ]

                print("Structured memory:")
                print(
                    json.dumps(
                        result["state"],
                        indent=2,
                        ensure_ascii=False
                    )
                )

            else:
                # I keep the old history if compression fails
                print(
                    "Compression failed. "
                    "The original history was kept."
                )

                if result["error"]:
                    print(
                        "Error:",
                        result["error"]
                    )

            continue

        # I treat every other line as a normal applicant message
        history.append({
            "role": "user",
            "content": user_text
        })

        response = client.responses.create(
            model=MODEL,
            instructions=MEMORY_SYSTEM_PROMPT,
            input=history
        )

        answer = response.output_text
        last_input_tokens = response.usage.input_tokens

        history.append({
            "role": "assistant",
            "content": answer
        })

        print("Assistant:", answer)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run the interactive memory chat"
    )

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        run_scripted()


if __name__ == "__main__":
    main()
