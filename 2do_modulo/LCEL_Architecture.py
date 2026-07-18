import asyncio
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

gpt_4 = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

claude_3 = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    temperature=0
)

parser = StrOutputParser()

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Sos un asistente útil. Respondé de forma clara y concisa."
    ),
    (
        "human",
        "{pregunta}"
    )
])

gpt_chain = prompt | gpt_4 | parser

claude_chain = prompt | claude_3 | parser

async def main():

    input_data = {
        "pregunta": "¿Qué ventajas tiene asyncio en Python?"
    }

    print("=== Respuesta GPT ===")

    respuesta_gpt = await gpt_chain.ainvoke(
        input_data
    )

    print(respuesta_gpt)

    print("\n=== Respuesta Claude ===")

    respuesta_claude = await claude_chain.ainvoke(
        input_data
    )

    print(respuesta_claude)


if __name__ == "__main__":
    asyncio.run(main())
