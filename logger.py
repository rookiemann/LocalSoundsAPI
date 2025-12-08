# logger.py
import logging
from collections import deque
log_buffer = deque(maxlen=30)
class LogCaptureHandler(logging.Handler):
    def emit(self, record):
        log_buffer.append(self.format(record))
log_handler = LogCaptureHandler()
log_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(log_handler)
logging.getLogger().setLevel(logging.INFO)
