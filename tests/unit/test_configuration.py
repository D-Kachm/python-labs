from pathlib import Path
import pytest
from car_catalog.config import AppConfig, load_config
from car_catalog.exceptions import ConfigurationError


@pytest.mark.unit
def test_load_valid_yaml_config(sample_yaml_config: Path) -> None:
    config = load_config(sample_yaml_config)
    assert isinstance(config, AppConfig)
    assert config.input.format == "csv"
    assert config.output.format == "json"
    assert config.processing.skip_invalid is True
    assert config.processing.filters.min_year == 2020
    assert config.processing.filters.max_year == 2025
    assert config.processing.filters.min_price == pytest.approx(20000.0)
    assert config.processing.filters.max_price == pytest.approx(80000.0)
    assert config.logging.level == "INFO"


@pytest.mark.unit
def test_load_config_missing_file_raises_error(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.yaml"
    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        load_config(non_existent)


@pytest.mark.unit
def test_load_config_invalid_yaml_syntax(tmp_path: Path) -> None:
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("app: [broken: yaml: syntax", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid YAML configuration"):
        load_config(bad_yaml)


@pytest.mark.unit
def test_config_invalid_year_range_raises_error(tmp_path: Path, sample_csv_file: Path) -> None:
    bad_config = tmp_path / "bad_range.yaml"
    content = f"""
input:
  path: "{sample_csv_file.as_posix()}"
  format: "csv"
output:
  path: "{tmp_path.as_posix()}/out.json"
  format: "json"
processing:
  filters:
    min_year: 2025
    max_year: 2010
"""
    bad_config.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="max_year cannot be less than min_year"):
        load_config(bad_config)


@pytest.mark.unit
def test_config_invalid_price_range_raises_error(tmp_path: Path, sample_csv_file: Path) -> None:
    bad_config = tmp_path / "bad_price.yaml"
    content = f"""
input:
  path: "{sample_csv_file.as_posix()}"
  format: "csv"
output:
  path: "{tmp_path.as_posix()}/out.json"
  format: "json"
processing:
  filters:
    min_price: 50000.0
    max_price: 10000.0
"""
    bad_config.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="max_price cannot be less than min_price"):
        load_config(bad_config)


@pytest.mark.unit
def test_config_missing_input_file_raises_error(tmp_path: Path) -> None:
    missing_input = tmp_path / "missing_input.yaml"
    content = f"""
input:
  path: "{tmp_path.as_posix()}/no_such_file.csv"
  format: "csv"
output:
  path: "{tmp_path.as_posix()}/out.json"
  format: "json"
"""
    missing_input.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Input file does not exist"):
        load_config(missing_input)


@pytest.mark.unit
def test_config_env_overrides_with_monkeypatch(
    sample_yaml_config: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_SKIP_INVALID", "false")
    monkeypatch.setenv("APP_LOG_LEVEL", "DEBUG")

    config = load_config(sample_yaml_config)
    assert config.processing.skip_invalid is False
    assert config.logging.level == "DEBUG"


@pytest.mark.unit
def test_config_env_removal_with_monkeypatch(
    sample_yaml_config: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_SKIP_INVALID", raising=False)
    monkeypatch.delenv("APP_LOG_LEVEL", raising=False)

    config = load_config(sample_yaml_config)
    assert config.processing.skip_invalid is True
    assert config.logging.level == "INFO"
