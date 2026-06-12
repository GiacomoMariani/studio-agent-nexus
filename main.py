import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from pydantic import BaseModel, Field

from auth import require_api_key
from models.answering import AnswerRequest, AnswerResponse
from models.ask_tasks import AskTaskSuggestionRequest, AskTaskSuggestionResponse
from models.board_import import (
    BoardImportEntityResult,
    BoardImportRequest,
    BoardImportResponse,
)
from models.chat import ChatRequest, ChatResponse
from models.classification import ClassifyRequest, ClassifyResponse
from models.document_qa import (
    DocumentAskRequest,
    DocumentAskResponse,
    DocumentContentResponse,
    DocumentDeleteResponse,
    DocumentIngestionJobResponse,
    DocumentListResponse,
    DocumentQueryLogListResponse,
    DocumentQueryLogResponse,
    DocumentQueryRetrievedSourceLogResponse,
    DocumentReindexResponse,
    DocumentSummaryResponse,
    KnowledgeGapListResponse,
    KnowledgeGapResponse,
)
from models.evaluation import (
    DocumentQAEvalLatestRunResponse,
    DocumentQAEvalStoredCaseResultResponse,
)
from models.extraction import ExtractRequest, ExtractResponse
from models.health import HealthResponse
from models.ingestion_queue_model import (
    DocumentReindexIngestionPayload,
    StoredTextUploadIngestionPayload,
)
from models.jira_task import (
    JiraTaskDraft,
    JiraTaskGenerateRequest,
    jira_task_schema,
)
from models.maintenance import (
    UploadedTextCleanupRequest,
    UploadedTextCleanupResponse,
)
from models.planning_suggestion import (
    SuggestionCreate,
    SuggestionResponse,
    suggestion_post_schema,
)
from models.review import ReviewCreate, ReviewResponse, review_post_schema
from models.risk import RiskCreate, RiskResponse, risk_post_schema
from models.routing import RouteRequest, RouteResponse
from models.summarization import SummarizeRequest, SummarizeResponse
from models.tool_assistant import ToolAssistantRequest, ToolAssistantResponse
from models.usage import (
    UsageRecentRequest,
    UsageRecentResponse,
    UsageRecordResponse,
    UsageSummaryResponse,
)
from providers.embedding_provider import embedding_provider
from services.answerer_factory import get_answerer
from services.answering_service import AnsweringService
from services.ask_task_suggestion_service import AskTaskSuggestionService
from services.chat_service import ChatService
from services.chatbot_factory import get_chatbot
from services.classification_service import ClassificationService
from services.classifier_factory import get_classifier
from services.demo_document_seeder import DemoDocumentSeeder
from services.document_answerer_factory import get_document_answerer, resolve_provider
from services.document_answering_service import DocumentAnsweringService
from services.document_ingestion_service import DocumentIngestionService
from services.document_ingestion_worker import DocumentIngestionWorker
from services.document_query_log_store import (
    SQLiteDocumentQueryLogStore,
    sqlite_document_query_log_store,
)
from services.evaluation_result_store import (
    SQLiteEvaluationResultStore,
    sqlite_evaluation_result_store,
)
from services.exceptions import AppServiceError
from services.extraction_service import ExtractionService
from services.extractor import get_extractor
from services.ingestion_job_store import SQLiteIngestionJobStore, sqlite_ingestion_job_store
from services.ingestion_queue import (
    DocumentIngestionQueue,
    FastAPIBackgroundTasksIngestionQueue,
)
from services.jira_task_generation_service import JiraTaskGenerationService
from services.jira_task_generator_factory import get_jira_task_generator
from services.pdf_parser import extract_pdf_pages
from services.planning_suggestion_store import (
    SQLiteSuggestionStore,
    sqlite_suggestion_store,
)
from services.related_task_service import RelatedTaskService
from services.retrieval_service import RetrievalService
from services.review_store import SQLiteReviewStore, sqlite_review_store
from services.risk_detection_service import RiskDetectionService
from services.risk_detector_factory import get_risk_detector
from services.risk_store import SQLiteRiskStore, sqlite_risk_store
from services.routing_service import RoutingService
from services.rule_based_router import RuleBasedRouter
from services.sqlite_document_store import sqlite_document_store
from services.summarization_service import SummarizationService
from services.summarizer_factory import get_summarizer
from services.tool_assistant_service import ToolAssistantService
from services.uploaded_text_cleanup_service import delete_stale_uploaded_texts
from services.uploaded_text_store import SQLiteUploadedTextStore, UploadedTextStore
from services.usage_tracking_service import (
    SQLiteUsageTrackingService,
    UsagePricing,
    sqlite_usage_tracking_service,
)
from settings import get_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Notional per-1k-token pricing used to cost each query log row. Applied to estimated
# token counts so the cost dashboard is populated even under the free rule-based answerer.
QUERY_LOG_PRICING = UsagePricing(
    input_cost_per_1k_tokens_usd=0.0003,
    output_cost_per_1k_tokens_usd=0.0012,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ingestion_service = DocumentIngestionService(
        store=sqlite_document_store,
        embedding_provider=embedding_provider,
        usage_tracking_service=sqlite_usage_tracking_service,
    )

    seeder = DemoDocumentSeeder(
        demo_dir="demo",
        ingestion_service=ingestion_service,
    )

    await seeder.seed()

    yield


app = FastAPI(
    title="Studio Agent Nexus",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid4().hex[:12])
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "Request failed method=%s path=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            duration_ms,
            request_id,
        )

        raise

    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "Request completed method=%s path=%s status_code=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )

    return response


class UserInput(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(ge=0, le=120)


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class TextAnalysisResponse(BaseModel):
    original_text: str
    character_count: int
    word_count: int
    sentence_count: int
    unique_words: int
    preview: str


def get_routing_service() -> RoutingService:
    router = RuleBasedRouter()
    return RoutingService(router)


RoutingServiceDependency = Annotated[
    RoutingService,
    Depends(get_routing_service),
]


def get_extraction_service() -> ExtractionService:
    extractor = get_extractor()
    return ExtractionService(extractor)


ExtractionServiceDependency = Annotated[
    ExtractionService,
    Depends(get_extraction_service),
]


def get_classification_service() -> ClassificationService:
    return ClassificationService(get_classifier(get_settings()))


ClassificationServiceDependency = Annotated[
    ClassificationService,
    Depends(get_classification_service),
]


def get_summarization_service() -> SummarizationService:
    return SummarizationService(get_summarizer(get_settings()))


SummarizationServiceDependency = Annotated[
    SummarizationService,
    Depends(get_summarization_service),
]


def get_answering_service() -> AnsweringService:
    return AnsweringService(get_answerer(get_settings()))


AnsweringServiceDependency = Annotated[
    AnsweringService,
    Depends(get_answering_service),
]


def get_tool_assistant_service() -> ToolAssistantService:
    return ToolAssistantService()


def get_document_ingestion_service() -> DocumentIngestionService:
    return DocumentIngestionService(
        store=sqlite_document_store,
        embedding_provider=embedding_provider,
        usage_tracking_service=sqlite_usage_tracking_service,
    )


DocumentIngestionServiceDependency = Annotated[
    DocumentIngestionService,
    Depends(get_document_ingestion_service),
]


def get_ingestion_job_store() -> SQLiteIngestionJobStore:
    return sqlite_ingestion_job_store


IngestionJobStoreDependency = Annotated[
    SQLiteIngestionJobStore,
    Depends(get_ingestion_job_store),
]


def get_evaluation_result_store() -> SQLiteEvaluationResultStore:
    return sqlite_evaluation_result_store


EvaluationResultStoreDependency = Annotated[
    SQLiteEvaluationResultStore,
    Depends(get_evaluation_result_store),
]


def get_document_ingestion_worker(
    ingestion_service: DocumentIngestionServiceDependency,
    job_store: IngestionJobStoreDependency,
) -> DocumentIngestionWorker:
    return DocumentIngestionWorker(
        ingestion_service=ingestion_service,
        job_store=job_store,
    )


DocumentIngestionWorkerDependency = Annotated[
    DocumentIngestionWorker,
    Depends(get_document_ingestion_worker),
]


def get_document_answering_service() -> DocumentAnsweringService:
    settings = get_settings()
    answerer = get_document_answerer(settings)

    return DocumentAnsweringService(
        store=sqlite_document_store,
        retrieval_service=RetrievalService(
            embedding_provider,
            min_score=settings.retrieval_min_score,
        ),
        answerer=answerer,
        usage_tracking_service=sqlite_usage_tracking_service,
        provider=resolve_provider(settings, answerer),
    )


DocumentAnsweringServiceDependency = Annotated[
    DocumentAnsweringService,
    Depends(get_document_answering_service),
]


def get_chat_service() -> ChatService:
    return ChatService(get_chatbot(get_settings()))


ChatServiceDependency = Annotated[
    ChatService,
    Depends(get_chat_service),
]


def get_usage_tracking_service() -> SQLiteUsageTrackingService:
    return sqlite_usage_tracking_service


UsageTrackingServiceDependency = Annotated[
    SQLiteUsageTrackingService,
    Depends(get_usage_tracking_service),
]


def get_document_ingestion_queue(
    background_tasks: BackgroundTasks,
) -> DocumentIngestionQueue:
    return FastAPIBackgroundTasksIngestionQueue(background_tasks)


DocumentIngestionQueueDependency = Annotated[
    DocumentIngestionQueue,
    Depends(get_document_ingestion_queue),
]


def get_uploaded_text_store() -> UploadedTextStore:
    settings = get_settings()
    return SQLiteUploadedTextStore(settings.uploaded_text_db_path)


UploadedTextStoreDependency = Annotated[
    UploadedTextStore,
    Depends(get_uploaded_text_store),
]


def get_document_query_log_store() -> SQLiteDocumentQueryLogStore:
    return sqlite_document_query_log_store


DocumentQueryLogStoreDependency = Annotated[
    SQLiteDocumentQueryLogStore,
    Depends(get_document_query_log_store),
]


def get_review_store() -> SQLiteReviewStore:
    return sqlite_review_store


ReviewStoreDependency = Annotated[
    SQLiteReviewStore,
    Depends(get_review_store),
]


def get_suggestion_store() -> SQLiteSuggestionStore:
    return sqlite_suggestion_store


SuggestionStoreDependency = Annotated[
    SQLiteSuggestionStore,
    Depends(get_suggestion_store),
]


def get_risk_store() -> SQLiteRiskStore:
    return sqlite_risk_store


RiskStoreDependency = Annotated[
    SQLiteRiskStore,
    Depends(get_risk_store),
]


def get_risk_detection_service() -> RiskDetectionService:
    return RiskDetectionService(
        document_store=sqlite_document_store,
        risk_store=sqlite_risk_store,
        detector=get_risk_detector(get_settings()),
    )


RiskDetectionServiceDependency = Annotated[
    RiskDetectionService,
    Depends(get_risk_detection_service),
]


def get_jira_task_generation_service() -> JiraTaskGenerationService:
    return JiraTaskGenerationService(
        document_store=sqlite_document_store,
        generator=get_jira_task_generator(get_settings()),
    )


JiraTaskGenerationServiceDependency = Annotated[
    JiraTaskGenerationService,
    Depends(get_jira_task_generation_service),
]


def get_ask_task_suggestion_service() -> AskTaskSuggestionService:
    settings = get_settings()
    return AskTaskSuggestionService(
        review_store=sqlite_review_store,
        suggestion_store=sqlite_suggestion_store,
        related_service=RelatedTaskService(
            embedding_provider=embedding_provider,
            min_score=settings.ask_task_match_min_score,
        ),
        generator=get_jira_task_generator(settings),
        suggest_max=settings.ask_task_suggest_max,
    )


AskTaskSuggestionServiceDependency = Annotated[
    AskTaskSuggestionService,
    Depends(get_ask_task_suggestion_service),
]


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/greet")
def greet(user: UserInput) -> dict[str, str]:
    return {"message": f"Hello {user.name}, age {user.age}"}


@app.post("/analyze", response_model=TextAnalysisResponse)
def analyze_text(request: TextRequest) -> TextAnalysisResponse:
    text = request.text.strip()

    words = re.findall(r"\b\w+\b", text.lower())
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]

    return TextAnalysisResponse(
        original_text=text,
        character_count=len(text),
        word_count=len(words),
        sentence_count=len(sentences),
        unique_words=len(set(words)),
        preview=text[:80],
    )


@app.post("/route", response_model=RouteResponse)
async def route_request(
    request: RouteRequest,
    routing_service: RoutingServiceDependency,
) -> RouteResponse:
    try:
        return await routing_service.route(request.user_input)
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@app.post(
    "/extract",
    response_model=ExtractResponse,
    dependencies=[Depends(require_api_key)],
)
async def extract_fields(
    request: ExtractRequest,
    extraction_service: ExtractionServiceDependency,
) -> ExtractResponse:
    try:
        return await extraction_service.extract(request.text)
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@app.post("/classify", response_model=ClassifyResponse)
async def classify_text(
    request: ClassifyRequest,
    classification_service: ClassificationServiceDependency,
) -> ClassifyResponse:
    try:
        return await classification_service.classify(request.text)
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_text(
    request: SummarizeRequest,
    summarization_service: SummarizationServiceDependency,
) -> SummarizeResponse:
    try:
        return await summarization_service.summarize(
            request.text,
            request.max_sentences,
        )
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@app.post(
    "/answer",
    response_model=AnswerResponse,
    dependencies=[Depends(require_api_key)],
)
async def answer_question(
    request: AnswerRequest,
    answering_service: AnsweringServiceDependency,
) -> AnswerResponse:
    try:
        return await answering_service.answer(
            request.question,
            request.context,
        )
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@app.post(
    "/documents/upload",
    response_model=DocumentIngestionJobResponse,
    dependencies=[Depends(require_api_key)],
)
async def upload_document(
    ingestion_worker: DocumentIngestionWorkerDependency,
    ingestion_queue: DocumentIngestionQueueDependency,
    uploaded_text_store: UploadedTextStoreDependency,
    file: UploadFile = File(...),
) -> DocumentIngestionJobResponse:
    filename = file.filename or "uploaded.txt"
    raw_bytes = await file.read()
    lower_filename = filename.lower()

    if lower_filename.endswith((".txt", ".md")):
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as ex:
            raise HTTPException(
                status_code=400,
                detail="Document must be valid UTF-8 text.",
            ) from ex

    elif lower_filename.endswith(".pdf"):
        try:
            pages = extract_pdf_pages(raw_bytes)
        except AppServiceError as ex:
            raise HTTPException(status_code=400, detail=str(ex)) from ex

        text = "\n\n".join(
            f"[Page {page.page_number}]\n{page.text}"
            for page in pages
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Only .txt, .md, and .pdf files are supported.",
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="Uploaded document is empty.")

    content_id = uploaded_text_store.save_text(
        filename=filename,
        text=text,
    )

    queued_job = ingestion_worker.create_text_upload_job(filename)

    ingestion_queue.enqueue_stored_text_upload(
        worker=ingestion_worker,
        text_store=uploaded_text_store,
        payload=StoredTextUploadIngestionPayload(
            job_id=queued_job.job_id,
            filename=filename,
            content_id=content_id,
        ),
    )

    return DocumentIngestionJobResponse(
        job_id=queued_job.job_id,
        filename=queued_job.filename,
        status=queued_job.status,
        document_id=queued_job.document_id,
        chunk_count=queued_job.chunk_count,
        error_message=queued_job.error_message,
        created_at=queued_job.created_at,
        updated_at=queued_job.updated_at,
    )


@app.get(
    "/documents",
    response_model=DocumentListResponse,
    dependencies=[Depends(require_api_key)],
)
async def list_documents() -> DocumentListResponse:
    documents = sqlite_document_store.list_documents()

    return DocumentListResponse(
        documents=[
            DocumentSummaryResponse(
                document_id=document.document_id,
                filename=document.filename,
                file_type=document.file_type,
                upload_date=document.upload_date,
                status=document.status,
                page_count=document.page_count,
                chunk_count=document.chunk_count,
                is_demo=document.is_demo,
            )
            for document in documents
        ]
    )


@app.get(
    "/documents/{document_id}/content",
    response_model=DocumentContentResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_document_content(document_id: str) -> DocumentContentResponse:
    document = sqlite_document_store.get_document(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentContentResponse(
        document_id=document.document_id,
        filename=document.filename,
        file_type=document.file_type,
        content=document.original_text,
    )


@app.post(
    "/documents/{document_id}/reindex",
    response_model=DocumentReindexResponse,
    dependencies=[Depends(require_api_key)],
)
async def reindex_document(
    document_id: str,
    ingestion_worker: DocumentIngestionWorkerDependency,
    ingestion_queue: DocumentIngestionQueueDependency,
) -> DocumentReindexResponse:
    try:
        job = ingestion_worker.create_document_reindex_job(document_id)
    except AppServiceError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex

    ingestion_queue.enqueue_document_reindex(
        worker=ingestion_worker,
        payload=DocumentReindexIngestionPayload(
            job_id=job.job_id,
            document_id=document_id,
        ),
    )

    return DocumentReindexResponse(
        job_id=job.job_id,
        document_id=document_id,
        filename=job.filename,
        status=job.status,
    )


@app.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse,
    dependencies=[Depends(require_api_key)],
)
async def delete_document(document_id: str) -> DocumentDeleteResponse:
    document = sqlite_document_store.get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if document.is_demo:
        raise HTTPException(
            status_code=403,
            detail="Demo documents cannot be deleted.",
        )

    deleted = sqlite_document_store.delete_document(document_id)

    if not deleted:
        raise HTTPException(
            status_code=500,
            detail="Document could not be deleted.",
        )

    return DocumentDeleteResponse(
        document_id=document_id,
        deleted=True,
    )


@app.get(
    "/documents/jobs/{job_id}",
    response_model=DocumentIngestionJobResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_document_ingestion_job(
    job_id: str,
    job_store: IngestionJobStoreDependency,
) -> DocumentIngestionJobResponse:
    job = job_store.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")

    return DocumentIngestionJobResponse(
        job_id=job.job_id,
        filename=job.filename,
        status=job.status,
        document_id=job.document_id,
        chunk_count=job.chunk_count,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@app.post(
    "/documents/ask",
    response_model=DocumentAskResponse,
    dependencies=[Depends(require_api_key)],
)
async def ask_document_question(
    request: DocumentAskRequest,
    document_answering_service: DocumentAnsweringServiceDependency,
    document_query_log_store: DocumentQueryLogStoreDependency,
    usage_tracking_service: UsageTrackingServiceDependency,
) -> DocumentAskResponse:
    start_time = time.perf_counter()

    try:
        if request.document_id:
            response = await document_answering_service.answer(
                document_id=request.document_id,
                question=request.question,
                top_k=request.top_k,
            )
        else:
            response = await document_answering_service.answer_all(
                question=request.question,
                top_k=request.top_k,
            )
    except AppServiceError as ex:
        if str(ex) == "Document not found.":
            raise HTTPException(status_code=404, detail=str(ex)) from ex

        raise HTTPException(status_code=500, detail=str(ex)) from ex

    latency_ms = (time.perf_counter() - start_time) * 1000

    # Unified log row: combine the audit fields with model + token + cost figures so the
    # Logs page reads everything from one table. Token counts come from the answering
    # service (estimated over the full retrieved context, so they stay accurate even when
    # the answer falls back and visible citations are stripped).
    # Reflect the configured answerer in the log: the live model when the LLM answerer
    # is selected, otherwise the rule-based path. Provider-agnostic by design.
    settings = get_settings()
    if settings.document_answerer_type == "llm":
        model_name = settings.document_qa_model_name
    else:
        model_name = "rule-based"

    estimated_cost_usd = usage_tracking_service.cost_for_tokens(
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        pricing=QUERY_LOG_PRICING,
    )

    document_query_log_store.record_query(
        document_id=request.document_id or "all-documents",
        question=request.question,
        answer=response.answer,
        citation_count=len(response.citations),
        was_fallback=response.was_fallback,
        latency_ms=latency_ms,
        retrieved_sources=response.citations,
        model_name=model_name,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )

    return response


@app.post(
    "/tool-assistant",
    response_model=ToolAssistantResponse,
    dependencies=[Depends(require_api_key)],
)
async def tool_assistant(
    request: ToolAssistantRequest,
    service: ToolAssistantService = Depends(get_tool_assistant_service),
) -> ToolAssistantResponse:
    result = await service.answer(request.message)
    return ToolAssistantResponse(**result)


@app.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_api_key)],
)
async def chat(
    request: ChatRequest,
    chat_service: ChatServiceDependency,
) -> ChatResponse:
    try:
        return await chat_service.chat(request.message)
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@app.get(
    "/evals/document-qa/latest",
    response_model=DocumentQAEvalLatestRunResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_latest_document_qa_eval(
    evaluation_result_store: EvaluationResultStoreDependency,
) -> DocumentQAEvalLatestRunResponse:
    latest_run = evaluation_result_store.get_latest_run()

    if latest_run is None:
        raise HTTPException(
            status_code=404,
            detail="No document QA evaluation runs found.",
        )

    case_results = evaluation_result_store.get_case_results(latest_run.run_id)

    return DocumentQAEvalLatestRunResponse(
        run_id=latest_run.run_id,
        total_cases=latest_run.total_cases,
        passed=latest_run.passed,
        failed=latest_run.failed,
        average_latency_ms=latest_run.average_latency_ms,
        created_at=latest_run.created_at,
        results=[
            DocumentQAEvalStoredCaseResultResponse(
                name=result.name,
                passed=result.passed,
                answer=result.answer,
                was_fallback=result.was_fallback,
                citation_count=result.citation_count,
                checks=result.checks,
                failures=result.failures,
                latency_ms=result.latency_ms,
                document_id=result.document_id,
            )
            for result in case_results
        ],
    )


@app.get(
    "/usage/summary",
    response_model=UsageSummaryResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_usage_summary(
    usage_tracking_service: UsageTrackingServiceDependency,
) -> UsageSummaryResponse:
    recent_records = usage_tracking_service.list_recent_usage(limit=100)

    return UsageSummaryResponse(
        total_estimated_cost_usd=usage_tracking_service.get_total_estimated_cost_usd(),
        recent_record_count=len(recent_records),
    )


@app.get(
    "/usage/recent",
    response_model=UsageRecentResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_recent_usage(
    query: UsageRecentRequest = Depends(),
    usage_tracking_service: UsageTrackingServiceDependency = None,
) -> UsageRecentResponse:
    records = usage_tracking_service.list_recent_usage(limit=query.limit)

    return UsageRecentResponse(
        records=[
            UsageRecordResponse(
                usage_id=record.usage_id,
                operation=record.operation,
                provider=record.provider,
                model_name=record.model_name,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                estimated_cost_usd=record.estimated_cost_usd,
                metadata=record.metadata,
                created_at=record.created_at,
            )
            for record in records
        ]
    )


@app.post(
    "/admin/uploaded-texts/cleanup",
    response_model=UploadedTextCleanupResponse,
    dependencies=[Depends(require_api_key)],
)
async def cleanup_uploaded_texts(
    request: UploadedTextCleanupRequest,
    uploaded_text_store: UploadedTextStoreDependency,
) -> UploadedTextCleanupResponse:
    settings = get_settings()
    max_age_hours = (
        request.max_age_hours
        if request.max_age_hours is not None
        else settings.uploaded_text_cleanup_max_age_hours
    )

    deleted_count = delete_stale_uploaded_texts(
        uploaded_text_store=uploaded_text_store,
        max_age_hours=max_age_hours,
    )

    logger.info(
        "Uploaded text cleanup completed max_age_hours=%s deleted_count=%s",
        max_age_hours,
        deleted_count,
    )

    return UploadedTextCleanupResponse(deleted_count=deleted_count)


@app.get(
    "/admin/document-query-logs",
    response_model=DocumentQueryLogListResponse,
    dependencies=[Depends(require_api_key)],
)
async def list_document_query_logs(
    document_query_log_store: DocumentQueryLogStoreDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> DocumentQueryLogListResponse:
    logs = document_query_log_store.get_recent_logs(limit=limit)

    return DocumentQueryLogListResponse(
        logs=[
            DocumentQueryLogResponse(
                query_id=log.query_log_id,
                document_id=log.document_id,
                question=log.question,
                answer=log.answer,
                citation_count=log.citation_count,
                latency_ms=log.latency_ms,
                was_fallback=log.was_fallback,
                created_at=log.created_at,
                model_name=log.model_name,
                input_tokens=log.input_tokens,
                output_tokens=log.output_tokens,
                estimated_cost_usd=log.estimated_cost_usd,
                retrieved_sources=[
                    DocumentQueryRetrievedSourceLogResponse(
                        source_id=source.source_id,
                        query_id=source.query_log_id,
                        chunk_id=source.chunk_id,
                        filename=source.filename or "",
                        snippet=source.snippet,
                        page_number=source.page_number,
                        vector_score=source.vector_score,
                        keyword_score=source.keyword_score,
                        hybrid_score=source.hybrid_score,
                    )
                    for source in log.retrieved_sources
                ],
            )
            for log in logs
        ]
    )


@app.post(
    "/admin/document-query-logs/clear",
    dependencies=[Depends(require_api_key)],
)
async def clear_document_query_logs(
    document_query_log_store: DocumentQueryLogStoreDependency,
) -> dict:
    document_query_log_store.clear()
    return {"cleared": True}


@app.get(
    "/admin/knowledge-gaps",
    response_model=KnowledgeGapListResponse,
    dependencies=[Depends(require_api_key)],
)
async def list_knowledge_gaps(
    document_query_log_store: DocumentQueryLogStoreDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> KnowledgeGapListResponse:
    fallback_logs = document_query_log_store.get_fallback_logs(limit=limit)

    return KnowledgeGapListResponse(
        gaps=[
            KnowledgeGapResponse(
                query_id=log.query_log_id,
                document_id=log.document_id,
                question=log.question,
                answer=log.answer,
                citation_count=log.citation_count,
                latency_ms=log.latency_ms,
                created_at=log.created_at,
            )
            for log in fallback_logs
        ]
    )


@app.post(
    "/reviews",
    response_model=ReviewResponse,
    dependencies=[Depends(require_api_key)],
)
async def upsert_review(
    request: ReviewCreate,
    review_store: ReviewStoreDependency,
) -> ReviewResponse:
    # Upsert: posting an existing task_id overwrites the stored record.
    record = review_store.upsert(
        task_id=request.task_id,
        title=request.title,
        description=request.description,
        department=request.department,
        priority=request.priority,
        source=request.source,
        state=request.state,
    )

    return ReviewResponse(**record)


@app.get(
    "/reviews",
    response_model=list[ReviewResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_reviews(
    review_store: ReviewStoreDependency,
) -> list[ReviewResponse]:
    return [ReviewResponse(**record) for record in review_store.list()]


@app.get(
    "/reviews/schema",
    dependencies=[Depends(require_api_key)],
)
async def get_reviews_schema() -> dict:
    return review_post_schema()


@app.delete(
    "/reviews/{task_id}",
    dependencies=[Depends(require_api_key)],
)
async def delete_review(
    task_id: str,
    review_store: ReviewStoreDependency,
) -> dict:
    deleted = review_store.delete(task_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found.")

    return {"task_id": task_id, "deleted": True}


@app.post(
    "/planning-suggestions",
    response_model=SuggestionResponse,
    dependencies=[Depends(require_api_key)],
)
async def upsert_suggestion(
    request: SuggestionCreate,
    suggestion_store: SuggestionStoreDependency,
) -> SuggestionResponse:
    # Upsert: posting an existing suggestion_id overwrites the stored record.
    record = suggestion_store.upsert(
        suggestion_id=request.suggestion_id,
        title=request.title,
        reason=request.reason,
        department=request.department,
        priority=request.priority,
        source=request.source,
    )

    return SuggestionResponse(**record)


@app.get(
    "/planning-suggestions",
    response_model=list[SuggestionResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_suggestions(
    suggestion_store: SuggestionStoreDependency,
) -> list[SuggestionResponse]:
    return [SuggestionResponse(**record) for record in suggestion_store.list()]


@app.get(
    "/planning-suggestions/schema",
    dependencies=[Depends(require_api_key)],
)
async def get_suggestions_schema() -> dict:
    return suggestion_post_schema()


@app.delete(
    "/planning-suggestions/{suggestion_id}",
    dependencies=[Depends(require_api_key)],
)
async def delete_suggestion(
    suggestion_id: str,
    suggestion_store: SuggestionStoreDependency,
) -> dict:
    deleted = suggestion_store.delete(suggestion_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Planning suggestion not found.")

    return {"suggestion_id": suggestion_id, "deleted": True}


@app.post(
    "/planning-suggestions/{suggestion_id}/promote",
    response_model=ReviewResponse,
    dependencies=[Depends(require_api_key)],
)
async def promote_suggestion(
    suggestion_id: str,
    suggestion_store: SuggestionStoreDependency,
    review_store: ReviewStoreDependency,
) -> ReviewResponse:
    suggestion = suggestion_store.get(suggestion_id)

    if suggestion is None:
        raise HTTPException(status_code=404, detail="Planning suggestion not found.")

    # Promote into a backlog review; task_id = suggestion_id keeps the link traceable.
    review = review_store.upsert(
        task_id=suggestion_id,
        title=suggestion["title"],
        description=suggestion["reason"],
        department=suggestion["department"],
        priority=suggestion["priority"],
        source=suggestion["source"],
        state="backlog",
    )

    suggestion_store.delete(suggestion_id)

    return ReviewResponse(**review)


@app.post(
    "/risks",
    response_model=RiskResponse,
    dependencies=[Depends(require_api_key)],
)
async def upsert_risk(
    request: RiskCreate,
    risk_store: RiskStoreDependency,
) -> RiskResponse:
    # Upsert: posting an existing risk_id overwrites the stored finding.
    record = risk_store.upsert(
        risk_id=request.risk_id,
        kind=request.kind,
        severity=request.severity,
        title=request.title,
        description=request.description,
        source=request.source,
        a_file=request.a_file,
        a_text=request.a_text,
        b_file=request.b_file,
        b_text=request.b_text,
    )

    return RiskResponse(**record)


@app.get(
    "/risks",
    response_model=list[RiskResponse],
    dependencies=[Depends(require_api_key)],
)
async def list_risks(
    risk_store: RiskStoreDependency,
) -> list[RiskResponse]:
    return [RiskResponse(**record) for record in risk_store.list()]


@app.get(
    "/risks/schema",
    dependencies=[Depends(require_api_key)],
)
async def get_risks_schema() -> dict:
    return risk_post_schema()


@app.delete(
    "/risks/{risk_id}",
    dependencies=[Depends(require_api_key)],
)
async def delete_risk(
    risk_id: str,
    risk_store: RiskStoreDependency,
) -> dict:
    deleted = risk_store.delete(risk_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Risk not found.")

    return {"risk_id": risk_id, "deleted": True}


@app.post(
    "/admin/board/import",
    response_model=BoardImportResponse,
    dependencies=[Depends(require_api_key)],
)
async def import_board(
    request: BoardImportRequest,
    review_store: ReviewStoreDependency,
    suggestion_store: SuggestionStoreDependency,
    risk_store: RiskStoreDependency,
) -> BoardImportResponse:
    # Bulk replace for the local→deployed board push (ticket-019): each entity key
    # present in the body has its whole set erased and re-inserted; absent keys stay
    # untouched. Pydantic validates the entire payload before this body runs, so one
    # invalid item rejects the import (422) with nothing erased. Only the three board
    # stores are reachable from here — documents/logs/usage cannot be affected.
    def replace_all(store, items) -> BoardImportEntityResult:
        deleted = len(store.list())
        store.clear()
        for item in items:
            store.upsert(**item.model_dump())
        # imported = rows now stored; duplicate ids in one payload collapse via upsert.
        return BoardImportEntityResult(deleted=deleted, imported=len(store.list()))

    return BoardImportResponse(
        reviews=(
            replace_all(review_store, request.reviews) if request.reviews is not None else None
        ),
        planning_suggestions=(
            replace_all(suggestion_store, request.planning_suggestions)
            if request.planning_suggestions is not None
            else None
        ),
        risks=(replace_all(risk_store, request.risks) if request.risks is not None else None),
    )


@app.post(
    "/admin/risks/detect",
    response_model=list[RiskResponse],
    dependencies=[Depends(require_api_key)],
)
async def detect_risks(
    service: RiskDetectionServiceDependency,
) -> list[RiskResponse]:
    # On-demand scan: refreshes the auto-detected findings (deletes prior auto-* and
    # re-inserts), leaving hand-posted risks untouched. Returns the stored findings.
    try:
        records = await service.detect_and_store()
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex

    return [RiskResponse(**record) for record in records]


@app.post(
    "/admin/jira-tasks/generate",
    response_model=list[JiraTaskDraft],
    dependencies=[Depends(require_api_key)],
)
async def generate_jira_tasks(
    request: JiraTaskGenerateRequest,
    service: JiraTaskGenerationServiceDependency,
) -> list[JiraTaskDraft]:
    # Ephemeral: generate Jira-shaped drafts from the selected document (or all documents
    # when document_id is null) and return them. Nothing is persisted.
    try:
        return await service.generate(request.document_id)
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@app.get(
    "/admin/jira-tasks/schema",
    dependencies=[Depends(require_api_key)],
)
async def get_jira_tasks_schema() -> dict:
    return jira_task_schema()


@app.post(
    "/documents/ask/task-suggestions",
    response_model=AskTaskSuggestionResponse,
    dependencies=[Depends(require_api_key)],
)
async def ask_task_suggestions(
    request: AskTaskSuggestionRequest,
    service: AskTaskSuggestionServiceDependency,
) -> AskTaskSuggestionResponse:
    # Ephemeral, LLM-gated affordance from the Ask page: related existing board tasks
    # (local-embedding match, no tokens) + suggested new Jira drafts (ticket-017 generator).
    # Nothing is persisted.
    try:
        result = await service.suggest(question=request.question, answer=request.answer)
    except AppServiceError as ex:
        raise HTTPException(status_code=500, detail=str(ex)) from ex

    return AskTaskSuggestionResponse(
        related=result["related"], suggested=result["suggested"]
    )
