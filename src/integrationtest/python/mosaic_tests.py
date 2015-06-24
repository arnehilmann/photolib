import unittest

import os

import photolib.mosaic as mosaic


class MosaicTest(unittest.TestCase):

    def test_init(self):
        samples_dir = "src/resources/testsamples"
        p = mosaic.Preparer(samples_dir)
        p.main()

        for subdir in (".", ".aha", "2999/04/04"):
            try:
                os.remove(os.path.join(samples_dir, subdir, "tables.mxt"))
            except:
                pass


if __name__ == "__main__":
    unittest.main()
