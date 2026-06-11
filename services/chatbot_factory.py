from providers.document_qa_model_client_factory import (
    get_document_qa_model_client,
)
from services.chatbot import Chatbot
from services.llm_chatbot import FallbackChatbot, LlmChatbot
from services.rule_based_chatbot import RuleBasedChatbot
from settings import Settings


def get_chatbot(settings: Settings) -> Chatbot:
    rule_chatbot = RuleBasedChatbot()

    if settings.chatbot_type == "rule":
        return rule_chatbot

    if settings.chatbot_type == "llm":
        try:
            llm_chatbot = LlmChatbot(
                model_client=get_document_qa_model_client(settings),
            )
        except ValueError:
            # No provider key / misconfigured client → degrade to the rule path.
            return rule_chatbot

        return FallbackChatbot(
            primary=llm_chatbot,
            fallback=rule_chatbot,
        )

    raise ValueError(
        "Unsupported CHATBOT_TYPE. Supported values: rule, llm."
    )
