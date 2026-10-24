"""코레일 자동 예매 핵심 로직.

korail2 라이브러리(코레일 모바일 API 래퍼)를 백엔드로 사용한다.
설정 조건에 맞는 열차를 반복 검색하여 좌석이 나오면 즉시 예매를 시도한다.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import os
import sys


def _import_korail2():
    """pip 설치본을 우선 사용하고, 없으면 vendor/ 의 사본을 사용한다."""
    try:
        import korail2  # noqa: F401
    except ImportError:
        vendor = os.path.join(os.path.dirname(__file__), "..", "vendor")
        sys.path.insert(0, os.path.abspath(vendor))
    try:
        from korail2 import (
            Korail,
            TrainType,
            ReserveOption,
            AdultPassenger,
            ChildPassenger,
            ToddlerPassenger,
            SeniorPassenger,
            SoldOutError,
            NoResultsError,
            NeedToLoginError,
        )
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "korail2 모듈을 불러올 수 없습니다. 의존성을 설치하세요: "
            "`pip install -r requirements.txt`"
        ) from exc
    return (
        Korail, TrainType, ReserveOption,
        AdultPassenger, ChildPassenger, ToddlerPassenger, SeniorPassenger,
        SoldOutError, NoResultsError, NeedToLoginError,
    )


(
    Korail, TrainType, ReserveOption,
    AdultPassenger, ChildPassenger, ToddlerPassenger, SeniorPassenger,
    SoldOutError, NoResultsError, NeedToLoginError,
) = _import_korail2()

from .config import Config
from .notifier import Notifier

logger = logging.getLogger(__name__)


def _resolve_train_type(name: str):
    """설정의 문자열을 korail2 의 TrainType 값으로 변환한다."""
    try:
        return getattr(TrainType, name)
    except AttributeError:
        valid = [a for a in dir(TrainType) if a.isupper()]
        raise ValueError(
            f"알 수 없는 열차 종류: {name}. 사용 가능: {', '.join(valid)}"
        )


def _resolve_seat_option(name: str):
    try:
        return getattr(ReserveOption, name)
    except AttributeError:
        valid = [a for a in dir(ReserveOption) if a.isupper()]
        raise ValueError(
            f"알 수 없는 좌석 옵션: {name}. 사용 가능: {', '.join(valid)}"
        )


def _build_passengers(cfg) -> list:
    """설정의 승객 수를 korail2 승객 객체 리스트로 만든다."""
    passengers = []
    if cfg.adult > 0:
        passengers.append(AdultPassenger(cfg.adult))
    if cfg.child > 0:
        passengers.append(ChildPassenger(cfg.child))
    if cfg.toddler > 0:
        passengers.append(ToddlerPassenger(cfg.toddler))
    if cfg.senior > 0:
        passengers.append(SeniorPassenger(cfg.senior))
    return passengers


class KorailAutoBooker:
    def __init__(self, config: Config, notifier: Optional[Notifier] = None):
        self.config = config
        self.notifier = notifier or Notifier(config.notify.telegram)
        if config.passengers.disability1to3 or config.passengers.disability4to6:
            logger.warning(
                "코레일 백엔드는 장애인 승객 구분을 지원하지 않습니다. 해당 인원은 무시됩니다."
            )
        self.korail = Korail(
            config.login.user_id,
            config.login.user_pw,
            auto_login=False,
        )
        self._train_type = _resolve_train_type(config.train.type)
        self._seat_option = _resolve_seat_option(config.train.seat_option)
        self._passengers = _build_passengers(config.passengers)

    # ── 로그인 ────────────────────────────────────────────────
    def login(self) -> None:
        ok = self.korail.login()
        if not ok:
            raise RuntimeError("코레일 로그인 실패. 아이디/비밀번호를 확인하세요.")
        self.notifier.info("코레일 로그인 성공")

    # ── 열차 필터 ──────────────────────────────────────────────
    def _matches_filters(self, train) -> bool:
        wanted = self.config.train.train_numbers
        if wanted and getattr(train, "train_no", None) not in wanted:
            return False

        limit = self.config.trip.time_limit
        if limit:
            dep_time = getattr(train, "dep_time", None)  # 'HHMMSS'
            if dep_time and dep_time > limit:
                return False
        return True

    def _has_target_seat(self, train) -> bool:
        """좌석 옵션에 맞는 좌석이 있는지 확인한다."""
        opt = self.config.train.seat_option
        if opt == "SPECIAL_ONLY":
            return train.has_special_seat()
        if opt == "GENERAL_ONLY":
            return train.has_general_seat()
        # *_FIRST 옵션은 일반/특실 아무거나 있으면 시도
        return train.has_seat()

    # ── 한 번의 검색/예매 시도 ────────────────────────────────
    def _attempt_once(self):
        cfg = self.config
        trains = self.korail.search_train(
            cfg.trip.dep,
            cfg.trip.arr,
            cfg.trip.date,
            cfg.trip.time,
            train_type=self._train_type,
            passengers=self._passengers,
            include_no_seats=True,
        )

        candidates: List = [t for t in trains if self._matches_filters(t)]
        if not candidates:
            logger.debug("조건에 맞는 열차 없음")
            return None

        for train in candidates:
            if not self._has_target_seat(train):
                continue
            logger.info("좌석 발견: %s. 예매 시도...", _train_desc(train))
            reservation = self.korail.reserve(
                train,
                passengers=self._passengers,
                option=self._seat_option,
            )
            return reservation
        return None

    # ── 메인 루프 ──────────────────────────────────────────────
    def run(self):
        cfg = self.config
        self.notifier.info(
            f"자동 예매 시작: {cfg.trip.dep} → {cfg.trip.arr} "
            f"{cfg.trip.date} {cfg.trip.time} 이후 ({cfg.train.type})"
        )

        attempt = 0
        while True:
            attempt += 1
            try:
                reservation = self._attempt_once()
                if reservation is not None:
                    msg = (
                        "🎉 예매 성공!\n"
                        f"{reservation}\n"
                        "코레일 앱/홈페이지에서 결제 시간 내에 결제하세요."
                    )
                    self.notifier.notify(msg)
                    return reservation
            except SoldOutError:
                logger.debug("[%d] 매진 상태, 재시도", attempt)
            except NoResultsError:
                logger.debug("[%d] 검색 결과 없음, 재시도", attempt)
            except NeedToLoginError:
                logger.warning("[%d] 세션 만료, 재로그인 시도", attempt)
                try:
                    self.login()
                except Exception as exc:  # pragma: no cover
                    logger.error("재로그인 실패: %s", exc)
            except Exception as exc:  # pragma: no cover - 예기치 못한 오류
                logger.error("[%d] 예상치 못한 오류: %s", attempt, exc)

            if cfg.booking.max_retries and attempt >= cfg.booking.max_retries:
                self.notifier.notify(
                    f"최대 시도 횟수({cfg.booking.max_retries}회)에 도달했습니다. 예매 실패."
                )
                return None

            if attempt % 30 == 0:
                logger.info("[%d회 시도 중] 아직 좌석 없음...", attempt)

            time.sleep(cfg.booking.retry_interval)


def _train_desc(train) -> str:
    return (
        f"{getattr(train, 'train_type_name', '')} "
        f"{getattr(train, 'train_no', '')} "
        f"{getattr(train, 'dep_name', '')}({getattr(train, 'dep_time', '')}) → "
        f"{getattr(train, 'arr_name', '')}({getattr(train, 'arr_time', '')})"
    ).strip()
