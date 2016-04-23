#! /bin/bash

# pyqt5-dev-tools

# Fichier servant :
# - Lors de la creation du paquet sources
# - Apres la creation d'un paquet source, les fichiers sont supprimés, il faut donc les recréer

chemin="$(cd "$(dirname "$0")";pwd)"
cd "${chemin}"

# Mise à jour des fichiers ts
pylupdate5 ui_MKVExtractorQt.ui MKVExtractorQt.py -ts MKVExtractorQt_fr_FR.ts MKVExtractorQt_cs_CZ.ts

# Convertion des fichiers ts en qm
[[ -e "/usr/lib/x86_64-linux-gnu/qt5/bin/lrelease" ]] && /usr/lib/x86_64-linux-gnu/qt5/bin/lrelease *.ts
[[ -e "/usr/lib/i386-linux-gnu/qt5/bin/lrelease" ]] && /usr/lib/i386-linux-gnu/qt5/bin/lrelease *.ts

# Création d'un fichier source python (contient les icones)
pyrcc5 MKVRessources.qrc -o MKVRessources_rc.py

# Conversion de l'interface graphique en fichier python
pyuic5 ui_MKVExtractorQt.ui -o ui_MKVExtractorQt.py

### Creation d'un systeme d'icone de secoure sur le fichier python ci-dessus
# Modification du systeme des icones en utilisant la fonction ci-dessous
while read line
do
    before="${line%%(*}"
    icon="${line##*/}"
    icon="${icon%%.*}"

    # Ne doit pas le faire pour l'icone du titre de la fenetre
    [[ $(grep "icon." <<< "${line}") ]] && continue

    new_line="${before}(IconBis('${icon}'))"
    sed -i "s@${line}@${new_line}@" ui_MKVExtractorQt.py
done < <(grep "QtGui.QPixmap" ui_MKVExtractorQt.py)

# Création d'une fonction
echo """
def IconBis(Icon):
    if QtGui.QIcon().hasThemeIcon(Icon):
        return QtGui.QPixmap(QtGui.QIcon().fromTheme(Icon).pixmap(24))
    else:
        return QtGui.QPixmap(':/img/{}.png'.format(Icon))""" >> ui_MKVExtractorQt.py


