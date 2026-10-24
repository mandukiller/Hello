"""코레일 자동 예매 프로그램."""

__version__ = "0.1.0"

from .config import Config, load_config

__all__ = ["Config", "load_config", "KorailAutoBooker", "SRTAutoBooker"]


def __getattr__(name):
    # korail2 / SRTrain 백엔드는 실제 예매 시에만 필요하므로 지연 임포트한다.
    if name == "KorailAutoBooker":
        from .booker import KorailAutoBooker

        return KorailAutoBooker
    if name == "SRTAutoBooker":
        from .srt_booker import SRTAutoBooker

        return SRTAutoBooker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
