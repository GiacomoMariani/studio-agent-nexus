import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extraction_service import ExtractionService  # noqa: E402
from services.rule_based_extractor import RuleBasedExtractor  # noqa: E402

CASES_PATH = ROOT / "evals" / "extraction_cases.json"


async def run_eval() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    extractor = RuleBasedExtractor()
    service = ExtractionService(extractor)

    passed = 0
    failed = 0

    for case in cases:
        actual_response = await service.extract(case["input"])
        actual = actual_response.model_dump()
        expected = case["expected"]

        if actual == expected:
            passed += 1
            print(f"PASS: {case['name']}")
        else:
            failed += 1
            print(f"FAIL: {case['name']}")
            print(f"  expected: {expected}")
            print(f"  actual:   {actual}")

    total = passed + failed

    print()
    print(f"Result: {passed}/{total} passed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run_eval()))