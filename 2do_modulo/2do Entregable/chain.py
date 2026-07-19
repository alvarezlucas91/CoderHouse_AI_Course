import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from schemas import EntityExtraction


logger = logging.getLogger(__name__)


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Eres un experto en programación y arquitectura de software.

            Analiza el texto técnico proporcionado y extrae:

            - Las tecnologías mencionadas.
            - El nivel de criticidad: baja, media o alta.
            - Un resumen técnico.

            La respuesta debe contener todos los campos requeridos
            por el esquema estructurado.
            """,
        ),
        (
            "human",
            "{input}",
        ),
    ]
)


model = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0,
)


structured_model = model.with_structured_output(
    EntityExtraction
)


chain = prompt | structured_model


resilient_chain = chain.with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True,
)


async def process_text(text: str) -> EntityExtraction:
    logger.info("Iniciando procesamiento del texto.")

    try:
        result = await resilient_chain.ainvoke(
            {
                "input": text
            }
        )

        if result is None:
            logger.error(
                "El modelo no devolvió un objeto estructurado."
            )

            raise ValueError(
                "La respuesta del modelo está vacía."
            )

        logger.info(
            "Respuesta validada correctamente como EntityExtraction."
        )

        logger.debug(
            "Resultado validado: %s",
            result.model_dump()
        )

        return result

    except Exception:
        logger.exception(
            "Falló el procesamiento después de los reintentos."
        )

        raise