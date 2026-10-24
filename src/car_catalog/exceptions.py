from typing import Any


class ApplicationError(Exception):
    pass


class ConfigurationError(ApplicationError):
    pass


class DataError(ApplicationError):
    pass


class DataImportError(DataError):
    pass


class RecordValidationError(DataError):
    def __init__(
        self,
        message: str,
        *,
        line_number: int | None = None,
        field: str | None = None,
        raw_record: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field
        self.raw_record = raw_record


class DataExportError(DataError):
    pass


class StorageError(ApplicationError):
    pass
