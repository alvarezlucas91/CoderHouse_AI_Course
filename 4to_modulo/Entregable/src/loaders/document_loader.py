from pathlib import Path

from langchain_core.documents import Document

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    JSONLoader,
)


class DocumentLoader:
    """
    Loads PDF, Markdown and JSON documents into LangChain Documents.
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".md",
        ".json",
    }

    def __init__(self, documents_path: Path):
        self.documents_path = Path(documents_path)

        if not self.documents_path.exists():
            raise FileNotFoundError(
                f"Directory '{self.documents_path}' does not exist."
            )

    def load(self) -> list[Document]:
        """
        Loads every supported document from the directory.
        """

        documents: list[Document] = []

        for file in self.documents_path.rglob("*"):

            if not file.is_file():
                continue

            if file.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            documents.extend(
                self._load_file(file)
            )

        print(f"Loaded {len(documents)} document(s).")

        return documents

    def _load_file(self, file: Path) -> list[Document]:

        suffix = file.suffix.lower()

        if suffix == ".pdf":
            loader = PyPDFLoader(str(file))

        elif suffix == ".md":
            loader = TextLoader(
                str(file),
                encoding="utf-8"
            )

        elif suffix == ".json":
            loader = JSONLoader(
                file_path=str(file),
                jq_schema=".[]",
                text_content=False
            )

        else:
            raise ValueError(
                f"Unsupported file type: {suffix}"
            )

        documents = loader.load()

        for document in documents:

            document.metadata.setdefault("source", file.name)
            document.metadata.setdefault("category", file.parent.name)

        return documents