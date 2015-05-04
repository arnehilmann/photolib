from datetime import datetime
import logging
import os
import re
import shutil
import subprocess
import time

from photolib.logging_subprocess import call
from photolib import PHOTO_SUFFICES, IGNORED_SUFFICES

FORMAT_NEW_PATH = "%Y/%Y-%m/%Y-%m-%d/%Y-%m-%dT%H:%M"
NEW_PATH_DATE_FORMAT = "%Y/%Y-%m/%Y-%m-%d"


class Counter(object):
    def __init__(self):
        self.counter = {"overall": {}}

    def inc(self, what, additional_name=None, amount=1):
        for name in filter(None, ["overall", additional_name]):
            self.counter.setdefault(name, {})
            self.counter[name][what] = self.counter[name].get(what, 0) + amount

    def get(self, name="overall"):
        return self.counter.get(name, {})

    def reset(self, name):
        self.counter[name] = {}


class PhotoImporter(object):
    def __init__(self, source_dirs, photos_dir, artist=None, exifdata=None):
        self.source_dirs = source_dirs
        self.photos_dir = photos_dir
        self.exifdata = exifdata if exifdata else []
        self.artist = artist
        self.number_prefix = re.sub("[^a-zA-Z]*", "", self.artist) if self.artist else None
        self.actual_sourcedir = None
        self.counter = Counter()
        if self.artist:
            self.exifdata.append("-Artist=%s" % self.artist)

    def _format_timedelta(self, delta):
        return time.strftime("%H:%M:%S", time.gmtime(delta))

    def _get_exiftool_fmt_file(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "res", "createdate.fmt")

    def main(self):
        start = time.time()
        logging.info("=" * 80)
        return_code = 2
        try:
            self._import()
            return_code = 0
        except KeyboardInterrupt:
            logging.warning("import aborted by user interaction")
            return_code = 127
        except Exception as e:
            logging.exception(e)
            logging.critical("aborting due to previous errors")
            return_code = 1
        end = time.time()
        logging.info("-" * 80)
        for key in sorted(self.counter.get().keys()):
            value = self.counter.get()[key]
            logging.info("%16i %s" % (value, key))
        logging.info("%16s %s" % (self._format_timedelta(end - start), "elapsed"))
        logging.info("photos dir: %s" % self.photos_dir)
        logging.info("=" * 80)
        return return_code

    def _import(self):
        for actual_sourcedir in self.source_dirs:
            self.actual_sourcedir = actual_sourcedir
            if not self.actual_sourcedir.endswith("/"):
                self.actual_sourcedir = self.actual_sourcedir + "/"
            for dirpath, dirnames, filenames in os.walk(actual_sourcedir):
                dirnames.sort()
                if not filenames:
                    continue
                start = time.time()
                self.counter.reset("dir")
                self.import_dir(dirpath, filenames)
                end = time.time()
                logging.debug("%s: %s elapsed" % (self.format_dirpath(dirpath), self._format_timedelta(end - start)))

    def format_dirpath(self, dirpath):
        reduced_dirpath = dirpath.replace(self.actual_sourcedir, "")
        if not reduced_dirpath:
            reduced_dirpath = "."
        return reduced_dirpath

    def guess_create_date_using_path(self, dirpath):
        parts = dirpath.split("/")
        while parts:
            for format in ["%Y-%m-%d", "%Y%m%d", "%y%m%d", "%Y"]:
                try:
                    return datetime.strptime("-".join(parts), format)
                except ValueError:
                    pass
            parts = parts[1:]
        return None

    def guess_create_date_using_ctime(self, dirpath, filename):
        return datetime.fromtimestamp(os.path.getctime(os.path.join(dirpath, filename)))

    def handle_file_without_exif_date(self, dirpath, filename):
        logging.debug("examining %s due to missing exif information" % os.path.join(dirpath, filename))
        prefix, suffix = os.path.splitext(filename)

        create_date = self.guess_create_date_using_path(dirpath)
        if not create_date:
            create_date = self.guess_create_date_using_ctime(dirpath, filename)
        if create_date:
            return os.path.join("__date_guessed__", datetime.strftime(create_date, NEW_PATH_DATE_FORMAT), prefix)

        return None

    def import_dir(self, dirpath, filenames=None):
        short_dirpath = os.path.basename(dirpath)
        if short_dirpath.startswith("."):
            logging.warn("%s: skipping due to dot-name" % dirpath)
            self.counter.inc("directories skipped due to dot-name")
            return
        logging.info("%s: scanning..." % self.format_dirpath(dirpath))
        self.counter.inc("directories scanned")
        with open(os.devnull, "w") as devnull:
            create_dates = subprocess.check_output(
                ["/usr/bin/exiftool",
                    "-q", "-p", self._get_exiftool_fmt_file(),
                    "-m", "-d", FORMAT_NEW_PATH, dirpath],
                stderr=devnull
            )
        old2new_pathes = {}
        for line in create_dates.splitlines():
            try:
                filename, new_filename = line.split("|")
                if not new_filename:
                    logging.debug("%s: no exif date found" % filename)
                    new_filename = self.handle_file_without_exif_date(dirpath, filename)
                    if new_filename:
                        logging.info("%s: guessing create date, resulting path: %s" % (filename, new_filename))
                        self.counter.inc("files with guessed creation date", "dir")
                    else:
                        filename_prefix, _ = os.path.splitext(filename)
                        new_filename = os.path.join("__unknown_date__",
                                                    os.path.basename(dirpath.rstrip("/")), filename_prefix)
                        logging.warn("%s: no date info available, falling back to %s" % (
                                     os.path.join(dirpath, filename), new_filename))
                        self.counter.inc("files with date unknown", "dir")
            except Exception as e:
                logging.warn("'%s': format problem, skipping" % line)
                logging.exception(e)
                self.counter.inc("files with exif format problem", "dir")
                continue
            path = os.path.join(dirpath, filename)
            name, suffix = os.path.splitext(filename)
            suffix = suffix.lower()
            number = ""
            if suffix in PHOTO_SUFFICES:
                number = re.sub(".*\.", "", name)
                number = re.sub(".*_", "", number)
                # number = re.sub("\D*", "", number)
            if self.number_prefix:
                number = "%s-%s" % (self.number_prefix, number)
            if number:
                number = ".%s" % number
            new_path = os.path.join(self.photos_dir, "%s%s%s" % (new_filename, number, suffix))
            old2new_pathes[path] = new_path
        self.counter.inc("files to check", amount=len(old2new_pathes))
        logging.info("%s: %i photos found" % (self.format_dirpath(dirpath), len(old2new_pathes)))

        for filename in filenames:
            _, suffix = os.path.splitext(filename)
            if suffix.lower() in IGNORED_SUFFICES:
                logging.debug("%s: ignored" % filename)
                self.counter.inc("files skipped due to ignored suffix %s" % suffix)
                continue
            filename = os.path.join(dirpath, filename)
            if filename not in old2new_pathes:
                logging.warn("%s: not considered a photo/video, thus skipping" % self.format_dirpath(filename))

        for old_path in sorted(old2new_pathes.keys()):
            new_path = old2new_pathes[old_path]
            if os.path.exists(new_path):
                logging.debug("%s: target file %s already exists, leaving untouched" % (old_path, new_path))
                self.counter.inc("files xferred (already transferred, thus skipped)", "dir")
                self.counter.inc("files xferred total")
            else:
                try:
                    self._import_photo(old_path, new_path)
                    self.counter.inc("files xferred total")
                    logging.info("%s xferred %s" % (os.path.basename(old_path),
                                 "(#%(files xferred total)i / %(files to check)i)" % self.counter.get()))
                except Exception as e:
                    logging.exception(e)
                    self.counter.inc("exceptions while importing", "dir")
                    logging.warn("cannot import %s" % os.path.join(dirpath, filename))
                    self.counter.inc("files skipped due to missing date", "dir")

    def _add_exif_data(self, path):
        if self.exifdata:
            call(["/usr/bin/exiftool"] + self.exifdata + ["-overwrite_original_in_place", path], logger=logging)

    def _import_photo(self, old_path, new_path):
        logging.debug("file %s: importing as %s" % (old_path, new_path))
        new_dir = os.path.dirname(new_path)
        if not os.path.exists(new_dir):
            logging.debug("creating subdir %s" % new_dir)
            os.makedirs(new_dir)
            self.counter.inc("subdirs created", "dir")
        name, suffix = os.path.splitext(old_path)
        if suffix.lower() in PHOTO_SUFFICES:
            tmp_path = "%s.tmp" % new_path
            shutil.copy(old_path, tmp_path)
            call(["/usr/bin/jhead", "-q", "-autorot", tmp_path], logger=logging)

            self._add_exif_data(tmp_path)

            shutil.move(tmp_path, new_path)
            self.counter.inc("photos with %s xferred" % suffix)
        else:
            shutil.copy(old_path, new_path)
            self.counter.inc("non-photos with %s xferred" % suffix)
        os.chmod(new_path, 0O444)
