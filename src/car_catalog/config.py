from functools import lru_cache
import os
from dataclasses import dataclass, field
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
from car_catalog.exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class FilterConfig:
    min_year: int = 1886
    max_year: int = 2026
    min_price: float = 0.0
    max_price: float = 1_000_000_000.0


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    skip_invalid: bool = True
    backup_existing: bool = False
    error_csv_path: Path | None = None
    filters: FilterConfig = field(default_factory=FilterConfig)


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"
    path: Path = field(default_factory=lambda: Path("logs/application.log"))
    console: bool = True


@dataclass(frozen=True, slots=True)
class InputConfig:
    path: Path = field(default_factory=lambda: Path("data/cars.csv"))
    format: str = "csv"


@dataclass(frozen=True, slots=True)
class OutputConfig:
    path: Path = field(default_factory=lambda: Path("output/cars.json"))
    format: str = "json"


@dataclass(frozen=True, slots=True)
class AppConfig:
    input: InputConfig
    output: OutputConfig
    processing: ProcessingConfig
    logging: LoggingConfig


def validate_config(config: AppConfig) -> None:
    if not config.input.path.exists():
        raise ConfigurationError(f"Input file does not exist: {config.input.path}")
    if config.processing.filters.min_year < 1886:
        raise ConfigurationError("min_year must be at least 1886")
    if config.processing.filters.max_year < config.processing.filters.min_year:
        raise ConfigurationError("max_year cannot be less than min_year")
    if config.processing.filters.min_price < 0:
        raise ConfigurationError("min_price cannot be negative")
    if config.processing.filters.max_price < config.processing.filters.min_price:
        raise ConfigurationError("max_price cannot be less than min_price")
    valid_formats = {"csv", "json", "jsonl", "yaml", "yml"}
    if config.input.format.lower() not in valid_formats:
        raise ConfigurationError(f"Unsupported input format: {config.input.format}")
    if config.output.format.lower() not in valid_formats:
        raise ConfigurationError(f"Unsupported output format: {config.output.format}")


def load_config(path: Path | str) -> AppConfig:
    cfg_path = Path(path)
    try:
        with cfg_path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {cfg_path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError("Invalid YAML configuration") from error

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration file must contain a top-level mapping")

    try:
        input_data = raw.get("input", {})
        input_path_val = input_data.get("path", "data/cars.csv")
        input_fmt_val = input_data.get("format", Path(input_path_val).suffix.lstrip(".").lower() or "csv")
        input_cfg = InputConfig(path=Path(input_path_val), format=str(input_fmt_val))

        output_data = raw.get("output", {})
        output_path_val = output_data.get("path", "output/cars.json")
        output_fmt_val = output_data.get("format", Path(output_path_val).suffix.lstrip(".").lower() or "json")
        output_cfg = OutputConfig(path=Path(output_path_val), format=str(output_fmt_val))

        proc_data = raw.get("processing", {})
        filt_data = proc_data.get("filters", {})
        filters_cfg = FilterConfig(
            min_year=int(filt_data.get("min_year", proc_data.get("min_year", 1886))),
            max_year=int(filt_data.get("max_year", proc_data.get("max_year", 2026))),
            min_price=float(filt_data.get("min_price", proc_data.get("min_price", 0.0))),
            max_price=float(filt_data.get("max_price", proc_data.get("max_price", 1_000_000_000.0))),
        )

        skip_inv_env = os.environ.get("APP_SKIP_INVALID")
        skip_invalid = (
            (skip_inv_env.lower() in {"true", "1", "yes"})
            if skip_inv_env is not None
            else bool(proc_data.get("skip_invalid", True))
        )
        backup_existing = bool(proc_data.get("backup_existing", False))
        err_path_val = proc_data.get("error_csv_path")
        error_csv_path = Path(err_path_val) if err_path_val else None

        processing_cfg = ProcessingConfig(
            skip_invalid=skip_invalid,
            backup_existing=backup_existing,
            error_csv_path=error_csv_path,
            filters=filters_cfg,
        )

        log_data = raw.get("logging", {})
        log_level = os.environ.get("APP_LOG_LEVEL") or str(log_data.get("level", "INFO"))
        log_path = Path(log_data.get("path", "logs/application.log"))
        console_log = bool(log_data.get("console", True))

        logging_cfg = LoggingConfig(
            level=log_level,
            path=log_path,
            console=console_log,
        )

        config = AppConfig(
            input=input_cfg,
            output=output_cfg,
            processing=processing_cfg,
            logging=logging_cfg,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigurationError("Configuration structure is invalid") from error

    validate_config(config)
    return config


class Settings(BaseSettings):
    app_name: str = "Car Catalog"
    environment: str = "development"
    database_url: str = "sqlite:///cars.db"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
