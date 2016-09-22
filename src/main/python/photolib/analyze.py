import ConfigParser
import json
import logging
import os
import re
import shutil
import subprocess
import sys

from wand.image import Image

from photolib.picasadb import (PicasaDb, UNKNOWN, PICASA_INI)
from photolib import match_any_tiles_suffices


# class Analyzer(object):
#    def __init__(self, photos_dirs, faces_dir, tiles_dir, picasa_contacts_file=None):
#        self.photos_dirs = photos_dirs
#
#        self.picasadb = PicasaDb(photos_dirs, picasa_contacts_file)
#
#        self.faces_dir = faces_dir
#        self.tiles_dir = tiles_dir
#
#    def main(self):
#        for images_dir in self.photos_dirs:
#            logging.info("scanning %s" % images_dir)
#            for dirpath, dirnames, filenames in os.walk(images_dir):
#                dirnames.sort()
#                if PICASA_INI in filenames:
#                    logging.info("analyzing %s" % dirpath)
#                    self.search_faces_in_picasa_ini(dirpath)
#
#    def search_faces_in_picasa_ini(self, dirpath):
#        config = ConfigParser.ConfigParser()
#        config.read(os.path.join(dirpath, PICASA_INI))
#        for source_image in config.sections():
#            logging.info("%s: analyzing" % source_image)
#            if not match_any_tiles_suffices(source_image):
#                continue
#            if not config.has_option(source_image, "faces"):
#                continue
#            logging.info("%s: face found" % source_image)
#            try:
#                for id, coords in self.picasadb.analyze_faces_string(config.get(source_image, "faces")):
#                    name = self.picasadb.id2person.get(id, UNKNOWN)
#                    if name is UNKNOWN:
#                        continue
#                    self.derive_images(dirpath, source_image, name, coords)
#            except Exception, e:
#                logging.exception(e)
#                continue
#
#    def derive_images(self, dirpath, source_image, name, coords):
#        basename, suffix = os.path.splitext(source_image)
#
#        year = None
#        if re.match("20......-", basename):
#            year = basename[0:4]
#        source_path = os.path.join(dirpath, source_image)
#        self.create_tile(name,
#                         source_path,
#                         os.path.join(*filter(None, [self.tiles_dir, "persons", name, year])),
#                         basename)
#
#        face_path = self.create_face_image(name,
#                                           coords,
#                                           source_path,
#                                           os.path.join(self.faces_dir, name),
#                                           basename,
#                                           suffix)
#        self.create_tile(name,
#                         face_path,
#                         os.path.join(*filter(None, [self.tiles_dir, "faces", name, year])),
#                         basename)
#
#    def create_tile(self, name, filepath, target_dir, basename):
#        suffix = ".png"
#        if not os.path.exists(target_dir):
#            os.makedirs(target_dir)
#        filename = os.path.join(target_dir, "%s%s" % (basename, suffix))
#        if os.path.exists(filename):
#            logging.debug("%s: tile for %s already exists, skipping" % (filepath, name))
#            return filename
#        logging.info("%s: creating tile for %s" % (filepath, name))
#        exit_code = subprocess.check_call(["convert", filepath, "-resize", "240x240^",
#                                           "-gravity", "Center", "-crop", "240x240+0+0!", filename])
#        logging.debug("exit code: %i" % exit_code)
#        return filename
#
#    def create_face_image(self, name, coords, filepath, target_dir, basename, suffix):
#        if not os.path.exists(target_dir):
#            os.makedirs(target_dir)
#        filename = os.path.join(target_dir, "%s.face%s" % (basename, suffix))
#        if os.path.exists(filename):
#            logging.debug("%s: face image for %s already exists, skipping" % (filepath, name))
#            return filename
#
#        with Image(filename=filepath) as img:
#            width, height = img.size
#        left = int(coords[0] * width)
#        top = int(coords[1] * height)
#        right = int(coords[2] * width)
#        bottom = int(coords[3] * height)
#
#        logging.debug("%s: %i/%i - %i/%i -> %s" % (name, left, top, right, bottom, filename))
#        logging.info("%s: cropping to face of %s" % (filepath, name))
#        # exit_code = subprocess.check_call(["convert", filepath, "-fill", "none", "-stroke", "yellow",
#        #                                    "-strokewidth", "10",
#        #                                    "-draw", "rectangle %i,%i %i,%i" % (left, top, right, bottom), filename])
#        crop_string = "%ix%i+%i+%i" % (right - left, bottom - top, left, top)
#        logging.debug("crop option: %s" % crop_string)
#        exit_code = subprocess.check_call(["convert", filepath, "-crop", crop_string, "+repage", filename])
#        logging.debug("exit code: %i" % exit_code)
#        return filename


class NewAnalyzer(object):
    def __init__(self, photos_dir, faces_dir, tiles_dir, panoramas_dir=None, tile_size=240):
        self.photos_dirs = photos_dir
        self.faces_dir = faces_dir
        self.tiles_dir = os.path.join(tiles_dir, tile_size)
        self.tile_size = tile_size
        self.panoramas_dir = panoramas_dir
        self.generated_files = set()

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
                        datas = json.load(datafile)
                except Exception as e:
                    print "an exception occured: %s" % e
                    continue
                # print json.dumps(exifs, indent=4)
                for data in datas:
                    sys.stdout.write(".")
                    self.analyze_size(dirpath, data)
                    self.analyze_format(dirpath, data)
                    self.analyze_exif(dirpath, data)
                sys.stdout.flush()
        for generated_file in sort(self.generated_files):
            logging.info("generated: %s" % generated_file)

    def analyze_size(self, dirpath, data):
        filename = os.path.join(dirpath, data["SourceFile"])
        if os.path.getsize(filename) == 0:
            logging.warn("%s: empty file" % filename)
            os.unlink(filename)

    def analyze_format(self, dirpath, data):
        if not self.panoramas_dir:
            return
        if not os.path.exists(self.panoramas_dir):
            os.makedirs(self.panoramas_dir)
        filename = os.path.join(dirpath, data["SourceFile"])
        exif = data.get("EXIF")
        if not exif:
            return
        width = exif.get("ExifImageWidth", 1)
        height = exif.get("ExifImageHeight", 1)
        if max(width, height) / min(width, height) >= 2:
            if not os.path.exists(os.path.join(self.panoramas_dir, filename)):
                logging.info("%s: new panorama found" % filename)
                shutil.copy(filename, self.panoramas_dir)

    def analyze_exif(self, dirpath, exif):
        filename = os.path.join(dirpath, exif["SourceFile"])
        # logging.info("analyzing '%s'" % filename)
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
        if "RegionName" not in xmp:
            logging.warn("region found but no name in %s" % basename)
            return

        region_area_x = xmp["RegionAreaX"]
        region_area_y = xmp["RegionAreaY"]
        region_area_w = xmp["RegionAreaW"]
        region_area_h = xmp["RegionAreaH"]
        region_area_unit = xmp["RegionAreaUnit"]
        region_name = xmp["RegionName"]
        region_type = xmp["RegionType"]

        multiple_regions = type(region_area_x) is list

        if not multiple_regions:
            region_area_x = [region_area_x]
            region_area_y = [region_area_y]
            region_area_w = [region_area_w]
            region_area_h = [region_area_h]
            region_area_unit = [region_area_unit]
            region_name = [region_name]
            region_type = [region_type]

        names = []
        for index, regiontype in enumerate(region_type):
            if regiontype != "Face":
                continue
            area_unit = region_area_unit[index]
            if area_unit != "normalized":
                logging.warn("unknown RegionAreaUnit '%s' found in %s" % (area_unit, basename))
                continue
            name = region_name[index]
            names.append(name)

            year = None
            if re.match("20..-..-..T", basename) or re.match("20......-", basename):
                year = basename[0:4]

            tile_filename = self.calc_tile_filename(filename, "photos", name, year)
            face_filename = self.calc_face_filename(filename, name, year)
            facetile_filename = self.calc_tile_filename(face_filename, "faces", name, year)
            self.generated_files.add(tile_filename)
            self.generated_files.add(face_filename)
            self.generated_files.add(facetile_filename)

            self.create_tile(filename, tile_filename)

            nx = region_area_x[index]
            ny = region_area_y[index]
            nw = region_area_w[index]
            nh = region_area_h[index]

            left = int((nx - nw / 2) * width)
            top = int((ny - nh / 2) * height)
            right = int((nx + nw / 2) * width)
            bottom = int((ny + nh / 2) * height)
            coords = (left, top, right, bottom)

            self.create_face_image(filename, coords, face_filename)
            if os.path.getsize(face_filename) > 0:
                self.create_tile(face_filename, facetile_filename)
            else:
                os.unlink(face_filename)

        # self.dump_exif(exif)
        return names

    def calc_face_filename(self, source_filename, name, year):
        year = year if year else ""
        target_dir = os.path.join(self.faces_dir, name, year)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        basename, suffix = os.path.splitext(os.path.basename(source_filename))
        return os.path.join(target_dir, "%s.face.%s%s" % (basename, name, suffix))


    def create_face_image(self, source_filename, coords, target_filename):
        target_dir = os.path.dirname(target_filename)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        basename, suffix = os.path.splitext(os.path.basename(source_filename))
        if os.path.exists(target_filename):
            logging.debug("%s: face image already exists, skipping" % (target_filename))
            return target_filename
        logging.info("face found, creating %s" % (target_filename))
        crop_string = "%ix%i+%i+%i" % (coords[2] - coords[0], coords[3] - coords[1], coords[0], coords[1])
        cmd = ["convert", source_filename, "-crop", crop_string, "+repage", target_filename]
        exit_code = subprocess.check_call(cmd)
        logging.debug("exit code: %i" % exit_code)
        return target_filename

    def calc_tile_filename(self, source_filename, subfolder, name, year):
        year = year if year else ""
        basename, suffix = os.path.splitext(os.path.basename(source_filename))
        target_dir = os.path.join(self.tiles_dir, subfolder, name, year)
        return os.path.join(target_dir, basename + suffix)

    def create_tile(self, source_filename, target_filename):
        target_dir = os.path.dirname(target_filename)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        if os.path.exists(target_filename):
            logging.debug("%s: tile already exists, skipping" % (target_filename))
            return target_filename
        logging.info("%s: creating tile" % (target_filename))
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
