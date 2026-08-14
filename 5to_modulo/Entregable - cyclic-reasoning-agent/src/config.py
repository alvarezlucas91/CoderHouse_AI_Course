from pathlib import Path
import os

from dotenv import load_dotenv


# ============================================================
# PATHS DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

KNOWLEDGE_BASE_PATH = DATA_DIR / "technical_knowledge.json"
SQLITE_DB_PATH = BASE_DIR / "agent_memory.db"


# ============================================================
# VARIABLES DE ENTORNO
# ============================================================

# Carga las variables definidas en el archivo .env
load_dotenv(BASE_DIR / ".env")


def _get_required_env(variable_name: str) -> str:
    """
    Obtiene una variable de entorno obligatoria.

    Esta función se utiliza principalmente para credenciales necesarias
    para ejecutar el agente, como GROQ_API_KEY. Si la variable no existe
    o está vacía, se genera un error explícito para evitar iniciar el
    agente con una configuración inválida.

    Ejemplo:
        GROQ_API_KEY debe estar definida en el archivo .env:

        GROQ_API_KEY=gsk_xxxxxxxxx

    Args:
        variable_name:
            Nombre de la variable de entorno que se desea recuperar.

    Returns:
        Valor de la variable de entorno.

    Raises:
        RuntimeError:
            Si la variable no existe o está vacía.
    """

    value = os.getenv(variable_name)

    if not value or not value.strip():
        raise RuntimeError(
            f"La variable de entorno '{variable_name}' es obligatoria "
            "y no está definida."
        )

    return value.strip()


def _get_positive_int_env(
    variable_name: str,
    default: int,
) -> int:
    """
    Obtiene una variable de entorno numérica positiva.

    Se utiliza para parámetros operativos del agente, como el límite
    máximo de pasos del grafo. Si la variable no existe, utiliza el
    valor por defecto.

    Args:
        variable_name:
            Nombre de la variable de entorno.
        default:
            Valor utilizado cuando la variable no está definida.

    Returns:
        Número entero positivo.

    Raises:
        RuntimeError:
            Si la variable contiene un valor no numérico o menor a 1.
    """

    raw_value = os.getenv(variable_name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)

    except ValueError as exc:
        raise RuntimeError(
            f"La variable '{variable_name}' debe contener un número entero."
        ) from exc

    if value < 1:
        raise RuntimeError(
            f"La variable '{variable_name}' debe ser mayor o igual a 1."
        )

    return value


# ============================================================
# CONFIGURACIÓN GROQ
# ============================================================

GROQ_API_KEY: str = _get_required_env("GROQ_API_KEY")

# El modelo se define mediante variable de entorno para evitar acoplar
# el proyecto a un modelo específico.
GROQ_MODEL: str = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
).strip()


# ============================================================
# CONFIGURACIÓN DEL AGENTE
# ============================================================

# Evita ciclos infinitos del tipo:
#
# agent -> tools -> agent -> tools -> ...
#
# Si el agente supera este número de pasos, LangGraph detendrá
# la ejecución.
RECURSION_LIMIT: int = _get_positive_int_env(
    "RECURSION_LIMIT",
    default=10,
)


# ============================================================
# VALIDACIÓN DE ARCHIVOS
# ============================================================

def validate_project_configuration() -> None:
    """
    Valida que los recursos básicos del proyecto estén disponibles.

    Se ejecutará antes de inicializar el agente para detectar problemas
    de configuración lo antes posible.

    Actualmente comprueba que exista la base de conocimiento que contiene
    incidentes, firmware y configuraciones de los dispositivos IoT.

    Raises:
        FileNotFoundError:
            Si no existe technical_knowledge.json.
        RuntimeError:
            Si GROQ_MODEL está vacío.
    """

    if not KNOWLEDGE_BASE_PATH.exists():
        raise FileNotFoundError(
            "No se encontró la base de conocimiento técnica en "
            f"'{KNOWLEDGE_BASE_PATH}'."
        )

    if not GROQ_MODEL:
        raise RuntimeError(
            "La variable GROQ_MODEL no puede estar vacía."
        )