from collections import Counter  # словарь-счётчик
from collections.abc import Iterable  # подпись: «то, что можно перебирать»
from dataclasses import dataclass, field  # «анкета» и настройка графы
from datetime import datetime  # дата и время

from .models import Event, Level  # карточка и список уровней

ERROR_LEVELS = (Level.ERROR, Level.CRITICAL)  # уровни, считающиеся ошибками


@dataclass  # «анкета»
class Stats:  # «блокнот» с итогами
    total: int = 0  # всего событий
    by_level: Counter = field(default_factory=Counter)  # по уровням
    by_source: Counter = field(default_factory=Counter)  # по источникам
    error_sources: Counter = field(default_factory=Counter)  # ошибки по источникам
    first_timestamp: datetime | None = None  # самая ранняя метка
    last_timestamp: datetime | None = None  # самая поздняя метка
    skipped: int = 0  # сколько строк пропущено

    def add(self, event: Event) -> None:  # записать одно событие
        self.total += 1  # +1 к общему числу
        self.by_level[event.level] += 1  # +1 к своему уровню
        self.by_source[event.source] += 1  # +1 к своему источнику
        if event.level in ERROR_LEVELS:  # ERROR или CRITICAL
            self.error_sources[event.source] += 1  # +1 к ошибкам источника
        first = self.first_timestamp  # короткое имя
        if first is None or event.timestamp < first:  # раньше всех?
            self.first_timestamp = event.timestamp
        last = self.last_timestamp  # короткое имя
        if last is None or event.timestamp > last:  # позже всех?
            self.last_timestamp = event.timestamp


def analyze(events: Iterable[Event], stats: Stats | None = None) -> Stats:
    if stats is None:  # блокнот не передали
        stats = Stats()  # заводим новый
    for event in events:  # события по одному, память не растёт
        stats.add(event)  # записываем
    return stats  # отдаём заполненный блокнот