PHOTO_SUFFICES = ["jpg", "jpeg", "JPG", "JPEG", "png", "PNG", "gif", "GIF"]

import logging.config
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
                'level':'INFO',
                'class':'logging.StreamHandler',
                'formatter':'simple'
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': 'import.log',
                'formatter':'complete'
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
