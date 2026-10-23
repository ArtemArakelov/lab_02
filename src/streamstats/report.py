import json  # превращение данных в JSON-текст
from typing import Any  # «что угодно», для подписи

from .analysis import Stats  # блокнот со статистикой
from .models import Level  # список уровней


def build_report(stats: Stats, files: list[str]) -> dict[str, Any]:  # блокнот → словарь для отчёта
    first = stats.first_timestamp  # первая метка (или None)
    last = stats.last_timestamp  # последняя метка
    return {
        "files": files,  # какие файлы обработали
        "total_events": stats.total,  # всего событий
        "skipped_lines": stats.skipped,  # сколько строк пропущено
        "by_level": {level.value: stats.by_level.get(level, 0) for level in Level},  # по уровням, нет события: 0
        "by_source": dict(stats.by_source.most_common()),  # источники от частых к редким
        "top_error_sources": [
            {"source": source, "count": count}
            for source, count in stats.error_sources.most_common(5)  # топ-5 по ошибкам
        ],
        "first_timestamp": first.isoformat() if first else None,  # метка текстом ISO
        "last_timestamp": last.isoformat() if last else None,
    }


def render_report(report: dict[str, Any]) -> str:  # словарь → красивый JSON-текст
    return json.dumps(report, ensure_ascii=False, indent=2)  # русские буквы остаются буквами, отступы 2


def write_report(report: dict[str, Any], path: str) -> None:  # записать отчёт в файл
    with open(path, "w", encoding="utf-8") as file:  # "w": запись; utf-8: русские буквы
        file.write(render_report(report))  # пишем отчёт
        file.write("\n")  # перевод строки в конце