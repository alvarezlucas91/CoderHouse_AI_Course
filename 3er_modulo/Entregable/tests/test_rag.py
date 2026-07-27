import asyncio

from src.rag_chain import get_rag_response


async def main():

    print("=" * 60)
    print("TEST 1 - QUESTION ANSWERED BY DOCUMENTS")
    print("=" * 60)

    response = await get_rag_response(
        "What is the main purpose of Amazon Redshift?"
    )

    print(
        response.model_dump_json(
            indent=2
        )
    )


    print("=" * 60)
    print("TEST 2 - OUT-OF-CONTEXT QUESTION")
    print("=" * 60)

    response = await get_rag_response(
        "What is the capital of Japan?"
    )

    print(
        response.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":

    asyncio.run(main())