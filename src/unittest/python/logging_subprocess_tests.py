import unittest

import logging

from photolib.logging_subprocess import call


class LoggingSubprocessTest(unittest.TestCase):

    def test_simple(self):
        logger = logging.getLogger("foo")
        logger.setLevel(logging.WARN)
        call(["ls", "-al", "/"], logger)

if __name__ == "__main__":
    unittest.main()
