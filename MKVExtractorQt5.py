#!/usr/bin/python3
# -*- coding: utf-8 -*-


"""Logiciel graphique d'extraction des pistes de fichiers MKV."""

###############################
### Importation des modules ###
###############################
import sys
from time import sleep
from shutil import disk_usage, rmtree # Utilisé pour tester la place restante
from functools import partial # Utilisé pour envoyer plusieurs infos via les connexions
from datetime import timedelta # utile pour le calcul de la progression de la conversion en ac3
from pathlib import Path # Nécessaire pour la recherche de fichier
import json # Necessaire au traitement des infos de mkvmerge

from PyQt5.QtWidgets import QPushButton, QSystemTrayIcon, QWidget, QTextEdit, QShortcut, QComboBox, QApplication, QAction, QDockWidget, QDesktopWidget, QMessageBox, QActionGroup, QTableWidgetItem, QCheckBox, QMainWindow, QMenu, QDialog, QHBoxLayout, QVBoxLayout, QDialogButtonBox, QStyleFactory, QLineEdit, QFileDialog
from PyQt5.QtCore import QCoreApplication, QFileInfo, QStandardPaths, QTemporaryDir, QTranslator, QThread, QLibraryInfo, QDir, QMimeType, QMimeDatabase, Qt, QSettings, QProcess, QUrl, QLocale, QSize, QFile
from PyQt5.QtGui import QTextCursor, QIcon, QKeySequence, QCursor, QDesktopServices, QPixmap, QPainter

from QFileDialogCustom.QFileDialogCustom import QFileDialogCustom # Version custom de sélecteur de fichier
from WhatsUp.WhatsUp import WhatsUp
from ui_MKVExtractorQt5 import Ui_mkv_extractor_qt5 # Utilisé pour la fenêtre principale
from CodecListFile import CodecList # Liste des codecs


#############################################################################
class QuitButton(QPushButton):
    """Sous classement d'un QPushButton permettant la prise en charge du clic droit sur le bouton quitter."""
    def mousePressEvent(self, event):
        """Fonction de récupération des touches souris utilisées."""
        MKVExtractorQt5Class.ui.soft_quit.animateClick()

        ### Récupération du bouton utilisé
        if event.button() == Qt.RightButton:
            from os import execl
            python = sys.executable
            execl(python, python, * sys.argv)

        # Acceptation de l'événement
        return super(type(self), self).mousePressEvent(event)


#############################################################################
class QTextEditCustom(QTextEdit):
    """Sous classement d'un QTextEdit pour y modifier le menu du clic droit."""
    def __init__(self, Parent=None):
        super().__init__(Parent)

        ### Création des raccourcis claviers qui serviront aux actions
        ExportShortcut = QShortcut("ctrl+e", self)
        ExportShortcut.activated.connect(self.ExportAction)

        CleanShortcut = QShortcut("ctrl+d", self)
        CleanShortcut.activated.connect(self.CleanAction)


    #========================================================================
    def contextMenuEvent(self, event):
        """Fonction de la création du menu contextuel."""
        ### Chargement du fichier qm de traduction (anglais utile pour les textes singulier/pluriel)
        appTranslator = QTranslator() # Création d'un QTranslator

        ## Pour la trad française
        if Configs.value("Language") == "fr_FR":
            find = appTranslator.load("MKVExtractorQt5_fr_FR", str(AppFolder))

            # Chargement de la traduction
            if find:
                app.installTranslator(appTranslator)

        ## Pour la version tchèque
        elif Configs.value("Language") == "cs_CZ":
            find = appTranslator.load("MKVExtractorQt5_cs_CZ", str(AppFolder))

            # Chargement de la traduction
            if find:
                app.installTranslator(appTranslator)


        # Création d'un menu standard
        Menu = self.createStandardContextMenu()

        # Création et ajout de l'action de nettoyage (icône, nom, raccourci)
        Clean = QAction(QIcon.fromTheme("edit-clear", QIcon(":/img/edit-clear.png")), QCoreApplication.translate("QTextEditCustom", "Clean the information fee&dback box"), Menu)
        Clean.setShortcut(QKeySequence("ctrl+d"))
        Clean.triggered.connect(self.CleanAction)
        Menu.addSeparator()
        Menu.addAction(Clean)

        # Création et ajout de l'action d'export (icône, nom, raccourci)
        Export = QAction(QIcon.fromTheme("document-export", QIcon(":/img/document-export.png")), QCoreApplication.translate("QTextEditCustom", "&Export info to ~/InfoMKVExtractorQt5.txt"), Menu)
        Export.setShortcut(QKeySequence("ctrl+e"))
        Export.triggered.connect(self.ExportAction)
        Menu.addSeparator()
        Menu.addAction(Export)

        # Grise les actions si le texte est vide
        if not self.toPlainText():
            Export.setEnabled(False)
            Clean.setEnabled(False)

        # Affichage du menu là où se trouve la souris
        Menu.exec(QCursor.pos())

        event.accept()


    #========================================================================
    def CleanAction(self, *args):
        """Fonction de nettoyage du texte."""
        self.clear()


    #========================================================================
    def ExportAction(self, *args):
        """Fonction d'exportation du texte."""
        # Récupération du texte
        text = self.toPlainText()

        # Arrête la fonction si pas de texte
        if not text: return

        # Création du lien vers le fichier
        ExportedFile = QFile(QDir.homePath() + '/InfoMKVExtractorQt5.txt')

        # Ouverture du fichier en écriture
        ExportedFile.open(QFile.WriteOnly)

        # Envoie du text au format bytes
        ExportedFile.write(text.encode())

        # Fermeture du fichier
        ExportedFile.close()



#############################################################################
class MKVExtractorQt5(QMainWindow):
    """Fenêtre principale du logiciel."""
    def __init__(self, parent=None):
        """Fonction d'initialisation appelée au lancement de la classe."""
        ### Commandes à ne pas toucher
        super(MKVExtractorQt5, self).__init__(parent)
        self.ui = Ui_mkv_extractor_qt5()
        self.ui.setupUi(self) # Lance la fonction définissant tous les widgets du fichier UI
        self.setWindowTitle('MKV Extractor Qt v{}'.format(app.applicationVersion())) # Nom de la fenêtre
        self.show() # Affichage de la fenêtre principale


        ### Création du QTextEditCustom affichant le retour avec un menu custom
        self.ui.reply_info = QTextEditCustom(self.ui.dockWidgetContents)
        self.ui.reply_info.setReadOnly(True)
        self.ui.reply_info.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.ui.reply_info.setLineWrapMode(QTextEdit.WidgetWidth)
        self.ui.reply_info.setTextInteractionFlags(Qt.TextSelectableByKeyboard|Qt.TextSelectableByMouse)
        self.ui.reply_info.resize(100, 150)
        self.ui.verticalLayout_8.addWidget(self.ui.reply_info)


        ### Gestion de la fenêtre
        ## Remet les widgets comme ils l'étaient
        if Configs.contains("WinState"):
            self.restoreState(Configs.value("WinState"))

        ## Repositionne et donne la bonne taille à la fenêtre
        if Configs.value("WindowAspect") and Configs.contains("WinGeometry"):
            self.restoreGeometry(Configs.value("WinGeometry"))

        ## Centrage de la fenêtre, en fonction de sa taille et de la taille de l'écran
        else:
            size_ecran = QDesktopWidget().screenGeometry() # Taille de l'écran
            self.move((size_ecran.width() - self.geometry().width()) / 2, (size_ecran.height() - self.geometry().height()) / 2)


        ### Modifications graphiques de boutons
        self.ui.mkv_stop.setVisible(False) # Cache le bouton d'arrêt
        self.ui.mkv_pause.setVisible(False) # Cache le bouton de pause


        ### Active les tooltips des actions dans les menus
        for Widget in (self.ui.menuFichier, self.ui.menuActions, self.ui.menuAide, self.ui.menuAide): Widget.setToolTipsVisible(True)


        ### Remplissage du menu des styles Qt disponibles
        for Style in QStyleFactory.keys(): # Styles disponibles
            QtStyleList[Style] = QAction(Style, self) # Création d'une action stockée dans le dico
            QtStyleList[Style].triggered.connect(partial(self.StyleChange, Style)) # Action créée pour cet element
            self.ui.option_style.addAction(QtStyleList[Style]) # Ajout de l'action à la liste

            # Si c'est le style actuel
            if Style.lower() == Configs.value("QtStyle").lower(): self.StyleChange(Style)


        ### Mise en place du system tray
        menulist = QMenu() # Création d'un menu
        icon = QIcon.fromTheme("application-exit", QIcon(":/img/application-exit.png"))
        self.SysTrayQuit = QAction(icon, '', self,) # Création d'un item sans texte
        menulist.addAction(self.SysTrayQuit) # Ajout de l'action à la liste

        self.SysTrayIcon = QSystemTrayIcon(QIcon.fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")), self)
        self.SysTrayIcon.setContextMenu(menulist)

        if not Configs.value("SysTray"): self.ui.option_systray.setChecked(False)
        else: self.SysTrayIcon.show()


        ### Menu du bouton de conversion SUB => SRT
        menulist = QMenu() # Création d'un menu
        menulist.setToolTipsVisible(True) # Active les tooltips des actions

        self.Qtesseract5 = QAction('', self, checkable=True) # Création d'un item sans texte
        self.Qtesseract5.setIcon(QIcon.fromTheme("Qtesseract5", QIcon(":/img/qtesseract5.png")))
        menulist.addAction(self.Qtesseract5) # Ajout de l'action à la liste

        menulist.addSeparator()
        self.BDSup2Sub = QAction('', self) # Création d'un item sans texte
        self.BDSup2Sub.setIcon(QIcon.fromTheme("BDSup2Sub", QIcon(":/img/BDSup2Sub.png")))
        menulist.addAction(self.BDSup2Sub) # Ajout de l'action à la liste

        self.ui.option_vobsub_srt.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Menu du bouton de conversion DTS => AC3
        menulist = QMenu() # Création d'un menu
        menulist.setToolTipsVisible(True) # Active les tooltips des actions

        icon = QIcon.fromTheme("ffmpeg", QIcon(":/img/ffmpeg.png"))
        self.option_ffmpeg = QAction(icon, '', self, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_ffmpeg) # Ajout de l'action à la liste

        icon = QIcon.fromTheme("audio-ac3", QIcon(":/img/audio-ac3.png"))
        self.option_to_ac3 = QAction(icon, '', self, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_to_ac3) # Ajout de l'action à la liste

        icon = QIcon.fromTheme("stereo", QIcon(":/img/stereo.png"))
        self.option_stereo = QAction(icon, '', self, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_stereo) # Ajout de l'action à la liste

        self.RatesMenu = QMenu(self) # Création d'un sous menu
        ag = QActionGroup(self) # Création d'un actiongroup
        QualityList["NoChange"] = QAction('', self, checkable=True) # Création d'un item radio sans nom
        self.RatesMenu.addAction(ag.addAction(QualityList["NoChange"])) # Ajout de l'item radio dans la sous liste
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]: # Qualités utilisables
            QualityList[nb] = QAction('', self, checkable=True) # Création d'un item radio sans nom
            self.RatesMenu.addAction(ag.addAction(QualityList[nb])) # Ajout de l'item radio dans la sous liste
        menulist.addMenu(self.RatesMenu) # Ajout du sous menu dans le menu

        self.PowerMenu = QMenu(self) # Création d'un sous menu
        ag = QActionGroup(self) # Création d'un actiongroup
        PowerList["NoChange"] = QAction('', self, checkable=True) # Création d'un item radio sans nom
        self.PowerMenu.addAction(ag.addAction(PowerList["NoChange"])) # Ajout de l'item radio dans la sous liste
        for nb in [2, 3, 4, 5]: # Puissances utilisables
            PowerList[nb] = QAction('', self, checkable=True) # Création d'un item radio sans nom
            self.PowerMenu.addAction(ag.addAction(PowerList[nb])) # Ajout de l'item radio dans la sous liste
        menulist.addMenu(self.PowerMenu) # Ajout du sous menu dans le menu

        self.ui.option_audio.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Menu du bouton de ré-encapsulage
        icon = QIcon.fromTheme("edit-delete", QIcon(":/img/edit-delete.png"))
        self.option_del_temp = QAction(icon, '', self, checkable=True) # Création d'une action cochable sans texte
        icon = QIcon.fromTheme("document-edit", QIcon(":/img/document-edit.png"))
        self.option_subtitles_open = QAction(icon, '', self, checkable=True) # Création d'une action cochable sans texte
        menulist = QMenu() # Création d'un menu
        menulist.addAction(self.option_del_temp) # Ajout de l'action à la liste
        menulist.addAction(self.option_subtitles_open) # Ajout de l'action à la liste
        self.ui.option_reencapsulate.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Désactivation des options dont les exécutables n'existent pas
        for Location, Widget in (("Location/BDSup2Sub", self.BDSup2Sub),
                                 ("Location/MKClean", self.ui.mk_clean),
                                 ("Location/MKVInfo", self.ui.mkv_info),
                                 ("Location/MKVToolNix", self.ui.mkv_mkvmerge),
                                 ("Location/MKValidator", self.ui.mk_validator),
                                 ("Location/Qtesseract5", self.ui.option_vobsub_srt)):

            # Définit l'adresse du programme
            if not QFileInfo(Configs.value(Location).split(" -")[0]).isExecutable(): Widget.setEnabled(False)


        ### Désactive le bouton whatsup s'il n'y a pas de changelog => en mettre un dans la version sans installation ?!
        if not Path('/usr/share/doc/mkv-extractor-qt5/changelog.Debian.gz').exists(): self.ui.whatsup.setEnabled(False)


        ### Recherche ffmpeg et avconv qui font la même chose
        # Désactive les radiobutton et l'option de conversion
        if not QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable() and not QFileInfo(Configs.value("Location/AvConv").split(" -")[0]).isExecutable():
            Configs.setValue("FFMpeg", False)
            self.option_ffmpeg.setEnabled(False)
            self.ui.option_audio.setEnabled(False)

        # Sélection automatique ffmpeg
        elif QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable() and not QFileInfo(Configs.value("Location/AvConv").split(" -")[0]).isExecutable():
            Configs.setValue("FFMpeg", True)
            self.option_ffmpeg.setEnabled(False)

        # Sélection automatique avconv
        elif not QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable() and QFileInfo(Configs.value("Location/AvConv").split(" -")[0]).isExecutable():
            Configs.setValue("FFMpeg", False)
            self.option_ffmpeg.setEnabled(False)

        # Les deux sont dispo, utilisation de ffmpeg par defaut
        else:
            Configs.setValue("FFMpeg", True)
            self.option_ffmpeg.setChecked(True)


        ### Activation et modifications des préférences
        QualityList[TempValues.value("AudioQuality")].setChecked(True) # Coche de la bonne valeur
        PowerList[TempValues.value("AudioBoost")].setChecked(True) # Coche de la bonne valeur

        if not Configs.value("RecentInfos"): self.ui.option_recent_infos.setChecked(True)

        if not Configs.value("WindowAspect"): self.ui.option_aspect.setChecked(False)

        if Configs.value("DebugMode"): self.ui.option_debug.setChecked(True)

        if not Configs.value("Feedback"):
            self.ui.option_feedback.setChecked(False)
            self.ui.feedback_widget.hide()

        if Configs.value("FeedbackBlock"):
            self.ui.option_feedback_block.setChecked(True)
            self.ui.feedback_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)

        ### Gestion la traduction, le widget n'est pas encore connecté
        # Sélection de la langue français
        if "fr_" in Configs.value("Language"):
            self.ui.lang_fr.setChecked(True)
            self.OptionLanguage("fr_FR")

        # Sélection de la langue tchèque
        elif "cs_" in Configs.value("Language"):
            self.ui.lang_cs.setChecked(True)
            self.OptionLanguage("cs_CZ")

        # Force le chargement de traduction si c'est la langue anglaise (par défaut)
        else:
            self.OptionLanguage("en_US")


        ### Réinitialisation du dossier de sortie s'il n'existe pas
        if not Configs.contains("OutputFolder") or not Configs.value("OutputFolder").is_dir():
            Configs.setValue("OutputFolder", Path().resolve())
            Configs.setValue("OutputSameFolder", True)


        ### Définition de la taille des colonnes du tableau des pistes
        largeur = (self.ui.mkv_tracks.size().width() - 75) / 3 # Calcul pour définir la taille des colonnes
        self.ui.mkv_tracks.setMouseTracking(True) # Nécessaire à l'affichage des statustip
        self.ui.mkv_tracks.hideColumn(0) # Cache la 1ere colonne
        self.ui.mkv_tracks.setColumnWidth(1, 25) # Définit la colonne 1 à 25px
        self.ui.mkv_tracks.setColumnWidth(2, 25) # Définit la colonne 2 à 25px
        self.ui.mkv_tracks.setColumnWidth(3, largeur + 30) # Définit la colonne 4
        self.ui.mkv_tracks.setColumnWidth(4, largeur + 15) # Définit la colonne 5
        self.ui.mkv_tracks.horizontalHeader().setStretchLastSection(True) # Définit la place restante à la dernière colonne


        ### Récupération du retour de MKVInfo
        for line in self.LittleProcess('mkvmerge --list-languages'):
            # Exclue la ligne contenant les ---
            if line[0] != "-":
                # Récupère la 2eme colonne, la langue en 3 lettres
                line = line.split('|')[1].strip()

                # Vérifie que le résultat est bien de 3 caractères puis ajoute la langue
                if len(line) == 3:
                    MKVLanguages.append(line)

        ## Range les langues dans l'ordre alphabétique
        MKVLanguages.sort()


        ### QProcess (permet de lancer les jobs en fond de taches)
        self.process = QProcess() # Création du QProcess
        self.process.setProcessChannelMode(1) # Unification des 2 sorties (normale + erreur) du QProcess


        ### Connexions de la grande partie des widgets (les autres sont ci-dessus ou via le fichier UI)
        self.ConnectActions()


        ### Recherche et mise à jour de leurs adresses dans softwares locations
        self.SoftwareFinding()


        ### Création du dossier temporaire
        self.FolderTempCreate()


        ### Cache les boutons non fonctionnels
        if Configs.value("HideOptions"): self.ui.option_hide_options.setChecked(True)


        ### Dans le cas du lancement du logiciel avec ouverture de fichier
        ## En cas d'argument simple
        if len(sys.argv) == 2:
            # Teste le fichier avant de l'utiliser
            if Path(sys.argv[1]).exists():
                Configs.setValue("InputFile", Path(sys.argv[1]))

            # En cas d'erreur
            else:
                QMessageBox(3, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgExist"].format(sys.argv[1]), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

        ## En cas arguments multiples
        elif len(sys.argv) > 2:
            # Suppression du fichier d'entrée
            Configs.remove("InputFile")

            # Message d'erreur
            QMessageBox(3, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgNb"].format("<br/> - ".join(sys.argv[1:])), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

        ## En cas de l'utilisation du dernier fichier ouvert
        elif Configs.value("InputFile") and Configs.value("LastFile"):
            # Si le fichier n'existe plus et qu'on ne cache pas le message, on affiche le message d'erreur
            if not Configs.value("InputFile").is_file() and not Configs.value("ConfirmErrorLastFile"):
                Configs.remove("InputFile")

                # Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, self.Trad["ErrorLastFileTitle"], self.Trad["ErrorLastFileText"], QMessageBox.NoButton, self)
                CheckBox = QCheckBox(self.Trad["Convert5"]) # Reprise du même texte
                dialog.setCheckBox(CheckBox)
                dialog.setStandardButtons(QMessageBox.Close)
                dialog.setDefaultButton(QMessageBox.Close)
                dialog.exec()

                Configs.setValue("ConfirmErrorLastFile", CheckBox.isChecked()) # Mise en mémoire de la case à cocher

        ## Dans les autres cas, on vire le nom du fichier
        elif Configs.contains("InputFile"):
            Configs.remove("InputFile")


        QCoreApplication.processEvents()
        ### Dans le cas du lancement du logiciel avec un argument
        if Configs.contains("InputFile"):
            QCoreApplication.processEvents()
            self.InputFile(Configs.value("InputFile"))


    #========================================================================
    def LittleProcess(self, Command):
        """Petite fonction récupérant les retours de process simples."""
        ### Envoie d'information en mode debug
        if Configs.value("DebugMode"):
            self.SetInfo(self.Trad["WorkCmd"].format(Command), newline=True)


        ### Liste qui contiendra les retours
        reply = []


        ### Création du QProcess avec unification des 2 sorties (normale + erreur)
        process = QProcess()
        process.setProcessChannelMode(1)


        ### Lance et attend la fin de la commande
        process.start(Command)
        process.waitForFinished()


        ### Ajoute les lignes du retour dans la liste
        for line in bytes(process.readAllStandardOutput()).decode('utf-8').splitlines():
            reply.append(line)


        ### Renvoie le résultat
        return reply


    #========================================================================
    def ConnectActions(self):
        """Fonction faisant les connexions non faites par qtdesigner."""
        ### Connexions du menu File (au clic)
        self.ui.input_file.triggered.connect(self.InputFile)
        self.ui.output_folder.triggered.connect(self.OutputFolder)


        ### Connexions du menu Actions (au clic)
        self.ui.mkv_info.triggered.connect(self.MKVInfoGui)
        self.ui.mkv_mkvmerge.triggered.connect(self.MKVMergeGui)
        self.ui.mk_validator.triggered.connect(self.MKValidator)
        self.ui.mk_clean.triggered.connect(self.MKClean)
        self.ui.mkv_view.triggered.connect(self.MKVView)


        ### Connexions du menu Options (au clic ou au coche)
        self.ui.option_recent_infos.toggled.connect(partial(self.OptionsValue, "RecentInfos"))
        self.ui.option_configuration_table.triggered.connect(self.Configuration)
        self.ui.option_feedback.toggled.connect(partial(self.OptionsValue, "Feedback"))
        self.ui.option_feedback_block.toggled.connect(partial(self.OptionsValue, "FeedbackBlock"))
        self.ui.option_aspect.toggled.connect(partial(self.OptionsValue, "WindowAspect"))
        self.ui.option_hide_options.toggled.connect(partial(self.OptionsValue, "HideOptions"))
        self.ui.option_softwares_locations.triggered.connect(lambda: (self.ui.stackedMiddle.setCurrentIndex(3)))
        self.ui.lang_en.triggered.connect(partial(self.OptionLanguage, "en_US"))
        self.ui.lang_fr.triggered.connect(partial(self.OptionLanguage, "fr_FR"))
        self.ui.lang_cs.triggered.connect(partial(self.OptionLanguage, "cs_CZ"))


        ### Connexions du menu Help (au clic ou au coche)
        self.ui.option_debug.toggled.connect(partial(self.OptionsValue, "DebugMode"))
        self.ui.help_mkvextractorqt5.triggered.connect(self.HelpMKVExtractorQt5)
        self.ui.they_talk_about.triggered.connect(self.TheyTalkAbout)
        self.ui.about.triggered.connect(self.AboutMKVExtractorQt5)
        self.ui.about_qt.triggered.connect(lambda: QMessageBox.aboutQt(MKVExtractorQt5Class))
        self.ui.mkvtoolnix.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://mkvtoolnix.download/downloads.html")))
        self.ui.whatsup.triggered.connect(lambda: WhatsUp('/usr/share/doc/mkv-extractor-qt5/changelog.Debian.gz', 'mkv-extractor-qt5', self.Trad["WhatsUpTitle"], self))


        ### Connexion du dockwidget
        self.ui.feedback_widget.visibilityChanged.connect(self.FeedbackWidget)


        ### Connexions des widgets de configuration (au clic ou changement de contenu)
        self.ui.configuration_table.itemChanged.connect(self.ConfigurationEdit)
        self.ui.configuration_close.clicked.connect(lambda: (self.ui.stackedMiddle.setCurrentIndex(0)))
        self.ui.configuration_reset.clicked.connect(self.ConfigurationReset)


        ### Connexions des widgets des locations de logiciels
        self.ui.locations_close.clicked.connect(lambda: (self.ui.stackedMiddle.setCurrentIndex(0)))
        self.ui.locations_reset.clicked.connect(partial(self.SoftwareFinding, True))
        self.ui.button_avconv.clicked.connect(partial(self.SoftwareSelector, "Location/AvConv", self.ui.location_avconv))
        self.ui.button_bdsup2sub.clicked.connect(partial(self.SoftwareSelector, "Location/BDSup2Sub", self.ui.location_bdsup2sub))
        self.ui.button_ffmpeg.clicked.connect(partial(self.SoftwareSelector, "Location/FFMpeg", self.ui.location_ffmpeg))
        self.ui.button_mkclean.clicked.connect(partial(self.SoftwareSelector, "Location/MKClean", self.ui.location_mkclean))
        self.ui.button_mkvinfo.clicked.connect(partial(self.SoftwareSelector, "Location/MKVInfo", self.ui.location_mkvinfo))
        self.ui.button_mkvtoolnix.clicked.connect(partial(self.SoftwareSelector, "Location/MKVToolNix", self.ui.location_mkvtoolnix))
        self.ui.button_mkvalidator.clicked.connect(partial(self.SoftwareSelector, "Location/MKValidator", self.ui.location_mkvalidator))
        self.ui.button_qtesseract5.clicked.connect(partial(self.SoftwareSelector, "Location/Qtesseract5", self.ui.location_qtesseract5))

        self.ui.location_avconv.textChanged.connect(partial(self.SoftwareChanged, "Location/AvConv"))
        self.ui.location_bdsup2sub.textChanged.connect(partial(self.SoftwareChanged, "Location/BDSup2Sub"))
        self.ui.location_ffmpeg.textChanged.connect(partial(self.SoftwareChanged, "Location/FFMpeg"))
        self.ui.location_mkclean.textChanged.connect(partial(self.SoftwareChanged, "Location/MKClean"))
        self.ui.location_mkvinfo.textChanged.connect(partial(self.SoftwareChanged, "Location/MKVInfo"))
        self.ui.location_mkvtoolnix.textChanged.connect(partial(self.SoftwareChanged, "Location/MKVToolNix"))
        self.ui.location_mkvalidator.textChanged.connect(partial(self.SoftwareChanged, "Location/MKValidator"))
        self.ui.location_qtesseract5.textChanged.connect(partial(self.SoftwareChanged, "Location/Qtesseract5"))


        ### Connexions du tableau listant les pistes du fichier mkv
        self.ui.mkv_tracks.itemChanged.connect(self.TrackModif) # Au changement du contenu d'un item
        self.ui.mkv_tracks.itemSelectionChanged.connect(self.TrackModif) # Au changement de sélection
        self.ui.mkv_tracks.horizontalHeader().sectionPressed.connect(self.TrackSelectAll) # Au clic sur le header horizontal


        ### Connexions des options sur les pistes du fichier mkv (au clic)
        self.ui.option_reencapsulate.toggled.connect(partial(self.OptionsValue, "Reencapsulate"))
        self.ui.option_vobsub_srt.toggled.connect(partial(self.OptionsValue, "VobsubToSrt"))
        self.ui.option_audio.toggled.connect(partial(self.OptionsValue, "AudioConvert"))
        #self.ui.option_mkv_folder.toggled.connect(partial(self.OptionsValue, "OutputSameFolder")) ICI
        self.ui.option_systray.toggled.connect(partial(self.OptionsValue, "SysTray"))
        self.option_stereo.toggled.connect(partial(self.OptionsValue, "AudioStereo"))
        self.option_to_ac3.toggled.connect(partial(self.OptionsValue, "AudioToAc3"))
        self.option_del_temp.toggled.connect(partial(self.OptionsValue, "DelTemp"))
        self.option_subtitles_open.toggled.connect(partial(self.OptionsValue, "SubtitlesOpen"))
        self.option_ffmpeg.toggled.connect(partial(self.OptionsValue, "FFMpeg"))
        self.Qtesseract5.triggered.connect(partial(self.OptionsValue, "Qtesseract5"))
        PowerList["NoChange"].triggered.connect(partial(self.OptionsValue, "AudioBoost", "NoChange"))
        QualityList["NoChange"].triggered.connect(partial(self.OptionsValue, "AudioQuality", "NoChange"))
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]: QualityList[nb].triggered.connect(partial(self.OptionsValue, "AudioQuality", nb))
        for nb in [2, 3, 4, 5]: PowerList[nb].triggered.connect(partial(self.OptionsValue, "AudioBoost", nb))


        ### Connexions en lien avec le system tray
        self.SysTrayQuit.triggered.connect(self.close)
        self.SysTrayIcon.activated.connect(self.SysTrayClick)


        ### Connexions des boutons du bas (au clic)
        self.ui.mkv_stop.clicked.connect(partial(self.WorkStop, "Stop"))
        self.ui.mkv_pause.clicked.connect(self.WorkPauseBefore)
        self.ui.mkv_execute.clicked.connect(self.CommandCreate)
        self.ui.soft_quit.__class__ = QuitButton # Utilisation de la classe QuitButton pour la prise en charge du clic droit

        ### Connexions du QProcess
        self.process.readyReadStandardOutput.connect(self.WorkReply) # Retours du travail
        self.process.finished.connect(self.WorkFinished) # Fin du travail


    #========================================================================
    def StyleChange(self, Value):
        """Fonction modifiant le style utilisé par Qt."""
        ### Enregistrement de la valeur
        Configs.setValue("QtStyle", Value)

        ### Grise le style actuellement utilisé
        for Style in QtStyleList.keys():
            if Value == Style :
                QtStyleList[Style].setEnabled(False)
            else:
                QtStyleList[Style].setEnabled(True)

        ### Applique le style graphique
        QApplication.setStyle(QStyleFactory.create(Value))



    #========================================================================
    def SoftwareFinding(self, Reset = False):
        """Fonction vérifiant les adresses des executables et les affichant dans la page des executables."""
        ### Si demande de reset
        if Reset:
            for Location in ("Location/AvConv", "Location/BDSup2Sub", "Location/FFMpeg", "Location/MKClean", "Location/MKVInfo", "Location/MKVToolNix", "Location/MKValidator", "Location/Qtesseract5"):
                Configs.setValue(Location, "")


        ### Traitement de tous les executables
        for Location, Executable, Widget in (("Location/AvConv", "avconv", self.ui.location_avconv),
                                             ("Location/BDSup2Sub", "bdsup2sub", self.ui.location_bdsup2sub),
                                             ("Location/FFMpeg", "ffmpeg", self.ui.location_ffmpeg),
                                             ("Location/MKClean", "mkclean", self.ui.location_mkclean),
                                             ("Location/MKVInfo", "mkvinfo-gui", self.ui.location_mkvinfo),
                                             ("Location/MKVToolNix", "mkvtoolnix-gui", self.ui.location_mkvtoolnix),
                                             ("Location/MKValidator", "mkvalidator", self.ui.location_mkvalidator),
                                             ("Location/Qtesseract5", "qtesseract5", self.ui.location_qtesseract5)):

            ## Sauvegarde de la valeur initiale
            InitialValue = Configs.value(Location)

            ## Si la variable est vide, on recherche le logiciel
            if not Configs.value(Location):
                # Recherche le fichier dans le PATH
                if QStandardPaths.findExecutable(Executable):
                    Configs.setValue(Location, str(QStandardPaths.findExecutable(Executable)))

                # Recherche le fichier à la base du logiciel
                elif QStandardPaths.findExecutable(Executable, [QFileInfo(Executable).absoluteFilePath()]):
                    Configs.setValue(Location, str(QStandardPaths.findExecutable(Executable, [QFileInfo(Executable).absoluteFilePath()])))

                # Cas spécifique à BDSup2Sub
                elif Location == "Location/BDSup2Sub":
                    if QStandardPaths.findExecutable("BDSup2Sub.jar"):
                        Configs.setValue("Location/BDSup2Sub", str(QStandardPaths.findExecutable("BDSup2Sub.jar")))

                    elif QStandardPaths.findExecutable("bdsup2sub", [QFileInfo("BDSup2Sub.jar").absoluteFilePath()]):
                        Configs.setValue("Location/BDSup2Sub", str(QStandardPaths.findExecutable("bdsup2sub", [QFileInfo("BDSup2Sub.jar").absoluteFilePath()])))

                # Cas spécifique à MKVToolNix
                elif Location == "Location/MKVToolNix":
                    if QStandardPaths.findExecutable("mmg"):
                        Configs.setValue("Location/MKVToolNix", str(QStandardPaths.findExecutable("mmg")))

                    elif QStandardPaths.findExecutable("mmg", [QFileInfo("mmg").absoluteFilePath()]):
                        Configs.setValue("Location/MKVToolNix", "{} --info".format(QStandardPaths.findExecutable("mmg", [QFileInfo("mmg").absoluteFilePath()])))

                # Cas spécifique à MKVInfo
                elif Location == "Location/MKVInfo":
                    if QStandardPaths.findExecutable("mkvtoolnix-gui"):
                        Configs.setValue("Location/MKVInfo", "{} --info".format(QStandardPaths.findExecutable("mkvtoolnix-gui")))

                    elif QStandardPaths.findExecutable("mkvtoolnix-gui", [QFileInfo("mkvtoolnix-gui").absoluteFilePath()]):
                        Configs.setValue("Location/MKVInfo", "{} --info".format(QStandardPaths.findExecutable("mkvtoolnix-gui", [QFileInfo("mkvtoolnix-gui").absoluteFilePath()])))

                    elif QStandardPaths.findExecutable("mkvinfo"):
                        Configs.setValue("Location/MKVInfo", "{} -g".format(QStandardPaths.findExecutable("mkvinfo")))

                    elif QStandardPaths.findExecutable("mkvinfo", [QFileInfo("mkvinfo").absoluteFilePath()]):
                        Configs.setValue("Location/MKVInfo", "{} --info".format(QStandardPaths.findExecutable("mkvinfo", [QFileInfo("mkvinfo").absoluteFilePath()])))


            ## Si la valeur n'a pas évoluée, au demarrage, le setText ne sera pas "fonctionnel", on l'appelle manuellement
            if InitialValue == Configs.value(Location): self.SoftwareChanged(Location, InitialValue, Widget)

            ## Envoie de l'adresse dans le line edit
            Widget.setText(Configs.value(Location))


    #========================================================================
    def SoftwareSelector(self, Location, Widget):
        """Fonction de séléction des executables."""
        ### Affichage de la fenêtre avec le bon dossier par défaut
        if Configs.value(Location): FileDialog = QFileDialog.getOpenFileName(self, self.Trad["LocationTitle"], Configs.value(Location))
        else: FileDialog = QFileDialog.getOpenFileName(self, self.Trad["LocationTitle"], QDir.homePath())

        ### En cas d'annulation, on arrête là
        if not FileDialog[0]: return

        ### Mise à jour du widget
        Widget.setText(FileDialog[0])


    #========================================================================
    def SoftwareChanged(self, Location, NewText, Widget = None):
        """Fonction vérifiant que l'adresse de l'executable est valide."""
        ### Mise à jour de la variable
        Configs.setValue(Location, NewText)


        ### Fait sauter les arguments afin de pouvoir tester uniquement l'executable
        NewText = NewText.split(" -")[0]


        ### Nom du widget appelant la fonction
        if not Widget: Widget = self.sender()


        ### Variable servant au (dé)grisement des options
        OptionActive = False


        ### Suppression des actions du widget
        for Action in Widget.actions(): Widget.removeAction(Action)


        ### Teste l'adresse et attribut une icone
        if not NewText:
            # Si l'adresse est introuvable, envoi d'une icone d'erreur dans le line edit
            Action = QAction(QIcon.fromTheme("emblem-question", QIcon(":/img/emblem-question.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationNo"])

        elif not Path(NewText.split(" -")[0]).exists():
            # Si l'adresse est introuvable, envoi d'une icone d'erreur dans le line edit
            Action = QAction(QIcon.fromTheme("emblem-error", QIcon(":/img/emblem-error.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationKO"])

        elif not QFileInfo(NewText.split(" -")[0]).isExecutable():
            # Si l'adresse est introuvable, envoi d'une icone d'erreur dans le line edit
            Action = QAction(QIcon.fromTheme("emblem-important", QIcon(":/img/emblem-important.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationOKO"])

        else:
            Action = QAction(QIcon.fromTheme("emblem-succed", QIcon(":/img/emblem-succed.svg")), "", Widget)
            Action.setStatusTip(self.Trad["LocationOK"])
            OptionActive = True


        ### Envoi de l'icone dans le line edit
        Widget.addAction(Action, QLineEdit.LeadingPosition)


        ### Récupération du widget de l'option
        if Location == "LocationBDSup2Sub": OptionWidget = self.BDSup2Sub
        elif Location == "LocationFFMpeg": OptionWidget = self.option_ffmpeg
        elif Location == "LocationMKClean": OptionWidget = self.ui.mk_clean
        elif Location == "LocationMKVInfo": OptionWidget = self.ui.mkv_info
        elif Location == "LocationMKVToolNix": OptionWidget = self.ui.mkv_mkvmerge
        elif Location == "LocationMKValidator": OptionWidget = self.ui.mk_validator
        elif Location == "LocationQtesseract5": OptionWidget = self.ui.option_vobsub_srt
        else: OptionWidget = None


        ### Si un widget a été donné
        if OptionWidget:
            ## Mise à jour de l'état de l'option
            OptionWidget.setEnabled(OptionActive)

            ## Fait apparaitre/disparaitre si besoin l'option
            if Configs.value("HideOptions") and not OptionActive: OptionWidget.setVisible(False)
            else: OptionWidget.setVisible(True)


        ### Recherche ffmpeg et avconv qui font la même chose
        if Location in ("Location/FFMpeg", "LocationAvConv"):
            # Désactive les radiobutton et l'option de conversion
            if not QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable() and not QFileInfo(Configs.value("Location/AvConv").split(" -")[0]).isExecutable():
                Configs.setValue("FFMpeg", False)
                self.option_ffmpeg.setEnabled(False)
                self.ui.option_audio.setEnabled(False)

            # Sélection automatique ffmpeg
            elif QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable() and not QFileInfo(Configs.value("Location/AvConv").split(" -")[0]).isExecutable():
                Configs.setValue("FFMpeg", True)
                self.option_ffmpeg.setEnabled(False)

            # Sélection automatique avconv
            elif not QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable() and QFileInfo(Configs.value("Location/AvConv").split(" -")[0]).isExecutable():
                Configs.setValue("FFMpeg", False)
                self.option_ffmpeg.setEnabled(False)

            # Les deux sont dispo, utilisation de ffmpeg par defaut
            else:
                Configs.setValue("FFMpeg", True)
                self.option_ffmpeg.setChecked(True)


    #========================================================================
    def OptionsValue(self, Option, Value):
        """Fonction de mise à jour des options."""
        ### Mise à jour de la variable et envoie de l'info
        Configs.setValue(Option, Value)

        if Configs.value("DebugMode"):
            self.SetInfo(self.Trad["OptionUpdate"].format(Option, Value), newline=True)


        ### Dans le cas de certaines options, il faut faire plus
        ## Si l'option OutputSameFolder est activée et qu'un fichier d'entré est déjà connu
        if Option == "OutputSameFolder" and Value and Configs.contains("InputFile"):
            # Recherche de l'option OutputSameFolder
            x = self.ui.configuration_table.findItems("OutputSameFolder", Qt.MatchExactly)[0].row()

            ## Il faut bloquer le signal pour éviter un cercle vicieux et modifier la valeur visuelle en directe
            self.ui.configuration_table.blockSignals(True)
            self.ui.configuration_table.item(x, 1).setText(str(Configs.value("InputFolder")))

            # Envoie de la nouvelle variable à la fonction de gestion des dossiers qui mettra à jour la variable
            self.OutputFolder(Configs.value("InputFolder"))

            # Déblocage des signaux
            self.ui.configuration_table.blockSignals(False)


        ## En cas de modification du dossier de sorti
        elif Option == "OutputFolder":
            Configs.setValue(Option, Path(Value))

            # Recherche de l'option OutputFolder
            x = self.ui.configuration_table.findItems("OutputSameFolder", Qt.MatchExactly)[0].row()

            # Il faut bloquer le signal pour éviter un cercle vicieux et modifier la valeur visuelle en directe
            self.ui.configuration_table.blockSignals(True)
            self.ui.configuration_table.item(x, 1).setText("False")

            # Mise à jour de la variable
            Configs.setValue("OutputSameFolder", False)

            # Envoie de la nouvelle variable à la fonction de gestion des dossiers
            self.OutputFolder(Configs.value("OutputFolder"))

            # Déblocage des signaux
            self.ui.configuration_table.blockSignals(False)


        ## Pour cacher ou afficher la box de retour d'informations
        elif Option == "Feedback":
            if Value:
                self.ui.feedback_widget.show()

            else:
                self.ui.feedback_widget.hide()


        ## Pour bloquer ou débloquer la box de retour d'informations
        elif Option == "FeedbackBlock":
            if Value:
                self.ui.feedback_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)

            else:
                self.ui.feedback_widget.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)


        ## Pour cacher ou afficher l'icône du systray
        elif Option == "SysTray":
            ## Affichage de l'icône
            if Value:
                self.SysTrayIcon.show()

            ## Cache l'icône après avoir affiché la fenêtre principale
            else:
                self.show()
                self.activateWindow()
                self.SysTrayIcon.hide()

        ## Pour cacher ou afficher l'icône du systray
        elif Option == "HideOptions":
            for Location, Widget in (("Location/BDSup2Sub", self.BDSup2Sub),
                                     ("Location/FFMpeg", self.option_ffmpeg),
                                     ("Location/MKClean", self.ui.mk_clean),
                                     ("Location/MKVInfo", self.ui.mkv_info),
                                     ("Location/MKVToolNix", self.ui.mkv_mkvmerge),
                                     ("Location/MKValidator", self.ui.mk_validator),
                                     ("Location/Qtesseract5", self.ui.option_vobsub_srt)):
                # S'il faut les afficher
                if not Value:
                    Widget.setVisible(True)

                # S'il faut les cacher
                else:
                    if not QFileInfo(Configs.value(Location).split(" -")[0]).isExecutable():
                        Widget.setVisible(False)


    #========================================================================
    def OptionLanguage(self, value):
        """Fonction modifiant en temps réel la traduction."""
        ### Mise à jour de la variable de la langue
        Configs.setValue("Language", value)


        ### Chargement du fichier QM de traduction (anglais utile pour les textes singulier/pluriel)
        appTranslator = QTranslator() # Création d'un QTranslator

        ## Pour la trad française
        if Configs.value("Language") == "fr_FR":
            find = appTranslator.load("MKVExtractorQt5_fr_FR", str(AppFolder))

            # Si le fichier n'a pas été trouvé, affiche une erreur et utilise la version anglaise
            if not find:
                QMessageBox(3, "Erreur de traduction", "Aucun fichier de traduction <b>française</b> trouvé.<br/>Utilisation de la langue <b>anglaise</b>.", QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()
                self.ui.lang_en.setChecked(True)
                Configs.setValue("Language", "en_US")

            # Chargement de la traduction
            else:
                app.installTranslator(appTranslator)

        ## Pour la version tchèque
        elif Configs.value("Language") == "cs_CZ":
            find = appTranslator.load("MKVExtractorQt5_cs_CZ", str(AppFolder))

            # Si le fichier n'a pas été trouvé, affiche une erreur et utilise la version anglaise
            if not find:
                QMessageBox(3, "Chyba překladu", "No translation file <b>Czech</b> found. Use <b>English</b> language. Soubor s překladem do <b>češtiny</b> nenalezen. Použít <b>anglický</b> jazyk.", QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()
                self.ui.lang_en.setChecked(True)
                Configs.setValue("Language", "en_US")

            # Chargement de la traduction
            else:
                app.installTranslator(appTranslator)


        ### Mise à jour du fichier langage de Qt
        translator_qt = QTranslator() # Création d'un QTranslator
        if translator_qt.load("qt_" + Configs.value("Language"), QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator_qt)


        ### Mise à jour du dictionnaire des textes
        # 008000 : vert                 0000c0 : bleu                           800080 : violet
        effet = """<span style=" color:#000000;">@=====@</span>"""
        self.Trad = {"AboutTitle": QCoreApplication.translate("About", "About MKV Extractor Gui"),
                     "AboutText": QCoreApplication.translate("About", """<html><head/><body><p align="center"><span style=" font-size:12pt; font-weight:600;">MKV Extractor Qt v{}</span></p><p><span style=" font-size:10pt;">GUI to extract/edit/remux the tracks of a matroska (MKV) file.</span></p><p><span style=" font-size:10pt;">This program follows several others that were coded in Bash and it codec in python3 + QT5.</span></p><p><span style=" font-size:8pt;">This software is licensed under </span><span style=" font-size:8pt; font-weight:600;"><a href="{}">GNU GPL v3</a></span><span style=" font-size:8pt;">.</span></p><p>Thanks to the <a href="http://www.developpez.net/forums/f96/autres-langages/python-zope/"><span style=" text-decoration: underline; color:#0057ae;">developpez.net</span></a> python forums for their patience</p><p align="right">Created by <span style=" font-weight:600;">Belleguic Terence</span> (Hizoka), November 2013</p></body></html>"""),


                     "TheyTalkAboutTitle": QCoreApplication.translate("TheyTalkAbout", "They talk about MKV Extractor Gui"),
                     "TheyTalkAboutText": QCoreApplication.translate("TheyTalkAbout", """<html><head/><body><p><a href="http://sysads.co.uk/2014/09/install-mkv-extractor-qt-5-1-4-ubuntu-14-04/"><span style=" text-decoration: underline; color:#0057ae;">sysads.co.uk</span></a> (English)</p><p><a href="http://www.softpedia.com/reviews/linux/mkv-extractor-qt-review-496919.shtml"><span style=" text-decoration: underline; color:#0057ae;">softpedia.com</span></a> (English)</p><p><a href="http://linux.softpedia.com/get/Multimedia/Video/MKV-Extractor-Qt-103555.shtml"><span style=" text-decoration: underline; color:#0057ae;">linux.softpedia.com</span></a> (English)</p><p><a href="http://zenway.ru/page/mkv-extractor-qt"><span style=" text-decoration: underline; color:#0057ae;">zenway.ru</span></a> (Russian)</p><p><a href="http://linuxg.net/how-to-install-mkv-extractor-qt-5-1-4-on-ubuntu-14-04-linux-mint-17-elementary-os-0-3-deepin-2014-and-other-ubuntu-14-04-derivatives/"><span style=" text-decoration: underline; color:#2980b9;">linuxg.net</span></a> (English)</p><p><a href="http://la-vache-libre.org/mkv-extractor-gui-virer-les-sous-titres-inutiles-de-vos-fichiers-mkv-et-plus-encore/"><span style=" text-decoration: underline; color:#2980b9;">la-vache-libre.org</span></a> (French)</p><p><a href="http://passionexubuntu.altervista.org/index.php/it/kubuntu/1152-mkv-extractor-qt-vs-5-1-3-kde.html"><span style=" text-decoration: underline; color:#2980b9;">passionexubuntu.altervista.org</span></a> (Italian)</p><p><a href="https://github.com/darealshinji/mkv-extractor-qt5"><span style=" text-decoration: underline; color:#2980b9;">an unofficial github </span></a>(English)</p><p><a href="https://gamblisfx.com/mkv-extractor-qt-5-2-1-extract-audio-and-video-from-mkv-files/"><span style=" text-decoration: underline; color:#2980b9;">gamblisfx.com</span></a><a href="https://github.com/darealshinji/mkv-extractor-qt5"><span style=" text-decoration: underline; color:#2980b9;"/></a>(English)</p><p><a href="https://aur.archlinux.org/packages/mkv-extractor-qt/"><span style=" text-decoration: underline; color:#2980b9;">An unofficial aur package</span></a></p><p><br/></p><p><br/></p><p><br/></p></body></html>"""),

                     "SysTrayQuit": QCoreApplication.translate("SysTray", "Quit"),
                     "SysTrayFinishTitle": QCoreApplication.translate("SysTray", "The command(s) have finished"),
                     "SysTrayFinishText": QCoreApplication.translate("SysTray", "The <b>{}</b> command have finished its work."),
                     "SysTrayTotalFinishText": QCoreApplication.translate("SysTray", "All commands have finished their work."),

                     "WhatsUpTitle": QCoreApplication.translate("WhatsUp", "MKV Extractor Qt5's changelog"),

                     "QTextEditStatusTip": QCoreApplication.translate("Main", "Use the right click for view options."),

                     "LocationOK": QCoreApplication.translate("Main", "This location is valid."),
                     "LocationKO": QCoreApplication.translate("Main", "This location is not valid."),
                     "LocationNo": QCoreApplication.translate("Main", "No location for this command."),
                     "LocationOKO": QCoreApplication.translate("Main", "This location is valid but not executable."),
                     "LocationTitle": QCoreApplication.translate("Main", "Please select the executable file"),

                     "AllFiles": QCoreApplication.translate("Main", "All compatible Files"),
                     "MatroskaFiles": QCoreApplication.translate("Main", "Matroska Files"),
                     "OtherFiles": QCoreApplication.translate("Main", "Other Files"),

                     "Convert0": QCoreApplication.translate("Main", "Do not ask again"),
                     "Convert1": QCoreApplication.translate("Main", "File needs to be converted"),
                     "Convert2": QCoreApplication.translate("Main", "This file is not supported by mkvmerge.\nDo you want convert this file in mkv ?"),
                     "Convert3": QCoreApplication.translate("Main", "MKVMerge Warning"),
                     "Convert4": QCoreApplication.translate("Main", "A warning has occurred during the convertion of the file, read the feedback informations."),
                     "Convert5": QCoreApplication.translate("Main", "Do not warn me"),
                     "Convert6": QCoreApplication.translate("Main", "Choose the out folder of the new mkv file"),

                     "FileExistsTitle": QCoreApplication.translate("Main", "Already existing file"),
                     "FileExistsText": QCoreApplication.translate("Main", "The <b>{}</b> is already existing, overwrite it?"),

                     "Resume1": QCoreApplication.translate("Main", "Awaiting resume"),
                     "Resume2": QCoreApplication.translate("Main", "The software is <b>pausing</b>.<br/>Thanks to clic on the '<b>Resume work</b>' button or '<b>Cancel work</b>' for cancel all the work and remove the temporary files."),
                     "Resume3": QCoreApplication.translate("Main", "Resume work"),
                     "Resume4": QCoreApplication.translate("Main", "Cancel work"),

                     "ErrorLastFileTitle": QCoreApplication.translate("Errors", "The last file doesn't exist"),
                     "ErrorLastFileText": QCoreApplication.translate("Errors", "You have checked the option who reload the last file to the launch of MKV Extractor Qt, but this last file doesn't exist anymore."),
                     "ErrorArgTitle": QCoreApplication.translate("Errors", "Wrong arguments"),
                     "ErrorArgExist": QCoreApplication.translate("Errors", "The <b>{}</b> file given as argument does not exist."),
                     "ErrorArgNb": QCoreApplication.translate("Errors", "<b>Too many arguments given:</b><br/> - {} "),
                     "ErrorConfigTitle": QCoreApplication.translate("Errors", "Wrong value"),
                     "ErrorConfigText": QCoreApplication.translate("Errors", "Wrong value for the <b>{}</b> option, MKV Extractor Qt will use the default value."),
                     "ErrorConfigPath": QCoreApplication.translate("Errors", "Wrong path for the <b>{}</b> option, MKV Extractor Qt will use the default path."),
                     "ErrorQuoteTitle": QCoreApplication.translate("Errors", "No way to open this file"),
                     "ErrorQuoteText": QCoreApplication.translate("Errors", "The file to open contains quotes (\") in its name. It's impossible to open a file with this carac. Please rename it."),
                     "ErrorSizeTitle": QCoreApplication.translate("Errors", "Space available"),
                     "ErrorSize": QCoreApplication.translate("Errors", "Not enough space available in the <b>{}</b> folder.<br/>It is advisable to have at least twice the size of free space on the disk file.<br>Free disk space: <b>{}</b>.<br>File size: <b>{}</b>."),
                     "ErrorSizeAttachement": QCoreApplication.translate("Errors", "Not enough space available in <b>{}</b> folder.<br/>Free space in the disk: <b>{}</b><br/>File size: <b>{}</b>."),

                     "HelpTitle": QCoreApplication.translate("Help", "Help me!"),
                     "HelpText": QCoreApplication.translate("Help", """<html><head/><body><p align="center"><span style=" font-weight:600;">Are you lost? Do you need help? </span></p><p><span style=" font-weight:600;">Normally all necessary information is present: </span></p><p>- Read the informations in the status bar when moving the mouse on widgets </p><p>- Read the informations in some tooltips, wait 2-3 secondes on actions or buttons.</p><p><span style=" font-weight:600;">Though, if you need more information: </span></p><p>- Forum Ubuntu-fr.org: <a href="https://forum.ubuntu-fr.org/viewtopic.php?id=1508741"><span style=" text-decoration: underline; color:#0057ae;">topic</span></a></p><p>- My email address: <a href="mailto:hizo@free.fr"><span style=" text-decoration: underline; color:#0057ae;">hizo@free.fr </span></a></p><p><span style=" font-weight:600;">Thank you for your interest in this program.</span></p></body></html>"""),

                     "AlreadyExistsTest": QCoreApplication.translate("Main", "Skip the existing file test."),
                     "AudioQuality": QCoreApplication.translate("Main", "Quality of the ac3 file converted."),
                     "AudioBoost": QCoreApplication.translate("Main", "Power of the ac3 file converted."),
                     "CheckSizeCheckbox": QCoreApplication.translate("Main", "Skip the free space disk test."),
                     "DebugMode": QCoreApplication.translate("Main", "View more informations in feedback box."),
                     "DelTemp": QCoreApplication.translate("Main", "Delete temporary files."),
                     "ConfirmErrorLastFile": QCoreApplication.translate("Main", "Remove the error message if the last file doesn't exist."),
                     "Feedback": QCoreApplication.translate("Main", "Show or hide the information feedback box."),
                     "FeedbackBlock": QCoreApplication.translate("Main", "Anchor or loose information feedback box."),
                     "FolderParentTemp": QCoreApplication.translate("Main", "The folder to use for extract temporaly the attachements file to view them."),
                     "FFMpeg": QCoreApplication.translate("Main", "Use FFMpeg for the conversion."),
                     "LastFile": QCoreApplication.translate("Main", "Keep in memory the last file opened for open it at the next launch of MKV Extractor Qt."),
                     "HideOptions": QCoreApplication.translate("Main", "Hide the disabled options."),
                     "MMGorMEQ": QCoreApplication.translate("Main", "Software to use for just encapsulate."),
                     "MMGorMEQCheckbox": QCoreApplication.translate("Main", "Skip the proposal to softaware to use."),
                     "ConfirmConvert": QCoreApplication.translate("Main", "Skip the confirmation of the conversion."),
                     "ConfirmWarning": QCoreApplication.translate("Main", "Hide the information of the conversion warning."),
                     "InputFolder": QCoreApplication.translate("Main", "Folder of the MKV files."),
                     "OutputFolder": QCoreApplication.translate("Main", "Output folder for the new MKV files."),
                     "Language": QCoreApplication.translate("Main", "Software language to use."),
                     "RecentInfos": QCoreApplication.translate("Main", "Remove the Qt file who keeps the list of the recent files for the window selection."),
                     "OutputSameFolder": QCoreApplication.translate("Main", "Use the same input and output folder."),
                     "RemuxRename": QCoreApplication.translate("Main", "Automatically rename the output file name in MEG_FileName."),
                     "AudioStereo": QCoreApplication.translate("Main", "Switch to stereo during conversion."),
                     "SubtitlesOpen": QCoreApplication.translate("Main", "Opening subtitles before encapsulation."),
                     "SysTray": QCoreApplication.translate("Main", "Display or hide the system tray icon."),
                     "WindowAspect": QCoreApplication.translate("Main", "Keep in memory the aspect and the position of the window for the next opened."),
                     "QtStyle": QCoreApplication.translate("Main", "Qt decoration."),

                     "OptionsDTStoAC31": QCoreApplication.translate("Options", "Convert in AC3"),
                     "OptionsDTStoAC32": QCoreApplication.translate("Options", "Convert audio tracks automatically to AC3."),
                     "OptionsDelTemp1": QCoreApplication.translate("Options", "Delete temporary files"),
                     "OptionsDelTemp2": QCoreApplication.translate("Options", "The temporary files are the extracted tracks."),
                     "OptionsFFMpeg": QCoreApplication.translate("Options", "Use FFMpeg for the conversion."),
                     "OptionsFFMpegStatusTip": QCoreApplication.translate("Options", "If FFMpeg and AvConv are installed, use FFMpeg."),
                     "OptionsPowerList": QCoreApplication.translate("Options", "Increase the sound power"),
                     "OptionsPower": QCoreApplication.translate("Options", "No power change."),
                     "OptionsPowerX": QCoreApplication.translate("Options", "Multiplying audio power by {}."),
                     "OptionsPowerY": QCoreApplication.translate("Options", "Power x {}"),
                     "OptionsQuality": QCoreApplication.translate("Options", "List of available flow rates of conversion"),
                     "OptionsQualityX": QCoreApplication.translate("Options", "Convert the audio quality in {} kbits/s."),
                     "OptionsQualityY": QCoreApplication.translate("Options", "{} kbits/s"),
                     "OptionsStereo1": QCoreApplication.translate("Options", "Switch to stereo during conversion"),
                     "OptionsStereo2": QCoreApplication.translate("Options", "The audio will not use the same number of channels, the audio will be stereo (2 channels)."),
                     "OptionsSub1": QCoreApplication.translate("Options", "Opening subtitles before encapsulation"),
                     "OptionsSub2": QCoreApplication.translate("Options", "Auto opening of subtitle srt files for correction. The software will be paused."),
                     "OptionUpdate": QCoreApplication.translate("Options", 'New value for <span style=" color:#0000c0;">{}</span> option: <span style=" color:#0000c0;">{}</span>'),
                     "NoChange1": QCoreApplication.translate("Options", "No change the quality"),
                     "NoChange2": QCoreApplication.translate("Options", "The quality of the audio tracks will not be changed."),
                     "NoChange1": QCoreApplication.translate("Options", "No change the power"),
                     "NoChange2": QCoreApplication.translate("Options", "The power of the audio tracks will not be changed."),
                     "OptionsStyles": QCoreApplication.translate("Options", "Use the {} style."),

                     "SelectedFile": QCoreApplication.translate("Select", "Selected file: {}."),
                     "SelectedFolder1": QCoreApplication.translate("Select", "Selected folder: {}."),
                     "SelectedFolder2": QCoreApplication.translate("Select", 'Always use the same output folder as the input MKV file (automatically updated)'),

                     "SelectFileInCheckbox": QCoreApplication.translate("Select", "Keep in memory the last file opened for open it at the next launch of MKV Extractor Qt (to use for tests)"),
                     "SelectFileIn": QCoreApplication.translate("Select", "Select the input MKV File"),
                     "SelectFileOut": QCoreApplication.translate("Select", "Select the output MKV file"),
                     "SelectFolder": QCoreApplication.translate("Select", "Select the output folder"),

                     "UseMMGTitle": QCoreApplication.translate("UseMMG", "MKV Merge Gui or MKV Extractor Qt ?"),
                     "UseMMGText": QCoreApplication.translate("UseMMG", "You want extract and reencapsulate the tracks without use other options.\n\nIf you just need to make this, you should use MMG (MKV Merge gui) who is more adapted for this job.\n\nWhat software do you want use ?\n"),

                     "RemuxRenameCheckBox": QCoreApplication.translate("RemuxRename", "Always use the default file rename (MEG_FileName)"),
                     "RemuxRenameTitle": QCoreApplication.translate("RemuxRename", "Choose the output file name"),

                     "Audio": QCoreApplication.translate("Track", "audio"),
                     "Subtitles": QCoreApplication.translate("Track", "subtitles"),
                     "Video": QCoreApplication.translate("Track", "video"),

                     "TrackAac": QCoreApplication.translate("Track", "If the remuxed file has reading problems, change this value."),
                     "TrackAudio": QCoreApplication.translate("Track", "Change the language if it's not right. 'und' means 'Undetermined'."),
                     "TrackAttachment": QCoreApplication.translate("Track", "This track can be renamed and must contain an extension to avoid reading errors by doubleclicking."),
                     "TrackChapters": QCoreApplication.translate("Track", "chapters"),
                     "TrackID1": QCoreApplication.translate("Track", "Work with track number {}."), # Pour les pistes normales
                     "TrackID2": QCoreApplication.translate("Track", "Work with attachment number {}."), # Pour les fichiers joints
                     "TrackID3": QCoreApplication.translate("Track", "Work with {}."), # Pour les chapitres et les tags
                     "TrackRename": QCoreApplication.translate("Track", "This track can be renamed by doubleclicking."),
                     "TrackTags": QCoreApplication.translate("Track", "tags"),
                     "TrackType": QCoreApplication.translate("Track", "This track is a {} type and cannot be previewed."),
                     "TrackType2": QCoreApplication.translate("Track", "This track is a {} type and can be previewed."),
                     "TrackTypeAttachment": QCoreApplication.translate("Track", "This attachment file is a {} type, it can be extracted (speedy) and viewed by clicking."),
                     "TrackVideo": QCoreApplication.translate("Track", "Change the fps value if needed. Useful in case of audio lag. Normal : 23.976, 25.000 and 30.000."),

                     "WorkCanceled" : effet + QCoreApplication.translate("Work", " All commands were canceled ") + effet,
                     "WorkCmd": QCoreApplication.translate("Work", """Command execution: <span style=" color:#0000c0;">{}</span>"""),
                     "WorkError" : effet + QCoreApplication.translate("Work", " The last command returned an error ") + effet,
                     "WorkFinished" : effet + QCoreApplication.translate("Work", " {} execution is finished ") + effet,
                     "WorkMerge" : effet + QCoreApplication.translate("Work", " MKV File Tracks ") + effet,
                     "WorkProgress" : effet + QCoreApplication.translate("Work", " {} execution in progress ") + effet,
                    }


        ### Recharge les textes de l'application graphique du fichier ui.py
        self.ui.retranslateUi(self)


        ### Mise au propre du widget de retour d'info et envoie de langue
        if not TempValues.value("FirstRun"): # Variable évitant l'envoie inutile d'info au démarrage
            self.ui.reply_info.clear()

            if Configs.value("DebugMode"):
                self.SetInfo(self.Trad["OptionUpdate"].format("Language", value), newline=True)

        else:
            TempValues.setValue("FirstRun", False)


        ### Recharge le SysTrayQuit
        self.SysTrayQuit.setText(self.Trad["SysTrayQuit"])


        ### Recharge les textes des toolbutton
        self.option_ffmpeg.setText(self.Trad["OptionsFFMpeg"])
        self.option_ffmpeg.setStatusTip(self.Trad["OptionsFFMpegStatusTip"])
        self.option_ffmpeg.setToolTip(self.Trad["OptionsFFMpegStatusTip"])
        self.option_to_ac3.setText(self.Trad["OptionsDTStoAC31"])
        self.option_to_ac3.setStatusTip(self.Trad["OptionsDTStoAC32"])
        self.option_stereo.setText(self.Trad["OptionsStereo1"])
        self.PowerMenu.setTitle(self.Trad["OptionsPowerList"])
        self.RatesMenu.setTitle(self.Trad["OptionsQuality"])
        self.option_del_temp.setText(self.Trad["OptionsDelTemp1"])
        self.option_subtitles_open.setText(self.Trad["OptionsSub1"])
        self.option_subtitles_open.setStatusTip(self.Trad["OptionsSub2"])
        self.option_stereo.setStatusTip(self.Trad["OptionsStereo2"])
        self.option_del_temp.setStatusTip(self.Trad["OptionsDelTemp2"])
        self.ui.reply_info.setStatusTip(self.Trad["QTextEditStatusTip"])

        PowerList["NoChange"].setText(self.Trad["NoChange1"])
        PowerList["NoChange"].setStatusTip(self.Trad["NoChange2"])
        for nb in [2, 3, 4, 5]:
            PowerList[nb].setText(self.Trad["OptionsPowerY"].format(nb))
            if nb == 1:
                PowerList[1].setStatusTip(self.Trad["OptionsPower"])

            else:
                PowerList[nb].setStatusTip(self.Trad["OptionsPowerX"].format(nb))

        QualityList["NoChange"].setText(self.Trad["NoChange1"])
        QualityList["NoChange"].setStatusTip(self.Trad["NoChange2"])
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
            QualityList[nb].setStatusTip(self.Trad["OptionsQualityX"].format(nb))
            QualityList[nb].setText(self.Trad["OptionsQualityY"].format(nb))

        self.Qtesseract5.setText("Open the SUB file in Qtesseract5")
        self.Qtesseract5.setStatusTip("Open the SUB file in Qtesseract5.")
        self.Qtesseract5.setToolTip("The SUB file will be open in Qtesseract5 gui for better configuration.")

        self.BDSup2Sub.setText("Open the SUP file in BDSup2Sub")
        self.BDSup2Sub.setStatusTip("Open SUP sup file in BDSup2Sub.")
        if not Path(Configs.value("Location/BDSup2Sub").split(" -")[0]).exists(): self.BDSup2Sub.setToolTip("BDSup2Sub isn't installed, impossible to convert SUP files to SUB files and open the SUP file into BDSup2Sub.")
        elif not QFileInfo(Configs.value("Location/BDSup2Sub").split(" -")[0]).isExecutable(): self.BDSup2Sub.setToolTip("BDSup2Sub isn't executable, impossible to convert SUP files to SUB files and open the SUP file into BDSup2Sub.")
        else: self.BDSup2Sub.setToolTip("The SUP file will be open in BDSup2Sub gui for better configuration.")


        for Style in QtStyleList.keys(): QtStyleList[Style].setStatusTip(self.Trad["OptionsStyles"].format(Style))


        ### Recharge les emplacements des executables
        self.SoftwareFinding()


        ### Si un dossier de sortie a déjà été sélectionné, mise à jour du statustip et affiche l'info
        if Configs.value("OutputFolder"):
            self.ui.output_folder.setStatusTip(self.Trad["SelectedFolder1"].format(Configs.value("OutputFolder")))
            self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + str(Configs.value("OutputFolder")) + '</span>'), newline=True)


        ### Si un fichier mkv à déjà été chargé, relance le chargement du fichier pour tout traduire et remet en place les cases et boutons cochés
        if TempValues.value("MKVLoaded"):
            ## Crée lka liste des  boutons cochés
            WidgetsList = []
            for Widget in [self.ui.option_reencapsulate, self.ui.option_vobsub_srt, self.ui.option_audio]:
                if Widget.isChecked():
                    WidgetsList.append(Widget)

            ## Relance le chargement du fichier mkv pour tout traduire
            self.InputFile(Configs.value("InputFile"))

            ## Recoche les pistes qui l'étaient, crée une liste car MKVDicoSelect sera modifié pendant la boucle
            for x in list(MKVDicoSelect.keys()):
                self.ui.mkv_tracks.item(x, 1).setCheckState(2)

            ## Recoche les boutons
            for Widget in WidgetsList:
                Widget.setChecked(True)


    #========================================================================
    def SetInfo(self, text, color="000000", center=False, newline=False):
        """Fonction mettant en page les infos à afficher dans le widget d'information."""
        ### Saut de ligne à la demande si le widget n'est pas vide
        if newline and self.ui.reply_info.toPlainText() != "":
            self.ui.reply_info.append('')


        ### Envoie du nouveau texte avec mise en page
        if center:
            self.ui.reply_info.append("""<center><table><tr><td><span style=" color:#{};">{}</span></td></tr></table></center>""".format(color, text))

        else:
            self.ui.reply_info.append("""<span style=" color:#{};">{}</span>""".format(color, text))


        ### Force l'affichage de la derniere ligne
        self.ui.reply_info.moveCursor(QTextCursor.End)


    #========================================================================
    def Configuration(self):
        """Fonction affichant les options et leur valeurs."""
        ### Bloque la connexion pour éviter les messages d'erreur
        self.ui.configuration_table.blockSignals(True)


        ### Nécessaire à l'affichage des statustip
        self.ui.configuration_table.setMouseTracking(True)


        ### Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 2:
            self.ui.stackedMiddle.setCurrentIndex(2)

        while self.ui.configuration_table.rowCount() != 0:
            self.ui.configuration_table.removeRow(0)


        ### Remplissage du tableau, chaque ligne renvoie (num_de_ligne, (Key, Value))
        for x, (Key, Value) in enumerate(DefaultValues.items()):
            # Création de la ligne
            self.ui.configuration_table.insertRow(x)

            # Remplissage de la ligne (nom, valeur, valeur par défaut)
            self.ui.configuration_table.setItem(x, 0, QTableWidgetItem(Key))
            self.ui.configuration_table.setItem(x, 1, QTableWidgetItem(str(Configs.value(Key))))
            self.ui.configuration_table.setItem(x, 2, QTableWidgetItem(str(Value)))

            # Blocage de la modification
            self.ui.configuration_table.item(x, 0).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.configuration_table.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            # Si c'est la variable d'un executable, on cache la ligne
            if Key[0:8] == 'Location':
                self.ui.configuration_table.setRowHidden(x, True)

            # Sinon on envoie du statustip
            else:
                self.ui.configuration_table.item(x, 0).setStatusTip(self.Trad[Key])
                self.ui.configuration_table.item(x, 1).setStatusTip(self.Trad[Key])
                self.ui.configuration_table.item(x, 2).setStatusTip(self.Trad[Key])


        ### Visuel du tableau
        self.ui.configuration_table.sortItems(0) # Rangement par ordre de nom d'option
        largeur = (self.ui.configuration_table.size().width() - 185) / 2 # Calcul de la largeur
        self.ui.configuration_table.setColumnWidth(0, 160) # Définition de la largeur de la colonne
        self.ui.configuration_table.setColumnWidth(1, largeur) # Définition de la largeur de la colonne
        self.ui.configuration_table.setColumnWidth(2, largeur) # Définition de la largeur de la colonne
        self.ui.configuration_table.setSortingEnabled(False) # Blocage du rangement


        ### Débloque la connexion
        self.ui.configuration_table.blockSignals(False)


    #========================================================================
    def ConfigurationEdit(self, Item):
        """Fonction de mise à jour de la configuration."""
        ### Récupération de la cellule modifiée et des valeurs
        x = self.ui.configuration_table.row(Item)
        Option = self.ui.configuration_table.item(x, 0).text()
        Value = self.ui.configuration_table.item(x, 1).text()


        ### Si la valeur est vide, on utilise celle par défaut
        if not Value:
            Value = self.ui.configuration_table.item(x, 2).text()
            self.ui.configuration_table.setItem(x, 1, QTableWidgetItem(Value))


        ### Vérifie la classe et corrige si besoin de la valeur
        ## En cas de type bool
        if isinstance(DefaultValues[Option], bool):
            # Pour gérer les vrai
            if Value in ["True", "true"]:
                self.OptionsValue(Option, True)

            # Pour gérer les faux
            elif Value in ["False", "false"]:
                self.OptionsValue(Option, False)

            # Si mauvaise valeur, on indique l'erreur et utilise la valeur par défaut
            else:
                # Message d'erreur
                QMessageBox(3, self.Trad["ErrorConfigTitle"], self.Trad["ErrorConfigText"].format(Option), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

                # Modification du texte et donc de la valeur (ça relance cette fonction)
                self.ui.configuration_table.item(x, 1).setText(str(DefaultValues[Option]))

        ## En cas de type int
        elif isinstance(DefaultValues[Option], int):
            # Essaie de convertir en int
            try:
                self.OptionsValue(Option, int(Value))

            # Si ça foire,  on indique l'erreur et utilise la valeur par défaut
            except:
                # Message d'erreur
                QMessageBox(3, self.Trad["ErrorConfigTitle"], self.Trad["ErrorConfigText"].format(Option), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

                # Modification du texte et donc de la valeur (ça relance cette fonction)
                self.ui.configuration_table.item(x, 1).setText(str(DefaultValues[Option]))

        ## En cas de type int
        else:
            # Si la valeur est une adresse existante, on converti en path
            if Path(Value).exists():
                self.OptionsValue(Option, Path(Value))

                # En cas de modification du dossier temporaire
                if Option == "FolderParentTemp":
                    self.OptionsValue(Option, Value)
                    self.FolderTempCreate()


            # Sinon, c'est que c'est juste du texte
            else:
                # Si c'est du texte alors que ça devrait être un path, c'est que l'adresse est erronée
                if Option in ["OutputFolder", "InputFolder", "MKVConvertThisFolder"]:
                    # Message d'erreur
                    QMessageBox(3, self.Trad["ErrorConfigTitle"], self.Trad["ErrorConfigPath"].format(Option), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

                    # Modification du texte et donc de la valeur (ça relance cette fonction)
                    self.ui.configuration_table.item(x, 1).setText(str(DefaultValues[Option]))

                else:
                    self.OptionsValue(Option, str(Value))


    #========================================================================
    def ConfigurationReset(self):
        """Fonction de réinitialisation des configs."""
        ### Utilisation de toutes les valeurs par défauts
        for Key, Value in DefaultValues.items():
            self.OptionsValue(Key, Value)


        ### Rechargement de la liste d'infos
        self.Configuration()


    #========================================================================
    def FeedbackWidget(self, value):
        """Fonction appelée lors de l'ouverture et la fermeture du dockwidget."""
        ### Mise à jour de la variable
        Configs.setValue("Feedback", value)


        ### Mise à jour de la case à cocher
        self.ui.option_feedback.setChecked(value)


    #========================================================================
    def HumanSize(self, Value):
        """Fonction rendant plus lisible les tailles."""
        ### Valeur finale
        HumanValue = ""


        ### Conversion dans une catégorie supérieure
        for count in ['Bytes', 'KB', 'MB', 'GB']:
            if Value > -1024.0 and Value < 1024.0:
                HumanValue = "%3.1f%s" % (Value, count)
            Value /= 1024.0

        if not HumanValue:
            HumanValue = "%3.1f%s" % (Value, 'TB')


        ### Renvoie la valeur finale
        return HumanValue


    #========================================================================
    def CheckSize(self, Folder, InputSize, OutputSize, Text):
        """Fonction vérifiant qu'il y a assez de place pour travailler."""
        ### Pas de teste si valeur le demandant
        if Configs.value("CheckSizeCheckbox", False): return False


        ### Affiche un message s'il n'y a pas la double de la place
        if (InputSize * 2) > OutputSize:
            HumanInputSize = self.HumanSize(int(InputSize))
            HumanOutputSize = self.HumanSize(int(OutputSize))

            ## Creation de la fenêtre d'information
            ChoiceBox = QMessageBox(2, self.Trad["ErrorSizeTitle"], Text.format(TempValues.value(Folder), HumanOutputSize, HumanInputSize), QMessageBox.NoButton, self, Qt.WindowSystemMenuHint)
            CheckBox = QCheckBox(self.Trad["Convert0"], ChoiceBox)
            Button1 = QPushButton(QIcon.fromTheme("folder-open", QIcon(":/img/folder-open.png")), "Change the directory", ChoiceBox)
            Button2 = QPushButton(QIcon.fromTheme("dialog-ok", QIcon(":/img/dialog-ok.png")), "I don't care", ChoiceBox)
            Button3 = QPushButton(QIcon.fromTheme("process-stop", QIcon(":/img/process-stop.png")), "I want stop this", ChoiceBox)
            ChoiceBox.setCheckBox(CheckBox) # Envoie de la checkbox
            ChoiceBox.addButton(Button3, QMessageBox.NoRole) # Ajout du bouton
            ChoiceBox.addButton(Button2, QMessageBox.YesRole) # Ajout du bouton
            ChoiceBox.addButton(Button1, QMessageBox.ApplyRole) # Ajout du bouton
            Choice = ChoiceBox.exec()

            Configs.setValue("CheckSizeCheckbox", CheckBox.isChecked())

            ## Si on veut changer de répertoire
            if Choice == 2:
                ## Affichage de la fenêtre
                FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFolder"], str(TempValues.value(Folder)))
                OutputFolder = Path(FileDialogCustom.createWindow("Folder", "Open", None, Qt.Tool)[0])

                if not OutputFolder.is_dir() or OutputFolder == Path():
                    return True

                else:
                    TempValues.setValue(Folder, OutputFolder)


            ## Si on continue
            elif Choice == 1:
                return False

            ## Si on stoppe
            elif Choice == 0:
                return True


    #========================================================================
    def FolderTempCreate(self):
        """Fonction créant le dossier temporaire."""
        while True:
            # Création du dossier temporaire
            self.FolderTempWidget = QTemporaryDir(Configs.value("FolderParentTemp") + "/mkv-extractor-qt5-")

            # Suppression de l'auto suppression du dossier non adapté
            self.FolderTempWidget.setAutoRemove(False)

            # Si le dossier estvalide, on l'enregistre et arrête la boucle
            if self.FolderTempWidget.isValid():
                TempValues.setValue("FolderTemp", Path(self.FolderTempWidget.path())) # Dossier temporaire
                break


    #========================================================================
    def AboutMKVExtractorQt5(self):
        """Fenêtre à propos de MKVExtractorQt5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["AboutTitle"], self.Trad["AboutText"].format(app.applicationVersion(), "http://www.gnu.org/copyleft/gpl.html"), QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def HelpMKVExtractorQt5(self):
        """Fenêtre à propos de MKVExtractorQt5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["HelpTitle"], self.Trad["HelpText"], QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def TheyTalkAbout(self):
        """Fenêtre à propos de MKVExtractorQt5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["TheyTalkAboutTitle"], self.Trad["TheyTalkAboutText"], QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def MKVInfoGui(self):
        """Fonction ouvrant le fichier MKV avec le logiciel MKVInfo en mode détaché."""
        self.process.startDetached('{} "{}"'.format(Configs.value("Location/MKVInfo"), Configs.value("InputFile")))


    #========================================================================
    def MKVMergeGui(self):
        """Fonction ouvrant le fichier MKV avec le logiciel mmg (avec le bon nom de commande) en mode détaché."""
        self.process.startDetached('{} "{}"'.format(Configs.value("Location/MKVToolNix"), Configs.value("InputFile")))


    #========================================================================
    def MKVView(self):
        """Fonction ouvrant le fichier MKV avec le logiciel de lecture par défaut."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Configs.value("InputFile"))))


   #========================================================================
    def MKClean(self):
        """Fonction lançant MKClean sur le fichier MKV."""
        ### On crée automatiquement l'adresse de sorti
        if Configs.value("MKCleanRename") and (Configs.value("MKCleanSameFolder") or Configs.value("MKCleanThisFolder")):
            ## Utilisation du même dossier en entré et sorti
            if Configs.value("MKCleanSameFolder"):
                MKCleanTemp = Path("{}/Clean_{}".format(Configs.value("OutputFolder"), Configs.value("InputFile").name))

            ## Utilisation du dossier choisi
            elif Configs.value("MKCleanThisFolder"):
                MKCleanTemp = Path("{}/Clean_{}".format(Configs.value("MKCleanFolder"), Configs.value("InputFile").name))


        ### Fenêtre de sélection de sortie du fichier MKV
        else:
            ## Création de la fenêtre
            FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFileOut"], str(Configs.value("OutputFolder")), "Matroska file (*.mkv *.mks *.mka *.mk3d *.webm *.webmv *.webma)")
            MKCleanTemp = Path(FileDialogCustom.createWindow("File", "Save", None, Qt.Tool, FileName="Clean_{}".format(Configs.value("InputFile").name), AlreadyExistsTest=Configs.value("AlreadyExistsTest", False)))


        ### Arrêt de la fonction s'il n'y a pas de fichier de choisi
        if MKCleanTemp == Path():
            return


        ### Code à exécuter
        TempFiles = [MKCleanTemp] # Ajout du fichier de sortie dans le listing des fichiers
        TempValues.setValue("Command", ["MKClean", 'mkclean --optimize "{}" "{}"'.format(Configs.value("InputFile"), MKCleanTemp)]) # Code à exécuter


        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.process.start(TempValues.value("Command")[1])


    #========================================================================
    def MKValidator(self):
        """Fonction lançant MKValidator sur le fichier MKV."""
        ### Code à exécuter
        TempValues.setValue("Command", ["MKValidator", 'mkvalidator "{}"'.format(Configs.value("InputFile"))])


        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.ui.progressBar.setMaximum(0) # Mode pulsation de la barre de progression
        self.process.start(TempValues.value("Command")[1])


    #========================================================================
    def MKVConvert(self, File):
        """Fonction de conversion d'une vidéo en fichier MKV."""
        ### Proposition de conversion de la vidéo
        if not Configs.value("ConfirmConvert"):
            ## Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
            dialog = QMessageBox(QMessageBox.Warning, self.Trad["Convert1"], self.Trad["Convert2"], QMessageBox.NoButton, self)
            CheckBox = QCheckBox(self.Trad["Convert0"])
            dialog.setCheckBox(CheckBox)
            dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            dialog.setDefaultButton(QMessageBox.Ok)
            dialog.setIconPixmap(QPixmap(QIcon().fromTheme("dialog-warning", QIcon(":/img/dialog-warning.png")).pixmap(64)))
            Confirmation = dialog.exec_()

            ## Mise en mémoire de la case à cocher
            Configs.setValue("ConfirmConvert", CheckBox.isChecked())

            ## Arrêt de la fonction en cas de refus
            if Confirmation != 1024:
                return


        ### Choix du dossier de sortie
        FileDialogCustom = QFileDialogCustom(self, self.Trad["Convert6"], str(File.parent))
        OutputFile = Path(FileDialogCustom.createWindow("File", "Save", None, Qt.Tool, FileName="{}.mkv".format(File.stem), AlreadyExistsTest=Configs.value("AlreadyExistsTest", False)))


        ### En cas d'annulation
        if OutputFile == Path(): return


        ### Nettoyage graphique ici aussi afin de tout nettoyer avant la conversion pour un visuel plus joli
        ## Désactivation des différentes options qui pourraient être activées
        for widget in [self.ui.option_reencapsulate, self.ui.option_vobsub_srt, self.ui.option_audio]:
            widget.setChecked(False)
            widget.setEnabled(False)


        ## Désactivation des widgets
        for widget in [self.ui.mkv_info, self.ui.mkv_view, self.ui.mkv_mkvmerge, self.ui.mk_validator, self.ui.mk_clean, self.ui.mkv_execute_2]: widget.setEnabled(False)


        ## Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 0:
            self.ui.stackedMiddle.setCurrentIndex(0)

        while self.ui.mkv_tracks.rowCount() != 0:
            self.ui.mkv_tracks.removeRow(0)


        ## Suppression du titre
        self.ui.mkv_title.setText("")


        ### Mise à jour des varables
        WarningReply.clear() # Réinitialisation des retours de warning de mkvmerge
        TempFiles.clear()
        TempFiles.append(OutputFile) # Ajout du fichier dans la liste en cas d'arrêt
        TempValues.setValue("Command", ["FileToMKV", 'mkvmerge -o "{}" "{}"'.format(OutputFile, File)]) # Commande de conversion


        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.process.start(TempValues.value("Command")[1])


    #========================================================================
    def RemoveTempFiles(self):
        """Fonction supprimant les fichiers contenu dans la liste des fichiers temporaires."""
        ### Boucle supprimant les fichiers temporaires s'ils existent
        for Item in TempFiles:
            if Item.exists() and Item.is_file():
                Item.unlink()

        TempFiles.clear()


    #========================================================================
    def OutputFolder(self, OutputFolderTemp=None):
        """Fonction de sélection du dossier de sortie, est appelée via un clic ou via un déposer de dossier."""
        if OutputFolderTemp == Configs.value("OutputFolder"):
            return

        ### En cas de lancement via l'interface graphique
        if not OutputFolderTemp:
            ## Création et coche si besoin de la checkbox
            CheckBox = QCheckBox(self.Trad["SelectedFolder2"])
            CheckBox.setChecked(Configs.value("OutputSameFolder"))

            ## Affichage de la fenêtre
            FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFolder"], str(Configs.value("OutputFolder")))
            OutputFolderTemp = Path(FileDialogCustom.createWindow("Folder", "Open", CheckBox, Qt.Tool))

            ## Mise à jour de l'option
            Configs.setValue("OutputSameFolder", CheckBox.isChecked())


        ### Arrêt de la fonction si aucun fichier n'est sélectionné et qu'on n'utilise pas le même dossier de sorti
        if not OutputFolderTemp.is_dir() or (OutputFolderTemp == Path() and not Configs.value("OutputSameFolder")):
            return


        ### Suite de la fonction
        # Mise à jour de la variable du dossier de sorti
        Configs.setValue("OutputFolder", OutputFolderTemp)

        # Mis à jour du statustip de l'item de changement de dossier
        self.ui.output_folder.setStatusTip(self.Trad["SelectedFolder1"].format(OutputFolderTemp))

        # Envoie d'information en mode debug
        if Configs.value("DebugMode"):
            self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + str(OutputFolderTemp) + '</span>'), newline=True)


        ### Modifications graphiques
        # Cela n'a lieu que si un dossier et un fichier mkv sont choisis
        if TempValues.value("MKVLoaded") and MKVDicoSelect:
            self.ui.option_reencapsulate.setEnabled(True) # Déblocage de widget
            self.ui.mkv_execute.setEnabled(True) # Déblocage de widget
            self.ui.mkv_execute_2.setEnabled(True) # Déblocage de widget
            self.ui.option_audio.setEnabled(False) # Blocage de widget
            self.ui.option_vobsub_srt.setEnabled(False) # Blocage de widget

            for valeurs in MKVDicoSelect.values(): # Boucle sur la liste des lignes
                # Recherche la valeur audio dans les sous listes
                if valeurs[2] == "audio-x-generic" and QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable():
                    self.ui.option_audio.setEnabled(True)

                # Recherche la valeur vobsub dans les sous listes
                elif "sub" in valeurs[-1] and QFileInfo(Configs.value("Location/Qtesseract5").split(" -")[0]).isExecutable():
                    self.ui.option_vobsub_srt.setEnabled(True) # Déblocage de widget


    #========================================================================
    def InputFile(self, MKVLinkTemp=None):
        """Fonction de sélection du fichier d'entré."""
        ### Si aucun fichier n'est donné en argument
        if not MKVLinkTemp:
            # Création du widget à ajouter à la boite
            BigWidget = QWidget()
            BigLayout = QVBoxLayout()
            CheckBox1 = QCheckBox(self.Trad["SelectFileInCheckbox"], BigWidget)
            CheckBox1.setChecked(Configs.value("LastFile"))
            BigLayout.addWidget(CheckBox1)
            BigWidget.setLayout(BigLayout)

            # Affichage de la fenêtre
            FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFileIn"], str(Configs.value("InputFolder")), '{}(*.m4a *.mk3d *.mka *.mks *.mkv *.mp4 *.nut *.ogg *.ogm *.ogv *.webm *.webma *.webmv);; {}(*.mk3d *.mka *.mks *.mkv *.webm *.webma *.webmv);; {}(*.m4a *.mp4 *.nut *.ogg *.ogm *.ogv)'.format(self.Trad["AllFiles"], self.Trad["MatroskaFiles"], self.Trad["OtherFiles"]))
            MKVLinkTemp = Path(FileDialogCustom.createWindow("File", "Open", BigWidget, Qt.Tool))

            # Mise à jour de l'option
            Configs.setValue("LastFile", CheckBox1.isChecked())


        ### Arrêt de la fonction si le fichier n'existe pas
        if not MKVLinkTemp.is_file():
            return


        ### Si le fichier nécessite une conversion en MKV
        if MKVLinkTemp.suffix in (".mp4", ".m4a", ".nut", ".ogg", ".ogm", ".ogv"):
            self.MKVConvert(MKVLinkTemp) # Lancement de la conversion et la fonction sera relancée par WorkFinished


        ### Continuation de la fonction si un fichier est bien sélectionné
        else:
            # Mise à jour de variables
            Configs.setValue("InputFile", MKVLinkTemp)
            Configs.setValue("InputFolder", MKVLinkTemp.parent)

            # Envoie d'information quelque soit le mode de debug
            self.SetInfo(self.Trad["SelectedFile"].format('<span style=" color:#0000c0;">' + str(Configs.value("InputFile")) + '</span>'))

            # Mise à jour du statustip du menu d'ouverture d'un fichier MKV
            self.ui.input_file.setStatusTip(self.Trad["SelectedFile"].format(Configs.value("InputFile")))

            # Dans le cas de l'utilisation de l'option SameFolder qui permet d'utiliser le même dossier en sorti qu'en entré
            if Configs.value("OutputSameFolder"):
                self.OutputFolder(Configs.value("InputFolder"))

            # Envoie d'information en mode debug de l'adresse du dossier de sortie s'il existe
            elif Configs.value("OutputFolder") and Configs.value("DebugMode"):
                self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + Configs.value("OutputFolder") + '</span>'))

            # Chargement du contenu du fichier MKV
            self.TracksLoad()


    #========================================================================
    def ComboModif(self, x, value):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'utilisation des combobox du tableau."""
        ### Si x est une chaîne, c'est que ça traite un fichier AAC
        if isinstance(x, str):
            ## Récupération de la ligne
            x = int(x.split("-")[0])

            ## Mise à jour de variables
            if value != MKVDico[x][6]:
                MKVDico[x][6] = value
                if self.ui.mkv_tracks.item(x, 1).checkState():
                    MKVDicoSelect[x][6] = value


        ### Pour les autres combobox
        elif value != MKVDico[x][5]:
            ## Mise à jour de variables
            MKVDico[x][5] = value
            if self.ui.mkv_tracks.item(x, 1).checkState():
                MKVDicoSelect[x][5] = value


    #========================================================================
    def TracksLoad(self):
        """Fonction de listage et d'affichage des pistes contenues dans le fichier MKV."""
        ### Curseur de chargement
        self.setCursor(Qt.WaitCursor)


        ### Mise à jour des variables
        TempValues.setValue("MKVLoaded", True) # Fichier MKV chargé
        TempValues.setValue("AllTracks", False) # Mode sélection all
        TempValues.setValue("SuperBlockTemp", True) # Sert à bloquer les signaux du tableau (impossible d'utiliser blocksignals)
        x = 0 # Sert à indiquer les numéros de lignes
        self.ComboBoxes = {} # Dictionnaire listant les combobox
        MKVDico.clear() # Mise au propre du dictionnaire


        ### Désactivation des différentes options qui pourraient être activés
        self.ui.mkv_execute.setEnabled(False)
        for widget in [self.ui.option_reencapsulate, self.ui.option_vobsub_srt, self.ui.option_audio]:
            widget.setChecked(False) # Décoche les boutons
            widget.setEnabled(False) # Grise les widgets


        ### Activation des widgets qui attendaient un fichier MKV valide
        self.ui.mkv_view.setEnabled(True)

        if QFileInfo(Configs.value("Location/MKValidator").split(" -")[0]).isExecutable(): self.ui.mk_validator.setEnabled(True)

        if QFileInfo(Configs.value("Location/MKClean").split(" -")[0]).isExecutable(): self.ui.mk_clean.setEnabled(True)

        if QFileInfo(Configs.value("Location/MKVInfo").split(" -")[0]).isExecutable(): self.ui.mkv_info.setEnabled(True)

        if QFileInfo(Configs.value("Location/MKVToolNix").split(" -")[0]).isExecutable(): self.ui.mkv_mkvmerge.setEnabled(True)


        ### Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 0:
            self.ui.stackedMiddle.setCurrentIndex(0)

        while self.ui.mkv_tracks.rowCount() != 0:
            self.ui.mkv_tracks.removeRow(0)


        ### Arrêt de la fonction si le fichier contient des "
        if Configs.value("InputFile").match('*"*'):
            QMessageBox(3, self.Trad["ErrorQuoteTitle"], self.Trad["ErrorQuoteText"], QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()
            self.setCursor(Qt.ArrowCursor)
            return


        ### Récupération du retour de MKVMerge
        JsonMKV = ""

        for line in self.LittleProcess('mkvmerge -J "{}"'.format(Configs.value("InputFile"))): JsonMKV += line

        # Convertion du json en un dictionnaire
        JsonMKV = json.loads(JsonMKV)


        ### traitement des données de Json
        # Titre du fichier MKV
        if "title" in JsonMKV["container"]["properties"]:
            # Si le titre existe
            TempValues.setValue("TitleFile", JsonMKV["container"]["properties"]["title"])

        else:
            # Sinon on utilise le nom du fichier
            TempValues.setValue("TitleFile", Configs.value("InputFile").stem)

        # Envoie de la valeur titre
        self.ui.mkv_title.setText(TempValues.value("TitleFile"))

        # Récupération de la durée du fichier MKV
        if "duration" in JsonMKV["container"]["properties"]:
            # Passage de nanosecondes à secondes 10 puissance 9 => il se plante d'un 0 ?!...
            TempValues.setValue("DurationFile", int(JsonMKV["container"]["properties"]["duration"]/10E8))

        ### Retours d'information
        self.SetInfo(self.Trad["WorkMerge"], "800080", True, True)
        self.SetInfo(self.Trad["WorkCmd"].format("mkvmerge -J {}".format(Configs.value("InputFile"))))


        ### Boucle traitant les pistes du fichier MKV
        ## Renvoie un truc du genre : 0 {"codec": "RealVideo", "id": 0, "properties": {... }}...
        for Track in JsonMKV["tracks"]:
            ID = Track["id"] # Récupération de l'ID de la piste

            # Récupération du codec de la piste
            if "codec_id" in Track["properties"]:
                codec = Track["properties"]["codec_id"]

                if codec in CodecList:
                     codecInfo = CodecList[codec][1]
                     codec = CodecList[codec][0]

                elif "codec" in Track:
                    codecInfo = codec
                    codec = Track["codec"]

                else:
                    codecInfo = ""
                    code = codec

            elif "codec" in Track:
                codecInfo = ""
                codec = Track["codec"]

            else:
                codecInfo = ""
                codec = "Unknow"

            # Traitement des videos
            if Track["type"] == "video":
                # Mise à jour des variables
                TrackTypeName = self.Trad["Video"]
                icone = 'video-x-generic'

                # Récupération de l'info1
                if "track_name" in Track["properties"]:
                    info1 = Track["properties"]["track_name"]

                elif "display_dimensions" in Track["properties"]:
                    info1 = Track["properties"]["display_dimensions"]

                elif "pixel_dimensions" in Track["properties"]:
                    info1 = Track["properties"]["pixel_dimensions"]

                else:
                    info1 = ""


                # Liste normale des fps
                ComboItems = ["23.976fps", "25.000fps", "30.000fps"]

                # Récupération du fps de la piste
                if "default_duration" in Track["properties"]:
                    infoTemp = Track["properties"]["default_duration"]

                    if infoTemp in [40000000, 40001000]:
                        info2 = "25.000fps"

                    elif infoTemp == 41708000:
                        info2 = "23.976fps"

                    elif infoTemp == 33333000:
                        info2 = "30.000fps"

                    else:
                        cal = "%.3f" % float(1000000000 / infoTemp)
                        info2 = "{}fps".format(cal)
                        ComboItems.append(str(info2)) # Ajout de la valeur inconnue
                        ComboItems.sort()

                # Cas spécifique où l'info est manquante
                else:
                    info2 = ""

                # Texte à afficher
                Text = self.Trad["TrackVideo"]


            # Traitement des audios
            elif Track["type"] in ["audio", "subtitles"]:
                # Variables spécifiques à l'audio
                if Track["type"] == "audio":
                    TrackTypeName = self.Trad["Audio"]
                    icone = 'audio-x-generic'

                    # Récupération de l'info1
                    if "track_name" in Track["properties"]:
                        info1 = Track["properties"]["track_name"]

                    elif "audio_sampling_frequency" in Track["properties"]:
                        info1 = Track["properties"]["audio_sampling_frequency"]

                    else:
                        info1 = ""

                # Variables spécifiques aux sous titres
                else:
                    # Mise à jour des variables
                    TrackTypeName = self.Trad["Subtitles"]
                    icone = 'text-x-generic'

                    # Récupération de l'info1
                    if "track_name" in Track["properties"]:
                        info1 = Track["properties"]["track_name"]

                    else:
                        info1 = ""

                # Variables communes
                # Récupération de la langue
                if "language" in Track["properties"]:
                    info2 = Track["properties"]["language"]

                else:
                    info2 = "und"

                # Item servant à remplir la combobox
                ComboItems = MKVLanguages

                # Texte à afficher
                Text = self.Trad["TrackAudio"]


            # Création, remplissage et connexion d'une combobox qui est envoyée dans une nouvelle ligne du tableau
            self.ui.mkv_tracks.insertRow(x)
            self.ComboBoxes[x] = QComboBox()
            self.ui.mkv_tracks.setCellWidget(x, 4, self.ComboBoxes[x])
            self.ComboBoxes[x].addItems(ComboItems)
            self.ComboBoxes[x].currentIndexChanged['QString'].connect(partial(self.ComboModif, x))

            # Envoie de l'info
            self.ComboBoxes[x].setStatusTip(Text)

            # Ajout de la piste au dico
            MKVDico[x] = [ID, "Track", icone, "unknown", info1, info2, codec]

            # Envoie des informations dans le tableaux
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem(ID)) # Envoie de l'ID
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem("")) # Texte bidon permettant d'envoyer la checkbox
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
            self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID1"].format(ID)) # StatusTip
            self.ui.mkv_tracks.setItem(x, 2, QTableWidgetItem(QIcon.fromTheme(icone, QIcon(":/img/{}.png".format(icone))), "")) # Envoie de l'icône
            self.ui.mkv_tracks.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
            self.ui.mkv_tracks.item(x, 2).setStatusTip(self.Trad["TrackType"].format(TrackTypeName)) # StatusTip
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1)) # Envoie de l'information
            self.ui.mkv_tracks.item(x, 3).setStatusTip(self.Trad["TrackRename"]) # StatusTip

            # Sélection de la valeur de la combobox
            self.ComboBoxes[x].setCurrentIndex(self.ComboBoxes[x].findText(str(info2)))

            # Dans le cas de codec AAC
            if "aac" in codec:
                # Création d'une combobox, remplissage, mise à jour du statustip, connexion, sélection de la valeur et envoie de la combobox dans le tableau
                name = "{}-aac".format(x)
                self.ComboBoxes[name] = QComboBox()
                self.ui.mkv_tracks.setCellWidget(x, 5, self.ComboBoxes[name])
                self.ComboBoxes[name].addItems(['aac', 'aac sbr'])
                self.ComboBoxes[name].setStatusTip(self.Trad["TrackAac"])
                self.ComboBoxes[name].currentIndexChanged['QString'].connect(partial(self.ComboModif, name))
                self.ComboBoxes[name].setCurrentIndex(self.ComboBoxes[name].findText(codec))

            # pour les autres audios
            else:
                self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem(codec))
                self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.item(x, 5).setStatusTip(codecInfo)

            # Incrémentation du numéro de ligne
            x += 1


        ### Boucle traitant les chapitrages
        ## Renvoie un truc du genre : 0 "num_entries": 15
        for Chapter in JsonMKV["chapters"]:
            # Mise à jour des variables
            info1 = self.Trad["TrackChapters"]
            info2 = "{} {}".format(Chapter["num_entries"], info1)

            # Mise à jour du dictionnaire des pistes du fichier MKV
            MKVDico[x] = ["NoID", "Chapters", "x-office-address-book", "document-preview", info1, info2, "Chapters"]

            # Création du bouton de visualisation
            Button = QPushButton(QIcon.fromTheme("x-office-address-book", QIcon(":/img/x-office-address-book.png")), "")
            Button.setFlat(True)
            Button.clicked.connect(partial(self.TrackView, x))
            Button.setStatusTip(self.Trad["TrackType2"].format(info1))

            # Envoie des informations dans le tableaux
            self.ui.mkv_tracks.insertRow(x) # Création de ligne
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem("chapters")) # Remplissage des cellules
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem(""))
            self.ui.mkv_tracks.setCellWidget(x, 2, Button) # Envoie du bouton
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1))
            self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2))
            self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem("text"))
            self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID3"].format(info1)) # Envoie des StatusTip
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
            self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            # Incrémentation du numéro de ligne
            x += 1


        ### Boucle traitant les tags
        ## Renvoie un truc du genre : 0 "num_entries": 15
        for GlobalTag in JsonMKV["global_tags"]:
            # Mise à jour des variables
            info1 = self.Trad["TrackTags"]
            info2 = "{} {}".format(GlobalTag["num_entries"], info1)

            # Mise à jour du dictionnaire des pistes du fichier MKV
            MKVDico[x] = ["NoID", "Global tags", "text-html", "document-preview", info1, info2, "Tags"]

            # Création du bouton de visualisation
            Button = QPushButton(QIcon.fromTheme("text-html", QIcon(":/img/text-html.png")), "")
            Button.setFlat(True)
            Button.clicked.connect(partial(self.TrackView, x))
            Button.setStatusTip(self.Trad["TrackType2"].format(info1))

            # Envoie des informations dans le tableaux
            self.ui.mkv_tracks.insertRow(x) # Création de ligne
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem("tags")) # Remplissage des cellules
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem(""))
            self.ui.mkv_tracks.setCellWidget(x, 2, Button) # Envoie du bouton
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1))
            self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2))
            self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem("xml"))
            self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID3"].format(info1)) # Envoie des StatusTip
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
            self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            # Incrémentation du numéro de ligne
            x += 1


        ### Boucle traitant les fichiers joints du fichier MKV
        ## Renvoie un truc du genre : 0 "content_type": "text/html", "description": "", "file_name": "index.php"...
        for Attachment in JsonMKV["attachments"]:
            # mise à jour des variables
            ID = Attachment["id"]
            Item1 = ID
            info2 = "{} octets".format(Attachment["size"])
            typecodec = Attachment["content_type"]
            typetrack = typecodec.split("/")[0]

            #* Utiliser les 2 infos ? verifier qu'ils ne sont pas vide ?

            # Récupération de l'information 1
            if "description" in Attachment and Attachment["description"]:
                info1 = Attachment["description"]

            elif "file_name" in Attachment:
                info1 = Attachment["file_name"]

            else:
                info1 = "No info"

            # Traitement des codecs
            if "/" in typecodec:
                typetrack = typecodec.split("/")[0]
                codec = typecodec.split("/")[1]

            else:
                typetrack = typecodec
                codec = typecodec

            # Mise à jour du codec pour plus de lisibilité
            if codec == "x-truetype-font":
                codec = "font"

            elif codec == "vnd.ms-opentype":
                codec = "font OpenType"

            elif codec == "x-msdos-program":
                codec = "application msdos"

            elif codec == "plain":
                codec = "text"

            elif codec in ["ogg", "ogm"]:
                typetrack = "audio" # Ils sont reconnus en tant qu'applications

            elif codec == "x-flac":
                codec = "flac"

            elif codec == "x-flv":
                codec = "flv"

            elif codec == "x-ms-bmp":
                codec = "bmp"

            # traitement des statustip
            StatusTip1 = self.Trad["TrackID2"].format(ID)
            StatusTip2 = self.Trad["TrackTypeAttachment"].format(typetrack)
            StatusTip3 = self.Trad["TrackAttachment"]

            # Icône du type de piste
            machin = QMimeDatabase().mimeTypeForName(typecodec)
            icone = QIcon().fromTheme(QMimeType(machin).iconName(), QIcon().fromTheme(QMimeType(machin).genericIconName())).name()

            # Dans le cas où l'icône n'a pas été déterminée
            if not icone:
                if "application" in typetrack:
                    icone = "system-run"

                elif typetrack == "image":
                    icone = "image-x-generic"

                elif typetrack == "text":
                    icone = "accessories-text-editor"

                elif typetrack in ["media", "video", "audio"]:
                    icone = "applications-multimedia"

                elif typetrack == "web":
                    icone = "applications-internet"

                else:
                    icone = "unknown"

            # Mise à jour du dictionnaire des pistes du fichier MKV
            MKVDico[x] = [ID, "Attachment", icone, "document-preview", info1, info2, codec]

            # Création du bouton de visualisation
            Button = QPushButton(QIcon.fromTheme(icone, QIcon(":/img/{}.png".format(icone))), "")
            Button.setFlat(True)
            Button.clicked.connect(partial(self.TrackView, x))
            Button.setStatusTip(StatusTip2)

            # Envoie des informations dans le tableaux
            self.ui.mkv_tracks.insertRow(x) # Création de ligne
            self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem(Item1)) # Remplissage des cellules
            self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem(""))
            self.ui.mkv_tracks.setCellWidget(x, 2, Button) # Envoie du bouton
            self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1))
            self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2))
            self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem(codec))
            self.ui.mkv_tracks.item(x, 1).setStatusTip(StatusTip1) # Envoie des StatusTip
            self.ui.mkv_tracks.item(x, 3).setStatusTip(StatusTip3)
            self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
            self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
            self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

            # Incrémentation du numéro de ligne
            x += 1


        ### Retours d'information, déblocage, curseur normal
        self.SetInfo(self.Trad["WorkMerge"], "800080", True, False)
        TempValues.setValue("SuperBlockTemp", False) # Variable servant à bloquer les signaux du tableau (impossible autrement)
        self.setCursor(Qt.ArrowCursor)


    #========================================================================
    def TrackView(self, x):
        """Fonction d'affichage des fichiers joins."""
        ### Dans le cas d'un fichier de chapitrage
        if MKVDico[x][1] == "Chapters":
            ## Fichier de sortie
            TempValues.setValue("ChaptersFile", Path(TempValues.value("FolderTemp"), "chapters.txt"))

            ## Extraction si le fichier n'existe pas
            if not TempValues.value("ChaptersFile").exists():
                with TempValues.value("ChaptersFile").open('w') as ChaptersFile:
                    for line in self.LittleProcess('mkvextract chapters "{}" -s'.format(Configs.value("InputFile"))):
                        ChaptersFile.write(line+'\n')

            ## Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(TempValues.value("ChaptersFile"))))


        ### Dans le cas de global tags
        elif MKVDico[x][1] == "Global tags":
            ## Fichier de sortie
            TempValues.setValue("TagsFile", Path(TempValues.value("FolderTemp"), "tags.xml"))

            ## Extraction si le fichier n'existe pas
            if not TempValues.value("TagsFile").exists():
                with TempValues.value("TagsFile").open('w') as TagsFile:
                    for line in self.LittleProcess('mkvextract tags "{}"'.format(Configs.value("InputFile"))):
                        TagsFile.write(line+'\n')

            ## Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(TempValues.value("TagsFile"))))


        ### Dans le cas de fichier joint
        elif MKVDico[x][1] == "Attachment":
            ## Teste la place disponible avant d'extraire
            FileSize = int(MKVDico[x][5].split(" ")[0])
            FreeSpaceDisk = disk_usage(str(TempValues.value("FolderTemp"))).free

            ## Teste de la place restante
            if self.CheckSize("FolderTemp", FileSize, FreeSpaceDisk, self.Trad["ErrorSizeAttachement"]): return

            ## Fichier de sortie
            fichier = Path(TempValues.value("FolderTemp"), 'attachement_{0[0]}_{0[4]}'.format(MKVDico[x]))

            ## Extraction si le fichier n'existe pas
            if not fichier.exists():
                self.LittleProcess('mkvextract attachments "{}" {}:"{}"'.format(Configs.value("InputFile"), MKVDico[x][0], fichier))

            ## Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(fichier)))


    #========================================================================
    def TrackModif(self, info):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'édition des textes."""
        ### Blocage de la fonction pendant le chargement des pistes
        if TempValues.value("SuperBlockTemp"): return


        ### Récupération de la cellule modifiée
        x, y = self.ui.mkv_tracks.row(info), self.ui.mkv_tracks.column(info)


        ### Dans le cas de la modification d'une checkbox
        if y == 1:
            ## Mise au propre du tableau
            MKVDicoSelect.clear() # Mise au propre du dictionnaire
            for x in range(self.ui.mkv_tracks.rowCount()): # Boucle traitant toutes les lignes du tableau
                if self.ui.mkv_tracks.item(x, 1).checkState(): # Teste si la ligne est cochée
                    MKVDicoSelect[x] = MKVDico[x] # mise à jour de la liste des pistes cochées

            ## Blocage des boutons par defaut
            for widget in (self.ui.mkv_execute, self.ui.mkv_execute_2, self.ui.option_audio, self.ui.option_vobsub_srt, self.ui.option_reencapsulate, self.BDSup2Sub):
                widget.setEnabled(False)

            ## Déblocage des options si besoin
            if MKVDicoSelect and Configs.value("OutputFolder"):
                # Déblocages des boutons
                for widget in (self.ui.mkv_execute, self.ui.mkv_execute_2, self.ui.option_reencapsulate):
                    widget.setEnabled(True)

                # Boucle sur la liste des lignes
                for valeurs in MKVDicoSelect.values():
                    # Recherche la valeur audio dans les sous listes
                    if valeurs[2] == "audio-x-generic" and QFileInfo(Configs.value("Location/FFMpeg").split(" -")[0]).isExecutable():
                        self.ui.option_audio.setEnabled(True)

                    # Recherche la valeur vobsub dans les sous listes
                    elif "sub" in valeurs[-1] and QFileInfo(Configs.value("Location/Qtesseract5").split(" -")[0]).isExecutable():
                        self.ui.option_vobsub_srt.setEnabled(True)

                    # Recherche la valeur vobsub dans les sous listes
                    elif "sup" in valeurs[-1] and QFileInfo(Configs.value("Location/BDSup2Sub").split(" -")[0]).isExecutable():
                        self.BDSup2Sub.setEnabled(True)

            ## Décoche les boutons s'ils sont grisés
            for widget in [self.ui.option_vobsub_srt, self.ui.option_reencapsulate, self.ui.option_audio]:
                if not widget.isEnabled():
                    widget.setChecked(False)


        ### Dans le cas d'une modification de texte
        else:
            ## Mise à jour du texte dans le dico des pistes
            MKVDico[x][y] = self.ui.mkv_tracks.item(x, y).text()

            ## Mise à jour du texte dans le dico des pistes sélectionnées si la ligne est sélectionnée
            if self.ui.mkv_tracks.item(x, 1).checkState():
                MKVDicoSelect[x][y] = MKVDico[x][y]


    #========================================================================
    def TrackSelectAll(self, Value):
        """Fonction (dé)cochant toutes les pistes avec un clic sur le header."""
        ### Ne traiter que la colonne des coches
        if Value == 1:
            ## Dans le cas où il faut tout cocher
            if not TempValues.value("AllTracks"):
                TempValues.setValue("AllTracks", True)

                # Boucle traitant toutes les lignes du tableau
                for x in range(self.ui.mkv_tracks.rowCount()):
                    self.ui.mkv_tracks.item(x, 1).setCheckState(2)

            ## Dans le cas où il faut tout décocher
            else:
                TempValues.setValue("AllTracks", False)

                # Boucle traitant toutes les lignes du tableau
                for x in range(self.ui.mkv_tracks.rowCount()):
                    self.ui.mkv_tracks.item(x, 1).setCheckState(0)


    #========================================================================
    def CommandCreate(self):
        """Fonction créant toutes les commandes : mkvextractor, ffmpeg, mkvmerge..."""
        ### Teste de la place restante
        FileSize = Path(Configs.value("InputFile")).stat().st_size
        FreeSpaceDisk = disk_usage(str(Configs.value("OutputFolder"))).free

        if self.CheckSize("OutputFolder", FileSize, FreeSpaceDisk, self.Trad["ErrorSize"]): return


        ### Mise au propre et initialisation de variables
        CommandList.clear() # Liste des commandes à exécuter à la suite
        TempFiles.clear() # Fichiers temporaires à effacer en cas d'arrêt
        SubConvert = []
        mkvextract_merge = ""
        mkvextract_track = "" # Commande d'extraction des pistes normales
        mkvextract_joint = "" # Commande d'extraction des fichiers joints
        mkvextract_chap = "" # Commande d'extraction des chapitres
        mkvextract_tag = "" # Commande d'extraction des tags
        dts_ffmpeg = "" # Commande de conversion DTS vers AC3
        mkvmerge = "" # Commande de réencapsulage
        SubToRemove = [] # Liste pour ne pas ouvrir les idx convertis


        ### Si on veut uniquement ré-encapsuler sans rien d'autre, on affiche un message conseillant d'utiliser mmg
        if TempValues.value("Reencapsulate") and not TempValues.value("AudioConvert") and not TempValues.value("VobsubToSrt") and not TempValues.value("SubtitlesOpen"):
            if not Configs.value("MMGorMEQCheckbox"):
                ### Création de la fenêtre
                UseMMG = QMessageBox(4, self.Trad["UseMMGTitle"], self.Trad["UseMMGText"], QMessageBox.Cancel, self, Qt.WindowSystemMenuHint)
                UseMMG.setWindowFlags(Qt.WindowTitleHint | Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.CustomizeWindowHint) # Enlève le bouton de fermeture de la fenêtre

                # Création des widgets à y mettre
                CheckBox = QCheckBox(self.Trad["Convert0"], UseMMG) # Création de la checkbox
                MMG = QPushButton(QIcon.fromTheme("mkvmerge", QIcon(":/img/mkvmerge.png")), "MKV Merge Gui", UseMMG) # Création du bouton MKV Merge Gui
                MEQ = QPushButton(QIcon.fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")), "MKV Extracor Qt 5", UseMMG) # Création du bouton MKV Extracor Qt

                # Remplissage de la fenêtre
                UseMMG.setCheckBox(CheckBox) # Envoie de la checkbox
                UseMMG.addButton(MMG, QMessageBox.YesRole) # Ajout du bouton
                UseMMG.addButton(MEQ, QMessageBox.NoRole) # Ajout du bouton
                UseMMG.setDefaultButton(MEQ) # Bouton par défaut : MKV Extracor Qt

                # Lancement de la fenêtre
                UseMMG.exec() # Message d'information

                # Mise à jour de la variable
                Configs.setValue("MMGorMEQCheckbox", CheckBox.isChecked())

                # Mise à jour de la variable du logiciel à utiliser
                if UseMMG.buttonRole(UseMMG.clickedButton()) == 5:
                    Configs.setValue("MMGorMEQ", "MMG")

                elif UseMMG.buttonRole(UseMMG.clickedButton()) == 6:
                    Configs.setValue("MMGorMEQ", "MEQ")

                else:
                    return

            # Si on veut utiliser MMG, on arrête là
            if Configs.value("MMGorMEQ") == "MMG":
                self.MKVMergeGui()
                return


        ### Boucle traitant les pistes une à une
        for Select in MKVDicoSelect.values():
            # Select[0] : ID
            # Select[1] : Type de piste : Track, Attachment, Chapters, Global
            # Select[2] : Icône
            # Select[3] : Icône de visualisation
            # Select[4] : Nom de la piste
            # Select[5] : Info : fps, langue...
            # Select[6] : Info : codec

            ## Traitement des pistes vidéos, mise à jour de commandes
            if Select[2] == "video-x-generic":
                TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_video_{0[4]}.mkv".format(Select)))
                mkvextract_track += '{0[0]}:"{1}/{0[0]}_video_{0[4]}.mkv" '.format(Select, Configs.value("OutputFolder"))
                mkvmerge += '--track-name "0:{0[4]}" --default-duration "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_video_{0[4]}.mkv" '.format(Select, Configs.value("OutputFolder"))
                mkvextract_merge += '--track-name "0:{0[4]}" --default-duration "0:{0[5]}" --compression "0:none" '.format(Select)


            ## Traitement des pistes audios
            elif Select[2] == "audio-x-generic":
                # Nom du fichier de sortie
                File = "{0}/{1[0]}_audio_{1[4]}.{2}".format(Configs.value("OutputFolder"), Select, Select[6])

                # Ajout du fichier de sortie dans la liste temporaire
                TempFiles.append(Path(File))

                # En cas de modification audio
                if TempValues.value("AudioConvert") and (TempValues.value("AudioBoost") != "NoChange" or TempValues.value("AudioStereo") or TempValues.value("AudioQuality", "NoChange") != "NoChange" or Configs.value("AudioToAc3")):
                    # Indique la piste audio
                    dts_ffmpeg += '-vn -map 0:{} '.format(Select[0])

                    # En cas de boost
                    if TempValues.value("AudioBoost") != "NoChange": dts_ffmpeg += '-af volume={} '.format(TempValues.value("AudioBoost"))

                    # En cas de passage en stéréo
                    if TempValues.value("AudioStereo"): dts_ffmpeg += '-ac 2 '

                    # En cas de modification de qualité
                    if TempValues.value("AudioQuality", "NoChange") != "NoChange": dts_ffmpeg += '-ab {0}k '.format(TempValues.value("AudioQuality", 128))

                    # En cas de passage en ac3
                    if Configs.value("AudioToAc3"):
                        File = "{0}/{1[0]}_audio_{1[4]}.ac3".format(Configs.value("OutputFolder"), Select)
                        dts_ffmpeg += '-f ac3 '

                    # Fichier de sortie
                    dts_ffmpeg += '"{}" '.format(File)

                    # Ajout du fichier de sortie dans la liste temporaire
                    TempFiles.append(Path(File))

                    # Ajout du fichier de sortie dans le futur fichier mkv
                    if File[-3:] == "aac":
                        # En cas de aac sbr
                        if Select[6] == "aac sbr":
                            mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:0" --compression "0:none" "{1}" '.format(Select, File)
                            mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:0" --compression "0:none" '.format(Select)
                        # En cas de aac
                        else:
                            mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:1" --compression "0:none" "{1}" '.format(Select, File)
                            mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:1" --compression "0:none" '.format(Select)

                    else:
                        # Pour les autres audio
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}" '.format(Select, File)
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)


                # Si pas de modification audio
                else:
                    mkvextract_track += '{0[0]}:"{1}" '.format(Select, File)

                    # Dans le cas où il faut ré-encapsuler des fichiers AAC, il faut préciser si sbr ou non
                    if "aac" in Select[6]:
                        if Select[6] == "aac sbr":
                            mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:0" --compression "0:none" "{1}" '.format(Select, File)
                            mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:0" --compression "0:none" '.format(Select)
                        else:
                            mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:1" --compression "0:none" "{1}" '.format(Select, File)
                            mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:1" --compression "0:none" '.format(Select)

                    # Dans le cas où il n'y a pas de fichier aac
                    else:
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}" '.format(Select, File)
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)


            ## Traitement des pistes sous titres
            elif Select[2] == "text-x-generic":
                # Dans le cas de sous titres de fichiers sub
                if Select[6] == "sub":
                    TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_subtitles_{0[4]}.idx".format(Select)))
                    TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_subtitles_{0[4]}.sub".format(Select)))
                    mkvextract_track += '{0[0]}:"{1}/{0[0]}_subtitles_{0[4]}.idx" '.format(Select, Configs.value("OutputFolder"))

                    # Dans le cas d'un conversion SUB => AC3, maj de commandes
                    if TempValues.value("VobsubToSrt"):
                        TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_subtitles_{0[4]}.srt".format(Select)))
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_subtitles_{0[4]}.srt" '.format(Select, Configs.value("OutputFolder"))
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)

                        # Différence de nom entre la langue de tesseract et celle de mkvalidator
                        if Select[5] == "fre":
                            Select[5] = "fra"

                        SubConvert.append([Select[0], Select[4], Select[5]])

                    # Dans le cas ou il n'y a pas de conversion, maj de commande
                    else:
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_subtitles_{0[4]}.idx" '.format(Select, Configs.value("OutputFolder"))
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)


                # Dans le cas de sous titres autre que de type sub, maj de commandes
                else:
                    mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_subtitles_{0[4]}.{0[6]}" '.format(Select, Configs.value("OutputFolder"))
                    mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)
                    TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_subtitles_{0[4]}.{0[6]}".format(Select)))
                    mkvextract_track += '{0[0]}:"{1}/{0[0]}_subtitles_{0[4]}.{0[6]}" '.format(Select, Configs.value("OutputFolder"))


            ## Traitement des pistes chapitrage, maj de commandes
            elif Select[2] == "x-office-address-book":
                TempFiles.append(Path(Configs.value("OutputFolder"), "chapters.txt"))
                mkvmerge += '--chapters "{}/chapters.txt" '.format(Configs.value("OutputFolder"))
                mkvextract_chap = 'mkvextract chapters "{}" -s '.format(Configs.value("InputFile"))
                TempValues.setValue("ChaptersFile", Path(Configs.value("OutputFolder"), "chapters.txt"))


            ## Traitement des pistes de tags, maj de commandes
            elif Select[2] == "text-html":
                TempFiles.append(Path(Configs.value("OutputFolder"), "tags.xml"))
                mkvmerge += '--global-tags "{}/tags.xml" '.format(Configs.value("OutputFolder"))
                mkvextract_tag = 'mkvextract tags "{}" '.format(Configs.value("InputFile"))
                TempValues.setValue("TagsFile", Path(Configs.value("OutputFolder"), "tags.xml"))


            ## Traitement des pistes jointes, maj de commandes
            else:
                mkvextract_joint += '{0[0]}:"{1}/{0[0]}_{0[4]}" '.format(Select, Configs.value("OutputFolder"))
                TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_{0[4]}".format(Select)))
                mkvmerge += '--attachment-name "{0[4]}" --attach-file "{1}/{0[0]}_{0[4]}" '.format(Select, Configs.value("OutputFolder"))


        ### Ajout de la commande mkvextract_track à la liste des commandes à exécuter
        if mkvextract_track:
            CommandList.append(["MKVExtract Tracks", 'mkvextract tracks "{}" {}'.format(Configs.value("InputFile"), mkvextract_track)])


        ### Ajout de la commande mkvextract_tag à la liste des commandes à exécuter
        if mkvextract_tag:
            if TempValues.value("TagsFile").exists():
                TempValues.value("TagsFile").unlink()
            CommandList.append(["MKVExtract Tags", mkvextract_tag])


        ### Ajout de la commande mkvextract_chap à la liste des commandes à exécuter
        if mkvextract_chap:
            if TempValues.value("ChaptersFile").exists():
                TempValues.value("ChaptersFile").unlink()
            CommandList.append(["MKVExtract Chapters", mkvextract_chap])


        ### Ajout de la commande mkvextract_joint à la liste des commandes à exécuter
        if mkvextract_joint:
            CommandList.append(["MKVExtract Attachments", 'mkvextract attachments "{}" {}'.format(Configs.value("InputFile"), mkvextract_joint)])


        ### Ajout de la commande mkvextract_joint à la liste des commandes à exécuter
        if dts_ffmpeg:
            if Configs.value("FFMpeg"):
                ffconv = "ffmpeg"

            else:
                ffconv = "avconv"

            CommandList.append([ffconv, '{} -y -i "{}" {}'.format(ffconv, Configs.value("InputFile"), dts_ffmpeg)])


        ### Ajout des commandes de conversion des vobsub en srt
        if TempValues.value("VobsubToSrt"):
            ## Pour chaque fichier à convertir
            for SubInfo in SubConvert:
                IDX = Path('{}/{}_subtitles_{}.idx'.format(Configs.value("OutputFolder"), SubInfo[0], SubInfo[1]))
                SRT = IDX.with_suffix(".srt")
                SubToRemove.append(IDX)

                if TempValues.value("Qtesseract5"):
                    CommandList.append(["Qtesseract5", 'qtesseract5 -g 2 -v 1 -r -c 0 -w -r -t {} -l "{}" "{}" "{}" '.format(QThread.idealThreadCount(), SubInfo[2], IDX, SRT)])

                else:
                    CommandList.append(["Qtesseract5", 'qtesseract5 -g 1 -v 1 -r -c 0 -w -r -t {} -l "{}" "{}" "{}" '.format(QThread.idealThreadCount(), SubInfo[2], IDX, SRT)])


        ### Ajout de la commande mkvmerge à la liste des commandes à exécuter
        if TempValues.value("Reencapsulate"):
            ## Si l'option de renommage automatique n'est pas utilisée
            if not Configs.value("RemuxRename"):
                # Fenêtre de sélection de sortie du fichier mkv
                CheckBox = QCheckBox(self.Trad["RemuxRenameCheckBox"])

                FileDialogCustom = QFileDialogCustom(self, self.Trad["RemuxRenameTitle"], str(Configs.value("OutputFolder")), "{}(*.mka *.mks *.mkv *.mk3d *.webm *.webmv *.webma)".format(self.Trad["MatroskaFiles"]))
                TempValues.setValue("OutputFile", Path(FileDialogCustom.createWindow("File", "Save", CheckBox, Qt.Tool, "MEG_{}".format(Configs.value("InputFile").name), AlreadyExistsTest=Configs.value("AlreadyExistsTest", False))))
                Configs.setValue("AlreadyExistsTest", CheckBox.isChecked())

                # Mise à jour de la variable
                Configs.setValue("RemuxRename", CheckBox.isChecked())

                # Arrêt de la fonction si aucun fichier n'est choisi => utilise . si négatif
                if TempValues.value("OutputFile") == Path(): return

            else:
                TempValues.setValue("OutputFile", Path(Configs.value("OutputFolder"), "MEG_{}".format(Configs.value("InputFile").name)))

            ## Ajout du fichier mkv à la liste des fichiers
            TempFiles.append(TempValues.value("OutputFile"))

            ## Dans le cas où il faut ouvrir les fichiers srt avant leur encapsulage
            if TempValues.value("SubtitlesOpen"):
                SubtitlesFiles.clear()

                # Ajout des fichiers sous titres
                for Item in TempFiles:
                    if Item.suffix in (".srt", ".ssa", ".ass", ".idx"):
                        SubtitlesFiles.append(Item)

                # Suppression des fichiers idx qui ont été convertis
                if SubToRemove:
                    for Item in SubToRemove: SubtitlesFiles.remove(Item)

                # Echo bidon pour être sur que la commande se termine bien
                if SubtitlesFiles:
                    CommandList.append(["Open Subtitles", "echo"])


            ## Récupération du titre du fichier dans le cas où il faut réencapsuler,
            TempValues.setValue("TitleFile", self.ui.mkv_title.text())

            ## Si le titre est vide, il plante mkvmerge
            if TempValues.value("TitleFile"):
                CommandList.append(["MKVMerge", 'mkvmerge -o "{}" --title "{}" {}'.format(TempValues.value("OutputFile"), TempValues.value("TitleFile"), mkvmerge)])
                mkvextract_merge = 'mkvmerge -o "{}" --title "{}" {}'.format(TempValues.value("OutputFile"), TempValues.value("TitleFile"), mkvextract_merge)

            else:
                CommandList.append(["MKVMerge", 'mkvmerge -o "{}" {}'.format(TempValues.value("OutputFile"), mkvmerge)])
                mkvextract_merge = 'mkvmerge -o "{}" --title "{}" {}'.format(TempValues.value("OutputFile"), Configs.value("InputFile").name, mkvextract_merge)


        ### Modifications graphiques
        self.WorkInProgress(True) # Blocage des widgets


        ### Code à exécuter
        TempValues.setValue("Command", CommandList.pop(0)) # Récupération de la 1ere commande


        ### Envoie de textes
        self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande
        self.process.start(TempValues.value("Command")[1])


    #========================================================================
    def WorkInProgress(self, value):
        """Fonction de modifications graphiques en fonction d'un travail en cours ou non."""
        ### Dans le cas d'un lancement de travail
        if value:
            ## Modifications graphiques
            self.setCursor(Qt.WaitCursor) # Curseur de chargement
            self.ui.mkv_execute.hide() # Cache le bouton exécuter
            self.ui.mkv_execute_2.setEnabled(False) # Grise le bouton exécuter
            self.ui.mkv_stop.show() # Affiche le bouton arrêter

            qtesseract5 = False
            for Command in CommandList:
                if "Qtesseract5" in Command: qtesseract5 = True

            if len(CommandList) > 1 or qtesseract5:
                self.ui.mkv_pause.show() # Affiche le bouton pause

            for widget in (self.ui.menubar, self.ui.tracks_bloc):
                widget.setEnabled(False)  # Blocage de widget


        ### Dans le cas où le travail vient de se terminer (bien ou mal)
        else:
            ## Modifications graphiques
            self.ui.mkv_execute.show() # Affiche le bouton exécuter
            self.ui.mkv_execute_2.setEnabled(True) # Dégrise le bouton exécuter
            self.ui.mkv_stop.hide() # Cache le bouton arrêter
            self.ui.mkv_pause.hide() # Cache le bouton pause

            if self.ui.progressBar.format() != "%p %":
                self.ui.progressBar.setFormat("%p %") # Réinitialisation du bon formatage de la barre de progression

            if self.ui.progressBar.maximum() != 100:
                self.ui.progressBar.setMaximum(100) # Réinitialisation de la valeur maximale de la barre de progression

            if self.ui.stackedMiddle.currentIndex() != 0:
                self.ui.stackedMiddle.setCurrentIndex(0) # Ré-affiche le tableau des pistes si ce n'est plus lui qui est affiché

            for widget in (self.ui.menubar, self.ui.tracks_bloc):
                widget.setEnabled(True) # Blocage de widget

            self.setCursor(Qt.ArrowCursor) # Curseur normal


    #========================================================================
    def WorkReply(self):
        """Fonction recevant tous les retours du travail en cours."""
        ### Récupération du retour (les 2 sorties sont sur la standard)
        data = self.process.readAllStandardOutput()

        ### Converti les data en textes et les traite
        for line in bytes(data).decode('utf-8').splitlines():
            ## Passe la boucle si le retour est vide, ce qui arrive et provoque une erreur
            if line == "":
                continue

            ## Dans le cas d'un encapsulation
            elif TempValues.value("Command")[0] == "MKVMerge":
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%":
                    line = int(line.split(": ")[1].strip()[0:-1]) #

            ## Dans le cas d'une conversion
            elif TempValues.value("Command")[0] == "FileToMKV":
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%":
                    line = int(line.split(": ")[1].strip()[0:-1])

            elif TempValues.value("Command")[0] == "MKVExtract Tags":
                with TempValues.value("TagsFile").open('a') as TagsFile:
                    TagsFile.write(line+'\n')

                line = ""

            elif TempValues.value("Command")[0] == "MKVExtract Chapters":
                with TempValues.value("ChaptersFile").open('a') as ChaptersFile:
                    ChaptersFile.write(line+'\n')

                line = ""

            ## MKVExtract renvoie une progression. Les fichiers joints ne renvoient rien.
            elif "MKVExtract" in TempValues.value("Command")[0]:
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%":
                    line = int(line.split(": ")[1].strip()[0:-1])

            ## MKValidator ne renvoie pas de pourcentage mais des infos ou des points, on vire les . qui indiquent un travail en cours
            elif TempValues.value("Command")[0] == "MKValidator":
                line = line.strip().replace('.', '')


            ## MKClean renvoie une progression et des infos, on ne traite que les pourcentages
            elif TempValues.value("Command")[0] == "MKClean":
                if line[-1] == "%":
                    line = int(line.split(": ")[1].strip()[0:-1])


            ## FFMpeg ne renvoie pas de pourcentage mais la durée de vidéo encodée en autre
            elif TempValues.value("Command")[0] in ["ffmpeg", "avconv"]:
                if "time=" in line and TempValues.contains("DurationFile"):
                    # Pour les versions renvoyant : 00:00:00
                    try:
                        value = line.split("=")[2].strip().split(".")[0].split(":")
                        value2 = timedelta(hours=int(value[0]), minutes=int(value[1]), seconds=int(value[2])).seconds

                    # Pour les versions renvoyant : 00000 secondes
                    except:
                        value = "caca"
                        value2 = line.split("=")[2].strip().split(".")[0]

                    # Pourcentage maison se basant sur la durée du fichier
                    line = int((value2 * 100) / TempValues.value("DurationFile"))

            ## Qtesseract5
            elif TempValues.value("Command")[0] == "Qtesseract5":
                if "Temporary folder:" in line: TempValues.setValue("Qtesseract5Folder", Path(line.split(": ")[1]))

                try:
                    line = int((int(line.split("/")[0]) / int(line.split("/")[1])) * 100)

                except:
                    pass


            ## Affichage du texte ou de la progression si c'est une nouvelle valeur
            if line and line != TempValues.value("WorkOldLine"): # Comparaison anti doublon
                TempValues.setValue("WorkOldLine", line) # Mise à jour de la variable anti doublon

                # Envoie du pourcentage à la barre de progression si c'est un nombre
                if isinstance(line, int):
                    self.ui.progressBar.setValue(line)

                # Envoie de l'info à la boite de texte si c'est du texte
                else:
                    # On ajoute le texte dans une variable en cas de conversion (utile pour le ressortir dans une fenêtre)
                    if TempValues.value("Command")[0] == "FileToMKV":
                        WarningReply.append(line)

                    self.SetInfo(line)


    #========================================================================
    def WorkFinished(self):
        """Fonction appelée à la fin du travail, que ce soit une fin normale ou annulée."""
        # TempValues.value("Command")[0] : Nom de la commande
        # TempValues.value("Command")[1] : Commande à executer ou liste de fichiers
        ### Si le travail est annulé (via le bouton stop ou via la fermeture du logiciel) ou a renvoyée une erreur, mkvmerge renvoie 1 s'il y a des warnings
        if (TempValues.value("Command")[0] == "FileToMKV" and self.process.exitCode() == 2) or (self.process.exitCode() != 0 and TempValues.value("Command")[0] != "FileToMKV"):
            ## Arrêt du travail
            if TempValues.value("Command")[0] == "Qtesseract5": self.WorkStop("SrtError")

            else: self.WorkStop("Error")

            ## Arrêt de la fonction
            return


        ### Traitement différent en fonction de la commande, rien de particulier pour MKValidator, MKClean, FFMpeg
        if TempValues.value("Command")[0] == "Open Subtitles":
            # Boucle ouvrant tous les fichiers srt d'un coup
            for Item in SubtitlesFiles:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Item)))


        elif "MKVExtract" in TempValues.value("Command")[0] == "MKVExtract" and (CommandList and "MKVExtract" in CommandList[0][0]): # Système n'affichant pas la fin tant qu'il y a des extractions
            TempValues.setValue("Command", CommandList.pop(0)) # Récupération de la commande suivante à exécuter
            self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1]), newline=True) # Envoie d'informations
            self.process.start(TempValues.value("Command")[1]) # Lancement de la commande
            return


        ### Indication de fin de pack de commande
        if TempValues.value("Command")[0] != "Open Subtitles":
            self.SetInfo(self.Trad["WorkFinished"].format(TempValues.value("Command")[0]), "800080", True) # Travail terminé
            self.ui.progressBar.setValue(100) # Mise à 100% de la barre de progression pour signaler la fin ok

            if Configs.value("SysTray"):
                self.SysTrayIcon.showMessage(self.Trad["SysTrayFinishTitle"], self.Trad["SysTrayFinishText"].format(TempValues.value("Command")[0], QSystemTrayIcon.Information, 3000))


        ### Lancement de l'ouverture du fichier MKV, ici pour un soucis esthétique du texte affiché
        # Dans le cas d'une conversion
        if TempValues.value("Command")[0] == "FileToMKV":
            ## Si mkvmerge a renvoyé un warning, on l'indique
            if self.process.exitCode() == 1 and not Configs.value("ConfirmWarning"):
                # Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, self.Trad["Convert3"], self.Trad["Convert4"], QMessageBox.NoButton, self)
                CheckBox = QCheckBox(self.Trad["Convert5"])
                dialog.setCheckBox(CheckBox)
                dialog.setStandardButtons(QMessageBox.Ok)
                dialog.setDefaultButton(QMessageBox.Ok)
                dialog.setDetailedText("\n".join(WarningReply))
                dialog.exec()

                # Mise en mémoire de la case à cocher
                Configs.setValue("ConfirmWarning", CheckBox.isChecked())

            ## Lancement de la fonction d'ouverture du fichier MKV créé avec le nom du fichier
            self.InputFile(TempFiles[-1])


        ### Dans le cas ou il faut mettre en pause entre 2 jobs
        if TempValues.value("WorkPause") or TempValues.value("Command")[0] == "Open Subtitles":
            # Remise à False de la variable pause
            TempValues.setValue("WorkPause", False)

            # Mise en pause du travail avec arrêt si besoin
            if not self.WorkPause():
                return


        ### S'il reste des commandes, exécution de la commande suivante
        if CommandList:
            qtesseract5 = False
            for Command in CommandList:
                if "Qtesseract5" in Command: qtesseract5 = True

            if len(CommandList) == 1 and not qtesseract5:
                self.ui.mkv_pause.show() # Affiche le bouton pause

            ## Récupération de la commande suivante à exécuter
            TempValues.setValue("Command", CommandList.pop(0))

            ## Mise à 0% de la barre de progression pour signaler le début du travail
            self.ui.progressBar.setValue(0)

            ## Évite de dire que la cmd mkmerge se lance et que le log est en pause
            if TempValues.value("Command")[0] != "Open Subtitles":
                self.SetInfo(self.Trad["WorkProgress"].format(TempValues.value("Command")[0]), "800080", True, True)

            ## Dans le cas des commandes bidons
            if TempValues.value("Command")[1] != "echo":
                self.SetInfo(self.Trad["WorkCmd"].format(TempValues.value("Command")[1]))

            ## Lancement de la commande suivante
            self.process.start(TempValues.value("Command")[1])


        ### Si c'était la dernière commande
        else:
            ## Si l'option de suppression des fichiers temporaire est activée lors du merge
            if Configs.value("DelTemp") and TempValues.value("Command")[0] == "MKVMerge":
                # Suppression du fichier mkv de sortie de la liste
                TempFiles.remove(TempValues.value("OutputFile"))

                # Suppression des fichiers temporaires
                self.RemoveTempFiles()

            ## Remise en état des widgets
            self.WorkInProgress(False)

            if Configs.value("SysTray"):
                self.SysTrayIcon.showMessage(self.Trad["SysTrayFinishTitle"], self.Trad["SysTrayTotalFinishText"], QSystemTrayIcon.Information, 3000)


    #========================================================================
    def WorkPauseBefore(self):
        """Fonction différentiente entre la pause entre jobs et celle pendant l'utilisation de Qtesseract."""
        ### Pause dépendante de la conversion de Tesseract
        if TempValues.value("Command")[0] == "Qtesseract5":
            Path(TempValues.value("Qtesseract5Folder"), "Pause").touch()
            self.WorkPause()


        ### Pause entre les taches
        else:
            TempValues.setValue("WorkPause", True)


    #========================================================================
    def WorkPause(self):
        """Fonction de mise en pause du travail entre 2 commandes."""
        ### Création d'une fenêtre de confirmation de reprise
        Resume = QMessageBox(self)
        Resume.setWindowTitle(self.Trad["Resume1"])
        Resume.setText(self.Trad["Resume2"])
        Resume.setIconPixmap(QPixmap(QIcon().fromTheme("dialog-warning", QIcon(":/img/dialog-warning.png")).pixmap(64)))

        ResumeButton = QPushButton(QIcon.fromTheme("view-refresh", QIcon(":/img/view-refresh.png")), self.Trad["Resume3"], Resume)
        CancelButton = QPushButton(QIcon.fromTheme("process-stop", QIcon(":/img/process-stop.png")), self.Trad["Resume4"], Resume)

        Resume.addButton(ResumeButton, QMessageBox.AcceptRole)
        Resume.addButton(CancelButton, QMessageBox.RejectRole)
        Resume.setEscapeButton(CancelButton)
        Resume.setDefaultButton(ResumeButton)
        Resume.exec()


        ### Fin de la fonction
        if Resume.clickedButton() != ResumeButton:
            ## Si la reprise n'est pas confirmée, on arrête le travail en cours
            self.WorkStop("Pause")

            return False

        else:
            ## Dans le cas spécifique de Qtesseract
            if TempValues.contains("Qtesseract5Folder") and Path(TempValues.value("Qtesseract5Folder"), "Pause").exists():
                Path(TempValues.value("Qtesseract5Folder"), "Pause").unlink()

            return True


    #========================================================================
    def WorkStop(self, Type):
        """Fonction d'arrêt du travail en cours."""
        ### Dans le cas spécifique de Qtesseract
        if TempValues.contains("Qtesseract5Folder") and TempValues.value("Qtesseract5Folder").exists() and Type != "Close":
            Path(TempValues.value("Qtesseract5Folder"), "Stop").touch()

            while TempValues.value("Qtesseract5Folder").exists():
                sleep(0.2)

            TempValues.remove("Qtesseract5Folder")


        ### Type : Error (en cas de plantage), Stop (en cas d'arrêt du travail), Close (en cas de fermeture du logiciel), Pause (en cas d'annulation pendant la pause), SrtError (en cas d'erreur tesseract)
        ### En cas de pause, il n'y a pas de travail en cours
        if Type != "Pause":
            ## Teste l'etat du process pour ne pas le killer plusieurs fois (stop puis error)
            if self.process.state() == 0:
                return

            ## Kill le boulot en cours
            self.process.kill()

            if not self.process.waitForFinished(1000):
                self.process.kill() # Attend que le travail soit arrété pdt 1s


        ### Suppression des fichiers temporaires
        self.RemoveTempFiles()


        ### Réinitialisation de la liste des commandes
        CommandList.clear()


        ### Envoie du texte le plus adapté
        if Type in ("Stop", "Pause"):
            self.SetInfo(self.Trad["WorkCanceled"], "FF0000", True) # Travail annulé

        elif Type in ("Error", "SrtError"):
            self.SetInfo(self.Trad["WorkError"], "FF0000", True) # Erreur pendant le travail

        elif Type == "Close":
            return


        ### Modifications graphiques
        self.ui.progressBar.setValue(0) # Remise à 0 de la barre de progression signifiant une erreur
        self.WorkInProgress(False) # Remise en état des widgets


    #========================================================================
    def SysTrayClick(self, event):
        """Fonction gérant les clics sur le system tray."""
        ### Si la fenêtre est cachée ou si elle n'a pas la main
        if not self.isVisible() or (not self.isActiveWindow() and self.isVisible()):
            self.show()
            self.activateWindow()


        ### Si la fenêtre est visible
        else:
            self.hide()


    #========================================================================
    def dragEnterEvent(self, event):
        """Fonction appelée à l'arrivée d'un fichier à déposer sur la fenêtre."""
        # Impossible d'utiliser mimetypes car il ne reconnaît pas tous les fichiers...
        ### Récupération du nom du fichier
        Item = Path(event.mimeData().urls()[0].path())


        ### Acceptation de l'événement en cas de fichier et de fichier valide (pour le fichier d'entrée)
        if Item.is_file() and Item.suffix in (".m4a", ".mk3d", ".mka", ".mks", ".mkv", ".mp4", ".nut", ".ogg", ".ogm", ".ogv", ".webm", ".webma", ".webmv"):
            event.accept()


        ### Acceptation de l'événement en cas de dossier (pour le dossier de sortie)
        elif Item.is_dir():
            event.accept()


    #========================================================================
    def dropEvent(self, event):
        """Fonction appelée à la dépose du fichier/dossier sur la fenêtre."""
        # Impossible d'utiliser mimetypes car il ne reconnaît pas tous les fichiers...
        ### Récupération du nom du fichier
        Item = Path(event.mimeData().urls()[0].path())


        ### En cas de fichier (pour le fichier d'entrée)
        if Item.is_file():
            ## Vérifie que l'extension fasse partie de la liste et lance la fonction d'ouverture du fichier MKV avec le nom du fichier
            if Item.suffix in (".mka", ".mks", ".mkv", ".mk3d", ".webm", ".webmv", ".webma"):
                self.InputFile(Item)

            ## Nécessite une conversion de la vidéo
            elif Item.suffix in (".mp4", ".nut", ".ogg"):
                self.MKVConvert(Item)


        ## Lancement de la fonction de gestion du dossier de sorti en cas de dossier (pour le dossier de sortie)
        elif Item.is_dir():
            self.OutputFolder(Item)


    #========================================================================
    def resizeEvent(self, event):
        """Fonction qui resize le tableau à chaque modification de la taille de la fenêtre."""
        ### Resize de la liste des pistes
        largeur = (self.ui.mkv_tracks.size().width() - 50) / 3 # Calcul pour définir la taille des colonnes
        self.ui.mkv_tracks.setColumnWidth(3, largeur + 30) # Modification de la largeur des colonnes
        self.ui.mkv_tracks.setColumnWidth(4, largeur + 15) # Modification de la largeur des colonnes


        ### Resize de la liste des options
        largeur = (self.ui.configuration_table.size().width() - 185) / 2 # Calcul pour définir la taille des colonnes
        self.ui.configuration_table.setColumnWidth(0, 160) # Modification de la largeur des colonnes
        self.ui.configuration_table.setColumnWidth(1, largeur) # Modification de la largeur des colonnes
        self.ui.configuration_table.setColumnWidth(2, largeur) # Modification de la largeur des colonnes


        ### Acceptation de l'événement
        event.accept()


    #========================================================================
    def closeEvent(self, event):
        """Fonction exécutée à la fermeture de la fenêtre quelqu'en soit la méthode."""
        ### Curseur de chargement
        self.setCursor(Qt.WaitCursor)


        ### Bloque les signaux sinon cela save toujours off
        self.ui.feedback_widget.blockSignals(True)


        ### Arrêt du travail en cours
        self.WorkStop("Close")


        ### Si l'option de suppression du fichier des fichiers et url récentes est activée, on l'efface
        if Configs.value("RecentInfos"):
            RecentFile = Path(QDir.homePath(), '.config/MKVExtractorQt5.pyrc')

            if RecentFile.exists():
                RecentFile.unlink()


        ### Enregistrement de l'intérieur de la fenêtre (dockwidget)
        Configs.setValue("WinState", self.saveState())


        ### Si on a demandé à conserver l'aspect
        if Configs.value("WindowAspect"):
            Configs.setValue("WinGeometry", self.saveGeometry())


        ### Si on a rien demandé, on détruit la valeur
        elif Configs.contains("WinGeometry"):
            Configs.remove("WinGeometry")


        ### Suppression du dossier temporaire de Qtesseract5
        if self.FolderTempWidget.isValid():
            self.FolderTempWidget.remove()


        ### Acceptation de l'événement
        event.accept()


        self.setCursor(Qt.ArrowCursor)


#############################################################################
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationVersion("5.5.8")
    app.setApplicationName("MKV Extractor Qt5")

    ### Dossier du logiciel, utile aux traductions et à la liste des codecs
    AppFolder = Path(sys.argv[0]).resolve().parent


    ### Création des dictionnaires et listes facilement modifiables partout
    MKVDico = {} # Dictionnaire qui contiendra toutes les pistes du fichier MKV
    MD5Dico = {} # Dictionnaire qui contiendra les sous titres à reconnaître manuellement
    MKVDicoSelect = {} # Dictionnaire qui contiendra les pistes sélectionnées
    MKVLanguages = [] # Liste qui contiendra et affichera dans les combobox les langues dispo (audio et sous titres)
    PowerList = {} # Dictionnaire qui contiendra les widgets de gestion de puissance de fichier AC3
    QualityList = {} # Dictionnaire qui contiendra les widgets de gestion de la qualité de fichier AC3
    QtStyleList = {} # Dictionnaire qui contiendra les styles possibles pour qt
    TempFiles = [] # Liste des fichiers temporaires pré ré-encapsulage ou en cas d'arrêt du travail
    CommandList = [] # Liste des commandes à exécuter
    SubtitlesFiles = [] # Adresse des fichiers sous titres à ouvrir avant l'encapsulage
    WarningReply = [] # Retour de mkvmerge en cas de warning


    ### Configs du logiciel
    # Valeurs par défaut des options, pas toutes (MMGorMEQ, les valeurs de la fenêtre, l'adresse du dernier fichier ouvert)
    DefaultValues = {"AlreadyExistsTest": False, # Option ne signalant que le fichier existe déjà
                     "CheckSizeCheckbox": False, # Option ne signalant pas le manque de place
                     "DebugMode": False, # Option affichant plus ou d'infos
                     "DelTemp": False, # Option de suppression des fichiers temporaires
                     "ConfirmErrorLastFile": False, # Ne plus prévenir en cas d'absence de fichier au démarrage
                     "Feedback": True, # Option affichant ou non les infos de retours
                     "FeedbackBlock": False, # Option bloquant les infos de retours
                     "FolderParentTemp": QDir.tempPath(), # Dossier temporaire dans lequel extraire les pistes pour visualisation
                     "FFMpeg": False, # Commande de conversion avconv ou ffmpeg
                     "HideOptions": False, # Option cachant ou non les options inutilisables
                     "LastFile": False, # Option conservant en mémoire le dernier mkv ouvert
                     "Location/AvConv": "", # Adresses des logiciels
                     "Location/BDSup2Sub": "",
                     "Location/FFMpeg": "",
                     "Location/MKClean": "",
                     "Location/MKVInfo": "",
                     "Location/MKVToolNix": "",
                     "Location/MKValidator": "",
                     "Location/Qtesseract5": "",
                     "MMGorMEQ": "MEQ", # Logiciel à utiliser
                     "MMGorMEQCheckbox": False, # Valeur sautant la confirmation du choix de logiciel à utiliser
                     "ConfirmConvert": False, # Valeur sautant la confirmation de conversion
                     "ConfirmWarning": False, # Valeur sautant l'information du warning de conversion
                     "InputFolder": Path(QDir.homePath()), # Dossier du fichier mkv d'entrée : Path(MKVLink).name
                     "OutputFolder": Path(QDir.homePath()), # Dossier de sortie
                     "Language": QLocale.system().name(), # Langue du système
                     "RecentInfos": True, # Option de suppression du fichier des fichiers et adresses récentes
                     "RemuxRename": False, # Renommer automatiquement le fichier de sorti remux
                     "OutputSameFolder": True, # Option d'utilisation du même dossier de sortie que celui du fichier mkv
                     "SysTray": True, # Option affichant l'icône du system tray
                     "WindowAspect": True, # Conserver la fenêtre et sa géométrie
                     "QtStyle": QApplication.style().objectName() # Conserver la fenêtre et sa géométrie
                    }


    ### Système de gestion des configurations QSettings
    ## Création ou ouverture du fichier de config
    Configs = QSettings(QSettings.NativeFormat, QSettings.UserScope, "MKV Extractor Qt5")

    ## Donne le bon type de variable
    try:
        # Boucle sur les valeurs par défaut
        for Key, Value in DefaultValues.items():
            # Si l'option n'existe pas, on l'ajoute au fichier avec la valeur de base
            if not Configs.contains(Key):
                Configs.setValue(Key, Value)

            # Si l'option existe, on la change dans le bon format
            else:
                KeyType = type(Value)

                if KeyType is bool: # Dans le cas de vrai ou faux
                    if Configs.value(Key) == "true":
                        Configs.setValue(Key, True)

                    else:
                        Configs.setValue(Key, False)

                elif KeyType is int: # Dans le cas de nombre
                    Configs.setValue(Key, int(Configs.value(Key)))

    ## S'il y a eu un problème, on réinitialise tout
    except:
        for Key, Value in DefaultValues.items():
            Configs.setValue(Key, Value)


    ### Valeurs temporaires
    ## Valeurs par défaut des options, pas toutes (MMGorMEQ, les valeurs de la fenêtre, l'adresse du dernier fichier ouvert)
    DefaultTempValues = {"AllTracks": False,
                         "AudioConvert": False,
                         "AudioBoost": "NoChange",
                         "AudioQuality": "NoChange",
                         "AudioStereo": False,
                         "ChaptersFile": "",
                         "Command": "",
                         "DurationFile": 0,
                         "FirstRun": True,
                         "FolderTemp": "",
                         "MKVLoaded": False,
                         "OutputFile": "",
                         "Qtesseract5Folder": Path(),
                         "Qtesseract5": False,
                         "Reencapsulate": False,
                         "SubtitlesOpen": False,
                         "SuperBlockTemp": False,
                         "TagsFile": "",
                         "TitleFile": "",
                         "VobsubToSrt": False,
                         "WorkOldLine": "",
                         "WorkPause": False}

    ## Création ou ouverture du fichier de config
    TempValues = QSettings(QSettings.NativeFormat, QSettings.UserScope, "MKV Extractor Qt5")

    ## Donne le bon type de variable
    for Key, Value in DefaultTempValues.items():
        TempValues.setValue(Key, Value)




    MKVExtractorQt5Class = MKVExtractorQt5()
    MKVExtractorQt5Class.setAttribute(Qt.WA_DeleteOnClose)
    sys.exit(app.exec())
