import os
from dataclasses import dataclass


def _get_int_env(
    name: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as ex:
        raise ValueError(f"{name} must be an integer.") from ex

    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be at least {min_value}.")

    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be at most {max_value}.")

    return value


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()

    if normalized_value in {"1", "true", "yes", "on"}:
        return True

    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise ValueError(
        f"{name} must be one of: true, false, 1, 0, yes, no, on, off."
    )


def _get_float_env(
    name: str,
    default: float,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError as ex:
        raise ValueError(f"{name} must be a number.") from ex

    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be at least {min_value}.")

    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be at most {max_value}.")

    return value


@dataclass(frozen=True)
class Settings:
    extractor_type: str = "rule"
    game_project_client_type: str = "local"
    game_project_api_base_url: str | None = None
    game_project_api_key: str | None = None
    uploaded_text_db_path: str = "uploaded_texts.db"
    uploaded_text_cleanup_max_age_hours: int = 24
    document_answerer_type: str = "llm"
    document_qa_model_client_type: str = "gemini"
    document_qa_model_name: str = "gemini-2.5-flash"
    document_qa_fallback_to_rule: bool = True
    classifier_type: str = "llm"
    summarizer_type: str = "llm"
    answerer_type: str = "llm"
    chatbot_type: str = "llm"
    risk_detector_type: str = "llm"
    risk_detection_fallback_to_rule: bool = True
    jira_task_generator_type: str = "llm"
    jira_task_generation_fallback_to_rule: bool = True
    ask_task_match_min_score: float = 0.3
    ask_task_suggest_max: int = 8
    retrieval_min_score: float = 0.3


def get_settings() -> Settings:
    return Settings(
        extractor_type=os.getenv("EXTRACTOR_TYPE", "rule").lower(),
        game_project_client_type=os.getenv("GAME_PROJECT_CLIENT_TYPE", "local").lower(),
        game_project_api_base_url=os.getenv("GAME_PROJECT_API_BASE_URL"),
        game_project_api_key=os.getenv("GAME_PROJECT_API_KEY"),
        uploaded_text_db_path=os.getenv(
            "APP_UPLOADED_TEXT_DB_PATH",
            "uploaded_texts.db",
        ),
        uploaded_text_cleanup_max_age_hours=_get_int_env(
            "APP_UPLOADED_TEXT_CLEANUP_MAX_AGE_HOURS",
            default=24,
            min_value=1,
            max_value=24 * 30,
        ),
        document_answerer_type=os.getenv(
            "DOCUMENT_ANSWERER_TYPE",
            "llm",
        ).lower(),
        document_qa_model_client_type=os.getenv(
            "DOCUMENT_QA_MODEL_CLIENT_TYPE",
            "gemini",
        ).lower(),
        document_qa_model_name=os.getenv(
            "DOCUMENT_QA_MODEL_NAME",
            "gemini-2.5-flash",
        ),
        document_qa_fallback_to_rule=_get_bool_env(
            "DOCUMENT_QA_FALLBACK_TO_RULE",
            default=True,
        ),
        classifier_type=os.getenv("CLASSIFIER_TYPE", "llm").lower(),
        summarizer_type=os.getenv("SUMMARIZER_TYPE", "llm").lower(),
        answerer_type=os.getenv("ANSWERER_TYPE", "llm").lower(),
        chatbot_type=os.getenv("CHATBOT_TYPE", "llm").lower(),
        risk_detector_type=os.getenv("RISK_DETECTOR_TYPE", "llm").lower(),
        risk_detection_fallback_to_rule=_get_bool_env(
            "RISK_DETECTION_FALLBACK_TO_RULE",
            default=True,
        ),
        jira_task_generator_type=os.getenv("JIRA_TASK_GENERATOR_TYPE", "llm").lower(),
        jira_task_generation_fallback_to_rule=_get_bool_env(
            "JIRA_TASK_GENERATION_FALLBACK_TO_RULE",
            default=True,
        ),
        ask_task_match_min_score=_get_float_env(
            "ASK_TASK_MATCH_MIN_SCORE",
            default=0.3,
            min_value=0.0,
            max_value=1.0,
        ),
        ask_task_suggest_max=_get_int_env(
            "ASK_TASK_SUGGEST_MAX",
            default=8,
            min_value=1,
            max_value=50,
        ),
        retrieval_min_score=_get_float_env(
            "RETRIEVAL_MIN_SCORE",
            default=0.3,
            min_value=0.0,
            max_value=1.0,
        ),
    )