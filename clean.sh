#!/bin/sh
rm -rf __pycache__ MKVRessources_rc.py ui_MKVExtractorQt5.py MKVRessources.qrc *.qm
rm -f changelog.Debian.gz

# clean de QFileDialogCustom
rm -rf QFileDialogCustom/__pycache__ QFileDialogCustom/*.qm