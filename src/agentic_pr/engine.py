from __future__ import annotations

from agentic_pr.config import AgentConfig, ConfigError
from agentic_pr.engines.base import CodingEngine
from agentic_pr.engines.aider_engine import AiderEngine


def get_engine(config: AgentConfig) -> CodingEngine:
    """Get the configured coding engine."""
    engine_name = getattr(config, "engine", "aider").lower()
    
    if engine_name == "aider":
        return AiderEngine()
    
    supported = ["aider"]
    raise ConfigError(
        f"Unsupported ENGINE={engine_name}. Supported engines: {', '.join(supported)}"
    )


def list_supported_engines() -> list[str]:
    """List all supported engine names."""
    return ["aider"]