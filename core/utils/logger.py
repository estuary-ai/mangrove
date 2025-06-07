import sys
from loguru import logger

# ensure logger and print output to stdout
logger.remove()
logger.add(sys.stdout)
