import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main  # noqa: E402
from services.document_query_log_store import SQLiteDocumentQueryLogStore  # noqa: E402
from services.evaluation_result_store import SQLiteEvaluationResultStore  # noqa: E402
from services.ingestion_job_store import SQLiteIngestionJobStore  # noqa: E402
from services.planning_suggestion_store import SQLiteSuggestionStore  # noqa: E402
from services.review_store import SQLiteReviewStore  # noqa: E402
from services.risk_store import SQLiteRiskStore  # noqa: E402
from services.sqlite_document_store import SQLiteDocumentStore  # noqa: E402
from services.usage_tracking_service import SQLiteUsageTrackingService  # noqa: E402


@pytest.fixture(autouse=True)
def use_test_sqlite_store(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_app.db"

    test_store = SQLiteDocumentStore(str(test_db_path))
    test_job_store = SQLiteIngestionJobStore(str(test_db_path))
    test_evaluation_result_store = SQLiteEvaluationResultStore(str(test_db_path))
    test_usage_tracking_service = SQLiteUsageTrackingService(str(test_db_path))
    test_document_query_log_store = SQLiteDocumentQueryLogStore(str(test_db_path))
    test_review_store = SQLiteReviewStore(str(test_db_path))
    test_suggestion_store = SQLiteSuggestionStore(str(test_db_path))
    test_risk_store = SQLiteRiskStore(str(test_db_path))

    monkeypatch.setattr(main, "sqlite_document_store", test_store)
    monkeypatch.setattr(main, "sqlite_ingestion_job_store", test_job_store)
    monkeypatch.setattr(main, "sqlite_review_store", test_review_store)
    monkeypatch.setattr(main, "sqlite_suggestion_store", test_suggestion_store)
    monkeypatch.setattr(main, "sqlite_risk_store", test_risk_store)
    monkeypatch.setattr(
        main,
        "sqlite_evaluation_result_store",
        test_evaluation_result_store,
    )
    monkeypatch.setattr(
        main,
        "sqlite_usage_tracking_service",
        test_usage_tracking_service,
    )
    monkeypatch.setattr(
        main,
        "sqlite_document_query_log_store",
        test_document_query_log_store,
    )

    yield

    test_risk_store.clear()
    test_suggestion_store.clear()
    test_review_store.clear()
    test_document_query_log_store.clear()
    test_usage_tracking_service.clear()
    test_evaluation_result_store.clear()
    test_job_store.clear()
    test_store.clear()


@pytest.fixture(autouse=True)
def set_test_api_key(monkeypatch):
    monkeypatch.setenv("APP_API_KEY", "test-secret-key")


@pytest.fixture(autouse=True)
def force_local_answerer(monkeypatch):
    # Keep the suite deterministic and free: never hit a real provider key from the dev .env.
    monkeypatch.setenv("DOCUMENT_ANSWERER_TYPE", "rule")
    monkeypatch.setenv("DOCUMENT_QA_MODEL_CLIENT_TYPE", "fake")
    monkeypatch.setenv("CLASSIFIER_TYPE", "rule")
    monkeypatch.setenv("SUMMARIZER_TYPE", "rule")
    monkeypatch.setenv("ANSWERER_TYPE", "rule")
    monkeypatch.setenv("CHATBOT_TYPE", "rule")
    monkeypatch.setenv("RISK_DETECTOR_TYPE", "rule")
    monkeypatch.setenv("JIRA_TASK_GENERATOR_TYPE", "rule")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)