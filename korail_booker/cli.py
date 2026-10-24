"""명령줄 진입점."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .booker import KorailAutoBooker
from .notifier import Notifier


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="korail-booker",
        description="코레일 KTX/일반열차 자동 예매 프로그램",
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="설정 파일 경로 (기본: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="자세한 로그 출력",
    )
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[설정 오류] {exc}", file=sys.stderr)
        return 2

    notifier = Notifier(config.notify.telegram)
    booker = KorailAutoBooker(config, notifier=notifier)

    try:
        booker.login()
    except Exception as exc:
        print(f"[로그인 오류] {exc}", file=sys.stderr)
        return 1

    try:
        reservation = booker.run()
    except KeyboardInterrupt:
        print("\n중단되었습니다.")
        return 130

    return 0 if reservation is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
