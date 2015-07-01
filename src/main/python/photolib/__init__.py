PHOTO_SUFFICES = [".jpg", ".jpeg", ".png", ".gif", ".cr2"]
TILES_SUFFICES = [".jpg", ".jpeg", ".png", ".gif"]
IGNORED_SUFFICES = [".ini", ".db", ".info"]

TILES_PATTERNS = ["*" + s for s in TILES_SUFFICES]
PHOTO_PATTERNS = ["*" + s for s in PHOTO_SUFFICES]

import time
import logging.config
import fnmatch


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


def match_any(filename, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def match_any_tiles_suffices(filename):
    return match_any(filename.lower(), TILES_PATTERNS)


def is_photo(filename):
    return match_any(filename.lower(), PHOTO_PATTERNS)


init_logging()
