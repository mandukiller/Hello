#!/usr/bin/env python3
"""코레일 자동 예매 실행 진입점.

사용법:
    python main.py              # config.yaml 사용
    python main.py -c my.yaml   # 다른 설정 파일 사용
    python main.py -v           # 자세한 로그
"""

from korail_booker.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
