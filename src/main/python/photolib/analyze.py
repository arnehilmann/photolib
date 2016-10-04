from functools import partial
import json
import logging
from multiprocessing import Pool
import os
import re
import shutil
import subprocess
import sys

from photolib import ProgressIndicator


def analyze_size(dirpath, data):
    filename = os.path.join(dirpath, data["SourceFile"])
    if os.path.getsize(filename) == 0:
        logging.warn("%s: empty file" % filename)
        os.unlink(filename)


def makedirs(dirpath):
    if not os.path.exists(dirpath):
        try:
            os.makedirs(dirpath)
        except OSError as e:
            if e.errno != 17:
                raise


def analyze_format(dirpath, data, panoramas_dir):
    if not panoramas_dir:
        return
    makedirs(panoramas_dir)
    filename = os.path.join(dirpath, data["SourceFile"])
    exif = data.get("EXIF")
    if not exif:
        return
    width = exif.get("ExifImageWidth", 1)
    height = exif.get("ExifImageHeight", 1)
    if max(width, height) / min(width, height) >= 2:
        if not os.path.exists(os.path.join(panoramas_dir, filename)):
            logging.info("%s: new panorama found" % filename)
            shutil.copy(filename, panoramas_dir)


def create_face_image(source_filename, coords, target_filename):
    target_dir = os.path.dirname(target_filename)
    makedirs(target_dir)
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


def calc_face_filename(source_filename, name, year, faces_dir):
    year = year if year else ""
    target_dir = os.path.join(faces_dir, name, year)
    makedirs(target_dir)
    basename, suffix = os.path.splitext(os.path.basename(source_filename))
    return os.path.join(target_dir, "%s.face.%s%s" % (basename, name, suffix))


def calc_tile_filename(source_filename, subfolder, name, year, tiles_dir):
    year = year if year else ""
    basename, suffix = os.path.splitext(os.path.basename(source_filename))
    target_dir = os.path.join(tiles_dir, subfolder, name, year)
    return os.path.join(target_dir, basename + suffix)


def create_tile(source_filename, target_filename, tile_size):
    target_dir = os.path.dirname(target_filename)
    makedirs(target_dir)
    if os.path.exists(target_filename):
        logging.debug("%s: tile already exists, skipping" % (target_filename))
        return target_filename
    logging.info("%s: creating tile" % (target_filename))
    exit_code = subprocess.check_call(["convert", source_filename,
                                       "-resize", "%sx%s^" % (tile_size, tile_size),
                                       "-gravity", "Center",
                                       "-crop", "%sx%s+0+0!" % (tile_size, tile_size),
                                       target_filename])
    logging.debug("exit code: %i" % exit_code)
    return target_filename


def analyze_exif(dirpath, exif, tiles_dir, faces_dir, tile_size):
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

    generated_files = set()
    for index, regiontype in enumerate(region_type):
        if regiontype != "Face":
            continue
        area_unit = region_area_unit[index]
        if area_unit != "normalized":
            logging.warn("unknown RegionAreaUnit '%s' found in %s" % (area_unit, basename))
            continue
        name = region_name[index]

        year = None
        if re.match("20..-..-..T", basename) or re.match("20......-", basename):
            year = basename[0:4]

        tile_filename = calc_tile_filename(filename, "photos", name, year, tiles_dir)
        face_filename = calc_face_filename(filename, name, year, faces_dir)
        facetile_filename = calc_tile_filename(face_filename, "faces", name, year, tiles_dir)
        generated_files.add(tile_filename)
        generated_files.add(face_filename)
        generated_files.add(facetile_filename)

        create_tile(filename, tile_filename, tile_size)

        nx = region_area_x[index]
        ny = region_area_y[index]
        nw = region_area_w[index]
        nh = region_area_h[index]

        left = int((nx - nw / 2) * width)
        top = int((ny - nh / 2) * height)
        right = int((nx + nw / 2) * width)
        bottom = int((ny + nh / 2) * height)
        coords = (left, top, right, bottom)

        create_face_image(filename, coords, face_filename)
        if os.path.getsize(face_filename) > 0:
            create_tile(face_filename, facetile_filename, tile_size)
        else:
            os.unlink(face_filename)
    return generated_files


def analyze(data, dirpath, tiles_dir, faces_dir, panoramas_dir, tile_size):
    analyze_size(dirpath, data)
    analyze_format(dirpath, data, panoramas_dir)
    generated_files = analyze_exif(dirpath, data, tiles_dir, faces_dir, tile_size)
    return generated_files if generated_files else set()


class NewAnalyzer(object):
    def __init__(self, photos_dir, faces_dir, tiles_dir, panoramas_dir=None, tile_size=240, cleanup=False):
        self.photos_dirs = photos_dir
        self.faces_dir = faces_dir
        self.tiles_dir = os.path.join(tiles_dir, tile_size)
        self.tile_size = tile_size
        self.panoramas_dir = panoramas_dir
        self.cleanup = cleanup

    def main(self):
        pi = ProgressIndicator()
        generated_files = []
        pool = Pool(processes=10)
        for images_dir in self.photos_dirs:
            logging.info("scanning %s" % images_dir)
            for dirpath, dirnames, filenames in os.walk(images_dir):
                dirnames.sort()
                try:
                    with open(os.path.join(dirpath, "exifdata.json")) as datafile:
                        datas = json.load(datafile)
                except Exception as e:
                    logging.exception("an exception occured: %s" % e)
                    continue
                pi.progress()

                analyze_dirpath = partial(analyze,
                                          dirpath=dirpath,
                                          tiles_dir=self.tiles_dir,
                                          faces_dir=self.faces_dir,
                                          panoramas_dir=self.panoramas_dir,
                                          tile_size=self.tile_size)

                results = pool.map(analyze_dirpath, datas)
                results = [item for subset in results for item in subset]
                if results:
                    generated_files.extend(results)

        logging.info("%i generated files" % len(generated_files))

        for top_dir in [self.faces_dir, self.tiles_dir]:
            for dirpath, dirnames, filenames in os.walk(top_dir):
                pi.progress()
                for filename in filenames:
                    if filename == "tables.mxt":
                        continue
                    if "photos" not in dirpath and "faces" not in dirpath:
                        continue
                    filepath = os.path.join(dirpath, filename)
                    if filepath not in generated_files:
                        logging.warn("obsolete %s found" % filepath)
                        if self.cleanup:
                            os.unlink(filepath)
                            logging.warn("%s removed" % filepath)

    @staticmethod
    def dump_exif(exif):
        for key, value in exif.items():
            if key.startswith("Region"):
                logging.debug("exif  %s: %s" % (key, value))
