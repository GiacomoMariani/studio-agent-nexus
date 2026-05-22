from dataclasses import dataclass


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
- For FAQ-style context, answer with the answer text after the relevant FAQ question. Do not return only the FAQ heading or question.
- If the retrieved context contains a question followed by an answer, include the answer, not just the question text.
- Do not start the final answer with copied document headings unless they are needed for clarity.
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

    return (
        f"[{block.source_id}] {block.filename}, {page_label}\n"
        f"{block.text.strip()}"
    )