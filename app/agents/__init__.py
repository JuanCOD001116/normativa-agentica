"""
Módulo de agentes y orquestación del sistema de normativa.

Expone las funciones principales para enrutar y ejecutar agentes.
"""

from .orchestrator import (
    AGENT_DOCUMENTS,
    AGENT_REGLAMENTO_ESTUDIANTES,
    AGENT_SCRAPING,
    AGENT_WEB,
    agent_reglamento_estudiantes,
    orchestrate,
    orchestrate_with_components,
    route_query,
)

__all__ = [
    "AGENT_DOCUMENTS",
    "AGENT_REGLAMENTO_ESTUDIANTES",
    "AGENT_SCRAPING",
    "AGENT_WEB",
    "agent_reglamento_estudiantes",
    "orchestrate",
    "orchestrate_with_components",
    "route_query",
]
