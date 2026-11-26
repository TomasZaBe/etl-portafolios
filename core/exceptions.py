class ApplicationError(Exception):
    """Error de la lógica de negocio que se informa al usuario.

    Sigue la propuesta del Django-Styleguide: los servicios y selectores lanzan
    esta excepción y el manejador de la API la convierte en una respuesta con
    ``message`` y ``extra``. ``status_code`` permite que cada error indique el
    código HTTP que le corresponde (400 por defecto).
    """

    status_code = 400

    def __init__(self, message: str, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}
