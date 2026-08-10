import logging

LOG_FILE = "dowv_auditoria.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class YTDLLogger:
    def debug(self, msg):
        if msg.startswith('[download]'):
            logging.info(msg)
        else:
            logging.debug(msg)
    def info(self, msg):
        logging.info(msg)
    def warning(self, msg):
        logging.warning(msg)
    def error(self, msg):
        logging.error(msg)
