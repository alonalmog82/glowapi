import sys

from loguru import logger


def setup_logging(log_level: int) -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            '{{"time":"{time:YYYY-MM-DDTHH:mm:ss.SSS}Z",'
            '"level":"{level}",'
            '"message":"{message}",'
            '"module":"{module}",'
            '"function":"{function}",'
            '"line":{line}}}'
        ),
        colorize=False,
    )
