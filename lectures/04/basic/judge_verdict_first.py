"""Basic experiment (judgment order): same as app.judge, but CriterionVerdict asks for verdict BEFORE reason.

Only the field order of the structured-output schema changes. Run from the repo root:
    uv run python lectures/04/basic/judge_verdict_first.py --out lectures/04/basic/order_verdict_first_r1.json
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pydantic import BaseModel, Field  # noqa: E402

from app import judge  # noqa: E402


class CriterionVerdict(BaseModel):
    """Judgment for one criterion. Verdict first, then reason (order swapped for the experiment)."""

    verdict: judge.Verdict = Field(description="One of pass / fail / unsure")
    reason: str = Field(description="Reason for the judgment, in one or two English sentences")


class JudgeResult(BaseModel):
    grounding: CriterionVerdict = Field(description=judge.JudgeResult.model_fields["grounding"].description)
    scope: CriterionVerdict = Field(description=judge.JudgeResult.model_fields["scope"].description)
    hint: CriterionVerdict = Field(description=judge.JudgeResult.model_fields["hint"].description)
    clarity: CriterionVerdict = Field(description=judge.JudgeResult.model_fields["clarity"].description)


judge.CriterionVerdict = CriterionVerdict
judge.JudgeResult = JudgeResult

if __name__ == "__main__":
    judge.main()
