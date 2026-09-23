from dotenv import load_dotenv

from evals.improve import apply_reinforcements, generate_reinforcements
from evals.runner import run_suite, score


def print_results(title, results):
    print(f"\n{title}")
    print("=" * len(title))
    for result in results:
        label = "PASS" if result["passed"] else "FAIL"
        print(f"{result['scenario_id']:<30} {label}")
        for failure in result["failures"]:
            print(f"  - {failure['code']}: {failure['detail']}")
    print(f"Score: {score(results):.1f}%")


def main():
    load_dotenv()

    before = run_suite()
    print_results("BASELINE", before)

    additions = generate_reinforcements(before)
    if not additions:
        print("\nNo failed scenarios produced a new reinforcement. Nothing to apply.")
        return

    print("\nGenerated reinforcements:")
    for item in additions:
        print(f"- [{item['failure_type']}] {item['rule']}")

    added = apply_reinforcements(additions)
    print(f"\nApplied {added} new reinforcement(s). Re-running the same suite...")

    after = run_suite()
    print_results("AFTER IMPROVEMENT", after)

    before_passed = {r["scenario_id"] for r in before if r["passed"]}
    regressions = [r["scenario_id"] for r in after if r["scenario_id"] in before_passed and not r["passed"]]
    print(f"\nScore movement: {score(before):.1f}% -> {score(after):.1f}%")
    print(f"Regressions: {len(regressions)}" + (f" ({', '.join(regressions)})" if regressions else ""))


if __name__ == "__main__":
    main()
