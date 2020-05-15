from laboratory import config
import time
import logging
import os

def lab(name):
    """Sets up logging messages for the laboratory. Sends to both a file and the console by default. Levels for both the file and console can be set to anything defined by the
    python logging package (DEBUG,INFO,WARNING,ERROR,CRITICAL). Specified log level AND GREATER will be included. Logfiles can be found in /logfiles/ """

    logger = logging.getLogger(name)    #define the logger
    logger.setLevel('DEBUG') #define root loger level

    #clear any handlers already present. Prevents duplicate messages
    if logger.hasHandlers():
        logger.handlers.clear()

    #create a folder for the log files if none exists
    folder = '../log'
    if not os.path.exists(config.LOG_DIR): os.mkdir(config.LOG_DIR)
    filepath = os.path.join(config.LOG_DIR, '{}_{}.log'.format(config.PROJECT_NAME,time.strftime('%d-%m-%Y_%H%M')))

    def sorted_ls(path):
        """Removes all but the 10 most recent logfiles -- prevent clutter during testing"""
        mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
        files = list(sorted(os.listdir(path), key=mtime))
        for f in files[1:-10]: os.remove(os.path.join(folder,f))
    # sorted_ls(folder)

    #setup file handler
    fh = logging.FileHandler(filepath)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s - %(name)s (line %(lineno)s)','%d-%m-%y %H:%M.%S')
    fh.setFormatter(formatter)
    fh.setLevel('DEBUG')
    logger.addHandler(fh)

    #set up console handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    ch.setLevel('INFO')
    logger.addHandler(ch)
    return logger
