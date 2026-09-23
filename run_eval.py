from dotenv import load_dotenv

from evals.evaluator import suite_summary
from evals.improve import close_improvement_loop
from evals.runner import run_suite


def print_results(title, results):
    summary = suite_summary(results)
    print(f"\n{title}")
    print("=" * len(title))
    for result in results:
        label = "PASS" if result["passed"] else "FAIL"
        critical = " CRITICAL" if result.get("critical_failure") else ""
        print(f"{result['scenario_id']:<38} {label:<4} {result['score']:>5.1f}%{critical}")
        for failure in result["failures"]:
            print(f"  - [{failure['category']}] {failure['code']}: {failure['detail']}")

    print(
        f"\nSuite score: {summary['score']:.1f}% | "
        f"Pass rate: {summary['passed']}/{summary['total']} ({summary['pass_rate']:.1f}%) | "
        f"Critical failures: {summary['critical_failures']}"
    )


def main():
    load_dotenv()

    outcome = close_improvement_loop(run_suite)
    print_results("BASELINE", outcome["before"])

    if not outcome["additions"]:
        print("\nNo allow-listed failure produced a candidate reinforcement.")
        return

    print("\nCandidate reinforcements:")
    for item in outcome["additions"]:
        print(
            f"- [{item['failure_type']}] {item['rule']}\n"
            f"  evidence: scenario={item['source_scenario']} code={item['failure_code']}"
        )

    print_results("CANDIDATE RE-RUN", outcome["after"])

    comparison = outcome["comparison"]
    print(
        f"\nScore movement: {comparison['before']['score']:.1f}% -> "
        f"{comparison['after']['score']:.1f}% ({comparison['score_delta']:+.1f})"
    )
    print(
        f"Pass-rate movement: {comparison['before']['pass_rate']:.1f}% -> "
        f"{comparison['after']['pass_rate']:.1f}% ({comparison['pass_rate_delta']:+.1f})"
    )
    print(f"Improvements: {len(comparison['improvements'])}")
    for item in comparison["improvements"]:
        print(f"  + {item['scenario_id']}: {item['before']:.1f}% -> {item['after']:.1f}%")

    print(f"Regressions: {len(comparison['regressions'])}")
    for item in comparison["regressions"]:
        print(f"  - {item['scenario_id']}: {item['before']:.1f}% -> {item['after']:.1f}%")

    if outcome["promoted"]:
        print("\nPROMOTED: reinforcement kept because it improved the suite with zero regressions.")
    else:
        print(f"\nROLLED BACK: {outcome['reason']}. Reinforcement file restored.")


if __name__ == "__main__":
    main()
