Graphical MKV demultiplexer
===========================

Inofficial working tree

Features:
  * DTS to AC3 conversion via ffmpeg
  * Automatic conversion from SUB to SRT via [Qtesseract5](https://github.com/darealshinji/Qtesseract5)
  * Read and extract joined files
  * Extract and re-encapsule tracks
  * And more again

Copyright (C) 2013-2020 Terence Belleguic <hizo@free.fr>

https://launchpad.net/~hizo/+archive/mkv-extractor-gui<br>
http://forum.ubuntu-fr.org/viewtopic.php?id=1508741


Requires Python 3.4 or higher.<br>
Build dependencies: `pyqt5-dev-tools qttools5-dev-tools`<br>
Runtime dependency: `mkvtoolnix` (http://www.bunkus.org/videotools/mkvtoolnix/)

Other branches:<br>
oldpython: made for python below version 3.4 (discontinued)<br>
subptools: addon for mkv-extractor-qt to convert vobsubs into soft subtitles.<br>
subptools build dependencies: `dh-autoreconf pkg-config libxml2-dev libtiff-dev libpng12-dev zlib1g-dev`
