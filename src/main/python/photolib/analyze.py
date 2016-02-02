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
    def __init__(self, photos_dir, faces_dir, tiles_dir, tile_size=240):
        self.photos_dirs = photos_dir
        self.faces_dir = faces_dir
        self.tiles_dir = os.path.join(tiles_dir, tile_size)
        self.tile_size = tile_size

    def main(self):
        for images_dir in self.photos_dirs:
            logging.info("scanning %s" % images_dir)
            for dirpath, dirnames, filenames in os.walk(images_dir):
                dirnames.sort()
#                rawexifs = subprocess.check_output(["exiftool", "-j", "-q", os.path.join(dirpath)])
#                if len(rawexifs) <= 0:
#                    continue
#                exifs = json.loads(rawexifs)
                try:
                    with open(os.path.join(dirpath, "exifdata.json")) as datafile:
                        exifs = json.load(datafile)
                except Exception as e:
                    print "an exception occured: %s" % e
                    continue
                # print json.dumps(exifs, indent=4)
                for exif in exifs:
                    self.analyze_exif(dirpath, exif)

    def analyze_exif(self, dirpath, exif):
        filename = os.path.join(dirpath, exif["SourceFile"])
        logging.info("analyzing '%s'" % filename)
        basename = os.path.basename(filename)
        xmp = exif.get("XMP")
        if not xmp:
            return
        region_unit = xmp.get("RegionAppliedToDimensionsUnit")

        if not region_unit:
            return
        if region_unit != "pixel":
            logging.warn("unknown RegionAppliedToDimensionsUnit '%s' found in %s" % (region_unit, basename))
            return
        width = xmp["RegionAppliedToDimensionsW"]
        height = xmp["RegionAppliedToDimensionsH"]

        if "RegionType" not in xmp:
            return
        for index, regiontype in enumerate(xmp["RegionType"]):
            if regiontype != "Face":
                continue
            if "RegionName" not in xmp:
                logging.warn("face region found but no name?")
                continue
            area_unit = xmp["RegionAreaUnit"][index]
            if area_unit != "normalized":
                logging.warn("unknown RegionAreaUnit '%s' found in %s" % (area_unit, basename))
                continue
            name = xmp["RegionName"][index]

            year = None
            if re.match("20..-..-..T", basename) or re.match("20......-", basename):
                year = basename[0:4]
            self.create_tile(filename, "photos", name, year)

            nx = xmp["RegionAreaX"][index]
            ny = xmp["RegionAreaY"][index]
            nw = xmp["RegionAreaW"][index]
            nh = xmp["RegionAreaH"][index]

            left = int((nx - nw / 2) * width)
            top = int((ny - nh / 2) * height)
            right = int((nx + nw / 2) * width)
            bottom = int((ny + nh / 2) * height)
            coords = (left, top, right, bottom)

            face_filename = self.create_face_image(filename, coords, name, year)
            self.create_tile(face_filename, "faces", name, year)
        self.dump_exif(exif)

    def create_face_image(self, source_filename, coords, name, year):
        year = year if year else ""
        target_dir = os.path.join(self.faces_dir, name, year)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        basename, suffix = os.path.splitext(os.path.basename(source_filename))
        target_filename = os.path.join(target_dir, "%s.face.%s%s" % (basename, name, suffix))
        if os.path.exists(target_filename):
            logging.debug("%s: face image for %s already exists, skipping" % (target_filename, name))
            return target_filename
        logging.info("face of '%s' found in %s, at %s" % (name, basename, "%s/%s %s/%s" % coords))
        crop_string = "%ix%i+%i+%i" % (coords[2] - coords[0], coords[3] - coords[1], coords[0], coords[1])
        cmd = ["convert", source_filename, "-crop", crop_string, "+repage", target_filename]
        exit_code = subprocess.check_call(cmd)
        logging.debug("exit code: %i" % exit_code)
        return target_filename

    def create_tile(self, source_filename, subfolder, name, year):
        year = year if year else ""
        basename, suffix = os.path.splitext(os.path.basename(source_filename))
        target_dir = os.path.join(self.tiles_dir, subfolder, name, year)
        target_filename = os.path.join(target_dir, basename + suffix)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        if os.path.exists(target_filename):
            logging.debug("%s: tile for %s already exists, skipping" % (target_filename, name))
            return target_filename
        logging.info("%s: creating tile for %s" % (target_filename, name))
        exit_code = subprocess.check_call(["convert", source_filename,
                                           "-resize", "%sx%s^" % (self.tile_size, self.tile_size),
                                           "-gravity", "Center",
                                           "-crop", "%sx%s+0+0!" % (self.tile_size, self.tile_size),
                                           target_filename])
        logging.debug("exit code: %i" % exit_code)
        return target_filename

    @staticmethod
    def dump_exif(exif):
        for key, value in exif.items():
            if key.startswith("Region"):
                logging.debug("exif  %s: %s" % (key, value))
