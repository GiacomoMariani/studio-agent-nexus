from components import page_footer, page_header, placeholder


def render() -> None:
    page_header(
        "Board",
        "Fetch the to-do from a document, review what's ready, and let planning surface "
        "the work you're still missing.",
    )
    placeholder("Board page — coming in ticket-005 (SQLite-backed tasks + mocked GitHub).")
    page_footer("board")
