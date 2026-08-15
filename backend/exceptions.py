class AppError(Exception):
    pass


class DatabaseConnectionError(AppError):
    pass


class QueryExecutionError(AppError):
    pass


class RecordNotFoundError(AppError):
    pass


class InvalidReferenceError(AppError):
    pass


class DuplicateRecordError(AppError):
    pass


class ValidationError(AppError):
    pass
