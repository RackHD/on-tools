import logging

# Global logger setup: CRITICAL < ERROR < WARNING < INFO < DEBUG
LOGFORMAT = '%(asctime)s:%(name)s:%(levelname)s - %(message)s'
LOGLEVELS = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}
LOGGER_LVL = "ERROR"
logging.basicConfig(level=LOGLEVELS[LOGGER_LVL], format=LOGFORMAT)

