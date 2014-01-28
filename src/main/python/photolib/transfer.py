from datetime import datetime
import logging
import os
import re
import shutil
import subprocess
import time

from photolib.logging_subprocess import call
from photolib import PHOTO_SUFFICES

FORMAT_NEW_PATH = "%Y/%m/%d/%Y%m%d-%H%M"
NEW_PATH_DATE_FORMAT = "%Y/%m/%d/%Y%m%d"

class Counter(object):
    def __init__(self):
        self.counter = {"overall":{}}

    def inc(self, what, additional_name=None, amount=1):
        for name in filter(None, ["overall", additional_name]):
            self.counter.setdefault(name, {})
            self.counter[name][what] = self.counter[name].get(what, 0) + amount

    def get(self, name="overall"):
        return self.counter.get(name, {})

    def reset(self, name):
        self.counter[name] = {}


class PhotoImporter(object):
    def __init__(self, source_dirs, photos_dir):
        self.source_dirs = source_dirs
        self.photos_dir = photos_dir
        self.actual_sourcedir = None
        self.counter = Counter()

    def _format_timedelta(self, delta):
        return time.strftime("%H:%M:%S", time.gmtime(delta))

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
        except Exception, e:
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
        return dirpath
        #reduced_dirpath = dirpath.replace(self.actual_sourcedir, "")
        #if not reduced_dirpath:
            #reduced_dirpath = "."
        #return reduced_dirpath

    def guess_create_date(self, dirpath):
        parts = dirpath.split("/")
        while parts:
            for format in ["%Y-%m-%d", "%Y%m%d", "%y%m%d", "%Y"]:
                try:
                    return datetime.strptime("-".join(parts), format)
                    break
                except ValueError:
                    pass
            parts = parts[1:]
        return None

    def handle_file_without_exif_date(self, dirpath, filename):
        logging.debug("examining %s due to missing exif information" % os.path.join(dirpath, filename))
        create_date = self.guess_create_date(dirpath)
        if create_date:
            return datetime.strftime(create_date, NEW_PATH_DATE_FORMAT)
        return None
        #name, suffix = os.path.splitext(filename)
        #return "_unknown_/%s" % name

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
                    "-q", "-p", "res/createdate.fmt",
                    "-m", "-d", FORMAT_NEW_PATH, dirpath],
                stderr = devnull
            )
        old2new_pathes = {}
        for line in create_dates.splitlines():
            try:
                filename, new_filename = line.split("|")
                if not new_filename:
                    logging.debug("%s: no exif date found" % filename)
                    self.counter.inc("files without exif date", "dir")
                    new_filename = self.handle_file_without_exif_date(dirpath, filename)
                    if new_filename:
                        logging.info("%s: guessing create date, resulting path: %s" % (filename, new_filename))
                    else:
                        logging.error("%s: no date info available, giving up" % os.path.join(dirpath, filename))
                        self.counter.inc("files skipped due to missing date", "dir")
                        continue
            except Exception, e:
                logging.exception(e)
                logging.debug("dir %s: format problem, skipping" % line)
                self.counter.inc("files with exif format problem", "dir")
                continue
            path = os.path.join(dirpath, filename)
            name, suffix = os.path.splitext(filename)
            suffix = suffix.lower()
            number = re.sub(".*\.", "", name)
            number = re.sub("\D*", "", number)
            if number:
                number = ".%s" % number
            new_path = os.path.join(self.photos_dir, "%s%s%s" % (new_filename, number, suffix))
            old2new_pathes[path] = new_path
        self.counter.inc("files to check", amount=len(old2new_pathes))
        logging.info("%s: %i photos found" % (self.format_dirpath(dirpath), len(old2new_pathes)))

        for filename in filenames:
            filename = os.path.join(dirpath, filename)
            if filename not in old2new_pathes:
                logging.warn("%s: not considered a photo/video, thus skipping" % filename)

        for old_path in sorted(old2new_pathes.keys()):
            new_path = old2new_pathes[old_path]
            if os.path.exists(new_path):
                logging.debug("%s: target file %s already exists, leaving untouched" % (old_path, new_path))
                self.counter.inc("files xferred (already transferred, thus skipped)", "dir")
                self.counter.inc("files xferred total")
            else:
                try:
                    self._import_photo(old_path, new_path)
                    self.counter.inc("files xferred")
                    logging.info("%s xferred %s" % (os.path.basename(old_path),
                        "(#%(files xferred)i / %(files to check)i)" % self.counter.get()))
                except Exception, e:
                    logging.exception(e)
                    self.counter.inc("exceptions while importing", "dir")
                    logging.warn("cannot import %s" % os.path.join(dirpath, filename))
                    self.counter.inc("files skipped due to missing date", "dir")

    def _import_photo(self, old_path, new_path):
        logging.debug("file %s: importing as %s" % (old_path, new_path))
        new_dir = os.path.dirname(new_path)
        if not os.path.exists(new_dir):
            logging.debug("creating subdir %s" % new_dir)
            os.makedirs(new_dir)
            self.counter.inc("subdirs created", "dir")
        name, suffix = os.path.splitext(old_path)
        if suffix in PHOTO_SUFFICES:
            tmp_path = "%s.tmp" % new_path
            shutil.copy(old_path, tmp_path)
            #call(["/usr/bin/jhead", "-q", "-ft", "-autorot", tmp_path], logger=logging)
            call(["/usr/bin/jhead", "-q", "-autorot", tmp_path], logger=logging)
            shutil.move(tmp_path, new_path)
        else:
            shutil.copy(old_path, new_path)
        os.chmod(new_path, 0444)
