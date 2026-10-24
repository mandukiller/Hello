"""예매 성공/실패 등을 알려주는 알림 모듈 (콘솔 + 선택적 텔레그램)."""

from __future__ import annotations

import logging

import requests

from .config import TelegramConfig

logger = logging.getLogger(__name__)


class Notifier:
    """콘솔 출력과 (설정 시) 텔레그램 메시지를 함께 보낸다."""

    def __init__(self, telegram: TelegramConfig | None = None):
        self.telegram = telegram

    def info(self, message: str) -> None:
        logger.info(message)

    def notify(self, message: str) -> None:
        """사용자에게 꼭 전달되어야 하는 중요한 알림."""
        logger.info(message)
        print(f"🔔 {message}")
        self._send_telegram(message)

    def _send_telegram(self, message: str) -> None:
        tg = self.telegram
        if not (tg and tg.enabled):
            return
        if not (tg.bot_token and tg.chat_id):
            logger.warning("텔레그램이 켜져 있지만 bot_token/chat_id 가 없어 건너뜁니다.")
            return
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{tg.bot_token}/sendMessage",
                data={"chat_id": tg.chat_id, "text": message},
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - 네트워크 의존
            logger.warning("텔레그램 알림 전송 실패: %s", exc)
