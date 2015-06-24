import ConfigParser
import logging
import os
import re
import subprocess

from wand.image import Image

from photolib.picasadb import (PicasaDb, UNKNOWN, PICASA_INI)


class Analyzer(object):
    def __init__(self, photos_dirs, faces_dir, tiles_dir, picasa_contacts_file=None):
        self.photos_dirs = photos_dirs

        self.picasadb = PicasaDb(photos_dirs, picasa_contacts_file)

        self.faces_dir = faces_dir
        self.tiles_dir = tiles_dir

    def main(self):
        for images_dir in self.photos_dirs:
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
                    for id, coords in self.picasadb.analyze_faces_string(config.get(source_image, "faces")):
                        name = self.id2person.get(id, UNKNOWN)
                        if name is UNKNOWN:
                            continue
                        basename, suffix = os.path.splitext(source_image)

                        year = None
                        if re.match("20......-", basename):
                            year = basename[0:4]
                        source_path = os.path.join(dirpath, source_image)
                        self.create_tile(name,
                                         source_path,
                                         os.path.join(*filter(None, [self.tiles_dir, "persons", name, year])),
                                         basename)

                        face_path = self.create_face_image(name,
                                                           coords,
                                                           source_path,
                                                           os.path.join(self.faces_dir, name),
                                                           basename,
                                                           suffix)
                        self.create_tile(name,
                                         face_path,
                                         os.path.join(*filter(None, [self.tiles_dir, "faces", name, year])),
                                         basename)

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
        exit_code = subprocess.check_call(["convert", filepath, "-resize", "240x240^",
                                           "-gravity", "Center", "-crop", "240x240+0+0!", filename])
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
        # exit_code = subprocess.check_call(["convert", filepath, "-fill", "none", "-stroke", "yellow",
        #                                    "-strokewidth", "10",
        #                                    "-draw", "rectangle %i,%i %i,%i" % (left, top, right, bottom), filename])
        crop_string = "%ix%i+%i+%i" % (right - left, bottom - top, left, top)
        logging.debug("crop option: %s" % crop_string)
        exit_code = subprocess.check_call(["convert", filepath, "-crop", crop_string, "+repage", filename])
        logging.debug("exit code: %i" % exit_code)
        return filename
