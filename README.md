# photolib

manage your photo archive

- import new photos, generate date-based hierarchy

- analyze photos and metainformation (faces detected by [picasa](http://picasa.google.com/))

    - generate smaller photos (aka tiles, 240x240px) for mosaic rendering

    - generate closeup of detected faces

- render mosaic using [metapixel](http://www.complang.tuwien.ac.at/schani/metapixel/)


## tl;dr

### install

download project, install prerequisites (ubuntu-specific)

```bash
git clone https://github.com/arnehilmann/photolib.git

cd photolib

bootstrap/ubuntu
```

### usage

```bash
source ve/bin/activate  # activate photolib

transfer-photos --source-dir <BUNCH_OF_NEW_PHOTOS> --photos-dir <MY_PHOTO_LIBRARY>

# picasa face detection in MY_PHOTO_LIBRARY happens here

analyze-photos --photos-dir <MY_PHOTO_LIBRARY>... --faces-dir <FACES_LIBRARY> --tiles-dir <TILES_LIBRARY>

render-mosaic --in <INPUT_FILE> --tiles-dir <TILES_LIBRARY> [options]

# deprecated: generate-gallery <NAME_OF_GALLERY> <PHOTOS...>
# consider using https://github.com/arnehilmann/gallery-generator instead
```


## Referenced Projects/Applications

- [python](http://www.python.org/)

- [virtualenv](http://www.virtualenv.org/en/latest/)

- [jhead](http://www.sentex.net/~mwandel/jhead/)

- [exiftool](http://www.sno.phy.queensu.ca/~phil/exiftool/)

- [imagemagick](http://www.imagemagick.org/)

- [metapixel](http://www.complang.tuwien.ac.at/schani/metapixel/)


## How to install picasa3.9 on ubuntu

**fast-lane, without picasaweb-integration**

* get and install the last (and old) official picasa version for ubuntu:

```google
https://www.google.com/search?q=%22picasa+3.0%22+download+ubuntu
```

```bash
sudo dpkg -i Downloads/picasa-3.0*.deb
```

* get and copy-over the last official (non-ubuntu) version of picasa

```google
https://www.google.com/search?q="picasa+3.9"+download
```

```bash
wine Downloads/picasa39-setup.exe
sudo cp -r .wine/drive_c/Program\ Files\ \(x86\)/Google/Picasa3/* /opt/google/picasa/3.0/wine/drive_c/Program\ Files/Google/Picasa3
```


## TODO

- make analyze-photos idempotent
 
  - check if analysis results already present and uptodate

  - let analyze-photos remove photos when face information changed

- add minimal exif data for photos without exif

- integrate better with digikam (sync of metadata)

- store face data in metadata with bounding box
