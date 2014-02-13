import ConfigParser
import json
import logging
import os
import re
from xml.dom import minidom

UNKNOWN = "__unknown__"
PICASA_INI = ".picasa.ini"


class PicasaDb(object):
    def __init__(self, photos_dirs, picasa_contacts_file=None):
        if not picasa_contacts_file:
            import fnmatch
            try:
                picasa_contacts_file = [os.path.join(dirpath, f)
                                        for dirpath, dirnames, files in os.walk(os.path.expanduser("~/.google/picasa/"))
                                        for f in fnmatch.filter(files, 'contacts.xml')][0]
            except IndexError:
                raise Exception("cannot find 'contacts.xml' file under default dir '~/.google/picasa'")
            logging.info("using %s as picasa contacts file" % picasa_contacts_file)
        self.photos_dirs = photos_dirs
        self.id2person = self.read_picasa_person_info(picasa_contacts_file)
        self.database = {}

    def read_picasa_person_info(self, filename):
        xmldoc = minidom.parse(filename)
        contacts = xmldoc.getElementsByTagName('contact')
        mapping = {"ffffffffffffffff": UNKNOWN}
        for contact in contacts:
            id = contact.attributes['id'].value
            name = contact.attributes['name'].value
            mapping[id] = name
        return mapping

    def import_db(self, filename):
        with open(filename) as f:
            try:
                self.database = json.load(f)
            except ValueError:
                logging.warn("%s has wrong format, discarding it" % filename)

    def store_db(self, filename):
        with open(filename, "w") as f:
            json.dump(self.database, f)

    def build_db(self):
        for images_dir in self.photos_dirs:
            logging.info("scanning %s" % images_dir)
            for dirpath, dirnames, filenames in os.walk(images_dir):
                dirnames.sort()
                if PICASA_INI in filenames:
                    logging.info("analyzing %s" % dirpath)
                    self.import_picasa_ini(dirpath)

    def import_picasa_ini(self, dirpath):
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(dirpath, PICASA_INI))
        for source_image in config.sections():
            if config.has_option(source_image, "faces"):
                try:
                    for id, coords in self.analyze_faces_string(config.get(source_image, "faces")):
                        name = self.id2person.get(id, UNKNOWN)
                        if name is UNKNOWN:
                            continue
                        if name not in self.database:
                            self.database[name] = []
                        source_path = os.path.join(dirpath, source_image)
                        self.database[name].append(source_path)
                except Exception, e:
                    logging.exception(e)
                    continue

    def analyze_faces_string(self, s):
        # thanks to reverse-engineering the picasa.ini format:
        # https://gist.github.com/fbuchinger/1073823
        for face_info in s.split(";"):
            rect_info, id = face_info.split(",")
            rect_match = re.match("rect64\((.*)\)", rect_info)
            if rect_match:
                rect = rect_match.group(1)
                yield (id, self.analyze_rect_string(rect))

    def analyze_rect_string(self, s):
        # yuk: leading zeros might be missing to 16 chars length
        while len(s) < 16:
            s = "0%s" % s
        return [int(s[i:i + 4], 16) / 65536.0 for i in range(0, 16, 4)]
