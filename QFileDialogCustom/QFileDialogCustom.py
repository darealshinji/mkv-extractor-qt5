#!/usr/bin/python3
# -*- coding: utf-8 -*-


from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import sys
from pathlib import Path # Nécessaire pour la recherche de fichier


#############################################################################
class QFileDialogCustom(QFileDialog):
    #========================================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        # Initialisation de la valeur de retour
        self.Retour = ""
        self.DoubleClic = False
        self.AlreadyExists = False


     #========================================================================
    def LanguageChoice(self, Lang):
        ### Chargement du fichier qm de traduction (anglais utile pour les textes singulier/pluriel)

        appTranslator = QTranslator() # Création d'un QTranslator
        Folder = Path(Path(sys.argv[0]).resolve().parent) # Dossier des traductions

        ### Pour la trad française
        if "fr" in Lang:
            find = appTranslator.load("QFileDialogCustom_fr_FR", str(Folder))

            ## Si le fichier n'a pas été trouvé, affiche une erreur et utilise la version anglaise
            if not find:
                QMessageBox(3, "Erreur de traduction", "Aucun fichier de traduction <b>française</b> trouvé.<br/>Utilisation de la langue <b>anglaise</b>.", QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

            ## Chargement de la traduction
            else:
                app.installTranslator(appTranslator)

            ## Mise à jour du fichier langage de Qt
            global translator_qt
            translator_qt = QTranslator() # Création d'un QTranslator
            if translator_qt.load("qt_fr_FR", QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
                app.installTranslator(translator_qt)


    #========================================================================
    def keyReleaseEvent(self, event):
        """Fonction pour prise en compte de la touche entrée."""
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self.done(2)


    #========================================================================
    def done(self, value):
        """En fonction de la valeur, on récupère une valeur ou non avant de fermer la fenêtre."""
        if value == 0:
            self.Retour = ""
            self.hide()

        elif value == 1:
            # Variable tmp pour tester le double clic
            RetourTmp = self.Retour

            # Essaie de récupérer le fichier choisi
            try: self.Retour = list(self.selectedFiles())[0]
            except: self.Retour = ""

            # Prise en compte du double clic
            if not self.DoubleClic:
                self.DoubleClic = True

            else:
                if RetourTmp != self.Retour:
                    self.DoubleClic = False

                else:
                    self.DoubleClic = False
                    self.hide()

        elif value == 2:
            try:
                self.Retour = list(self.selectedFiles())[0]
                self.hide()

            except:
                pass


    #========================================================================
    def test(self, value):
        """Dit à done que le bouton valider à été utiliser (ne renvoie pas 0 mais 2 pour court-circuiter le souci de fermeture à la sélection de fichier)."""
        ### Le numero change parfois...
        for x, Item in enumerate(self.enfants):
            if type(Item) == QDialogButtonBox:
                if self.enfants[x].buttonRole(value) == 0: self.done(2)
                break


    #========================================================================
    def createWindow(self, Type="File", Action="Open", WidgetToAdd=None, Flags=None, FileName=None, Options=None, AlreadyExistsTest=True):
        """Fonction affichant la fenêtre."""
        if Action == "Open": self.setAcceptMode(QFileDialog.AcceptOpen)

        elif Action == "Save": self.setAcceptMode(QFileDialog.AcceptSave)

        self.setOption(QFileDialog.DontConfirmOverwrite, True) # La fenetre d'ecriture par dessus un fichier existant n'indique pas le resultat du choix donc inutile, il faut en faire une maison
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self.setOption(QFileDialog.DontUseCustomDirectoryIcons, True)

        if Type == "File":
            self.setOption(QFileDialog.HideNameFilterDetails)
            if Action == "Open": self.setFileMode(QFileDialog.ExistingFile)
            elif Action == "Save": self.setFileMode(QFileDialog.AnyFile)

        elif Type == "Folder":
            self.setFileMode(QFileDialog.Directory) # Mode Folder
            self.setOption(QFileDialog.ShowDirsOnly, True)

        if Flags != None: self.setWindowFlags(Flags)
        if Options != None: self.setOptions(Options)
        if FileName != None: self.selectFile(FileName) # Nécessaire car si on utilise HideNameFilterDetails et save, il utilise la 1ere extension dans le fichier


        ### Ajout du widget à la fenêtre de dialogue
        if WidgetToAdd != None:
            layout = self.layout()
            layout.addWidget(WidgetToAdd, 4, 0, 4, 3)


        ### Court-circuitage des boutons
        ### Le numero change parfois...
        self.enfants = self.children()

        for x, Item in enumerate(self.enfants):
            if type(Item) == QDialogButtonBox:
                self.enfants[x].clicked.connect(self.test)
                break


        ### Affichage de la fenêtre
        self.exec()


        ### Fonction d'ecrasement
        if Action == "Save" and (Options == None or not "DontConfirmOverwrite" in Options) and AlreadyExistsTest:
            if self.Retour and Path(self.Retour).exists():
                ## Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, QCoreApplication.translate("main", "Already existing file"), QCoreApplication.translate("main", "The <b>{}</b> file is already existing, overwrite it?").format(self.Retour), QMessageBox.NoButton, self)
                dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                dialog.setDefaultButton(QMessageBox.Yes)
                dialog.setEscapeButton(QMessageBox.No)
                Choix = dialog.exec_()

                self.AlreadyExists

                # Si on ne le remplace pas, on renvoie une version vide
                if Choix != QMessageBox.Yes: self.Retour = ""


        ### Retour de la valeur choisie
        if Type == "File":
            if Action == "Open":
                if Path(self.Retour).is_file(): return self.Retour
                else: return ""

            elif Action == "Save":
                return self.Retour

        elif Type == "Folder":
            if Path(self.Retour).is_dir(): return self.Retour
            else: return ""



#############################################################################
if __name__ == '__main__':
    print("popo")
    app = QApplication(sys.argv)
    app.setApplicationVersion("1.0")
    app.setApplicationName("QFileDialogCustom")
    QFileDialogCustom = QFileDialogCustom()
    QFileDialogCustom.setAttribute(Qt.WA_DeleteOnClose)
    print("je suis la")
    app.exec_()