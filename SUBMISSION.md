# HW2 submission

**Name:** Timofeyeva Ulyana
**Student ID:** S23067472
**Group:** CSS4007-ENG-9
**Repository:** https://github.com/ylaway456-dot/HW2_Ulyana.git

## AI tool disclosure

> I used ChatGPT to clarify several assignment requirements, review parts of my
> prompts and Python code, and help with debugging and wording. I ran the
> experiments myself, checked the outputs, and used the actual results from my
> own runs in this submission.


## Sublab Easy — one task, four roles

### Decisions per role

One row per enquiry. In each cell I show the `decision` returned by my run.
✅ means that it agrees with `expected` in `data/enquiries.json`, while ❌ means
that the role changed the expected decision.

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted ✅ | granted ✅ | more_info ❌ | granted ✅ |
| E-02 | more_info ✅ | more_info ✅ | more_info ✅ | more_info ✅ |
| E-03 | refused ✅ | more_info ❌ | refused ✅ | refused ✅ |
| E-04 | refused ✅ | more_info ❌ | refused ✅ | refused ✅ |
| E-05 | granted ✅ | granted ✅ | more_info ❌ | granted ✅ |
| E-06 | granted ✅ | granted ✅ | more_info ❌ | granted ✅ |
| E-07 | granted ✅ | granted ✅ | more_info ❌ | granted ✅ |
| E-08 | not_found ✅ | not_found ✅ | not_found ✅ | not_found ✅ |
| E-09 | refused ✅ | more_info ❌ | refused ✅ | refused ✅ |
| E-10 | more_info ✅ | more_info ✅ | more_info ✅ | more_info ✅ |
| **agrees with `expected`** | 10/10 | 7/10 | 6/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | None | None |
| `decision` | E-03, E-04, E-09 under `front_desk`; E-01, E-05, E-06, E-07 under `auditor` | `front_desk`, `auditor` |
| `amount` | None | None |
| `missing_documents` | None | None |

The only structured field that moved in my final run was `decision`.

### Raw replies

**E-03 — front_desk**

    {"applicant_id":"A-203","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"The application cannot be granted because the recorded GPA is 2.4, below the minimum 2.67. The GPA would need to reach at least 2.67; income band and required documents meet the policy."}

**E-07 — bilingual_clerk**

    {"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"Сіз грантқа сәйкес келесіз: GPA көрсеткіші талаптан жоғары, табыс санатыңыз 1 және қажетті құжаттардың екеуі де тіркелген. Грант сомасы — 250 000 KZT."}

### Written answers

**1. Which fields are role-sensitive and which are not?**

In my final run, `decision` was the only role-sensitive structured field.
The `front_desk` role changed the decision on E-03, E-04 and E-09, while
the `auditor` changed it on E-01, E-05, E-06 and E-07. The fields `found`,
`amount` and `missing_documents` did not move on any enquiry. The
`bilingual_clerk` preserved all four structured fields relative to the
policy officer; its role-specific effect appeared only in the language
of the human-readable `reason`.

**2. Which enquiries are most sensitive to the role, and why those?**

E-03 tests a candidate whose GPA is below the required threshold. The
policy officer returns `refused`, while the front-desk instruction changes
this to `more_info` because that role is instructed not to issue a direct
refusal.

E-04 tests an ineligible income band and shows the same type of role effect.

E-07 tests language handling. The bilingual clerk preserves the policy
decision but gives the `reason` in Kazakh, while the auditor changes the
first-reading grant to `more_info`.

E-10 tests whether the model trusts the applicant's statement or the
official record. Although the applicant says that the ID card was uploaded,
the official record still shows it as missing, so the result remains
`more_info`.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?**

I would use the role paragraph to control the model's conversational
behaviour, but I would not use it as the final enforcement mechanism for
an important decision. A downstream program can read structured fields
such as `decision`, `amount` and `missing_documents`, but it cannot reliably
infer which role produced the record from those fields alone. Several roles
produced exactly the same structured output on some enquiries.

If the decision has real consequences, I would keep deterministic
eligibility rules in code and use the model mainly for interpretation and
explanation.

**4. Is a role a boundary?**

No. A role is not a hard boundary. In Week 2 terms, the role paragraph is
still natural-language input represented as tokens in the model's context.
It influences the model's output, but it does not enforce a rule in the
same way as deterministic program logic.

If a wrong `decision` were expensive, I would implement eligibility checks
in code, validate the returned JSON against a schema, compare important
fields with the official records, and reject or flag inconsistent outputs
instead of relying on the prompt alone.

---

## Sublab Medium — memory you choose

### Tokens per call

I treat the numbered rows below as positions in the provided conversation script.
In Mode A, position 10 (`<compress>`) is a control command and therefore no API
call is made there. In Mode B, position 10 is the separate compression API call.

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 326 | 326 |
| 2 | 383 | 393 |
| 3 | 487 | 516 |
| 4 | 572 | 604 |
| 5 | 647 | 655 |
| 6 | 758 | 731 |
| 7 | 852 | 817 |
| 8 | 944 | 906 |
| 9 | 1018 | 982 |
| 10 | — skipped | 1214 |
| 11 | 1108 | 648 |
| 12 | 1273 | 790 |
| **peak** | 1273 | 1214 |
| **total for the run** | 8368 | 8582 |

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | ✅ | You are **Daniyar Qoshan**, applicant **A-202**. | ✅ | You are **Daniyar Qoshan**, applicant **A-202**. |
| Q-2 missing document | turn 5 | ✅ | Your **id card** is still missing from your file. | ✅ | The **id card** is still missing from your file; you could not upload it because your home scanner broke. |
| Q-3 band and amount | turns 3–4 | ✅ | You stated that your income band is **2**, but it has not been officially confirmed in the record. If band 2 is verified and you meet the other requirements, the grant amount is **150,000 KZT**. | ✅ | You stated that your family's certificate shows **income band 2**. If that band is confirmed in the record, the grant amount is **150,000 KZT**. |
| Q-4 the constraint | turn 6 | ✅ | You can come to the office on **Thursdays**. | ✅ | You can come to the office on **Thursdays**. |
| Q-5 the open question | turn 7 | ✅ | You asked whether a **scanned letter from your employer** would count or whether the **original** was required. I said the policy does not specify the acceptable format and advised confirming with the office. | ✅ | You asked whether a **scanned letter from your employer** is accepted as proof of income, or whether the **original** is required. |
| **retrieved** | | 5/5 | | 5/5 | |

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Study grant eligibility and application documents",
  "facts": [
    "The applicant's name is Daniyar Qoshan.",
    "The applicant stated that they sent their transcript last week.",
    "The applicant stated that their family's certificate shows income band 2.",
    "The applicant could not upload their ID card because their home scanner broke.",
    "The applicant can come to the office only on Thursdays because they have lab classes all week otherwise.",
    "The applicant stated that their sister, Aruzhan, applied last year and is on file."
  ],
  "decisions": [
    "Eligibility has not been confirmed.",
    "If eligibility is confirmed, the grant amount for income band 2 is 150,000 KZT."
  ],
  "constraints": [
    "Eligibility requires a confirmed GPA of at least 2.67.",
    "Eligibility requires a confirmed income band of 1 or 2.",
    "The transcript and ID card must be on file.",
    "The applicant can submit the ID card at the office only on Thursdays.",
    "The processing timeline for a decision is not specified."
  ],
  "open_questions": [
    "Does the applicant qualify for the study grant?",
    "Is a scanned letter from the employer accepted as proof of income, or is the original required?",
    "If the applicant brings the ID card on Thursday, will the decision be made the same day?"
  ],
  "language": "English"
}
```

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> In my final program run, Mode A reached a peak of **1273 input tokens** and
> used **8368 input tokens** in total. Mode B reached a slightly lower peak of
> **1214 input tokens**, but used **8582 input tokens** in total. Therefore,
> compression reduced the peak by **59 tokens** (about **4.6%**), but increased
> total input usage by **214 tokens** (about **2.6%**) because the separate
> compression call itself was relatively expensive. Both modes retrieved
> **5/5 probes**, so no tested memory was lost. In this short conversation,
> compression improved the size of the later context but did not yet pay for
> its own compression cost.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

> A structured state makes different kinds of memory explicit. For example,
> `facts`, `decisions`, `constraints`, and `open_questions` have different
> meanings and can be handled separately by the program. The JSON object can
> also be validated automatically against a schema. A free-form paragraph
> may contain the same information, but the program cannot reliably tell
> whether an applicant ID, unresolved question, or constraint was omitted or
> mixed with another type of information. Structured memory therefore makes
> the compressed context easier to validate, inspect, and reuse.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

> I would add provenance, such as a `source_turn` or evidence reference for
> each important memory item. That would make it possible to see where a fact
> came from and distinguish a direct applicant statement from a model-derived
> conclusion. To pay for that extra information, I would drop low-value details
> such as the fact that the applicant's sister Aruzhan applied last year. I
> would also avoid storing general policy requirements inside `constraints`
> when those rules are already available in the system prompt.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

> Compression is a poor choice when the exact wording, chronology, or complete
> evidence may matter later. For example, in an appeal or dispute about a grant
> decision, an exact earlier statement could become important. Once the
> original history is discarded, a detail omitted by the summary cannot be
> recovered from the compressed state. My program would detect malformed JSON
> or a schema-invalid state, but it would not necessarily notice a semantically
> incomplete summary that still satisfies the schema. Schema validation checks
> structure, not whether every important detail was preserved.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | Yes | Yes | None | None |
| story-02 | Yes | Yes | graduation_year, gpa_original_value, gpa_original_scale, gpa_4_scale | No GPA stated |
| story-03 | Yes | Yes | None | GPA on another scale; under-review paper not counted |
| story-04 | Yes | Yes | None | Under-review and in-preparation papers not counted |
| story-05 | Yes | Yes | None | Paper still being written was not counted as published |
| story-06 | Yes | Yes | graduation_year, gpa_original_value, gpa_original_scale, gpa_4_scale | Contradictory GPA and graduation information |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Paste the extraction for **story-06**, the one that contradicts itself:

```json
{
  "candidate_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_original_value": null,
  "gpa_original_scale": null,
  "gpa_4_scale": null,
  "languages": [
    "Kazakh",
    "Russian",
    "English"
  ],
  "published_peer_reviewed_outputs": 1,
  "non_published_outputs": [
    "One poster at a local event"
  ],
  "relevant_experience_months": 40,
  "uncountable_experience": [],
  "ambiguities": [
    "GPA is contradicted: the story states 3.2 and 3.5.",
    "Graduation information is contradicted: the story states graduation in 2024 and also says the candidate is a final-year student graduating in 2026."
  ],
  "evidence": {
    "candidate_id": "CANDIDATE ID: story-06",
    "full_name": "# Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "languages": "Languages: Kazakh, Russian, English.",
    "published_peer_reviewed_outputs": "one paper published, in a peer-reviewed proceedings, on survey weighting",
    "non_published_outputs": "One poster at a local event, which I do not think counts.",
    "relevant_experience_months": "I have been at an insurance analytics team since February 2023, which is about forty months."
  }
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 | 5 | 5 | 2 | 4.40 |
| story-02 | 0 | 1 | 5 | 1.30 |
| story-03 | 4 | 2.5 | 3 | 3.35 |
| story-04 | 4 | 2.5 | 5 | 3.75 |
| story-05 | 5 | 2.5 | 1.25 | 3.50 |
| story-06 | 0 | 2.5 | 5 | 1.75 |

**Winner, computed by my code:** `story-01` with a weighted total of **4.40**

**The model's prose answer, asked separately ("who should win?"):**

> **Aziza Bekova** should win the scholarship. She has a clearly stated 3.8 GPA on a 4.0 scale, meeting the rubric’s strongest academic benchmark, and two published peer-reviewed outputs, which is the top research category. Although she has only eight months of relevant experience, the scholarship’s heavier academic and research weights make her the strongest overall candidate.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> I had to make the contradiction rule explicit: when a story gives
> conflicting values for the same field, I return `null`, record the conflict
> in `ambiguities`, and do not choose or average the values. `story-06` forced
> this rule because it gives both 3.2 and 3.5 for GPA and also says both that
> the candidate graduated in 2024 and is graduating in 2026. Without the rule,
> the model could silently choose one value and create a cleaner but unsupported
> record.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> The model had to use judgement where the rubric did not fully specify an
> intermediate score. In my final run, `story-02` received a research score
> of 1 for one published output, while several other candidates with one
> published output received 2.5. This shows that an under-specified rubric can
> lead to different model interpretations even when the extracted publication
> count is clear. My code did not make that judgement. Once the three criterion
> scores were returned, it deterministically applied
> `0.5 * academic + 0.3 * research + 0.2 * experience`, rounded the result to
> two decimals, and selected the highest weighted total.

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> Yes. Both methods selected `story-01`, Aziza Bekova. My Python ranking gave
> her a weighted total of **4.40**, and the separate prose answer also chose
> her. I trust the code-computed ranking more for the final arithmetic because
> it is reproducible and applies the stated weights exactly. However, the
> criterion scores themselves still come from the model. Agreement in one run
> is not enough for me to trust the prose ranking alone; I would want stable
> results across repeated runs, explicit evidence for each criterion, and a
> deterministic recalculation of the weighted score.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

> I did not resolve or average the contradictory GPA in `story-06`. During
> extraction, I set the GPA fields to `null` and recorded the contradiction in
> `ambiguities`. In my scoring run, the model then returned an academic score
> of **0**. I kept that as the observed result, but the rubric does not actually
> define 0 as the correct consequence of a contradictory GPA. I think the rule
> should explicitly send a contradicted academic field to manual review or
> mark the criterion as unscored until the contradiction is resolved. If the
> system requires a numeric score, the rubric should state that numeric fallback
> explicitly rather than leaving the model to infer one.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> My top two candidates were not within 0.05. `story-01` scored **4.40** and
> `story-04` scored **3.75**, so the gap was **0.65**. Therefore, this run did
> not produce a near-tie. If the gap had been within 0.05, I would tell the
> committee that the ranking was too sensitive to uncertain intermediate
> rubric scores to treat the order as decisive. I would strengthen the
> extraction by attaching source evidence or source-turn provenance to every
> scored field and require manual review of ambiguous evidence before making
> the final choice.

---

## Reflection (optional, one short paragraph)

> After completing the three sublabs, I would separate model judgement from
> deterministic validation more clearly. I would use strict schemas, preserve
> source evidence for important extracted facts, and keep calculations and
> high-impact rules in code instead of relying only on prompts. I also learned
> that compression is not automatically cheaper: in my short conversation it
> reduced the later context size but the compression call itself added cost.
> For reliable structured output, I would combine clear prompts with schema
> validation, explicit ambiguity handling, and deterministic post-processing.
