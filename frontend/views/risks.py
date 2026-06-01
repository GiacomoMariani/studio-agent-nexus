from components import page_footer, page_header, placeholder


def render() -> None:
    page_header(
        "Risks & Contradictions",
        "Detect risks, gaps, and conflicts across your documents.",
    )
    placeholder("Risks page — coming in ticket-006 (mock-driven).")
    page_footer("risks")
