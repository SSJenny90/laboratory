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

    #set up console handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    ch.setLevel('INFO')
    logger.addHandler(ch)
    return logger

def file_handler(logger, project_name):
    # #create a folder for the log files if none exists
    # if not os.path.exists(config.LOG_DIR): 
    #     os.mkdir(config.LOG_DIR)
    filepath = os.path.join(config.DATA_DIR, project_name, '{}_{}.log'.format(project_name,time.strftime('%d-%m-%Y_%H%M')))

    #setup file handler
    fh = logging.FileHandler(filepath)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s - %(name)s (line %(lineno)s)','%d-%m-%y %H:%M.%S')
    fh.setFormatter(formatter)
    fh.setLevel('DEBUG')
    logger.addHandler(fh)
    return logger