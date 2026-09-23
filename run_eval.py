from dotenv import load_dotenv

from evals.evaluator import compare_runs, suite_summary
from evals.improve import apply_reinforcements, generate_reinforcements
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
    print("Category scores:")
    for category, value in summary["category_scores"].items():
        print(f"  {category:<26} {value:>5.1f}%")


def main():
    load_dotenv()

    before = run_suite()
    print_results("BASELINE", before)

    additions = generate_reinforcements(before)
    if not additions:
        print("\nNo failed scenarios produced a supported new reinforcement. Nothing to apply.")
        return

    print("\nGenerated reinforcements:")
    for item in additions:
        print(f"- [{item['failure_type']}] {item['rule']}")

    added = apply_reinforcements(additions)
    print(f"\nApplied {added} new reinforcement(s). Re-running the identical suite...")

    after = run_suite()
    print_results("AFTER IMPROVEMENT", after)

    comparison = compare_runs(before, after)
    print(
        f"\nScore movement: {comparison['before']['score']:.1f}% -> "
        f"{comparison['after']['score']:.1f}% ({comparison['score_delta']:+.1f})"
    )
    print(
        f"Pass-rate movement: {comparison['before']['pass_rate']:.1f}% -> "
        f"{comparison['after']['pass_rate']:.1f}% ({comparison['pass_rate_delta']:+.1f})"
    )
    print(f"Regressions: {len(comparison['regressions'])}")
    for item in comparison["regressions"]:
        print(f"  - {item['scenario_id']}: {item['before']:.1f}% -> {item['after']:.1f}%")


if __name__ == "__main__":
    main()
