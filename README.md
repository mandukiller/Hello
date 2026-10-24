# 코레일 / SRT 자동 예매 프로그램 🚄

코레일(KTX·새마을·무궁화 등) 또는 **SRT(수서고속철도)** 에서 원하는 구간·날짜·시간의
열차를 반복 검색하여 **매진된 좌석에 자리가 나는 순간 자동으로 예매**해 주는 프로그램입니다.
명절·주말처럼 표가 금방 매진되는 구간을 노릴 때 유용합니다.

`config.yaml` 의 `provider` 로 두 시스템 중 하나를 고릅니다.

| provider | 대상 | 예 |
|----------|------|----|
| `korail` | 코레일 (KTX/새마을/무궁화 …) | 서울, 용산, 부산, 동대구 … |
| `srt`    | SRT 수서고속철도 | **수서, 동탄, 평택지제**, 대전, 동대구, 부산 … |

> ⚠️ **동탄·평택지제 등은 SRT 전용역**입니다. 코레일(KTX)로는 조회·예매되지
> 않으니 반드시 `provider: srt` 로 설정해야 합니다.

> 백엔드: 코레일은 [`korail2`](https://pypi.org/project/korail2/) (최신 Python 에서
> `pip` 빌드가 깨져 있어 순수 파이썬 모듈을 `vendor/korail2/` 에 포함, BSD),
> SRT 는 [`SRTrain`](https://pypi.org/project/SRTrain/) 패키지를 사용합니다.

---

## ⚠️ 먼저 읽어주세요

- 이 프로그램은 **본인 계정 · 개인 용도**로 표를 구하기 위한 보조 도구입니다.
- 코레일의 비공식 API를 사용하므로, 코레일 측 변경이 있으면 동작이 멈출 수 있습니다.
- 과도한 요청은 서버에 부담을 주고 계정이 제한될 수 있습니다.
  기본 재시도 간격(2초) 이상을 유지하세요. (최소 0.5초 제한)
- **결제는 자동으로 하지 않습니다.** 예매(좌석 선점) 성공 후, 정해진 시간 안에
  코레일 앱/홈페이지에서 직접 결제해야 표가 확정됩니다.
- 암표 매매 등 부정한 목적의 사용은 금지되어 있습니다. 책임은 사용자에게 있습니다.

---

## 설치

```bash
# (권장) 가상환경
python3 -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
```

## 설정

1. 설정 파일 복사 후 값 입력:

   ```bash
   cp config.example.yaml config.yaml
   cp .env.example .env
   ```

2. `config.yaml` 에서 `provider`(korail/srt), 구간·날짜·시간·승객·열차 조건을 설정합니다.
3. 비밀번호는 보안을 위해 `.env` 의 `KORAIL_PW` / `SRT_PW` 에 넣는 것을 권장합니다.
   (`.env` 와 `config.yaml` 은 `.gitignore` 에 포함되어 커밋되지 않습니다.)

주요 설정 항목:

| 항목 | 설명 |
|------|------|
| `provider` | `korail` 또는 `srt` |
| `login.id` | 회원번호 / 이메일 / 휴대폰번호 (`korail_id` 구버전 키도 호환) |
| `login.pw` | 비밀번호 (비우면 `.env` 의 `SRT_PW`/`KORAIL_PW` 사용) |
| `trip.dep` / `trip.arr` | 출발·도착역 (예: `서울`, `부산`, `동탄`, `대전`) |
| `trip.date` | 출발일 `YYYYMMDD` |
| `trip.time` | 이 시각(`HHMMSS`) 이후 열차 검색 |
| `trip.time_limit` | 이 시각 이후 열차는 제외 (선택) |
| `train.type` | **[korail 전용]** `KTX`, `KTX_SANCHEON`, `SAEMAEUL`, `MUGUNGHWA`, `TONGGUEN`, `NURIRO`, `ITX_SAEMAEUL`, `ITX_CHEONGCHUN`, `AIRPORT`, `ALL` |
| `train.train_numbers` | 특정 열차번호만 노릴 때 (예: `["101","103"]`) |
| `train.seat_option` | `GENERAL_FIRST` / `GENERAL_ONLY` / `SPECIAL_FIRST` / `SPECIAL_ONLY` |
| `passengers.*` | 어른/어린이/유아(korail)/경로/장애인1~3·4~6급(srt) 인원 |
| `booking.retry_interval` | 재시도 간격(초), 2초 이상 권장 |
| `booking.max_retries` | 최대 시도 횟수 (`0` = 무제한) |

### SRT 예매 설정 예시 (예: 동탄 → 대전)

```yaml
provider: "srt"
login:
  id: "01012345678"      # SRT 회원 로그인
  pw: ""                 # .env 의 SRT_PW 사용 권장
trip:
  dep: "동탄"
  arr: "대전"
  date: "20261025"
  time: "190000"         # 19:00 이후
  time_limit: "210000"   # 21:00 이전 (= 오후 8시 전후)
train:
  seat_option: "GENERAL_FIRST"
passengers:
  adult: 1
```

> 💡 이 구간(동탄 → 대전, 2026-10-25 오후 8시 전후)은 바로 쓸 수 있는 프리셋
> `config.dongtan-daejeon.yaml` 로 저장되어 있습니다. `login.id` 만 채우고
> 비밀번호는 `.env` 의 `SRT_PW` 에 넣은 뒤 아래처럼 실행하세요:
> ```bash
> python main.py -c config.dongtan-daejeon.yaml
> ```

## 실행

```bash
python main.py            # config.yaml 사용
python main.py -c my.yaml # 다른 설정 파일
python main.py -v         # 자세한 로그
```

좌석이 잡히면 콘솔(및 설정 시 텔레그램)으로 알림이 오고 프로그램이 종료됩니다.
알림을 받으면 **코레일 앱/홈페이지에서 결제**하세요.

## 텔레그램 알림 (선택)

1. [@BotFather](https://t.me/BotFather) 로 봇을 만들어 토큰을 받습니다.
2. 봇과 대화를 시작한 뒤 chat id 를 확인합니다.
3. `.env` 의 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 를 채우고
   `config.yaml` 의 `notify.telegram.enabled: true` 로 설정합니다.

## 프로젝트 구조

```
.
├── main.py                  # 실행 진입점
├── config.example.yaml      # 설정 예시
├── .env.example             # 민감정보 예시
├── requirements.txt
├── korail_booker/
│   ├── config.py            # 설정 로딩/검증
│   ├── booker.py            # 코레일 자동 예매 로직
│   ├── srt_booker.py        # SRT 자동 예매 로직
│   ├── notifier.py          # 콘솔·텔레그램 알림
│   └── cli.py               # 명령줄 인터페이스 (provider 에 따라 백엔드 선택)
└── vendor/korail2/          # 코레일 API 래퍼 (포함, BSD)
```

## 테스트

```bash
python -m pytest           # 또는: python tests/test_config.py
```

## 라이선스

개인 학습·사용 목적. 사용에 따른 책임은 사용자 본인에게 있습니다.
