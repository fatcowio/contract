import os
import time


DEBUG = True
LOG_DIR = os.path.join(os.getcwd(), f'log/{time.strftime("%Y-%m-%d")}.log')
LOG_FORMAT = '<level>{level: <8}</level>  <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> - <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>'