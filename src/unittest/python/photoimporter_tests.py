import unittest
from mock import MagicMock, patch

import os
from datetime import datetime
import logging

import photolib
from photolib.transfer import PhotoImporter


class PhotoImporterTest(unittest.TestCase):

    def setUp(self):
        self.pi = PhotoImporter(["...source..."], "...photos...", artist="me///", exifdata=["bar"])

    def test_init(self):
        self.assertEqual(self.pi.number_prefix, "me")

    # def test_guess_create_date_using_ctime(self):
    #     os.path.getctime = MagicMock()
    #     os.path.getctime.returnvalue = datetime.now()

    #     self.assertEqual(self.pi.guess_create_date_using_ctime("foo", "bar"), datetime(1970, 1, 1, 1, 0, 1))

    def test_guess_create_date_using_path(self):
        self.assertEqual(self.pi.guess_create_date_using_path("1970-02-02"), datetime(1970, 2, 2, 0, 0))
        self.assertEqual(self.pi.guess_create_date_using_path("foo/1970-02-02"), datetime(1970, 2, 2, 0, 0))
        self.assertEqual(self.pi.guess_create_date_using_path("foo"), None)

    def test_format_dirpath(self):
        self.pi.actual_sourcedir = "/foo"
        self.assertEqual(self.pi.format_dirpath(""), ".")
        self.assertEqual(self.pi.format_dirpath("/braz"), "/braz")
        self.assertEqual(self.pi.format_dirpath("/foo/bar"), "/bar")

    def test_format_timedelta(self):
        self.assertEqual(self.pi._format_timedelta(1.0), "00:00:01")

    def test_get_exiftool_fmt_file(self):
        orig_file = photolib.transfer.__file__
        photolib.transfer.__file__ = "/foo"
        self.assertEqual(self.pi._get_exiftool_fmt_file(), "/res/createdate.fmt")
        photolib.transfer.__file__ = orig_file

    def test_main_without_input(self):
        logging.disable(logging.WARN)
        self.pi.counter.inc("test")
        self.pi.main()

    @patch("os.chmod")
    @patch("shutil.move")
    @patch("shutil.copy")
    @patch("os.makedirs")
    def test_import_dir(self, *mocks):
        logging.disable(logging.WARN)
        self.pi.actual_sourcedir = "src/resources/testsamples/2999/04/04"
        self.pi.import_dir(".", ["this_file.ignored.info"])
        self.pi.import_dir("src/resources/testsamples/2999/04/04", ["this_file.ignored.info",
                                                                    "20150621Allium_ursinum1.jpg"])


if __name__ == "__main__":
    unittest.main()
