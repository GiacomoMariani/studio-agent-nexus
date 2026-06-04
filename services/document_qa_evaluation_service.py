from time import perf_counter

from models.evaluation import (
    DocumentQAEvalCase,
    DocumentQAEvalCaseResult,
    DocumentQAEvalSummary,
)
from services.document_answering_service import DocumentAnsweringService
from services.document_ingestion_service import DocumentIngestionService


class DocumentQAEvaluationService:
    def __init__(
        self,
        ingestion_service: DocumentIngestionService,
        answering_service: DocumentAnsweringService,
    ):
        self.ingestion_service = ingestion_service
        self.answering_service = answering_service

    async def evaluate_cases(
        self,
        cases: list[DocumentQAEvalCase],
    ) -> DocumentQAEvalSummary:
        results = [
            await self.evaluate_case(case)
            for case in cases
        ]

        passed = sum(1 for result in results if result.passed)
        failed = len(results) - passed

        average_latency_ms = (
            sum(result.latency_ms for result in results) / len(results)
            if results
            else 0.0
        )

        return DocumentQAEvalSummary(
            total_cases=len(results),
            passed=passed,
            failed=failed,
            average_latency_ms=round(average_latency_ms, 2),
            results=results,
        )

    async def evaluate_case(
        self,
        case: DocumentQAEvalCase,
    ) -> DocumentQAEvalCaseResult:
        start_time = perf_counter()
        checks: list[str] = []
        failures: list[str] = []
        document_id: str | None = None
        answer = ""
        was_fallback = False
        citation_count = 0

        try:
            ingestion_result = await self.ingestion_service.ingest_text(
                filename=case.document_filename,
                text=case.document_text,
            )
            document_id = ingestion_result.document_id

            answer_response = await self.answering_service.answer(
                document_id=document_id,
                question=case.question,
                top_k=max(case.min_citations, 1),
            )

            answer = answer_response.answer
            was_fallback = answer_response.was_fallback
            citations = answer_response.citations
            citation_count = len(citations)

            self._check_answer_contains(
                case=case,
                answer=answer,
                checks=checks,
                failures=failures,
            )

            self._check_expected_fallback(
                case=case,
                was_fallback=was_fallback,
                checks=checks,
                failures=failures,
            )

            self._check_citation_count(
                case=case,
                citation_count=citation_count,
                checks=checks,
                failures=failures,
            )

            self._check_citation_contains(
                case=case,
                citation_snippets=[citation.snippet for citation in citations],
                checks=checks,
                failures=failures,
            )

            self._check_retrieval_scores(
                case=case,
                citations=citations,
                checks=checks,
                failures=failures,
            )
        except Exception as ex:
            failures.append(f"Evaluation case crashed: {ex}")

        latency_ms = round((perf_counter() - start_time) * 1000, 2)

        return DocumentQAEvalCaseResult(
            name=case.name,
            passed=not failures,
            answer=answer,
            was_fallback=was_fallback,
            citation_count=citation_count,
            checks=checks,
            failures=failures,
            latency_ms=latency_ms,
            document_id=document_id,
        )

    def _check_answer_contains(
        self,
        case: DocumentQAEvalCase,
        answer: str,
        checks: list[str],
        failures: list[str],
    ) -> None:
        normalized_answer = answer.lower()

        for expected_text in case.expected_answer_contains:
            if expected_text.lower() in normalized_answer:
                checks.append(f"Answer contains '{expected_text}'.")
            else:
                failures.append(f"Answer does not contain '{expected_text}'.")

    def _check_expected_fallback(
        self,
        case: DocumentQAEvalCase,
        was_fallback: bool,
        checks: list[str],
        failures: list[str],
    ) -> None:
        if case.expected_was_fallback is None:
            return

        if was_fallback is case.expected_was_fallback:
            checks.append(f"Fallback matched expected value {case.expected_was_fallback}.")
        else:
            failures.append(
                f"Expected fallback to be {case.expected_was_fallback}, got {was_fallback}."
            )

    def _check_citation_count(
        self,
        case: DocumentQAEvalCase,
        citation_count: int,
        checks: list[str],
        failures: list[str],
    ) -> None:
        if citation_count >= case.min_citations:
            checks.append(
                f"Returned at least {case.min_citations} citation(s)."
            )
        else:
            failures.append(
                f"Expected at least {case.min_citations} citation(s), got {citation_count}."
            )

    def _check_citation_contains(
        self,
        case: DocumentQAEvalCase,
        citation_snippets: list[str],
        checks: list[str],
        failures: list[str],
    ) -> None:
        normalized_snippets = [
            snippet.lower()
            for snippet in citation_snippets
        ]

        for expected_text in case.expected_citation_contains:
            normalized_expected_text = expected_text.lower()

            if any(
                normalized_expected_text in snippet
                for snippet in normalized_snippets
            ):
                checks.append(f"Citation contains '{expected_text}'.")
            else:
                failures.append(f"No citation contains '{expected_text}'.")

    def _check_retrieval_scores(
        self,
        case: DocumentQAEvalCase,
        citations: list[object],
        checks: list[str],
        failures: list[str],
    ) -> None:
        if not case.require_retrieval_scores:
            return

        if not citations:
            failures.append(
                "Retrieval scores could not be checked because no citations were returned."
            )
            return

        for citation in citations:
            scores = [
                citation.vector_score,
                citation.keyword_score,
                citation.hybrid_score,
            ]

            if all(0.0 <= score <= 1.0 for score in scores):
                continue

            failures.append(
                f"Citation {citation.chunk_id} has retrieval scores outside the 0.0 to 1.0 range."
            )
            return

        checks.append("All citation retrieval scores are between 0.0 and 1.0.")