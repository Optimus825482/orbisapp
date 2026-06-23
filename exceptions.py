"""
Custom Exception Classes
========================

Bu modül, uygulama genelindeki custom exception sınıflarını içerir.
Tutarlı error handling ve anlamlı hata mesajları için kullanılır.

Kullanım:
    from exceptions import AstroCalculationError, InvalidDateError, APIError
    raise InvalidDateError("Geçersiz tarih: 32/01/1990")
"""

from functools import wraps
from typing import Optional, Any


# =============================================================================
# BASE EXCEPTION
# =============================================================================
class AstroError(Exception):
    """
    Base exception class for all astroloji uygulaması hataları.
    
    Tüm custom exception'lar bu sınıftan türetilir.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        AstroError'u başlat.
        
        Args:
            message: Hata mesajı
            error_code: Hata kodu (opsiyonel)
            details: Ek hata detayları (opsiyonel)
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Exception'ı dict olarak döndür (API response için)."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }
    
    def __str__(self) -> str:
        """String representation."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


# =============================================================================
# VALIDATION ERRORS
# =============================================================================
class ValidationError(AstroError):
    """Validasyon hatası - kullanıcı girdisi geçersiz."""
    pass


class InvalidDateError(ValidationError):
    """Geçersiz tarih hatası."""
    
    def __init__(self, date_value: Any, format_hint: str = "%Y-%m-%d"):
        """
        InvalidDateError'u başlat.
        
        Args:
            date_value: Geçersiz tarih değeri
            format_hint: Beklenen format
        """
        self.date_value = date_value
        self.format_hint = format_hint
        message = f"Geçersiz tarih: '{date_value}'. Beklenen format: {format_hint}"
        super().__init__(
            message=message,
            error_code="INVALID_DATE",
            details={"date_value": str(date_value), "expected_format": format_hint}
        )


class InvalidTimeError(ValidationError):
    """Geçersiz saat hatası."""
    
    def __init__(self, time_value: Any, format_hint: str = "%H:%M"):
        """
        InvalidTimeError'u başlat.
        
        Args:
            time_value: Geçersiz saat değeri
            format_hint: Beklenen format
        """
        self.time_value = time_value
        self.format_hint = format_hint
        message = f"Geçersiz saat: '{time_value}'. Beklenen format: {format_hint}"
        super().__init__(
            message=message,
            error_code="INVALID_TIME",
            details={"time_value": str(time_value), "expected_format": format_hint}
        )


class InvalidCoordinatesError(ValidationError):
    """Geçersiz koordinat hatası."""
    
    def __init__(self, latitude: float, longitude: float):
        """
        InvalidCoordinatesError'u başlat.
        
        Args:
            latitude: Enlem değeri
            longitude: Boylam değeri
        """
        self.latitude = latitude
        self.longitude = longitude
        message = f"Geçersiz koordinatlar: Enlem={latitude} (-90 ile 90 arası olmalı), Boylam={longitude} (-180 ile 180 arası olmalı)"
        super().__init__(
            message=message,
            error_code="INVALID_COORDINATES",
            details={"latitude": latitude, "longitude": longitude}
        )


# =============================================================================
# CALCULATION ERRORS
# =============================================================================
class CalculationError(AstroError):
    """Astrolojik hesaplama hatası."""
    pass


class EphemerisError(CalculationError):
    """Ephemeris hesaplama hatası."""
    
    def __init__(self, details: str):
        """
        EphemerisError'u başlat.
        
        Args:
            details: Hata detayları
        """
        message = f"Ephemeris hesaplama hatası: {details}"
        super().__init__(
            message=message,
            error_code="EPHEMERIS_ERROR",
            details={"ephemeris_details": details}
        )


class HouseCalculationError(CalculationError):
    """Ev hesaplama hatası."""
    
    def __init__(self, house_system: str, details: str):
        """
        HouseCalculationError'u başlat.
        
        Args:
            house_system: Ev sistemi
            details: Hata detayları
        """
        self.house_system = house_system
        message = f"Ev hesaplama hatası ({house_system}): {details}"
        super().__init__(
            message=message,
            error_code="HOUSE_CALCULATION_ERROR",
            details={"house_system": house_system, "calculation_details": details}
        )


# =============================================================================
# API ERRORS
# =============================================================================
class APIError(AstroError):
    """API çağrısı hatası."""
    
    def __init__(
        self, 
        provider: str, 
        status_code: Optional[int] = None,
        details: Optional[str] = None
    ):
        """
        APIError'u başlat.
        
        Args:
            provider: API sağlayıcısı (Hyperbolic, OpenRouter, vb.)
            status_code: HTTP status code
            details: Hata detayları
        """
        self.provider = provider
        self.status_code = status_code
        self.details = details or ""
        
        message = f"{provider} API hatası"
        if status_code:
            message += f" (Status: {status_code})"
        if details:
            message += f": {details}"
        
        super().__init__(
            message=message,
            error_code="API_ERROR",
            details={
                "provider": provider,
                "status_code": status_code,
                "api_details": details
            }
        )


class APITimeoutError(APIError):
    """API timeout hatası."""
    
    def __init__(self, provider: str, timeout_seconds: int):
        """
        APITimeoutError'u başlat.
        
        Args:
            provider: API sağlayıcısı
            timeout_seconds: Timeout süresi
        """
        message = f"{provider} API timeout ({timeout_seconds}s)"
        super().__init__(
            provider=provider,
            status_code=None,
            details=f"Request timeout after {timeout_seconds} seconds"
        )
        self.error_code = "API_TIMEOUT"


class APIRateLimitError(APIError):
    """API rate limit hatası."""
    
    def __init__(self, provider: str, retry_after: Optional[int] = None):
        """
        APIRateLimitError'u başlat.
        
        Args:
            provider: API sağlayıcısı
            retry_after: Retry header değeri (saniye)
        """
        message = f"{provider} API rate limit aşıldı"
        if retry_after:
            message += f". {retry_after} saniye sonra tekrar deneyin."
        
        super().__init__(
            provider=provider,
            status_code=429,
            details=f"Rate limit exceeded. Retry after {retry_after}s" if retry_after else "Rate limit exceeded"
        )
        self.error_code = "API_RATE_LIMIT"
        self.retry_after = retry_after


# =============================================================================
# DATABASE ERRORS
# =============================================================================
class DatabaseError(AstroError):
    """Veritabanı hatası."""
    pass


class SessionNotFoundError(DatabaseError):
    """Session bulunamadı hatası."""
    
    def __init__(self, session_id: str):
        """
        SessionNotFoundError'u başlat.
        
        Args:
            session_id: Session ID
        """
        self.session_id = session_id
        message = f"Session bulunamadı: {session_id}"
        super().__init__(
            message=message,
            error_code="SESSION_NOT_FOUND",
            details={"session_id": session_id}
        )


class SaveError(DatabaseError):
    """Kaydetme hatası."""
    
    def __init__(self, resource: str, details: str):
        """
        SaveError'u başlat.
        
        Args:
            resource: Kaynak tipi (session, calculation, vb.)
            details: Hata detayları
        """
        message = f"{resource} kaydedilirken hata: {details}"
        super().__init__(
            message=message,
            error_code="SAVE_ERROR",
            details={"resource": resource, "save_details": details}
        )


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================
class ConfigurationError(AstroError):
    """Yapılandırma hatası."""
    pass


class MissingEnvironmentVariableError(ConfigurationError):
    """Environment variable eksik hatası."""
    
    def __init__(self, var_name: str):
        """
        MissingEnvironmentVariableError'u başlat.
        
        Args:
            var_name: Eksik environment variable adı
        """
        self.var_name = var_name
        message = f"Environment variable eksik: {var_name}"
        super().__init__(
            message=message,
            error_code="MISSING_ENV_VAR",
            details={"variable_name": var_name}
        )


class InvalidConfigurationError(ConfigurationError):
    """Geçersiz yapılandırma hatası."""
    
    def __init__(self, config_key: str, config_value: Any, reason: str):
        """
        InvalidConfigurationError'u başlat.
        
        Args:
            config_key: Yapılandırma anahtarı
            config_value: Geçersiz değer
            reason: Geçersizlik sebebi
        """
        self.config_key = config_key
        self.config_value = config_value
        message = f"Geçersiz yapılandırma: {config_key}={config_value}. {reason}"
        super().__init__(
            message=message,
            error_code="INVALID_CONFIG",
            details={
                "config_key": config_key,
                "config_value": str(config_value),
                "reason": reason
            }
        )


# =============================================================================
# ERROR HANDLER DECORATORS
# =============================================================================
def handle_errors(default_message: str = "Bir hata oluştu"):
    """
    Error handling decorator'ı.
    
    Tüm beklenmeyen exception'ları yakalar ve log'lar.
    
    Args:
        default_message: Varsayılan hata mesajı
        
    Usage:
        @handle_errors("Hesaplama başarısız")
        def calculate_astro_data():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                return func(*args, **kwargs)
            except AstroError as e:
                # Bizim custom exception'lar - log'la ve yeniden raise et
                logger.error(f"{func.__name__} failed: {e}")
                raise
            except Exception as e:
                # Beklenmeyen exception - log'la ve AstroError'a çevir
                logger.exception(f"Unexpected error in {func.__name__}: {e}")
                raise AstroError(
                    message=f"{default_message}: {str(e)}",
                    error_code="UNEXPECTED_ERROR",
                    details={"function": func.__name__, "original_error": str(e)}
                ) from e
        
        return wrapper
    return decorator


def safe_execute(default_value: Any = None):
    """
    Safe execution decorator - exception'ları yakalar ve default değer döndürür.
    
    Args:
        default_value: Hata durumunda döndürülecek değer
        
    Usage:
        @safe_execute(default_value={})
        def get_user_data():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"{func.__name__} failed safely: {e}")
                return default_value
        
        return wrapper
    return decorator


# =============================================================================
# ERROR RESPONSE HELPERS
# =============================================================================
def error_response(error: Exception, status_code: int = 500) -> tuple:
    """
    Exception'dan JSON error response oluştur.
    
    Args:
        error: Exception objesi
        status_code: HTTP status code
        
    Returns:
        (dict, status_code) tuple - Flask jsonify için
    """
    from flask import jsonify
    
    if isinstance(error, AstroError):
        return error.to_dict(), 400 if isinstance(error, ValidationError) else 500
    else:
        return {
            "error": "INTERNAL_ERROR",
            "message": "Beklenmeyen bir hata oluştu",
            "details": {"error_type": type(error).__name__, "message": str(error)}
        }, status_code


if __name__ == "__main__":
    # Test exception'lar
    print("Testing custom exceptions...")
    
    try:
        raise InvalidDateError("32/01/1990")
    except InvalidDateError as e:
        print(f"✅ InvalidDateError: {e.to_dict()}")
    
    try:
        raise InvalidCoordinatesError(100, 200)
    except InvalidCoordinatesError as e:
        print(f"✅ InvalidCoordinatesError: {e.to_dict()}")
    
    try:
        raise APIError("Hyperbolic", status_code=500, details="Internal server error")
    except APIError as e:
        print(f"✅ APIError: {e.to_dict()}")
    
    print("✅ All custom exceptions working!")
