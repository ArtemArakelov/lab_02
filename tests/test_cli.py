import json
import os
import subprocess
import sys


def line(level, source="сервер"):
    data = {"timestamp": "2026-10-22T10:00:00", "level": level}
    data["source"] = source
    data["message"] = "x"
    return json.dumps(data, ensure_ascii=False)


def write(folder, name, *lines):  # создать файл во временной папке
    path = folder / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_report(folder):  # прочитать готовый отчёт
    text = (folder / "r.json").read_text(encoding="utf-8")
    return json.loads(text)


def run_cli(folder, *args):  # запустить `python -m streamstats ...`
    env = dict(os.environ, PYTHONIOENCODING="utf-8")  # чтобы русский не ломался
    command = [sys.executable, "-m", "streamstats", *args]
    return subprocess.run(
        command,
        cwd=folder,  # запускаем внутри временной папки
        env=env,
        capture_output=True,  # забираем вывод
        text=True,
        encoding="utf-8",
        check=False,  # код выхода проверяем сами в тестах
    )


def test_cli_help(tmp_path):
    result = run_cli(tmp_path, "--help")
    assert result.returncode == 0
    assert "analyze" in result.stdout


def test_cli_writes_report(tmp_path):
    write(tmp_path, "a.jsonl", line("INFO"), line("ERROR"))
    args = ["analyze", "a.jsonl", "--format", "jsonl", "--output", "r.json"]
    result = run_cli(tmp_path, *args)
    assert result.returncode == 0
    report = read_report(tmp_path)
    assert report["total_events"] == 2
    assert report["by_source"]["сервер"] == 2  # русские буквы дошли целыми
    assert report["by_level"]["ERROR"] == 1


def test_cli_bad_line_stops(tmp_path):
    write(tmp_path, "bad.jsonl", line("INFO"), "это не JSON")
    args = ["analyze", "bad.jsonl", "--format", "jsonl"]
    result = run_cli(tmp_path, *args)
    assert result.returncode == 2  # код выхода 2, как в задании
    assert "bad.jsonl" in result.stderr
    assert "строка 2" in result.stderr


def test_cli_skip_invalid(tmp_path):
    write(tmp_path, "bad.jsonl", line("INFO"), "это не JSON")
    args = ["analyze", "bad.jsonl", "--format", "jsonl"]
    args += ["--skip-invalid", "--output", "r.json"]
    result = run_cli(tmp_path, *args)
    assert result.returncode == 0
    assert "WARNING" in result.stderr  # предупреждение в журнале
    report = read_report(tmp_path)
    assert report["total_events"] == 1
    assert report["skipped_lines"] == 1  # пропущенная строка попала в отчёт


def test_cli_two_csv_files(tmp_path):
    header = "timestamp,level,source,message"
    write(tmp_path, "a.csv", header, "2026-10-22T10:00:00,INFO,сервер,запуск")
    write(tmp_path, "b.csv", header, "2026-10-22T10:00:05,ERROR,db,сбой")
    args = ["analyze", "a.csv", "b.csv", "--format", "csv", "--output", "r.json"]
    result = run_cli(tmp_path, *args)
    assert result.returncode == 0
    assert read_report(tmp_path)["total_events"] == 2  # два файла объединены


def test_cli_unsupported_format(tmp_path):
    write(tmp_path, "a.xml", "")
    result = run_cli(tmp_path, "analyze", "a.xml", "--format", "xml")
    assert result.returncode == 2


def test_cli_missing_format(tmp_path):
    write(tmp_path, "a.jsonl", line("INFO"))
    result = run_cli(tmp_path, "analyze", "a.jsonl")  # --format не указан
    assert result.returncode == 2