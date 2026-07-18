import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

model = ChatOpenAI(model="gpt-4o", temperature=0.7)
parser = StrOutputParser()

# --- Paso 1: generar una descripción de producto ---
descripcion_chain = (
    ChatPromptTemplate.from_template(
        "Escribí una descripción de producto de 2 oraciones para: {producto}"
    )
    | model
    | parser
)

# --- Paso 2: condensar esa descripción a un tweet ---
tweet_chain = (
    ChatPromptTemplate.from_template(
        "Resumí esto en un tweet de menos de 120 caracteres, con 1 emoji: {descripcion}"
    )
    | model
    | parser
)

# --- Cadena secuencial: la salida (string) del paso 1 se "envuelve" en el dict
#     que espera el paso 2. La función lambda se convierte en Runnable automáticamente. ---
full_chain = descripcion_chain | (lambda desc: {"descripcion": desc}) | tweet_chain

async def main():
    # .abatch procesa varios productos a la vez (más eficiente que un for con ainvoke)
    productos = [{"producto": "termo de acero 1L"}, {"producto": "mochila antirrobo"}]
    tweets = await full_chain.abatch(productos)
    for p, t in zip(productos, tweets):
        print(f"{p['producto']}: {t}")

if __name__ == "__main__":
    asyncio.run(main())
