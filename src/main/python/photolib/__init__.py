PHOTO_SUFFICES = [".jpg", ".jpeg", ".png", ".gif", ".cr2"]
MOVIE_SUFFICES = [".mov", ".mp4"]
HANDLED_SUFFICES = PHOTO_SUFFICES + MOVIE_SUFFICES
TILES_SUFFICES = [".jpg", ".jpeg", ".png", ".gif"]
IGNORED_SUFFICES = [".ini", ".db", ".info"]

TILES_PATTERNS = ["*" + s for s in TILES_SUFFICES]
PHOTO_PATTERNS = ["*" + s for s in PHOTO_SUFFICES]

import fnmatch
import logging.config
import sys
import time


def init_logging():
    logging.config.dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '%(levelname)8s  %(message)s'
                },
                'complete': {
                    'format': '%(asctime)s %(levelname)8s  %(message)s'
                },
            },
            'handlers': {
                'console': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'simple'
                },
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.FileHandler',
                    'filename': time.strftime('import-%Y-%m-%d.log'),
                    'formatter': 'complete'
                }
            },
            'loggers': {
                '': {
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG',
                    'propagate': True
                },
            }
        }
    )


def map_model(modelname):
    modelname = modelname.lower()
    for substring, replacement in {"6d": "6d", "20d": "20d", "430": "430", "lg": "lg", "desire hd": "dhd"}.items():
        if substring in modelname:
            return replacement
    return modelname.replace(" ", "")


def match_any(filename, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def match_any_tiles_suffices(filename):
    return match_any(filename.lower(), TILES_PATTERNS)


def is_photo(filename):
    return match_any(filename.lower(), PHOTO_PATTERNS)


class ProgressIndicator(object):
    def __init__(self):
        self.count = 0
        self.symbols = [".", "o", "O", "0", "O", "o", ".", "_"]

    def progress(self):
        self.count += 1
        sys.stderr.write("%s\r" % self.symbols[self.count % len(self.symbols)])
        sys.stderr.flush()


init_logging()
