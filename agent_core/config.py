"""Central configuration.

Reads MODEL_NAME and every D:\ data root from .env ONLY — no hardcoded paths
live anywhere else in the codebase. This is what makes the CPU -> GitHub -> GPU
round-trip painless (PLAN: "CPU -> GitHub -> GPU discipline").
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # protected_namespaces=() silences pydantic's warning about the `model_*`
    # field prefix; `model_name` is the configurable Ollama tag.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    # --- Ollama / model ---
    ollama_host: str = "http://localhost:11434"
    model_name: str = "qwen2.5:7b-instruct-q4_K_M"
    embed_model: str = "bge-m3"

    # --- Data roots (on D:\) ---
    data_dir: Path = Path("D:/smart-mfg-agent/data")
    vectorstore_dir: Path = Path("D:/smart-mfg-agent/vectorstore")
    memory_dir: Path = Path("D:/smart-mfg-agent/memory")

    # --- Agent service (FastAPI) ---
    agent_host: str = "0.0.0.0"
    agent_port: int = 8000

    # --- Reproducibility ---
    seed: int = 42


# Import this singleton everywhere; never re-read the environment elsewhere.
settings = Settings()
