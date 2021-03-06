import unittest
from mock import patch, mock_open

import logging

from photolib import init_logging
import photolib.mosaic as mosaic


class MosaicTest(unittest.TestCase):

    def test_preparer(self):
        init_logging()
        logging.disable(logging.WARN)
        p = mosaic.Preparer("src/resources/tiles")

        m = mock_open()
        with patch("tempfile.mkdtemp", return_value="/invalid_dir"):
            with patch("subprocess.call"):
                with patch("shutil.rmtree"):
                    with patch("__builtin__.open", m, create=True):
                        p.main()
        m.assert_any_call("src/resources/tiles/tables.mxt", "w")
        m.assert_any_call("/invalid_dir/tables.mxt")


if __name__ == "__main__":
    unittest.main()
