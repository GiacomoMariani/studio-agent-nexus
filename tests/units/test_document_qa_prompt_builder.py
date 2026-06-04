from dataclasses import dataclass

_DEMO_NOTICE_PATTERNS = (
    "important demo notice",
    "fictional sample data only",
    "fictional portfolio-demo",
    "safe for local testing",
    "created for local testing",
    "does not describe any real company policy",
    "does not describe any real customer obligation",
)


@dataclass(frozen=True)
class RetrievedContextBlock:
    source_id: int
    filename: str
    page_number: int | None
    text: str


def build_document_qa_prompt(
    question: str,
    context_blocks: list[RetrievedContextBlock],
) -> str:
    formatted_context = "\n\n".join(
        _format_context_block(block)
        for block in context_blocks
    )

    return f"""You are a document-grounded business knowledge-base assistant.

Rules:
- Answer only using the retrieved context below.
- Do not use outside knowledge.
- Answer the user's exact question, not a nearby or more general topic.
- Prefer the most specific policy, product, architecture, or operational detail that directly answers the question.
- Ignore demo notices, safety disclaimers, and fictional-data warnings unless the user specifically asks about them.
- When documents are fictional demo documents, answer using the demo facts as demo policy facts.
- Do not respond only by saying the documents are fictional unless the user asks whether they are real.
- If the question asks about company policy and the retrieved context is demo policy/FAQ content, phrase the answer as "According to the demo documents..." or "For this demo business..."
- If the context does not contain the answer, say that the answer was not found in the uploaded documents.
- If the context is incomplete, answer only the supported part and clearly say what is missing.
- Cite sources using [source_id].
- Do not invent company policy, pricing, legal, HR, or support details.

Question:
{question}

Retrieved context:
{formatted_context}

Answer:
"""


def _format_context_block(block: RetrievedContextBlock) -> str:
    page_label = (
        f"page {block.page_number}"
        if block.page_number is not None
        else "page unavailable"
    )

    clean_text = _remove_demo_notice_text(block.text)

    return (
        f"[{block.source_id}] {block.filename}, {page_label}\n"
        f"{clean_text}"
    )


def _remove_demo_notice_text(text: str) -> str:
    sentences = text.replace("\n", " ").split(". ")

    kept_sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
        and not any(
            pattern in sentence.lower()
            for pattern in _DEMO_NOTICE_PATTERNS
        )
    ]

    cleaned_text = ". ".join(kept_sentences).strip()

    return cleaned_text or text.strip()