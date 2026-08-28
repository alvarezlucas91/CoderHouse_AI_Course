import hashlib
import re
from pathlib import Path

from app.schemas import Evidence


FRONTMATTER_PATTERN = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", re.DOTALL)


def load_markdown_corpus(documents_dir: Path) -> list[Evidence]:
    if not documents_dir.is_dir():
        raise FileNotFoundError(f"Corpus directory does not exist: {documents_dir}")

    evidence: list[Evidence] = []
    for path in sorted(documents_dir.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        metadata: dict[str, str] = {}
        match = FRONTMATTER_PATTERN.match(raw)
        if match:
            for line in match.group(1).splitlines():
                if ":" in line and not line.lstrip().startswith("#"):
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip().strip("'\"")
            raw = raw[match.end():].lstrip()

        title = metadata.get("title", path.stem.replace("_", " "))
        category = metadata.get("category", "unknown")
        sections = _split_by_heading(raw)
        for section_title, content in sections:
            identifier = hashlib.sha256(
                f"{path.name}|{section_title}|{content}".encode("utf-8")
            ).hexdigest()
            evidence.append(
                Evidence(
                    evidence_id=identifier,
                    content=content,
                    source=path.name,
                    title=title,
                    category=category,
                    section=section_title,
                    source_url=metadata.get("source_url") or None,
                    fused_score=0,
                    metadata={**metadata, "document_id": path.stem},
                )
            )
    return evidence


def _split_by_heading(markdown: str, max_chars: int = 1800) -> list[tuple[str, str]]:
    heading = "Introduction"
    buffer: list[str] = []
    sections: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal buffer
        text = "\n".join(buffer).strip()
        while text:
            boundary = min(max_chars, len(text))
            if boundary < len(text):
                paragraph = text.rfind("\n\n", 0, boundary)
                boundary = paragraph if paragraph > max_chars // 2 else boundary
            chunk, text = text[:boundary].strip(), text[boundary:].strip()
            if chunk:
                sections.append((heading, chunk))
        buffer = []

    for line in markdown.splitlines():
        if line.startswith("## "):
            flush()
            heading = line.removeprefix("## ").strip()
        else:
            buffer.append(line)
    flush()
    return sections

