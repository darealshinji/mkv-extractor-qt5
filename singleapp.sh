#!/bin/sh

./build.sh
sed '/import MKVRessources_rc/r MKVRessources_rc.py' ui_MKVExtractorQt.py > tmp1.py
sed '/from ui_MKVExtractorQt import/r tmp1.py' MKVExtractorQt.py > tmp2.py
sed '/import MKVRessources_rc/d; /from ui_MKVExtractorQt import/d' tmp2.py > tmp3.py

pyminifier --version 2>/dev/null >/dev/null
if [ $? = 0 ]; then
  pyminifier tmp3.py > MKVExtractorQt_new.py
else
  mv tmp3.py MKVExtractorQt_new.py
fi

rm -f tmp?.py
chmod a+x MKVExtractorQt_new.py

