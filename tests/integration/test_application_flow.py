import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from car_catalog.config import load_config
from car_catalog.protocols import AsyncExternalMarketClient
from car_catalog.services import (
    AsyncVehicleMarketService,
    async_run_import_export_pipeline,
    run_import_export_pipeline,
)

@pytest.mark.integration
def test_full_application_pipeline_execution(tmp_path: Path, sample_csv_with_errors: Path) -> None:
    output_file = tmp_path / "final_output.json"
    error_csv = tmp_path / "rejected_records.csv"
    output_file.write_text('[{"initial": true}]', encoding="utf-8")

    config_path = tmp_path / "app_run_config.yaml"
    config_content = f"""
input:
  path: "{sample_csv_with_errors.as_posix()}"
  format: "csv"
output:
  path: "{output_file.as_posix()}"
  format: "json"
processing:
  skip_invalid: true
  backup_existing: true
  error_csv_path: "{error_csv.as_posix()}"
  filters:
    min_year: 2015
    max_year: 2025
    min_price: 10000.0
    max_price: 100000.0
"""
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)

    stats = run_import_export_pipeline(config)

    assert stats.total == 5
    assert stats.valid == 2
    assert stats.invalid == 3
    assert stats.exported == 2

    backup_file = output_file.with_suffix(".json.bak")
    assert backup_file.exists()
    assert '[{"initial": true}]' in backup_file.read_text(encoding="utf-8")

    assert error_csv.exists()
    assert "Brand cannot be empty" in error_csv.read_text(encoding="utf-8")

    assert output_file.exists()
    exported_data = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(exported_data) == 2

@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_application_pipeline_flow(tmp_path: Path, sample_csv_file: Path) -> None:
    output_file = tmp_path / "async_final_output.json"
    config_path = tmp_path / "async_run_config.yaml"
    config_content = f"""
input:
  path: "{sample_csv_file.as_posix()}"
  format: "csv"
output:
  path: "{output_file.as_posix()}"
  format: "json"
processing:
  skip_invalid: false
  backup_existing: false
  filters:
    min_year: 2020
    max_year: 2025
"""
    config_path.write_text(config_content, encoding="utf-8")
    config = load_config(config_path)

    mock_client = AsyncMock(spec=AsyncExternalMarketClient)
    mock_client.fetch_market_evaluation.return_value = {"estimated_price": 30000.0}
    market_service = AsyncVehicleMarketService(mock_client)

    stats = await async_run_import_export_pipeline(config, market_service)

    assert stats.total == 3
    assert stats.valid == 3
    assert stats.exported == 3
    assert mock_client.fetch_market_evaluation.await_count == 3
    assert output_file.exists()
