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
        logging.info("starting import")
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
        for key, value in self.counter.get().iteritems():
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
            #logging.info("scanning %s" % actual_sourcedir)
            for dirpath, dirnames, filenames in os.walk(actual_sourcedir):
                dirnames.sort()
                #if not filenames:
                    #continue
                start = time.time()
                self.counter.reset("dir")
                self._import_dir(dirpath)
                end = time.time()
                #for key, value in self.counter.get("dir").iteritems():
                    #logging.info("dir %s: %i %s" % (self.format_dirpath(dirpath), value, key))
                logging.debug("dir %s: %s elapsed" % (self.format_dirpath(dirpath), self._format_timedelta(end - start)))

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
        logging.info("examining %s due to missing exif information" % os.path.join(dirpath, filename))
        create_date = self.guess_create_date(dirpath)
        if create_date:
            logging.info("guessing create date %s" % datetime.strftime(create_date, "%Y-%m-%d"))
            return datetime.strftime(create_date, FORMAT_NEW_PATH)
        return "_unknown_/%s" % filename

    def _import_dir(self, dirpath):
        short_dirpath = os.path.basename(dirpath)
        if short_dirpath.startswith("."):
            logging.info("skipping %s" % dirpath)
            self.counter.inc("directories skipped due to dot-name")
            return
        logging.info("scanning %s" % self.format_dirpath(dirpath))
        self.counter.inc("directories scanned")
        create_dates = subprocess.check_output(
            #["/usr/bin/exiftool", "-q", "-p", "res/createdate.fmt", "-m", "-d", "%Y/%m/%d/%Y%m%d-%H%M%S", dirpath]
            ["/usr/bin/exiftool", "-q", "-p", "res/createdate.fmt", "-m", "-d", FORMAT_NEW_PATH, dirpath]
        )
        old2new_pathes = {}
        for line in create_dates.splitlines():
            try:
                filename, new_filename = line.split("|")
                if not new_filename:
                    logging.debug("dir %s: no exif data found, skipping" % line)
                    self.counter.inc("files without exif date", "dir")
                    new_filename = self.handle_file_without_exif_date(dirpath, filename)
                    if not new_filename:
                        logging.info("no date info for %s available" % filename)
                        logging.warn("cannot import %s" % os.path.join(dirpath, filename))
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
            new_path = os.path.join(self.photos_dir, "%s.%s%s" % (new_filename, number, suffix))
            old2new_pathes[path] = new_path
        self.counter.inc("files to check", amount=len(old2new_pathes))
        #logging.info("dir %s: %i photos found" % (self.format_dirpath(dirpath), len(old2new_pathes)))
        for old_path in sorted(old2new_pathes.keys()):
            new_path = old2new_pathes[old_path]
            if os.path.exists(new_path):
                logging.debug("%s: target file %s already exists, leaving untouched" % (old_path, new_path))
                self.counter.inc("files already imported, thus skipped", "dir")
                self.counter.inc("files xferred")
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
        self.counter.inc("files imported successfully", "dir")
