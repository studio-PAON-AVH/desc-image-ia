from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import status


class AppException(Exception):
    """Exception de base pour toutes les erreurs métier."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppException):
    """Ressource introuvable (404)."""

    def __init__(self, resource: str = "Ressource"):
        super().__init__(f"{resource} introuvable", "NOT_FOUND")


class ForbiddenError(AppException):
    """Accès refusé (403)."""

    def __init__(self, message: str = "Accès interdit"):
        super().__init__(message, "FORBIDDEN")


class UnauthorizedError(AppException):
    """Non authentifié (401)."""

    def __init__(self, message: str = "Authentification requise"):
        super().__init__(message, "UNAUTHORIZED")


class ConflictError(AppException):
    """Conflit de données (409) — ex: email déjà utilisé, fichier déjà existant."""

    def __init__(self, message: str = "Ressource déjà existante"):
        super().__init__(message, "CONFLICT")


class ValidationError(AppException):
    """Données invalides (422)."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class ServiceUnavailableError(AppException):
    """Service externe indisponible (503) — ex: modèle IA injoignable."""

    def __init__(self, service: str = "Service"):
        super().__init__(f"{service} indisponible", "SERVICE_UNAVAILABLE")


class FileTooLargeError(AppException):
    """Fichier trop volumineux (413)."""

    def __init__(self, max_size_mb: int = 50):
        super().__init__(f"Fichier trop volumineux (max {max_size_mb} Mo)", "FILE_TOO_LARGE")


class InvalidFileError(AppException):
    """Fichier invalide ou corrompu (400)."""

    def __init__(self, message: str = "Fichier invalide"):
        super().__init__(message, "INVALID_FILE")


_STATUS_MAP: dict[type[AppException], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ServiceUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    FileTooLargeError: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    InvalidFileError: status.HTTP_400_BAD_REQUEST,
    AppException: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def get_http_status(exc: AppException) -> int:
    return _STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    À enregistrer dans main.py :
        app.add_exception_handler(AppException, app_exception_handler)
    """
    return JSONResponse(
        status_code=get_http_status(exc),
        content={"success": False, "error": exc.message, "code": exc.code},
    )
