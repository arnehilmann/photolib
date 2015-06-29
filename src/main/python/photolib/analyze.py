import ConfigParser
import json
import logging
import os
import re
import subprocess

from wand.image import Image

from photolib.picasadb import (PicasaDb, UNKNOWN, PICASA_INI)
from photolib import match_any_tiles_suffices


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
            logging.info("%s: analyzing" % source_image)
            if not match_any_tiles_suffices(source_image):
                continue
            if not config.has_option(source_image, "faces"):
                continue
            logging.info("%s: face found" % source_image)
            try:
                for id, coords in self.picasadb.analyze_faces_string(config.get(source_image, "faces")):
                    name = self.picasadb.id2person.get(id, UNKNOWN)
                    if name is UNKNOWN:
                        continue
                    self.derive_images(dirpath, source_image, name, coords)
            except Exception, e:
                logging.exception(e)
                continue

    def derive_images(self, dirpath, source_image, name, coords):
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

    def create_tile(self, name, filepath, target_dir, basename):
        suffix = ".png"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        filename = os.path.join(target_dir, "%s%s" % (basename, suffix))
        if os.path.exists(filename):
            logging.debug("%s: tile for %s already exists, skipping" % (filepath, name))
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
            logging.debug("%s: face image for %s already exists, skipping" % (filepath, name))
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


class NewAnalyzer(object):
    def __init__(self, photos_dirs, faces_dir, tiles_dir, tiles_size=240):
        self.photos_dirs = [photos_dirs]
        self.faces_dir = faces_dir
        self.tiles_dir = os.path.join(tiles_dir, tiles_size)
        self.tiles_size = tiles_size

    def main(self):
        for images_dir in self.photos_dirs:
            logging.info("scanning %s" % images_dir)
            for dirpath, dirnames, filenames in os.walk(images_dir):
                dirnames.sort()
                rawexifs = subprocess.check_output(["exiftool", "-j", "-q", os.path.join(dirpath)])
                if len(rawexifs) <= 0:
                    continue
                exifs = json.loads(rawexifs)
                for exif in exifs:
                    self.analyze_exif(exif)

    def analyze_exif(self, exif):
        if "RegionAppliedToDimensionsUnit" not in exif:
            return
        filename = exif["SourceFile"]
        basename = os.path.basename(filename)
        region_unit = exif["RegionAppliedToDimensionsUnit"]
        if region_unit != "pixel":
            logging.warn("unknown RegionAppliedToDimensionsUnit '%s' found in %s" % (region_unit, basename))
            return
        width = exif["RegionAppliedToDimensionsW"]
        height = exif["RegionAppliedToDimensionsH"]

        if "RegionType" not in exif:
            return
        for index, regiontype in enumerate(exif["RegionType"]):
            if regiontype != "Face":
                continue
            area_unit = exif["RegionAreaUnit"][index]
            if area_unit != "normalized":
                logging.warn("unknown RegionAreaUnit '%s' found in %s" % (area_unit, basename))
                continue
            name = exif["RegionName"][index]

            self.create_tile(filename, name, "photos")

            nx = exif["RegionAreaX"][index]
            ny = exif["RegionAreaY"][index]
            nw = exif["RegionAreaW"][index]
            nh = exif["RegionAreaH"][index]

            left = int((nx - nw / 2) * width)
            top = int((ny - nh / 2) * height)
            right = int((nx + nw / 2) * width)
            bottom = int((ny + nh / 2) * height)

            # coords = (left, bottom, right, top)
            coords = (left, top, right, bottom)

            face_filename = self.create_face_image(filename, name, coords)
            self.create_tile(face_filename, name, "faces")
        self.dump_exif(exif)

    def create_face_image(self, source_filename, name, coords):
        target_dir = os.path.join(self.faces_dir, name)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        basename, suffix = os.path.splitext(os.path.basename(source_filename))
        target_filename = os.path.join(target_dir, "%s.face.%s%s" % (basename, name, suffix))
        if os.path.exists(target_filename):
            logging.debug("%s: face image for %s already exists, skipping" % (target_filename, name))
            return target_filename
        logging.info("face of '%s' found in %s, at %s" % (name, basename, "%s/%s %s/%s" % coords))

        # cmd = ["convert", source_filename,
        #        "-fill", "none",
        #        "-stroke", "yellow",
        #        "-strokewidth", "20",
        #        "-draw", "arc %i,%i %i,%i 0,360" % coords,
        #        target_filename]

        # crop_string = "%ix%i+%i+%i" % (right - left, bottom - top, left, top)
        crop_string = "%ix%i+%i+%i" % (coords[2] - coords[0], coords[3] - coords[1], coords[0], coords[1])
        cmd = ["convert", source_filename, "-crop", crop_string, "+repage", target_filename]
        logging.info(" ".join(cmd))
        exit_code = subprocess.check_call(cmd)
        logging.debug("exit code: %i" % exit_code)
        return target_filename

    def create_tile(self, source_filename, name, subfolder):
        suffix = ".png"
        basename, suffix = os.path.splitext(os.path.basename(source_filename))
        target_dir = os.path.join(self.tiles_dir, subfolder, name)
        target_filename = os.path.join(target_dir, basename + suffix)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        if os.path.exists(target_filename):
            logging.debug("%s: tile for %s already exists, skipping" % (target_filename, name))
            return target_filename
        logging.info("%s: creating tile for %s" % (target_filename, name))
        exit_code = subprocess.check_call(["convert", source_filename,
                                           "-resize", "%sx%s^" % (self.tiles_size, self.tiles_size),
                                           "-gravity", "Center",
                                           "-crop", "%sx%s+0+0!" % (self.tiles_size, self.tiles_size),
                                           target_filename])
        logging.debug("exit code: %i" % exit_code)
        return target_filename

    @staticmethod
    def dump_exif(exif):
        for key, value in exif.items():
            if key.startswith("Region"):
                logging.debug("exif  %s: %s" % (key, value))


if __name__ == "__main__":
    from docopt import docopt
    arguments = docopt("""
    Usage:
        analyze PHOTOS_DIR FACES_DIR TILES_DIR [--tiles-size=INT]

    Options:
        --tiles-size=INT  size of a tile [default: 240]
            """)
    na = NewAnalyzer(arguments["PHOTOS_DIR"],
                     arguments["FACES_DIR"],
                     arguments["TILES_DIR"],
                     arguments["--tiles-size"])
    na.main()
