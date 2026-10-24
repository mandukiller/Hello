"""config 로딩/검증 테스트 (korail2 설치 없이도 동작)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from korail_booker.config import load_config  # noqa: E402


SAMPLE = """
login:
  korail_id: "1234567890"
  korail_pw: "secret"
trip:
  dep: "서울"
  arr: "부산"
  date: "20261225"
  time: "060000"
  time_limit: "120000"
train:
  type: "ktx"
  train_numbers: [101, 103]
  seat_option: "general_first"
passengers:
  adult: 2
  child: 1
  toddler: 0
  senior: 0
booking:
  retry_interval: 2.0
  max_retries: 5
notify:
  telegram:
    enabled: false
"""


class ConfigTest(unittest.TestCase):
    def _write(self, text: str) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        f.write(text)
        f.close()
        return f.name

    def test_load_valid(self):
        path = self._write(SAMPLE)
        try:
            cfg = load_config(path)
        finally:
            os.unlink(path)
        self.assertEqual(cfg.trip.dep, "서울")
        self.assertEqual(cfg.trip.arr, "부산")
        self.assertEqual(cfg.train.type, "KTX")  # 대문자 정규화
        self.assertEqual(cfg.train.seat_option, "GENERAL_FIRST")
        self.assertEqual(cfg.train.train_numbers, ["101", "103"])  # 문자열화
        self.assertEqual(cfg.passengers.total, 3)
        self.assertEqual(cfg.booking.max_retries, 5)

    def test_password_from_env(self):
        text = SAMPLE.replace('korail_pw: "secret"', 'korail_pw: ""')
        path = self._write(text)
        os.environ["KORAIL_PW"] = "envpw"
        try:
            cfg = load_config(path)
            self.assertEqual(cfg.login.korail_pw, "envpw")
        finally:
            os.unlink(path)
            del os.environ["KORAIL_PW"]

    def test_missing_password_raises(self):
        text = SAMPLE.replace('korail_pw: "secret"', 'korail_pw: ""')
        path = self._write(text)
        os.environ.pop("KORAIL_PW", None)
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_too_fast_interval_raises(self):
        text = SAMPLE.replace("retry_interval: 2.0", "retry_interval: 0.1")
        path = self._write(text)
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_no_passenger_raises(self):
        text = SAMPLE.replace("adult: 2", "adult: 0").replace("child: 1", "child: 0")
        path = self._write(text)
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
