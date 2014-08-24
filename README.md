Graphical MKV demultiplexer
===========================

Inofficial working tree

Features:
  * DTS to AC3 conversion via ffmpeg
  * Automatic conversion from SUB to SRT via tesseract
  * Read and extract joined files
  * Extract and re-encapsule tracks
  * And more again

Copyright (C) 2013-2014 Terence Belleguic <hizo@free.fr>

https://launchpad.net/~hizo/+archive/mkv-extractor-gui<br>
https://launchpad.net/~djcj/+archive/ubuntu/mkvtoolnix (inofficial)<br>
http://forum.ubuntu-fr.org/viewtopic.php?id=1508741


mkv-extractor-qt: made for python 3.4 or higher<br>
mkv-extractor-qt-oldpython: made for python below version 3.4<br>
Build dependencies: `pyqt4-dev-tools qt4-linguist-tools`<br>
Runtime dependency: `mkvtoolnix` (http://www.bunkus.org/videotools/mkvtoolnix/)

mkv-extractor-qt-subptools: addon for mkv-extractor-qt to convert vobsubs into soft subtitles.<br>
Build dependencies: `dh-autoreconf pkg-config libxml2-dev libtiff-dev libpng12-dev zlib1g-dev`
