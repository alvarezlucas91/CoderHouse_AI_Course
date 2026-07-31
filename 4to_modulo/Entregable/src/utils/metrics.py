from langchain_core.documents import Document


def recall_at_k(
    retrieved: list[Document],
    expected_documents: list[str],
) -> float:
    """
    Computes Recall@k.
    """

    retrieved_sources = {
        doc.metadata["source"]
        for doc in retrieved
    }

    expected = set(expected_documents)

    return float(
        len(retrieved_sources & expected) > 0
    )


def precision_at_k(
    retrieved: list[Document],
    expected_documents: list[str],
) -> float:
    """
    Computes Precision@k.
    """

    if not retrieved:
        return 0.0

    retrieved_sources = [
        doc.metadata["source"]
        for doc in retrieved
    ]

    relevant = sum(
        source in expected_documents
        for source in retrieved_sources
    )

    return relevant / len(retrieved)

def average(values: list[float]) -> float:
    """
    Computes the arithmetic mean of a list of values.
    """

    if not values:
        return 0.0

    return sum(values) / len(values)