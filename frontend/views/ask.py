from components import page_footer, page_header, placeholder


def render() -> None:
    page_header(
        "Ask",
        "Ask anything. Every answer is grounded in your uploaded documents.",
    )
    placeholder("Ask page — coming in ticket-004 (wired to real Q&A).")
    page_footer("ask")
