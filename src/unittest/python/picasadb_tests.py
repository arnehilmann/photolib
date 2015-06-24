import unittest
from mock import patch, mock_open

from photolib.picasadb import PicasaDb


class PicasaDbTest(unittest.TestCase):

    def test_find_contacts_file(self):
        with patch("os.path.expanduser", return_value="src/resources"):
            pdb = PicasaDb(["src/resources/testsamples"])
            self.assertEqual(pdb.id2person["d920"], "foo")

    def test_build_db(self):
        with patch("photolib.picasadb.PicasaDb._find_contacts_file",
                   return_value="src/resources/testsamples/contacts.xml"):
            pdb = PicasaDb(["src/resources/testsamples"])
            pdb.build_db()

    def test_store_and_read_database(self):
        with patch("photolib.picasadb.PicasaDb._find_contacts_file",
                   return_value="src/resources/testsamples/contacts.xml"):
            pdb = PicasaDb(["src/resources/testsamples"])
            pdb.build_db()

            m = mock_open()
            with patch("__builtin__.open", m, create=True):
                pdb.store_db("/...invalid.filename...")
            m.assert_called_once_with("/...invalid.filename...", "w")

            m = mock_open()
            with patch("__builtin__.open", m, create=True):
                pdb.import_db("/...invalid.filename...")
            m.assert_called_once_with("/...invalid.filename...")

    def test_analyze_faces_string(self):
        with patch("photolib.picasadb.PicasaDb._find_contacts_file",
                   return_value="src/resources/testsamples/contacts.xml"):
            pdb = PicasaDb(["src/resources/testsamples"])
            for face in pdb.analyze_faces_string("rect64(000800000008000),foo;rect64(67890),bar"):
                self.assertEqual(("foo", [0, 0.5, 0.0, 0.5]), face)
                break


if __name__ == "__main__":
    unittest.main()
