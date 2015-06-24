import unittest

import photolib


class PhotolibTest(unittest.TestCase):

    def test_match_photos(self):
        self.assertTrue(photolib.match_any_tiles_suffices("foo.png"))
        self.assertTrue(photolib.match_any_tiles_suffices("foo.jPeG"))
        self.assertFalse(photolib.match_any_tiles_suffices("bar.txt"))


if __name__ == "__main__":
    unittest.main()
