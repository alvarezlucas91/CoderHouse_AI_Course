# Technical Entity Extraction Pipeline

Pipeline asíncrono de extracción de entidades técnicas construido con **LangChain**, **LCEL**, **Pydantic** y **OpenAI**.

El script recibe un texto técnico sin procesar, como un log de error o una descripción de arquitectura, y devuelve un objeto estructurado con:

* Tecnologías identificadas.
* Nivel de criticidad (`baja`, `media` o `alta`).
* Resumen técnico.

## Estructura

```text
.
├── schemas.py
├── chain.py
├── main.py
└── requirements.txt
```

### `schemas.py`

Define el esquema de salida mediante Pydantic. También contiene el enum `Criticidad` y las validaciones de los campos.

### `chain.py`

Contiene la lógica principal del pipeline:

* `ChatPromptTemplate` para construir el prompt de forma modular.
* `ChatOpenAI` como modelo de lenguaje.
* `with_structured_output()` para obtener una respuesta validada según `EntityExtraction`.
* Composición LCEL mediante `prompt | model`.
* `with_retry()` para reintentar ante errores de validación o respuestas estructuradas inválidas.
* La función asíncrona `process_text(text)`.

### `main.py`

Contiene un ejemplo de ejecución del pipeline utilizando `ainvoke()` y muestra el resultado obtenido.

## Flujo

```text
Texto de entrada
      ↓
ChatPromptTemplate
      ↓
ChatOpenAI
      ↓
Salida estructurada
      ↓
Validación Pydantic
      ↓
EntityExtraction
```

La cadena principal se construye mediante LCEL:

```python
chain = prompt | model.with_structured_output(EntityExtraction)
```

Además, se incorpora una estrategia de reintentos para mejorar la resiliencia ante respuestas inválidas o incompletas.

## Ejecución

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

Configurar la variable de entorno:

```env
OPENAI_API_KEY=tu_api_key
```

Ejecutar el ejemplo:

```bash
python main.py
```

## Consideraciones

La salida del modelo no se utiliza directamente sin validación. El esquema Pydantic actúa como contrato de salida y permite detectar respuestas incompletas o inválidas antes de procesarlas.

Además, el prompt se define mediante `ChatPromptTemplate` en lugar de utilizar f-strings, manteniendo separadas las instrucciones del modelo y los datos de entrada.

El proyecto utiliza ejecución asíncrona y logs para facilitar la observación del proceso de validación y los posibles errores.
