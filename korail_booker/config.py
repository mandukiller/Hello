"""설정 파일(config.yaml)과 환경변수(.env)를 읽어 구조화된 설정으로 반환한다."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

try:  # .env 는 선택 사항
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

VALID_PROVIDERS = ("korail", "srt")


@dataclass
class LoginConfig:
    user_id: str
    user_pw: str


@dataclass
class TripConfig:
    dep: str
    arr: str
    date: str
    time: str = "000000"
    time_limit: Optional[str] = None


@dataclass
class TrainConfig:
    type: str = "KTX"
    train_numbers: List[str] = field(default_factory=list)
    seat_option: str = "GENERAL_FIRST"


@dataclass
class PassengerConfig:
    adult: int = 1
    child: int = 0
    toddler: int = 0          # 코레일 전용 (SRT 미지원)
    senior: int = 0
    disability1to3: int = 0   # SRT 전용 (코레일 미지원)
    disability4to6: int = 0   # SRT 전용 (코레일 미지원)

    @property
    def total(self) -> int:
        return (
            self.adult
            + self.child
            + self.toddler
            + self.senior
            + self.disability1to3
            + self.disability4to6
        )


@dataclass
class BookingConfig:
    retry_interval: float = 2.0
    max_retries: int = 0
    reserve_first_available: bool = True


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class NotifyConfig:
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


@dataclass
class Config:
    provider: str
    login: LoginConfig
    trip: TripConfig
    train: TrainConfig
    passengers: PassengerConfig
    booking: BookingConfig
    notify: NotifyConfig

    def validate(self) -> None:
        if self.provider not in VALID_PROVIDERS:
            raise ValueError(
                f"provider 는 {VALID_PROVIDERS} 중 하나여야 합니다 (현재: {self.provider})."
            )
        if not self.login.user_id:
            raise ValueError("login.id 가 비어 있습니다.")
        if not self.login.user_pw:
            raise ValueError(
                "비밀번호가 없습니다. config.yaml 의 login.pw 또는 "
                ".env 의 SRT_PW / KORAIL_PW 를 설정하세요."
            )
        if not (self.trip.dep and self.trip.arr and self.trip.date):
            raise ValueError("trip.dep / trip.arr / trip.date 는 필수입니다.")
        if self.passengers.total < 1:
            raise ValueError("승객 수가 최소 1명 이상이어야 합니다.")
        if self.booking.retry_interval < 0.5:
            raise ValueError(
                "retry_interval 은 0.5초 이상이어야 합니다 (서버 부담 방지)."
            )


def load_config(path: str | os.PathLike = "config.yaml") -> Config:
    """config.yaml 과 .env 를 읽어 Config 객체를 만든다."""
    if load_dotenv is not None:
        load_dotenv()

    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"설정 파일을 찾을 수 없습니다: {cfg_path}\n"
            "config.example.yaml 을 config.yaml 로 복사해 채우세요."
        )

    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    provider = str(raw.get("provider", "korail")).strip().lower()

    login_raw = raw.get("login", {}) or {}
    # id: 신규 키(id) → 구버전 키(korail_id) → 환경변수(provider 별)
    id_env = os.getenv("SRT_ID") if provider == "srt" else os.getenv("KORAIL_ID")
    user_id = (
        login_raw.get("id")
        or login_raw.get("korail_id")
        or id_env
        or ""
    )
    # pw: 신규 키(pw) → 구버전(korail_pw) → 환경변수(provider 별)
    pw_env = os.getenv("SRT_PW") if provider == "srt" else os.getenv("KORAIL_PW")
    user_pw = (
        login_raw.get("pw")
        or login_raw.get("korail_pw")
        or pw_env
        or ""
    )

    trip_raw = raw.get("trip", {}) or {}
    train_raw = raw.get("train", {}) or {}
    psgr_raw = raw.get("passengers", {}) or {}
    booking_raw = raw.get("booking", {}) or {}
    notify_raw = raw.get("notify", {}) or {}
    tg_raw = (notify_raw.get("telegram", {}) or {})

    time_limit = trip_raw.get("time_limit") or None

    config = Config(
        provider=provider,
        login=LoginConfig(
            user_id=str(user_id).strip(),
            user_pw=str(user_pw).strip(),
        ),
        trip=TripConfig(
            dep=str(trip_raw.get("dep", "")).strip(),
            arr=str(trip_raw.get("arr", "")).strip(),
            date=str(trip_raw.get("date", "")).strip(),
            time=str(trip_raw.get("time", "000000")).strip(),
            time_limit=str(time_limit).strip() if time_limit else None,
        ),
        train=TrainConfig(
            type=str(train_raw.get("type", "KTX")).strip().upper(),
            train_numbers=[str(n).strip() for n in (train_raw.get("train_numbers") or [])],
            seat_option=str(train_raw.get("seat_option", "GENERAL_FIRST")).strip().upper(),
        ),
        passengers=PassengerConfig(
            adult=int(psgr_raw.get("adult", 1)),
            child=int(psgr_raw.get("child", 0)),
            toddler=int(psgr_raw.get("toddler", 0)),
            senior=int(psgr_raw.get("senior", 0)),
            disability1to3=int(psgr_raw.get("disability1to3", 0)),
            disability4to6=int(psgr_raw.get("disability4to6", 0)),
        ),
        booking=BookingConfig(
            retry_interval=float(booking_raw.get("retry_interval", 2.0)),
            max_retries=int(booking_raw.get("max_retries", 0)),
            reserve_first_available=bool(
                booking_raw.get("reserve_first_available", True)
            ),
        ),
        notify=NotifyConfig(
            telegram=TelegramConfig(
                enabled=bool(tg_raw.get("enabled", False)),
                bot_token=str(tg_raw.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip(),
                chat_id=str(tg_raw.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID", "")).strip(),
            )
        ),
    )

    config.validate()
    return config
