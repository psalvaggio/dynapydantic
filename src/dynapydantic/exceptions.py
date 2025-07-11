"""Custom exception types"""


class Error(Exception):
    """Base class for all dynapydanitc errors"""


class RegistrationError(Error):
    """Occurs when a model cannot be registered"""


class AmbiguousDiscriminatorValueError(Error):
    """Occurs when the discriminator value is ambiguous"""


class ConfigurationError(Error):
    """Occurs when the user misconfigured a tracking setup"""
