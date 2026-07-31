import json

from src.config import EVALUATION_DATASET
from src.rag_system import RAGSystem

from src.utils.metrics import (
    recall_at_k,
    precision_at_k,
    average,
)


def evaluate() -> None:
    """
    Evaluates the hybrid retriever using a golden dataset.
    """

    with open(EVALUATION_DATASET, "r", encoding="utf-8") as file:
        benchmark = json.load(file)

    rag = RAGSystem()

    recalls = []
    precisions = []

    print("\n========== Evaluation ==========\n")

    for sample in benchmark:

        question = sample["question"]
        expected = sample["expected_documents"]

        retrieved = rag.search(question)

        print("Retrieved documents:")
        for document in retrieved:
            print(f" - {document.metadata['source']}")
        print()

        recall = recall_at_k(
            retrieved,
            expected,
        )

        precision = precision_at_k(
            retrieved,
            expected,
        )

        recalls.append(recall)
        precisions.append(precision)

        print(f"Question : {question}")
        print(f"Recall@5 : {recall:.2f}")
        print(f"Precision@5 : {precision:.2f}")
        print("-" * 40)

    print("\n========== Summary ==========\n")

    print(f"Average Recall@5    : {average(recalls):.2f}")
    print(f"Average Precision@5 : {average(precisions):.2f}")


if __name__ == "__main__":
    evaluate()