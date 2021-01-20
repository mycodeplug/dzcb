import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)
LOG_FORMAT = "%(asctime)s [%(name)s] [%(levelname)s]  %(message)s"


def change_log_level(to):
    def _change_log_level(r):
        r.levelno = to
        r.levelname = logging.getLevelName(r.levelno)
        return True

    return _change_log_level


def ltrim_to_delimiter(d):
    def _ltrim_to_delimiter(r):
        r.args = (r.args[0].partition(d)[2], *r.args[1:])
        return True

    return _ltrim_to_delimiter


def keep_to_delimiter(d):
    def _keep_to_delimiter(r):
        r.args = (r.args[0].partition(d)[0], *r.args[1:])
        return True

    return _keep_to_delimiter


def init_logging(log_path=None):
    formatter = logging.Formatter(LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(logging.NOTSET)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    root.addHandler(stream_handler)

    if log_path is not None:
        filename = time.strftime("dzcb.%Y_%m_%d_%H%M%S.log")
        path = Path(log_path) / filename
        logger.info("Logging to '%s' at DEBUG level", path)
        file_handler = logging.FileHandler(path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)

        # if a file was specified, spew warnings there instead of the console
        warning_logger = logging.getLogger("py.warnings")
        warning_logger.addFilter(filter=change_log_level(to=logging.DEBUG))
        warning_logger.addFilter(filter=ltrim_to_delimiter(": "))
        warning_logger.addFilter(filter=keep_to_delimiter("\n"))
        logging.captureWarnings(True)
