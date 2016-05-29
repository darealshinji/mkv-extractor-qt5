#! /bin/bash

# set -e
# set -v

# Fichier servant :
# - Lors de la creation du paquet sources
# - Apres la creation d'un paquet source, les fichiers sont supprimés, il faut donc les recréer

# if [[ ! $(which "pyrcc5") ]]
# then
#     echo "The pyrcc5 program is missing, installing of pyqt5-dev-tools package."
#     sudo apt-get install pyqt5-dev-tools
# fi

chemin="$(cd "$(dirname "$0")";pwd)"
cd "${chemin}"

# Mise à jour des fichiers ts
pylupdate5 ui_MKVExtractorQt5.ui MKVExtractorQt5.py -ts MKVExtractorQt5_fr_FR.ts MKVExtractorQt5_cs_CZ.ts
pylupdate5 QFileDialogCustom/QFileDialogCustom.py -ts QFileDialogCustom/QFileDialogCustom_fr_FR.ts

# Convertion des fichiers ts en qm
if [[ -e "/usr/lib/x86_64-linux-gnu/qt5/bin/lrelease" ]]
then
    /usr/lib/x86_64-linux-gnu/qt5/bin/lrelease *.ts QFileDialogCustom/*.ts
elif [[ -e "/usr/lib/i386-linux-gnu/qt5/bin/lrelease" ]]
then
    /usr/lib/i386-linux-gnu/qt5/bin/lrelease *.ts QFileDialogCustom/*.ts
else
    echo "cannot find \`lrelease'"
    exit 1
fi

# Création d'un fichier source python (contient les icones)
pyrcc5 MKVRessources.qrc -o MKVRessources_rc.py

# Conversion de l'interface graphique en fichier python
pyuic5 ui_MKVExtractorQt5.ui -o ui_MKVExtractorQt5.py

# Creation d'un systeme d'icone de secoure sur le fichier python ci-dessus
sed -i '/icon = QtGui.QIcon.fromTheme/ s@\([^"]*\)"\([^"]*\)")@\1"\2", QtGui.QIcon(":/img/\2.png"))@g' ui_MKVExtractorQt5.py
