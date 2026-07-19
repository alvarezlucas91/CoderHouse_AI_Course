import asyncio
import time


# Semaphore global:
# como máximo 2 llamadas pueden ejecutarse al mismo tiempo
semaphore = asyncio.Semaphore(2)


async def gpt_4_call(call_id: int) -> str:
    async with semaphore:
        start = time.perf_counter()

        print(f"[{call_id}] GPT-4 inicia")

        await asyncio.sleep(1)

        elapsed = time.perf_counter() - start
        print(f"[{call_id}] GPT-4 termina en {elapsed:.2f}s")

        return f"Respuesta GPT-4 - llamada {call_id}"


async def claude_3_call(call_id: int) -> str:
    async with semaphore:
        start = time.perf_counter()

        print(f"[{call_id}] Claude 3 inicia")

        await asyncio.sleep(1.5)

        elapsed = time.perf_counter() - start
        print(f"[{call_id}] Claude 3 termina en {elapsed:.2f}s")

        return f"Respuesta Claude 3 - llamada {call_id}"


async def local_llama_call(call_id: int) -> str:
    async with semaphore:
        start = time.perf_counter()

        print(f"[{call_id}] Local Llama inicia")

        await asyncio.sleep(3)

        elapsed = time.perf_counter() - start
        print(f"[{call_id}] Local Llama termina en {elapsed:.2f}s")

        return f"Respuesta Local Llama - llamada {call_id}"
        
        
async def orchestrate_calls():
    """ Orquestador para las llamadas hacia los LLM """


    tasks = [
        asyncio.create_task(gpt_4_call(1)),
        asyncio.create_task(claude_3_call(1)),
        asyncio.create_task(local_llama_call(1)),
    ]

    try:
        async with asyncio.timeout(2):
            results = await asyncio.gather(*tasks)

            print("\nResultados:")
            for result in results:
                print(result)

    except TimeoutError:
        print("\nERROR: La ejecución superó el límite de 2 segundos.")

        for task in tasks:
            task.cancel()

        await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

async def run_simulations():
    """ Función para realizar simulaciones de prueba """

    tasks = []

    for i in range(10):
        tasks.extend([
            asyncio.create_task(gpt_4_call(i)),
            asyncio.create_task(claude_3_call(i)),
            asyncio.create_task(local_llama_call(i)),
        ])

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True
    )

    print("\nTodas las simulaciones finalizaron.")

    for result in results:
        print(result)


async def main():
    """ Función principal utilizando el orquestador con las simulaciones de testing. """

    print("=== Orquestación de 3 modelos ===")

    await orchestrate_calls()

    print("\n=== 10 simulaciones con máximo 2 concurrentes ===")

    await run_simulations()


if __name__ == "__main__":
    asyncio.run(main())