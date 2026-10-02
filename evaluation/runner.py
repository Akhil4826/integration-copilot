"""AI Evaluation Runner for benchmarking Tool Selection, Confirmation Compliance, and Safety."""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.agent.agent import AgentService
from app.agent.schemas import AgentRequest, AgentStatus
from app.llm.mock_provider import MockLLMProvider
from app.llm.ollama_provider import OllamaProvider


class EvaluationRunner:
    def __init__(self, cases_file: str, provider_name: str = "mock"):
        self.cases_file = cases_file
        self.provider_name = provider_name

        if provider_name == "ollama":
            llm = OllamaProvider()
        else:
            llm = MockLLMProvider()

        self.agent = AgentService(llm_provider=llm)

    def load_cases(self) -> List[Dict[str, Any]]:
        with open(self.cases_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("cases", [])

    async def run(self) -> Dict[str, Any]:
        cases = self.load_cases()
        print("\n=======================================================")
        print("  INTEGRATION COPILOT — AI EVALUATION SUITE")
        print(f"  Provider: {self.provider_name.upper()} | Benchmark Cases: {len(cases)}")
        print("=======================================================\n")

        total_cases = len(cases)
        passed_cases = 0
        tool_selection_matches = 0
        confirmation_compliance_matches = 0
        anti_hallucination_matches = 0
        results = []

        total_start = time.perf_counter()

        for case in cases:
            c_id = case["id"]
            name = case["name"]
            query = case["query"]
            exp_tool = case.get("expected_tool")
            req_conf = case.get("requires_confirmation", False)
            anti_hal = case.get("anti_hallucination_check", False)

            print(f"[{c_id}] Running: '{name}'...")
            t0 = time.perf_counter()
            resp = await self.agent.run(AgentRequest(message=query))
            dur_ms = (time.perf_counter() - t0) * 1000

            # 1. Evaluate tool selection
            called_tools = [t.tool for t in resp.tool_trace]
            if resp.confirmation_request:
                called_tools.append(resp.confirmation_request.tool_name)

            tool_match = exp_tool in called_tools if exp_tool else True
            if tool_match:
                tool_selection_matches += 1

            # 2. Evaluate confirmation compliance
            if req_conf:
                conf_match = (
                    resp.status == AgentStatus.AWAITING_CONFIRMATION
                    and resp.confirmation_request is not None
                    and resp.confirmation_request.tool_name == exp_tool
                )
            else:
                conf_match = resp.status != AgentStatus.AWAITING_CONFIRMATION

            if conf_match:
                confirmation_compliance_matches += 1

            # 3. Evaluate anti-hallucination
            hal_passed = True
            if anti_hal:
                # Response must convey not found and not fabricate details
                lower_msg = resp.message.lower()
                hal_passed = any(
                    term in lower_msg
                    for term in [
                        "not found",
                        "error",
                        "no matching",
                        "cannot find",
                        "does not exist",
                    ]
                )
                if hal_passed:
                    anti_hallucination_matches += 1

            # Overall case pass
            case_passed = tool_match and conf_match and hal_passed
            if case_passed:
                passed_cases += 1
                status_icon = "PASS"
            else:
                status_icon = "FAIL"

            print(f"      -> {status_icon} ({dur_ms:.1f}ms) | Tools Called: {called_tools}")
            if not case_passed:
                print(
                    f"         Failure detail: ToolMatch={tool_match}, ConfMatch={conf_match}, HalPassed={hal_passed}"
                )

            results.append(
                {
                    "id": c_id,
                    "name": name,
                    "passed": case_passed,
                    "tool_match": tool_match,
                    "conf_match": conf_match,
                    "duration_ms": dur_ms,
                }
            )

        total_duration = time.perf_counter() - total_start
        conf_cases = sum(1 for c in cases if c.get("requires_confirmation"))
        hal_cases = sum(1 for c in cases if c.get("anti_hallucination_check"))

        tool_acc = (tool_selection_matches / total_cases) * 100
        conf_acc = (confirmation_compliance_matches / total_cases) * 100
        pass_rate = (passed_cases / total_cases) * 100

        print("\n=======================================================")
        print("  EVALUATION SUMMARY REPORT")
        print("=======================================================")
        print(f"  Total Test Cases           : {total_cases}")
        print(f"  Passed                     : {passed_cases}")
        print(f"  Failed                     : {total_cases - passed_cases}")
        print(f"  Pass Rate                  : {pass_rate:.1f}%")
        print(f"  Tool Selection Accuracy    : {tool_acc:.1f}%")
        print(f"  Confirmation Cases Tested  : {conf_cases}")
        print(f"  Confirmation Compliance    : {conf_acc:.1f}%")
        if hal_cases > 0:
            hal_rate = (anti_hallucination_matches / hal_cases) * 100
            print(f"  Anti-Hallucination Rate    : {hal_rate:.1f}%")
        print(f"  Total Benchmark Duration   : {total_duration:.2f}s")
        print("=======================================================\n")

        return {
            "total_cases": total_cases,
            "passed": passed_cases,
            "failed": total_cases - passed_cases,
            "pass_rate_pct": round(pass_rate, 1),
            "tool_selection_accuracy_pct": round(tool_acc, 1),
            "confirmation_compliance_pct": round(conf_acc, 1),
            "total_duration_sec": round(total_duration, 2),
            "results": results,
        }


def main():
    parser = argparse.ArgumentParser(description="Integration Copilot AI Evaluation Runner")
    parser.add_argument(
        "--provider",
        choices=["mock", "ollama"],
        default="mock",
        help="LLM provider to use for evaluation (default: mock)",
    )
    parser.add_argument(
        "--cases",
        default=str(Path(__file__).parent / "cases.yaml"),
        help="Path to YAML cases file",
    )
    args = parser.parse_args()

    runner = EvaluationRunner(cases_file=args.cases, provider_name=args.provider)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
