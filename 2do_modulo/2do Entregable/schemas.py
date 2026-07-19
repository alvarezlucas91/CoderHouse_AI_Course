from pydantic import BaseModel, Field
from enum import Enum

class Criticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EntityExtraction(BaseModel):
    """Esquema para la extracción de entidades clave de un texto técnico."""
    
    tecnologias: list[str] = Field(min_length=1,description="Lista de tecnologías identificadas")
    nivel_de_criticidad: Criticidad = Field(description="Nivel de criticidad: baja, media o alta")
    resumen_tecnico: str = Field(min_length=1,description="Texto que resume a nivel tecnico la tecnología seleccionada")


