class StreamStatsError(Exception):
    """Базовая ошибка пакета streamstats."""


class UnsupportedFormatError(StreamStatsError):
    """Неподдерживаемый формат входного файла."""


class InvalidEventError(StreamStatsError):
    """Событие не прошло проверку (пустой source, неизвестный level и т. п.)."""


class InvalidTimestampError(InvalidEventError):
    """Временная метка не соответствует ISO 8601."""


class CliConfigError(StreamStatsError):
    """Ошибка конфигурации CLI (неверные аргументы или параметры)."""