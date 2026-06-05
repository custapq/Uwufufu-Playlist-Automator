"""tests/test_retry.py — Unit tests for the retry decorator."""

import pytest

from src.utils.retry import retry


class TestRetry:
    def test_succeeds_first_try(self):
        calls = []

        @retry(max_attempts=3, delay=0.0)
        def ok():
            calls.append(1)
            return "done"

        assert ok() == "done"
        assert len(calls) == 1

    def test_retries_then_succeeds(self):
        calls = []

        @retry(max_attempts=3, delay=0.0, exceptions=(ValueError,))
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert len(calls) == 3

    def test_reraises_after_max_attempts(self):
        calls = []

        @retry(max_attempts=2, delay=0.0, exceptions=(ValueError,))
        def always_fail():
            calls.append(1)
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            always_fail()
        assert len(calls) == 2

    def test_only_catches_listed_exceptions(self):
        @retry(max_attempts=3, delay=0.0, exceptions=(ValueError,))
        def raises_type_error():
            raise TypeError("wrong")

        # TypeError is not in the retry list → should propagate immediately
        with pytest.raises(TypeError):
            raises_type_error()

    def test_preserves_function_metadata(self):
        @retry()
        def my_func():
            """my docstring"""

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "my docstring"

    def test_backoff_increases_delay(self):
        sleeps = []

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("src.utils.retry.time.sleep", lambda s: sleeps.append(s))

            @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(ValueError,))
            def fail():
                raise ValueError()

            with pytest.raises(ValueError):
                fail()

        assert sleeps == [1.0, 2.0]
