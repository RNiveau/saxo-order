import logging


class Logger:

    __logger = None

    @staticmethod
    def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        if Logger.__logger is None:
            Logger.__logger = logging.getLogger("k-order")
            Logger.__logger.setLevel(logging.INFO)
            ch = logging.StreamHandler()
            ch.setLevel(level)
            ch.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            Logger.__logger.addHandler(ch)
        return logging.getLogger(f"k-order.{name}")
