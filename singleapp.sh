#!/bin/sh -e

./build.sh

sed -e 's@</qresource>@<file>MKVExtractorQt_cs_CZ.qm</file><file>MKVExtractorQt_fr_FR.qm</file></qresource>@' \
  MKVRessources.qrc > MKVRessources_2.qrc
pyrcc5 MKVRessources_2.qrc -o MKVRessources_rc.py

sed -e 's@"MKVExtractorQt_fr_FR", str(folder)@":/MKVExtractorQt_fr_FR.qm"@' \
    -e 's@"MKVExtractorQt_cs_CZ", str(folder)@":/MKVExtractorQt_cs_CZ.qm"@' \
MKVExtractorQt.py > MKVExtractorQt_2.py

sed '/import MKVRessources_rc/r MKVRessources_rc.py' ui_MKVExtractorQt.py > tmp1.py
sed '/from ui_MKVExtractorQt import/r tmp1.py' MKVExtractorQt_2.py > tmp2.py
sed '/import MKVRessources_rc/d; /from ui_MKVExtractorQt import/d' tmp2.py > tmp3.py

if pyminifier --version 2>/dev/null >/dev/null ; then
  pyminifier tmp3.py > MKVExtractorQt_new.py
else
  echo "no pyminifier found"
  mv tmp3.py MKVExtractorQt_new.py
fi

rm -f tmp?.py MKVExtractorQt_2.py MKVRessources_2.qrc
chmod a+x MKVExtractorQt_new.py

