"""Modelos ORM. Importar este paquete registra todas las tablas en ``Base.metadata``."""

from app.bd.modelos.administracion import CacheMetadatos, Configuracion, EventoTecnico
from app.bd.modelos.borradores import VersionBorrador
from app.bd.modelos.casos import CambioNorma, Caso, Coleccion
from app.bd.modelos.corpus import Documento, ExclusionCorpus, Fragmento
from app.bd.modelos.importacion import ImportacionReferencias, ReferenciaImportada
from app.bd.modelos.seguridad import Cuenta, Sesion
from app.bd.modelos.solicitudes import (
    Decision,
    FragmentoRecuperado,
    FuenteAportada,
    Resultado,
    Solicitud,
    Verificacion,
)

__all__ = [
    "CacheMetadatos",
    "CambioNorma",
    "Caso",
    "Coleccion",
    "Configuracion",
    "Cuenta",
    "Decision",
    "Documento",
    "EventoTecnico",
    "ExclusionCorpus",
    "Fragmento",
    "FragmentoRecuperado",
    "FuenteAportada",
    "ImportacionReferencias",
    "ReferenciaImportada",
    "Resultado",
    "Sesion",
    "Solicitud",
    "Verificacion",
    "VersionBorrador",
]

# Tablas que contienen datos de un caso: toda consulta sobre ellas filtra por caso_id (4.5).
TABLAS_DE_CASO = frozenset(
    {
        "version_borrador",
        "solicitud",
        "fragmento_recuperado",
        "resultado",
        "verificacion",
        "decision",
        "fuente_aportada",
        "cambio_norma",
    }
)
