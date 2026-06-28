from __future__ import annotations

from agentic_pr.config import AgentConfig, ConfigError
from agentic_pr.engines.base import CodingEngine
from agentic_pr.engines.aider_engine import AiderEngine
from agentic_pr.engines.openhands_engine import OpenHandsEngine


SUPPORTED_ENGINES = ["aider", "openhands"]


def get_engine(config: AgentConfig) -> CodingEngine:
    """Get the configured coding engine."""
    engine_name = getattr(config, "engine", "aider").lower()
    
    if engine_name == "aider":
        return AiderEngine()

    if engine_name == "openhands":
        if not config.openhands_experimental:
            raise ConfigError("ENGINE=openhands requires OPENHANDS_EXPERIMENTAL=true")
        return OpenHandsEngine(
            command=config.openhands_command,
            extra_args=config.openhands_extra_args,
            use_json_output=config.openhands_use_json_output,
            llm_base_url=config.openhands_llm_base_url,
            api_key=config.openhands_api_key,
            docker_image=config.openhands_docker_image,
            persistence_dir=str(config.openhands_persistence_dir) if config.openhands_persistence_dir else None,
        )

    raise ConfigError(
        f"Unsupported ENGINE={engine_name}. Supported engines: {', '.join(SUPPORTED_ENGINES)}"
    )


def list_supported_engines() -> list[str]:
    """List all supported engine names."""
    return list(SUPPORTED_ENGINES)
