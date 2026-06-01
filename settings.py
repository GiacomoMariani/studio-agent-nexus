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


@dataclass(frozen=True)
class Settings:
    extractor_type: str = "rule"
    game_project_client_type: str = "local"
    game_project_api_base_url: str | None = None
    game_project_api_key: str | None = None
    uploaded_text_db_path: str = "uploaded_texts.db"
    uploaded_text_cleanup_max_age_hours: int = 24
    document_answerer_type: str = "rule"
    document_qa_model_client_type: str = "fake"
    document_qa_model_name: str = "fake-document-qa"
    document_qa_fallback_to_rule: bool = True


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
            "rule",
        ).lower(),
        document_qa_model_client_type=os.getenv(
            "DOCUMENT_QA_MODEL_CLIENT_TYPE",
            "fake",
        ).lower(),
        document_qa_model_name=os.getenv(
            "DOCUMENT_QA_MODEL_NAME",
            "fake-document-qa",
        ),
        document_qa_fallback_to_rule=_get_bool_env(
            "DOCUMENT_QA_FALLBACK_TO_RULE",
            default=True,
        ),
    )