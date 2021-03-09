import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)
LOG_FORMAT = "%(asctime)s [%(name)s] [%(levelname)s]  %(message)s"
file_handler = None
stream_handler = None

root_logger = logging.getLogger()


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


def deinit_stream_handler():
    global stream_handler
    if stream_handler is not None:
        root_logger.removeHandler(stream_handler)
        stream_handler = None


def deinit_file_handler():
    global file_handler
    if file_handler is not None:
        root_logger.removeHandler(file_handler)
        file_handler = None
        redirect_warnings(remove=True)


warning_filters = (
    change_log_level(to=logging.DEBUG),
    ltrim_to_delimiter(": "),
    keep_to_delimiter("\n"),
)


def redirect_warnings(remove=False):
    warning_logger = logging.getLogger("py.warnings")
    adjustFilter = warning_logger.addFilter
    if remove:
        adjustFilter = warning_logger.removeFilter
    for f in warning_filters:
        adjustFilter(filter=f)
    logging.captureWarnings(not remove)


def init_logging(log_path=None):
    global file_handler, stream_handler

    if stream_handler is not None:
        deinit_stream_handler()

    formatter = logging.Formatter(LOG_FORMAT)
    root_logger.setLevel(logging.NOTSET)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    root_logger.addHandler(stream_handler)

    if log_path is not None:
        if file_handler is not None:
            deinit_file_handler()
        filename = time.strftime("dzcb.%Y_%m_%d_%H%M%S.log")
        path = Path(log_path) / filename
        logger.info("Logging to '%s' at DEBUG level", path)
        file_handler = logging.FileHandler(path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

        # if a file was specified, spew warnings there instead of the console
        redirect_warnings()


def deinit_logging():
    deinit_stream_handler()
    deinit_file_handler()
