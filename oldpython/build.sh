#! /bin/bash

# Fichier servant :
# - Lors de la creation du paquet sources
# - Apres la creation d'un paquet source, les fichiers sont supprimés, il faut donc les recréer

chemin="$(cd "$(dirname "$0")";pwd)"
cd "${chemin}"

# Convertion des fichiers ts en qm
lrelease-qt4 *.ts

# Conversion de l'interface graphique en fichier python
pyuic4 ui_MKVExtractorQt.ui -o ui_MKVExtractorQt.py

# Creation d'un systeme d'icone de secour ce le fichier python ci-dessus
while read icone
do
    nom_icone=$(sed -n 's/.*_fromUtf8("\(.*\)".*/\1/p' <<< "${icone}")
    espacement="        "

    new_icone="iconbis = QtGui.QIcon()\n${espacement}iconbis.addPixmap(QtGui.QPixmap(\":/img/${nom_icone}.png\"), QtGui.QIcon.Normal, QtGui.QIcon.Off)\n${espacement}icon = QtGui.QIcon.fromTheme(_fromUtf8(\"${nom_icone}\"), iconbis)"

    sed -i "s@${icone}@${new_icone}@" ui_MKVExtractorQt.py
done < <(grep "QtGui.QIcon.fromTheme" ui_MKVExtractorQt.py)

# Création d'un fichier source python (contient les icones)
pyrcc4 MKVRessources.qrc -o MKVRessources_rc.py -py3

# Création d'un fichier licence ne servant qu'en local (il est effacer lors de la creation d'un paquet debian)
now=$(date -R)
echo """This package was debianized by Terence Belleguic <hizo@free.fr> on
${now}

Format: http://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Source: https://launchpad.net/~hizo/+archive/mkv-extractor-gui

It was downloaded from :
https://launchpad.net/~hizo/+archive/mkv-extractor-gui
http://forum.ubuntu-fr.org/viewtopic.php?id=1508741

Icon file based on the oxygen theme under GNU LGPL 3 license.

Files: *
Copyright: 2014 Terence Belleguic <hizo@free.fr>
License: GNU GPL v3
 On Debian systems, the complete text of the GNU General
 Public License version 3 can be found in \"/usr/share/common-licenses/GPL-3\".""" > licence
