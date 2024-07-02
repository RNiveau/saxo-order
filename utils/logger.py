import logging
import os


class Logger:

    __logger = None

    @staticmethod
    def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        if Logger.__logger is None:
            basic_level = os.getenv("LOG_LEVEL", logging.INFO)
            Logger.__logger = logging.getLogger("k-order")
            Logger.__logger.setLevel(basic_level)
            ch = logging.StreamHandler()
            ch.setLevel(basic_level)
            ch.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            Logger.__logger.addHandler(ch)
        logger = logging.getLogger(f"k-order.{name}")
        logger.setLevel(level)
        return logger
