from pathlib import Path

from app.rag.corpus import load_markdown_corpus


def test_frontmatter_is_metadata_and_sections_are_independent(tmp_path: Path) -> None:
    (tmp_path / "document.md").write_text(
        """---
title: Monitoring
category: operations
---
# Document
Intro text.
## Queue
Queue time explanation.
## Execution
Execution time explanation.
""",
        encoding="utf-8",
    )

    corpus = load_markdown_corpus(tmp_path)

    assert [item.section for item in corpus] == ["Introduction", "Queue", "Execution"]
    assert all(item.title == "Monitoring" for item in corpus)
    assert all(item.category == "operations" for item in corpus)
    assert all("title:" not in item.content for item in corpus)
