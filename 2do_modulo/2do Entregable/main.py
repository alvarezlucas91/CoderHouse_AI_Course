import asyncio
import logging

from chain import process_text


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def main():

    text = """
    La aplicación utiliza Python, FastAPI y PostgreSQL.
    Actualmente presenta errores de conexión con la base de datos.
    """

    result = await process_text(text)

    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())