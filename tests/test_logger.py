import logging

from src.utils.logger import setup_logger


class TestSetupLogger:
    def test_creates_log_file(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger = setup_logger(name="test1", log_dir=str(log_dir))
        logger.info("hello")
        files = list(log_dir.glob("automation_*.log"))
        assert len(files) == 1

    def test_has_console_and_file_handlers(self, tmp_path):
        logger = setup_logger(name="test2", log_dir=str(tmp_path / "logs"))
        handler_types = {type(h).__name__ for h in logger.handlers}
        assert "StreamHandler" in handler_types
        assert "FileHandler" in handler_types

    def test_does_not_duplicate_handlers(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        logger1 = setup_logger(name="test3", log_dir=log_dir)
        count1 = len(logger1.handlers)
        logger2 = setup_logger(name="test3", log_dir=log_dir)
        assert len(logger2.handlers) == count1

    def test_file_handler_captures_debug(self, tmp_path):
        log_dir = tmp_path / "logs"
        logger = setup_logger(name="test4", log_dir=str(log_dir), level=logging.INFO)
        logger.debug("debug-only-message")
        log_file = next(log_dir.glob("automation_*.log"))
        contents = log_file.read_text(encoding="utf-8")
        assert "debug-only-message" in contents
