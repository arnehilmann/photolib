import ConfigParser
import logging
import os
import re
import subprocess
from xml.dom import minidom

from wand.image import Image

UNKNOWN = "__unknown__"
PICASA_INI = ".picasa.ini"


class Analyzer(object):
    def __init__(self, images_dirs, faces_dir, tiles_dir, picasa_contacts_file=None):
        if not picasa_contacts_file:
            import fnmatch
            picasa_contacts_file = [os.path.join(dirpath, f)
                                    for dirpath, dirnames, files in os.walk(os.path.expanduser("~/.google/picasa/"))
                                    for f in fnmatch.filter(files, 'contacts.xml')][0]
            logging.info("using %s as picasa contacts file" % picasa_contacts_file)
        self.images_dirs = images_dirs
        self.faces_dir = faces_dir
        self.tiles_dir = tiles_dir
        self.id2person = self.read_picasa_person_info(picasa_contacts_file)

    def read_picasa_person_info(self, filename):
        xmldoc = minidom.parse(filename)
        contacts = xmldoc.getElementsByTagName('contact')
        mapping = {"ffffffffffffffff": UNKNOWN}
        for contact in contacts:
            id = contact.attributes['id'].value
            name = contact.attributes['name'].value
            mapping[id] = name
        return mapping

    def main(self):
        for images_dir in self.images_dirs:
            logging.info("scanning %s" % images_dir)
            for dirpath, dirnames, filenames in os.walk(images_dir):
                dirnames.sort()
                if PICASA_INI in filenames:
                    logging.info("analyzing %s" % dirpath)
                    self.search_faces_in_picasa_ini(dirpath)

    def search_faces_in_picasa_ini(self, dirpath):
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(dirpath, PICASA_INI))
        for source_image in config.sections():
            if config.has_option(source_image, "faces"):
                logging.info("%s: analyzing" % source_image)
                try:
                    for id, coords in self.analyze_faces_string(config.get(source_image, "faces")):
                        name = self.id2person.get(id, UNKNOWN)
                        if name is UNKNOWN:
                            continue
                        basename, suffix = os.path.splitext(source_image)
                        source_path = os.path.join(dirpath, source_image)

                        face_path = self.create_face_image(name, coords, source_path, os.path.join(self.faces_dir, name), basename, suffix)

                        self.create_tile(name, source_path, os.path.join(self.tiles_dir, "persons", name), basename)
                        self.create_tile(name, face_path, os.path.join(self.tiles_dir, "faces", name), basename)

                except Exception, e:
                    logging.exception(e)
                    continue

    def create_tile(self, name, filepath, target_dir, basename):
        suffix = ".png"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        filename = os.path.join(target_dir, "%s%s" % (basename, suffix))
        if os.path.exists(filename):
            logging.info("%s: tile for %s already exists, skipping" % (filepath, name))
            return filename
        logging.info("%s: creating tile for %s" % (filepath, name))
        exit_code = subprocess.check_call(["convert", filepath, "-resize", "240x240^", "-gravity", "Center", "-crop", "240x240+0+0!", filename])
        logging.debug("exit code: %i" % exit_code)
        return filename

    def create_face_image(self, name, coords, filepath, target_dir, basename, suffix):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        filename = os.path.join(target_dir, "%s.face%s" % (basename, suffix))
        if os.path.exists(filename):
            logging.info("%s: face image for %s already exists, skipping" % (filepath, name))
            return filename

        with Image(filename=filepath) as img:
            width, height = img.size
        left = int(coords[0] * width)
        top = int(coords[1] * height)
        right = int(coords[2] * width)
        bottom = int(coords[3] * height)

        logging.debug("%s: %i/%i - %i/%i -> %s" % (name, left, top, right, bottom, filename))
        logging.info("%s: cropping to face of %s" % (filepath, name))
        #exit_code = subprocess.check_call(["convert", filepath, "-fill", "none", "-stroke", "yellow", "-strokewidth", "10", "-draw", "rectangle %i,%i %i,%i" % (left, top, right, bottom), filename])
        crop_string = "%ix%i+%i+%i" % (right - left, bottom - top, left, top)
        logging.debug("crop option: %s" % crop_string)
        exit_code = subprocess.check_call(["convert", filepath, "-crop", crop_string, "+repage", filename])
        logging.debug("exit code: %i" % exit_code)
        return filename

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
        while len(s) < 16:
            s = "0%s" % s
        return [int(s[i:i + 4], 16) / 65536.0 for i in range(0, 16, 4)]
