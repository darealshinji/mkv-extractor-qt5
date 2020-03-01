#!/bin/sh
set -e
#set -v

# build regular files
./clean.sh
./build.sh

# add localizations and changelog to resources
sed -e 's@</qresource>@<file>MKVExtractorQt5_cs_CZ.qm</file><file>MKVExtractorQt5_fr_FR.qm</file><file>changelog.Debian</file></qresource>@' \
  MKVRessources.qrc > tmp_MKVRessources.qrc
pyrcc5 tmp_MKVRessources.qrc -o MKVRessources_rc.py

# use embedded localizations and changelog
sed -e 's@"MKVExtractorQt5_fr_FR", str(AppFolder)@":/MKVExtractorQt5_fr_FR.qm"@' \
    -e 's@"MKVExtractorQt5_cs_CZ", str(AppFolder)@":/MKVExtractorQt5_cs_CZ.qm"@' \
    -e 's@/usr/share/doc/mkv-extractor-qt5/changelog.Debian.gz@:/changelog.Debian@g' \
MKVExtractorQt5.py > tmp_MKVExtractorQt5.py

# remove some import lines
sed '/import MKVRessources_rc/d' ui_MKVExtractorQt5.py > tmp_ui_MKVExtractorQt5.py
sed -i '/^from QFileDialogCustom/d; /^from WhatsUp/d; /^from ui_MKVExtractorQt5/d' tmp_MKVExtractorQt5.py

# whatsup
sed -i '/changelog.Debian...exists/d; /self.ui.whatsup.setVisible/d' tmp_MKVExtractorQt5.py
echo 'changelog_data = b"\\' > tmp_changelog.py
xxd -g1 changelog.Debian | cut -d ':' -f2 | sed -e 's|  .*||' -e 's| |\\x|g; s|$|\\|g' >> tmp_changelog.py
echo '"' >> tmp_changelog.py

# make final script usable
awk "/if __name__ == '__main__':/ {exit} {print}" QFileDialogCustom/QFileDialogCustom.py > tmp_QFileDialogCustom.py
awk "/if __name__ == '__main__':/ {exit} {print}" WhatsUp/WhatsUp.py > tmp_WhatsUp.py
sed -i '/gzip.open/d' tmp_WhatsUp.py
sed -i 's@    file_content = f.read()@file_content = changelog_data@' tmp_WhatsUp.py

# merge scripts
cat tmp_changelog.py tmp_WhatsUp.py tmp_QFileDialogCustom.py tmp_ui_MKVExtractorQt5.py MKVRessources_rc.py CodecListFile.py > tmp.py
sed -i -e '/^from CodecListFile/r tmp.py' -e '/^from CodecListFile/d' tmp_MKVExtractorQt5.py

# minify script
if pyminifier --version 2>/dev/null >/dev/null ; then
  pyminifier tmp_MKVExtractorQt5.py > MKVExtractorQt5-standalone.py
else
  echo "no pyminifier found"
  mv tmp_MKVExtractorQt5.py MKVExtractorQt5-standalone.py
fi

rm -f tmp*
chmod a+x MKVExtractorQt5-standalone.py

