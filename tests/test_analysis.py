import json

from streamstats import analysis, parsers, report
from streamstats.models import Level, build_event


def make_event(level="INFO", source="db", timestamp="2026-10-22T10:00:00"):
    raw = {"timestamp": timestamp, "level": level}  # быстро делаем карточку
    raw["source"] = source
    raw["message"] = "x"
    return build_event(raw)


def test_counts():
    events = [
        make_event("INFO", "db"),
        make_event("ERROR", "db"),
        make_event("CRITICAL", "api"),
        make_event("INFO", "api"),
    ]
    stats = analysis.analyze(events)
    assert stats.total == 4
    assert stats.by_level[Level.INFO] == 2
    assert stats.by_source["db"] == 2
    assert stats.error_sources["db"] == 1  # у db одна ошибка (ERROR)
    assert stats.error_sources["api"] == 1  # у api одна ошибка (CRITICAL)


def test_first_and_last_timestamp():
    stamps = [
        "2026-10-22T10:00:05Z",  # с буквой Z
        "2026-10-22T09:00:00",  # без часового пояса
        "2026-10-22T11:00:00+00:00",  # с поясом
    ]
    events = [make_event(timestamp=t) for t in stamps]
    stats = analysis.analyze(events)
    assert stats.first_timestamp.isoformat() == "2026-10-22T09:00:00+00:00"
    assert stats.last_timestamp.isoformat() == "2026-10-22T11:00:00+00:00"


def test_top_5_error_sources():
    events = []
    for i in range(7):  # семь источников: у s0 одна ошибка, у s6 семь
        events += [make_event("ERROR", f"s{i}")] * (i + 1)
    top = report.build_report(analysis.analyze(events), [])["top_error_sources"]
    assert len(top) == 5  # в топе ровно пять
    assert top[0] == {"source": "s6", "count": 7}


def test_empty_input_report():
    result = report.build_report(analysis.analyze([]), [])
    assert result["total_events"] == 0
    assert result["first_timestamp"] is None  # меток нет
    assert result["top_error_sources"] == []
    json.dumps(result)  # отчёт должен превращаться в JSON


def jsonl_line(level, source):
    data = {"timestamp": "2026-10-22T10:00:00", "level": level}
    data["source"] = source
    data["message"] = "x"
    return json.dumps(data, ensure_ascii=False)


def test_multiple_files(tmp_path):
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    text = jsonl_line("INFO", "db") + "\n" + jsonl_line("ERROR", "db") + "\n"
    first.write_text(text, encoding="utf-8")
    second.write_text(jsonl_line("ERROR", "сервер") + "\n", encoding="utf-8")
    stats = analysis.Stats()  # один блокнот на оба файла
    for path in (first, second):
        analysis.analyze(parsers.parse_jsonl(path), stats)
    assert stats.total == 3  # 2 + 1
    assert stats.by_source["db"] == 2
    assert stats.by_source["сервер"] == 1
    assert stats.error_sources["db"] == 1
    assert stats.error_sources["сервер"] == 1