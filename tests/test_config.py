"""config 로딩/검증 테스트 (korail2/SRTrain 설치 없이도 동작)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from korail_booker.config import load_config  # noqa: E402


SAMPLE = """
provider: "srt"
login:
  id: "1234567890"
  pw: "secret"
trip:
  dep: "동탄"
  arr: "대전"
  date: "20261025"
  time: "190000"
  time_limit: "210000"
train:
  type: "ktx"
  train_numbers: [101, 103]
  seat_option: "general_first"
passengers:
  adult: 2
  child: 1
  disability1to3: 1
booking:
  retry_interval: 2.0
  max_retries: 5
notify:
  telegram:
    enabled: false
"""

LEGACY_SAMPLE = """
login:
  korail_id: "9876543210"
  korail_pw: "legacy"
trip:
  dep: "서울"
  arr: "부산"
  date: "20261225"
passengers:
  adult: 1
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
        self.assertEqual(cfg.provider, "srt")
        self.assertEqual(cfg.login.user_id, "1234567890")
        self.assertEqual(cfg.trip.dep, "동탄")
        self.assertEqual(cfg.trip.arr, "대전")
        self.assertEqual(cfg.train.seat_option, "GENERAL_FIRST")
        self.assertEqual(cfg.train.train_numbers, ["101", "103"])
        self.assertEqual(cfg.passengers.total, 4)
        self.assertEqual(cfg.passengers.disability1to3, 1)

    def test_legacy_korail_keys(self):
        path = self._write(LEGACY_SAMPLE)
        try:
            cfg = load_config(path)
        finally:
            os.unlink(path)
        self.assertEqual(cfg.provider, "korail")  # 기본값
        self.assertEqual(cfg.login.user_id, "9876543210")
        self.assertEqual(cfg.login.user_pw, "legacy")

    def test_password_from_env(self):
        text = SAMPLE.replace('pw: "secret"', 'pw: ""')
        path = self._write(text)
        os.environ["SRT_PW"] = "envpw"
        try:
            cfg = load_config(path)
            self.assertEqual(cfg.login.user_pw, "envpw")
        finally:
            os.unlink(path)
            del os.environ["SRT_PW"]

    def test_missing_password_raises(self):
        text = SAMPLE.replace('pw: "secret"', 'pw: ""')
        path = self._write(text)
        os.environ.pop("SRT_PW", None)
        os.environ.pop("KORAIL_PW", None)
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_invalid_provider_raises(self):
        text = SAMPLE.replace('provider: "srt"', 'provider: "ktx_express"')
        path = self._write(text)
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
        text = (
            SAMPLE.replace("adult: 2", "adult: 0")
            .replace("child: 1", "child: 0")
            .replace("disability1to3: 1", "disability1to3: 0")
        )
        path = self._write(text)
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
