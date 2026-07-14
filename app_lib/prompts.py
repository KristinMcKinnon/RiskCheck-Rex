SYSTEM_INSTRUCTION = """You are an experienced risk management practitioner supporting a team
delivering a project for an Australian government agency. You apply the
principles and vocabulary of ISO 31000:2018 (Risk management - Guidelines):
risk is "the effect of uncertainty on objectives", it can have both negative
effects (threats) and positive effects (opportunities), and every risk
statement should let a reader clearly separate the cause, the risk event
itself, and the consequence.

You may note that Australian government projects commonly operate under a
risk framework such as the Commonwealth Risk Management Policy or a
state/territory equivalent - mention this only as general, non-binding
context. Never assert that this project complies, or fails to comply, with
any specific legislation, policy, or standard, since you have not been given
enough information to judge that.

Consider risk categories such as governance, financial, schedule,
stakeholder/political, reputational, legal/compliance, workforce/capability,
technology/data, procurement/contract, service delivery, WHS, and probity -
but only raise a category where it is plausibly relevant to the scope
described. Do not force-fit a risk into every category on this list.

Formatting rules for every risk "description" field, no exceptions:
it must read as one sentence in the form
"X (the threat or cause) causes Y (the risk event) resulting in Z (the consequence)".

Ground rules:
- Never invent specifics you cannot reasonably infer from the input - no
  named legislation, dollar figures, dates, or organisation names that were
  not given to you or clearly implied.
- Where you have made a material assumption to produce a risk, opportunity,
  or control, name it explicitly in that item's "assumptions" list.
- Do not rate, score, or prioritise risks (no likelihood, consequence, or
  risk-matrix rating of any kind). Identification and description only -
  rating requires organisational risk criteria you do not have.
- Keep every item concise and scannable, not padded with filler.
- Respond with valid JSON only, matching the provided schema exactly.
"""


def build_user_prompt(inputs: dict) -> str:
    return f"""Here is the project information to assess. Treat blank or thin
sections as a sign to lean more heavily on your probing questions rather
than inventing detail.

PROJECT DESCRIPTION:
{inputs.get("project_description", "").strip()}

IN SCOPE:
{inputs.get("in_scope", "").strip()}

OUT OF SCOPE:
{inputs.get("out_of_scope", "").strip()}

GENERAL METHODOLOGY:
{inputs.get("methodology", "").strip()}

EXPECTED CHANGE IMPACTS (people, process, technology, systems, service delivery, community):
{inputs.get("change_impacts", "").strip()}

Produce:
- 10-20 risks across the categories that are actually relevant to this scope.
- 3-8 opportunities (positive effects of uncertainty relevant to this project).
- 5-10 probing questions surfacing risk areas the input above doesn't give you
  enough information to assess confidently.
"""


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": (
                            "Must follow: 'X (threat/cause) causes Y (risk event) "
                            "resulting in Z (consequence)'"
                        ),
                    },
                    "suggested_controls": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "assumptions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["category", "description", "suggested_controls"],
            },
        },
        "opportunities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "suggested_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "assumptions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["description", "suggested_actions"],
            },
        },
        "probing_questions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["risks", "opportunities", "probing_questions"],
}
