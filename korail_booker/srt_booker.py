"""SRT(수서고속철도) 자동 예매 핵심 로직.

SRTrain 라이브러리(SRT 모바일 API 래퍼)를 백엔드로 사용한다.
설정 조건에 맞는 열차를 반복 검색하여 좌석이 나오면 즉시 예매를 시도한다.

동탄·평택지제 등 SRT 전용역은 코레일(KTX) 백엔드로는 예매할 수 없으므로
이 백엔드(provider: srt)를 사용해야 한다.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

try:
    from SRT import (
        SRT,
        SeatType,
        Adult,
        Child,
        Senior,
        Disability1To3,
        Disability4To6,
        SRTError,
        SRTLoginError,
        SRTResponseError,
        SRTNotLoggedInError,
    )
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "SRTrain 라이브러리가 필요합니다. `pip install -r requirements.txt` 를 실행하세요."
    ) from exc

from .config import Config
from .notifier import Notifier

logger = logging.getLogger(__name__)


def _resolve_seat_option(name: str):
    try:
        return getattr(SeatType, name)
    except AttributeError:
        valid = [a for a in dir(SeatType) if a.isupper()]
        raise ValueError(
            f"알 수 없는 좌석 옵션: {name}. 사용 가능: {', '.join(valid)}"
        )


def _build_passengers(cfg) -> list:
    """설정의 승객 수를 SRT 승객 객체 리스트로 만든다."""
    passengers = []
    if cfg.adult > 0:
        passengers.append(Adult(cfg.adult))
    if cfg.child > 0:
        passengers.append(Child(cfg.child))
    if cfg.senior > 0:
        passengers.append(Senior(cfg.senior))
    if cfg.disability1to3 > 0:
        passengers.append(Disability1To3(cfg.disability1to3))
    if cfg.disability4to6 > 0:
        passengers.append(Disability4To6(cfg.disability4to6))
    return passengers


class SRTAutoBooker:
    def __init__(self, config: Config, notifier: Optional[Notifier] = None):
        self.config = config
        self.notifier = notifier or Notifier(config.notify.telegram)
        if config.passengers.toddler:
            logger.warning(
                "SRT 백엔드는 유아(toddler) 구분을 지원하지 않습니다. 해당 인원은 무시됩니다."
            )
        self.srt = SRT(
            config.login.user_id,
            config.login.user_pw,
            auto_login=False,
        )
        self._seat_option = _resolve_seat_option(config.train.seat_option)
        self._passengers = _build_passengers(config.passengers)

    # ── 로그인 ────────────────────────────────────────────────
    def login(self) -> None:
        self.srt.login()
        self.notifier.info("SRT 로그인 성공")

    # ── 열차 필터 ──────────────────────────────────────────────
    def _matches_filters(self, train) -> bool:
        wanted = self.config.train.train_numbers
        if wanted and getattr(train, "train_number", None) not in wanted:
            return False

        limit = self.config.trip.time_limit
        if limit:
            dep_time = getattr(train, "dep_time", None)  # 'HHMMSS'
            if dep_time and dep_time > limit:
                return False
        return True

    def _has_target_seat(self, train) -> bool:
        opt = self.config.train.seat_option
        if opt == "SPECIAL_ONLY":
            return train.special_seat_available()
        if opt == "GENERAL_ONLY":
            return train.general_seat_available()
        return train.seat_available()

    # ── 한 번의 검색/예매 시도 ────────────────────────────────
    def _attempt_once(self):
        cfg = self.config
        trains = self.srt.search_train(
            cfg.trip.dep,
            cfg.trip.arr,
            cfg.trip.date,
            cfg.trip.time,
            time_limit=cfg.trip.time_limit,
            available_only=False,
        )

        candidates: List = [t for t in trains if self._matches_filters(t)]
        if not candidates:
            logger.debug("조건에 맞는 열차 없음")
            return None

        for train in candidates:
            if not self._has_target_seat(train):
                continue
            logger.info("좌석 발견: %s. 예매 시도...", _train_desc(train))
            reservation = self.srt.reserve(
                train,
                passengers=self._passengers,
                special_seat=self._seat_option,
            )
            return reservation
        return None

    # ── 메인 루프 ──────────────────────────────────────────────
    def run(self):
        cfg = self.config
        self.notifier.info(
            f"SRT 자동 예매 시작: {cfg.trip.dep} → {cfg.trip.arr} "
            f"{cfg.trip.date} {cfg.trip.time} 이후"
            + (f" ~ {cfg.trip.time_limit}" if cfg.trip.time_limit else "")
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
                        "SRT 앱/홈페이지에서 결제 시간 내에 결제하세요."
                    )
                    self.notifier.notify(msg)
                    return reservation
            except SRTNotLoggedInError:
                logger.warning("[%d] 세션 만료, 재로그인 시도", attempt)
                try:
                    self.login()
                except Exception as exc:  # pragma: no cover
                    logger.error("재로그인 실패: %s", exc)
            except SRTResponseError as exc:
                # 매진·좌석없음 등은 메시지로 내려오므로 디버그 수준으로 무시하고 재시도
                logger.debug("[%d] 응답 오류(재시도): %s", attempt, exc)
            except SRTError as exc:
                logger.debug("[%d] SRT 오류(재시도): %s", attempt, exc)
            except Exception as exc:  # pragma: no cover
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
        f"{getattr(train, 'train_name', '')} "
        f"{getattr(train, 'train_number', '')} "
        f"{getattr(train, 'dep_station_name', '')}({getattr(train, 'dep_time', '')}) → "
        f"{getattr(train, 'arr_station_name', '')}({getattr(train, 'arr_time', '')})"
    ).strip()
