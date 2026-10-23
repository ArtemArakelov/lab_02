import json
import logging

import pytest

from streamstats import errors, parsers
from streamstats.models import Level

HEADER = "timestamp,level,source,message"  # заголовок CSV
GOOD_ROW = "2026-10-22T10:00:00,INFO,db,ok"  # хорошая строка CSV
BAD_ROW = "2026-10-22T10:00:00,ERORR,db,x"  # плохая строка CSV: опечатка в уровне


def jsonl_line(level="INFO", timestamp="2026-10-22T10:00:00", source="db"):
    data = {"timestamp": timestamp, "level": level}  # собираем событие
    data["source"] = source
    data["message"] = "ok"
    return json.dumps(data, ensure_ascii=False)  # словарь → JSON-текст


def write(tmp_path, name, *lines):  # создать файл во временной папке
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_jsonl_valid(tmp_path):  # tmp_path: временная папка от pytest
    path = write(tmp_path, "a.jsonl", jsonl_line("INFO"), jsonl_line("ERROR"))
    events = list(parsers.parse_jsonl(path))  # list() заставляет генератор отдать всё
    assert len(events) == 2
    assert events[0].level == Level.INFO
    assert events[1].level == Level.ERROR
    assert events[0].source == "db"


def test_csv_valid(tmp_path):
    row = '2026-10-22T10:00:00Z,ERROR,db,"lost, retry"'  # запятая внутри кавычек
    path = write(tmp_path, "a.csv", HEADER, row)
    events = list(parsers.parse_csv(path))
    assert len(events) == 1
    assert events[0].level == Level.ERROR
    assert events[0].message == "lost, retry"


@pytest.mark.parametrize("parse", [parsers.parse_jsonl, parsers.parse_csv])
def test_empty_file(tmp_path, parse):  # один тест запускается для обоих парсеров
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")
    assert list(parse(path)) == []  # событий нет, ошибки тоже нет


def test_jsonl_bad_line_stops(tmp_path):
    path = write(tmp_path, "bad.jsonl", jsonl_line(), "это не JSON")
    with pytest.raises(errors.InvalidEventError) as info:  # ждём нашу ошибку
        list(parsers.parse_jsonl(path))
    assert "bad.jsonl" in str(info.value)  # в сообщении есть файл
    assert "строка 2" in str(info.value)  # и номер строки


def test_jsonl_bad_line_skipped(tmp_path, caplog):  # caplog: записи журнала
    path = write(tmp_path, "bad.jsonl", jsonl_line(), "это не JSON")
    counter = parsers.ParseStats()
    with caplog.at_level(logging.WARNING):
        events = list(parsers.parse_jsonl(path, skip_invalid=True, stats=counter))
    assert len(events) == 1  # хорошая строка осталась
    assert counter.skipped == 1  # плохая посчитана
    assert "WARNING" in caplog.text
    assert "строка 2" in caplog.text


def test_csv_bad_line_stops(tmp_path):
    path = write(tmp_path, "bad.csv", HEADER, GOOD_ROW, BAD_ROW)
    with pytest.raises(errors.InvalidEventError) as info:
        list(parsers.parse_csv(path))
    assert "bad.csv" in str(info.value)
    assert "строка 3" in str(info.value)  # заголовок = 1, хорошая = 2, плохая = 3


def test_csv_bad_line_skipped(tmp_path, caplog):
    path = write(tmp_path, "bad.csv", HEADER, GOOD_ROW, BAD_ROW)
    counter = parsers.ParseStats()
    with caplog.at_level(logging.WARNING):
        events = list(parsers.parse_csv(path, skip_invalid=True, stats=counter))
    assert len(events) == 1
    assert counter.skipped == 1
    assert "WARNING" in caplog.text


def test_bad_timestamp(tmp_path):
    path = write(tmp_path, "t.jsonl", jsonl_line(timestamp="вчера"))
    with pytest.raises(errors.InvalidTimestampError):  # ждём ошибку метки
        list(parsers.parse_jsonl(path))


def test_unsupported_format(tmp_path):
    with pytest.raises(errors.UnsupportedFormatError):  # xml не поддерживается
        parsers.parse_file(tmp_path / "a.xml", "xml")


def test_csv_missing_column(tmp_path):
    header = "timestamp,level,message"  # нет столбца source
    path = write(tmp_path, "m.csv", header, "2026-10-22T10:00:00,INFO,ok")
    with pytest.raises(errors.InvalidEventError):
        list(parsers.parse_csv(path))


def test_unicode(tmp_path):
    path = write(tmp_path, "u.jsonl", jsonl_line(source="сервер"))
    events = list(parsers.parse_jsonl(path))
    assert events[0].source == "сервер"
    row = "2026-10-22T10:00:00,INFO,сервер,Привет"
    path = write(tmp_path, "u.csv", HEADER, row)
    events = list(parsers.parse_csv(path))
    assert events[0].message == "Привет"