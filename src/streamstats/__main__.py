import argparse  # разбор команды из терминала
import logging  # журнал предупреждений
import sys  # поток ошибок и код выхода

from .analysis import Stats, analyze  # блокнот и подсчёт
from .errors import CliConfigError, StreamStatsError  # наши ошибки
from .parsers import ParseStats, parse_file  # чтение файлов
from .report import build_report, render_report, write_report  # отчёт


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    # 1. Что понимает программа
    parser = argparse.ArgumentParser(prog="streamstats")
    parser.add_argument("command", choices=["analyze"])
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--format", required=True)
    parser.add_argument("--output")
    parser.add_argument("--skip-invalid", action="store_true")
    args = parser.parse_args()

    # 2. Выполняем
    skip = args.skip_invalid  # короткое имя, чтобы строки ниже были короче
    counter = ParseStats()  # счётчик пропущенных строк
    stats = Stats()  # общий блокнот на все файлы
    try:
        if args.output in args.inputs:  # отчёт затёр бы входной файл
            raise CliConfigError("--output совпадает с входным файлом")
        for path in args.inputs:  # по очереди каждый файл
            events = parse_file(path, args.format, skip_invalid=skip, stats=counter)
            analyze(events, stats)  # записываем события в блокнот
        stats.skipped = counter.skipped  # переносим число пропущенных
        report = build_report(stats, args.inputs)  # собираем отчёт
        if args.output:
            write_report(report, args.output)  # пишем в файл
        else:
            print(render_report(report))  # или показываем на экране
    except StreamStatsError as exc:  # любая наша ошибка
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2  # код выхода 2
    except OSError as exc:  # файл не найден, нет доступа и т. п.
        print(f"Ошибка файла: {exc}", file=sys.stderr)
        return 1
    return 0  # всё хорошо


if __name__ == "__main__":  # только при запуске через python -m streamstats
    sys.exit(main())  # завершаем программу с кодом из main