import asyncio
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from models.evaluation import DocumentQAEvalCase  # noqa: E402
from services.document_answering_service import DocumentAnsweringService  # noqa: E402
from services.document_ingestion_service import DocumentIngestionService  # noqa: E402
from services.document_qa_evaluation_service import DocumentQAEvaluationService  # noqa: E402
from services.document_store import InMemoryDocumentStore  # noqa: E402
from services.evaluation_result_store import SQLiteEvaluationResultStore  # noqa: E402
from services.retrieval_service import RetrievalService  # noqa: E402
from services.rule_based_answerer import RuleBasedAnswerer  # noqa: E402

logger = logging.getLogger(__name__)

CASES_PATH = ROOT / "evals" / "document_qa_cases.json"


class DeterministicEmbeddingProvider:
    vocabulary = [
        "fastapi",
        "backend",
        "framework",
        "pytest",
        "testing",
        "docker",
        "background",
        "ingestion",
        "jobs",
        "uploads",
        "queued",
        "processing",
        "completed",
        "failed",
        "hybrid",
        "retrieval",
        "vector",
        "similarity",
        "keyword",
        "search",
        "citations",
        "scores",
    ]

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        normalized_text = text.lower()

        return [
            1.0 if token in normalized_text else 0.0
            for token in self.vocabulary
        ]


async def run_eval() -> int:
    raw_cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = [
        DocumentQAEvalCase(**raw_case)
        for raw_case in raw_cases
    ]

    store = InMemoryDocumentStore()
    embedding_provider = DeterministicEmbeddingProvider()

    ingestion_service = DocumentIngestionService(
        store=store,
        embedding_provider=embedding_provider,
    )

    retrieval_service = RetrievalService(
        embedding_provider=embedding_provider,
    )

    answering_service = DocumentAnsweringService(
        store=store,
        retrieval_service=retrieval_service,
        answerer=RuleBasedAnswerer(),
    )

    evaluation_service = DocumentQAEvaluationService(
        ingestion_service=ingestion_service,
        answering_service=answering_service,
    )

    summary = await evaluation_service.evaluate_cases(cases)

    result_store = SQLiteEvaluationResultStore()
    stored_run = result_store.save_summary(summary)

    logger.info("Saved evaluation run: %s", stored_run.run_id)

    for result in summary.results:
        status = "PASS" if result.passed else "FAIL"

        logger.info(
            "%s: %s | answer=%r | citations=%s | latency_ms=%s",
            status,
            result.name,
            result.answer,
            result.citation_count,
            result.latency_ms,
        )

        for check in result.checks:
            logger.info("check: %s | %s", result.name, check)

        for failure in result.failures:
            logger.warning("failure: %s | %s", result.name, failure)

    logger.info(
        "Evaluation result: %s/%s passed (%s failed)",
        summary.passed,
        summary.total_cases,
        summary.failed,
    )

    logger.info(
        "Average latency: %s ms",
        summary.average_latency_ms,
    )

    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    raise SystemExit(asyncio.run(run_eval()))