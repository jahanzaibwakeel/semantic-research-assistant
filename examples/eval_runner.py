#!/usr/bin/env python
"""Run lightweight RAG regression checks against the API.

Set SRA_API_KEY to an API key with qa:read access.

Example:
    python examples/eval_runner.py evals/sample_rag_eval.json --output eval-results.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request


DEFAULT_API_URL = "http://localhost:8000/api"


class EvalError(RuntimeError):
    pass


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    score: float
    checks: dict[str, bool]
    answer: str
    source_count: int
    rewritten_query: str | None


def api_url(path: str) -> str:
    return f"{os.getenv('SRA_API_URL', DEFAULT_API_URL).rstrip('/')}{path}"


def api_key() -> str:
    value = os.getenv("SRA_API_KEY")
    if not value:
        raise EvalError("Set SRA_API_KEY before running evaluations.")
    return value


def post_json(path: str, body: dict) -> dict:
    req = request.Request(
        api_url(path),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "X-API-Key": api_key(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as response:
            return json.loads(response.read())
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise EvalError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise EvalError(f"Request failed: {exc.reason}") from exc


def run_case(case: dict, defaults: dict) -> CaseResult:
    merged = {**defaults, **case}
    payload = {
        "question": merged["question"],
        "document_id": merged.get("document_id"),
        "project_id": merged.get("project_id"),
        "document_type": merged.get("document_type"),
        "tags": merged.get("tags"),
        "mode": merged.get("mode", "hybrid"),
        "limit": merged.get("limit", 8),
        "rewrite_query": merged.get("rewrite_query", True),
        "min_score": merged.get("min_score"),
    }
    response = post_json("/qa/ask", payload)
    answer = response.get("answer", "")
    sources = response.get("sources", [])
    required_terms = [term.lower() for term in merged.get("required_answer_terms", [])]
    min_sources = int(merged.get("min_sources", 1))

    checks = {
        "has_answer": bool(answer.strip()),
        "min_sources": len(sources) >= min_sources,
        "required_terms": all(term in answer.lower() for term in required_terms),
    }
    passed_checks = sum(1 for passed in checks.values() if passed)
    return CaseResult(
        case_id=merged["id"],
        passed=all(checks.values()),
        score=round(passed_checks / len(checks), 3),
        checks=checks,
        answer=answer,
        source_count=len(sources),
        rewritten_query=response.get("rewritten_query"),
    )


def run_dataset(path: Path) -> dict:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    defaults = dataset.get("defaults", {})
    results = [run_case(case, defaults) for case in dataset.get("cases", [])]
    passed = sum(1 for result in results if result.passed)
    return {
        "name": dataset.get("name", path.stem),
        "case_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 3) if results else 0,
        "results": [result.__dict__ for result in results],
    }


def write_report(summary: dict, output: Path | None) -> None:
    if output is None:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return
    if output.suffix.lower() == ".md":
        lines = [
            f"# Evaluation Report: {summary['name']}",
            "",
            f"- Cases: {summary['case_count']}",
            f"- Passed: {summary['passed']}",
            f"- Failed: {summary['failed']}",
            f"- Pass rate: {summary['pass_rate']}",
            "",
            "| Case | Passed | Score | Sources | Checks |",
            "| --- | --- | ---: | ---: | --- |",
        ]
        for result in summary["results"]:
            checks = ", ".join(f"{name}={value}" for name, value in result["checks"].items())
            lines.append(f"| {result['case_id']} | {result['passed']} | {result['score']} | {result['source_count']} | {checks} |")
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Semantic Research Assistant RAG evaluations")
    parser.add_argument("dataset", help="Path to an evaluation dataset JSON file")
    parser.add_argument("--api-url", help="API base URL. Defaults to SRA_API_URL or http://localhost:8000/api")
    parser.add_argument("--output", help="Write JSON or Markdown report to this path")
    parser.add_argument("--fail-under", type=float, default=1.0, help="Exit non-zero when pass rate is below this value")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.api_url:
        os.environ["SRA_API_URL"] = args.api_url
    try:
        summary = run_dataset(Path(args.dataset))
        write_report(summary, Path(args.output) if args.output else None)
    except EvalError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0 if summary["pass_rate"] >= args.fail_under else 2


if __name__ == "__main__":
    raise SystemExit(main())
