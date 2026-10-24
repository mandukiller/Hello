# vendor/korail2

[`korail2`](https://pypi.org/project/korail2/) 0.4.0 (코레일 모바일 API 래퍼, BSD 라이선스)을
프로젝트에 포함(vendoring)한 것입니다.

PyPI 패키지의 `setup.py` 가 오래되어 최신 Python/setuptools 에서 `pip install korail2`
빌드가 실패하기 때문에, 순수 파이썬 모듈만 그대로 가져왔습니다.
라이브러리 자체는 수정 없이 사용합니다 (`LICENSE` 참고).

런타임 의존성: `six`, `PyCryptodome` (상위 `requirements.txt` 에 포함).

`pip install korail2` 가 정상적으로 되는 환경이라면 그 패키지가 우선 사용되고,
없으면 이 폴더의 사본이 사용됩니다.
