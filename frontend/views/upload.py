from components import page_footer, page_header, placeholder


def render() -> None:
    page_header(
        "Knowledge Base",
        "Upload and manage the documents Studio Agent Nexus reasons over.",
    )
    placeholder("Upload page — coming in ticket-003 (wired to real ingestion).")
    page_footer("upload")
