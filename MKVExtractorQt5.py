#!/usr/bin/python3
# -*- coding: utf-8 -*-


from PyQt5.QtWidgets import QPushButton, QSystemTrayIcon, QWidget, QTextEdit, QShortcut, QComboBox, QApplication, QAction, QDockWidget, QInputDialog, QVBoxLayout, QDesktopWidget, QMessageBox, QActionGroup, QTableWidgetItem, QCheckBox, QMainWindow, QMenu
from PyQt5.QtCore import QFileInfo, QStandardPaths, QTemporaryDir, QTranslator, QThread, QLibraryInfo, QDir, QMimeType, QMimeDatabase, Qt, QSettings, QProcess, QUrl, QLocale
from PyQt5.QtGui import QTextCursor, QIcon, QKeySequence, QCursor, QDesktopServices, QPixmap


import sys
from shutil import disk_usage, rmtree # Utilisé pour tester la place restante
from functools import partial # Utilisé pour envoyer plusieurs infos via les connexions
from datetime import timedelta # utile pour le calcul de la progression de la conversion en ac3
from pathlib import Path # Nécessaire pour la recherche de fichier
from QFileDialogCustom.QFileDialogCustom import QFileDialogCustom # Version custom de selecteur de fichier
from ui_MKVExtractorQt5 import Ui_mkv_extractor_qt5 # Utilisé pour la fenêtre principale
from CodecListFile import CodecList # Liste des codecs


#############################################################################
### Class et fonction permettant la prise en charge du clic droit sur le bouton quitter
class QuitButton(QPushButton):
    def mousePressEvent(self, event):
        """Fonction de reccup des touches souris utilisées."""
        MKVExtractorQt5Class.ui.soft_quit.animateClick()

        ### Récupération du bouton utilisé
        if event.button() == Qt.RightButton:
            from os import execl
            python = sys.executable
            execl(python, python, * sys.argv)

        # Acceptation de l'événement
        return super(type(self), self).mousePressEvent(event)



#############################################################################
### Creation d'une version perso pour modifier le clic droit et possibilités offertes
class QTextEditCustom(QTextEdit):
    #========================================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ### Création des raccourcis claviers qui serviront aux actions
        ExportShortcut = QShortcut("ctrl+e", self)
        ExportShortcut.activated.connect(self.ExportAction)

        CleanShortcut = QShortcut("ctrl+d", self)
        CleanShortcut.activated.connect(self.CleanAction)



    def contextMenuEvent(self, event):
        """Fonction de la création du menu contextuel."""
        ### TRADUCTION
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
        Clean = QAction(QIcon.fromTheme("edit-clear", QIcon(":/img/edit-clear.png")), self.tr("Clean the information fee&dback box"), Menu)
        Clean.setShortcut(QKeySequence("ctrl+d"))
        Clean.triggered.connect(self.CleanAction)
        Menu.addSeparator()
        Menu.addAction(Clean)

        # Création et ajout de l'action d'export (icône, nom, raccourci)
        Export = QAction(QIcon.fromTheme("document-export", QIcon(":/img/document-export.png")), self.tr("&Export info to ~/InfoMKVExtractorQt5.txt"), Menu)
        Export.setShortcut(QKeySequence("ctrl+e"))
        Export.triggered.connect(self.ExportAction)
        Menu.addSeparator()
        Menu.addAction(Export)

        # Grise les actions si le texte est vide
        if not self.toPlainText():
            Export.setEnabled(False)
            Clean.setEnabled(False)

        # Affichage du menu là où se trouve la souris
        Menu.exec_(QCursor.pos())


    def CleanAction(self, *args):
        """Fonction de nettoyage du texte."""
        self.clear()


    def ExportAction(self, *args):
        """Fonction d'exportation du texte."""
        # Récupération du texte
        text = self.toPlainText()

        # Arrête la fonction si pas de texte
        if not text: return()

        # Fichier de sortie
        file = Path(QDir.homePath(), 'InfoMKVExtractorQt5.txt')

        # Enregistrement du texte
        with file.open("w") as info_file: info_file.write(text)



#############################################################################
class MKVExtractorQt5(QMainWindow):
    def __init__(self, parent=None):
        """Fonction d'initialisation appelée au lancement de la classe."""
        ### Commandes à ne pas toucher
        super(MKVExtractorQt5, self).__init__(parent)
        self.ui = Ui_mkv_extractor_qt5()
        self.ui.setupUi(self) # Lance la fonction définissant tous les widgets du fichier UI
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
        ## Nom de la fenêtre
        self.setWindowTitle('MKV Extractor Qt v{}'.format(app.applicationVersion()))

        ## Remet les widgets comme ils l'étaient
        if Configs.contains("WinState"): self.restoreState(Configs.value("WinState"))

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


        ### Recherche les différents logiciels complémentaires
        ffconv = False


        ### Cache les options dont les executables n'existe pas
        for Executable, Widget in (("mkvalidator", self.ui.mk_validator), ("mkclean", self.ui.mk_clean), ("mkvinfo-gui", self.ui.mkv_info), ("qtesseract5", self.ui.option_vobsub_srt), ("qtesseract5", self.ui.about_qtesseract5)):
            x = QStandardPaths.findExecutable(Executable)
            y = QStandardPaths.findExecutable(Executable, [QFileInfo(".").absoluteFilePath()])

            # Définit l'adresse du programme
            if not x and not y: Widget.setVisible(False)


        ## Commande à utiliser pour mmg
        if QStandardPaths.findExecutable("mmg"): Configs.setValue("mmgExec", "mmg")
        elif QStandardPaths.findExecutable("mkvtoolnix-gui"): Configs.setValue("mmgExec", "mkvtoolnix-gui")
        else: self.ui.mkv_mkvmerge.setVisible(False) # Cache l'option mmg si le l'exécutable n'existe pas


        ## Recherche ffmpeg et avconv qui font la même chose
        # Cache les radiobutton et l'option de conversion
        if not QStandardPaths.findExecutable("ffmpeg") and not QStandardPaths.findExecutable("avconv"): self.ui.option_audio.setVisible(False)

        # Sélection automatique ffmpeg
        elif QStandardPaths.findExecutable("ffmpeg") and not QStandardPaths.findExecutable("avconv"): Configs.setValue("FFMpeg", True)

        # Sélection automatique avconv
        elif not QStandardPaths.findExecutable("ffmpeg") and QStandardPaths.findExecutable("avconv"): Configs.setValue("FFMpeg", False)

        # Les deux sont dispo, utilisation de ffmpeg par defaut
        else: ffconv = True


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
        icon = QIcon.fromTheme("cpu", QIcon(":/img/cpu.png"))
        self.TesseractCpu = QAction(icon, '', self) # Création d'un item sans texte
        menulist.addAction(self.TesseractCpu) # Ajout de l'action à la liste
        self.ui.option_vobsub_srt.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Menu du bouton de conversion DTS => AC3
        menulist = QMenu() # Création d'un menu

        if ffconv:
            icon = QIcon.fromTheme("ffmpeg", QIcon(":/img/ffmpeg.png"))
            self.option_ffmpeg = QAction(icon, '', self, checkable=True) # Création d'un item sans texte
            menulist.addAction(self.option_ffmpeg) # Ajout de l'action à la liste
            self.option_ffmpeg.toggled.connect(partial(self.OptionsValue, "FFMpeg"))
            if Configs.value("FFMpeg"): self.option_ffmpeg.setChecked(True)

        icon = QIcon.fromTheme("audio-ac3", QIcon(":/img/audio-ac3.png"))
        self.option_to_ac3 = QAction(icon, '', self, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_to_ac3) # Ajout de l'action à la liste

        icon = QIcon.fromTheme("audio-headphones", QIcon(":/img/audio-headphones.png"))
        self.option_stereo = QAction(icon, '', self, checkable=True) # Création d'un item sans texte
        menulist.addAction(self.option_stereo) # Ajout de l'action à la liste

        self.RatesMenu = QMenu(self) # Création d'un sous menu
        ag = QActionGroup(self, exclusive=True) # Création d'un actiongroup
        QualityList["OptionsQualityNoChange"] = QAction('', self, checkable=True) # Création d'un item radio sans nom
        self.RatesMenu.addAction(ag.addAction(QualityList["OptionsQualityNoChange"])) # Ajout de l'item radio dans la sous liste
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]: # Qualités utilisables
            QualityList[nb] = QAction('', self, checkable=True) # Création d'un item radio sans nom
            self.RatesMenu.addAction(ag.addAction(QualityList[nb])) # Ajout de l'item radio dans la sous liste
        menulist.addMenu(self.RatesMenu) # Ajout du sous menu dans le menu

        self.PowerMenu = QMenu(self) # Création d'un sous menu
        ag = QActionGroup(self, exclusive=True) # Création d'un actiongroup
        PowerList["OptionsPowerNoChange"] = QAction('', self, checkable=True) # Création d'un item radio sans nom
        self.PowerMenu.addAction(ag.addAction(PowerList["OptionsPowerNoChange"])) # Ajout de l'item radio dans la sous liste
        for nb in [2, 3, 4, 5]: # Puissances utilisables
            PowerList[nb] = QAction('', self, checkable=True) # Création d'un item radio sans nom
            self.PowerMenu.addAction(ag.addAction(PowerList[nb])) # Ajout de l'item radio dans la sous liste
        menulist.addMenu(self.PowerMenu) # Ajout du sous menu dans le menu

        self.ui.option_audio.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Menu du bouton de reencapsulage
        icon = QIcon.fromTheme("edit-delete", QIcon(":/img/edit-delete.png"))
        self.option_del_temp = QAction(icon, '', self, checkable=True) # Création d'une action cochable sans texte
        icon = QIcon.fromTheme("document-edit", QIcon(":/img/document-edit.png"))
        self.option_subtitles_open = QAction(icon, '', self, checkable=True) # Création d'une action cochable sans texte
        menulist = QMenu() # Création d'un menu
        menulist.addAction(self.option_del_temp) # Ajout de l'action à la liste
        menulist.addAction(self.option_subtitles_open) # Ajout de l'action à la liste
        self.ui.option_reencapsulate.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Activation et modifications des préférences
        QualityList[Configs.value("AudioQuality", "OptionsQualityNoChange")].setChecked(True) # Coche de la bonne valeur
        PowerList[Configs.value("AudioBoost", "OptionsPowerNoChange")].setChecked(True) # Coche de la bonne valeur

        if Configs.value("OutputSameFolder"): self.ui.option_mkv_folder.setChecked(True)

        if not Configs.value("RecentInfos"): self.ui.option_recent_infos.setChecked(True)

        if not Configs.value("WindowAspect"): self.ui.option_aspect.setChecked(False)

        if Configs.value("DebugMode"): self.ui.option_debug.setChecked(True)

        if not Configs.value("Feedback"):
            self.ui.option_feedback.setChecked(False)
            self.ui.feedback_widget.hide()

        if Configs.value("FeedbackBlock"):
            self.ui.option_feedback_block.setChecked(True)
            self.ui.feedback_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)


        ### Réinitialisation du dossier de sortie s'il n'existe pas
        if not Configs.contains("OutputFolder") or not Configs.value("OutputFolder").is_dir():
            Configs.setValue("OutputFolder", Path().resolve())

            self.ui.option_mkv_folder.setChecked(True) # Activation de l'option même dossier afin qu'un dossier de sortie soit pris en compte au prochain mkv


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


        ### Gestion la traduction, le widget n'est pas encore connecté
        ## Sélection de la langue français
        if "fr_" in Configs.value("Language"):
            self.ui.lang_fr.setChecked(True)
            self.OptionLanguage("fr_FR")

        ## Sélection de la langue tchèque
        elif "cs_" in Configs.value("Language"):
            self.ui.lang_cs.setChecked(True)
            self.OptionLanguage("cs_CZ")

        ## Force le chargement de traduction si c'est la langue anglaise (par défaut)
        else:
            self.OptionLanguage("en_US")


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
                if len(line) == 3: MKVLanguages.append(line)

        ## Range les langues dans l'ordre alphabétique
        MKVLanguages.sort()


        ### QProcess (permet de lancer les jobs en fond de taches)
        self.process = QProcess() # Création du QProcess
        self.process.setProcessChannelMode(1) # Unification des 2 sorties (normale + erreur) du QProcess


        ### Connexions de la grande partie des widgets (les autres sont ci-dessus ou via le fichier ui)
        self.ConnectActions()


        ### Dans le cas du lancement du logiciel avec ouverture de fichier
        ## En cas d'argument simple
        if len(sys.argv) == 2:
            # Teste le fichier avant de l'utiliser
            if Path(sys.argv[1]).exists(): Configs.setValue("InputFile", Path(sys.argv[1]))

            # En cas d'erreur
            else: QMessageBox(3, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgExist"].format(sys.argv[1]), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

        ## En cas arguments multiples
        elif len(sys.argv) > 2:
            # Suppression du fichier d'entrée
            Configs.remove("InputFile")

            # Message d'erreur
            QMessageBox(3, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgNb"].format("<br/> - ".join(sys.argv[1:])), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

        ## En cas de l'utilisation du dernier fichier ouvert
        elif Configs.value("LastFile"):
            # Si le fichier n'existe plus et qu'on ne cache pas le message, on affiche le message d'erreur
            if not Configs.value("InputFile").is_file() and not Configs.value("ConfirmErrorLastFile"):
                Configs.remove("InputFile")

                # Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, self.Trad["ErrorLastFileTitle"], self.Trad["ErrorLastFileText"], QMessageBox.NoButton, self)
                CheckBox = QCheckBox(self.Trad["Convert5"]) # Reprise du même texte
                dialog.setCheckBox(CheckBox)
                dialog.setStandardButtons(QMessageBox.Close)
                dialog.setDefaultButton(QMessageBox.Close)
                dialog.exec_()

                Configs.setValue("ConfirmErrorLastFile", CheckBox.isChecked()) # Mise en mémoire de la case à cocher

        ## Dans les autres cas, on vire le nom du fichier
        elif Configs.contains("InputFile"):
            Configs.remove("InputFile")


        ### Dans le cas du lancement du logiciel avec un argument
        if Configs.contains("InputFile"): self.InputFile(Configs.value("InputFile"))


    #========================================================================
    def LittleProcess(self, Command):
        """Petite fonction reccupérant les retours de process simples."""
        ### Envoie d'information en mode debug
        if Configs.value("DebugMode"): self.SetInfo(self.Trad["WorkCmd"].format(Command), newline=True)

        ### Liste qui contiendra les retours
        reply = []

        ### Création du QProcess avec unification des 2 sorties (normale + erreur)
        process = QProcess()
        process.setProcessChannelMode(1)

        ### Lance et attend la din de la commande
        process.start(Command)
        process.waitForFinished()

        ### Ajoute les lignes du retour dans la liste
        for line in bytes(process.readAllStandardOutput()).decode('utf-8').splitlines(): reply.append(line)

        ### Renvoie le resultat
        return(reply)


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
        self.ui.lang_en.triggered.connect(partial(self.OptionLanguage, "en_US"))
        self.ui.lang_fr.triggered.connect(partial(self.OptionLanguage, "fr_FR"))
        self.ui.lang_cs.triggered.connect(partial(self.OptionLanguage, "cs_CZ"))


        ### Connexions du menu Help (au clic ou au coche)
        self.ui.option_debug.toggled.connect(partial(self.OptionsValue, "DebugMode"))
        self.ui.help_mkvextractorqt5.triggered.connect(self.HelpMKVExtractoQt5)
        self.ui.they_talk_about.triggered.connect(self.TheyTalkAbout)
        self.ui.about.triggered.connect(self.AboutMKVExtractoQt5)
        self.ui.about_qt.triggered.connect(lambda: QMessageBox.aboutQt(MKVExtractorQt5Class))
        self.ui.mkvtoolnix.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://mkvtoolnix.download/downloads.html")))
        self.ui.about_qtesseract5.triggered.connect(self.AboutQtesseract5)


        ### Connexion du dockwidget
        self.ui.feedback_widget.visibilityChanged.connect(self.FeedbackWidget)


        ### Connexions des widgets de configuration (au clic ou changement de contenu)
        self.ui.configuration_table.itemChanged.connect(self.ConfigurationEdit)
        self.ui.configuration_ok.clicked.connect(lambda: (self.ui.stackedMiddle.setCurrentIndex(0)))
        self.ui.configuration_reset.clicked.connect(self.ConfigurationReset)


        ### Connexions du tableau listant les pistes du fichier mkv
        self.ui.mkv_tracks.itemChanged.connect(self.TrackModif) # Au changement du contenu d'un item
        self.ui.mkv_tracks.itemSelectionChanged.connect(self.TrackModif) # Au changement de séléction
        self.ui.mkv_tracks.horizontalHeader().sectionPressed.connect(self.TrackSelectAll) # Au clic sur le header horizontal


        ### Connexions des options sur les pistes du fichier mkv (au clic)
        self.ui.option_reencapsulate.toggled.connect(partial(self.OptionsValue, "Reencapsulate"))
        self.ui.option_vobsub_srt.toggled.connect(partial(self.OptionsValue, "VobsubToSrt"))
        self.ui.option_audio.toggled.connect(partial(self.OptionsValue, "AudioConvert"))
        self.ui.option_mkv_folder.toggled.connect(partial(self.OptionsValue, "OutputSameFolder"))
        self.ui.option_systray.toggled.connect(partial(self.OptionsValue, "SysTray"))
        self.option_stereo.toggled.connect(partial(self.OptionsValue, "AudioStereo"))
        self.option_to_ac3.toggled.connect(partial(self.OptionsValue, "AudioToAc3"))
        self.option_del_temp.toggled.connect(partial(self.OptionsValue, "DelTemp"))
        self.option_subtitles_open.toggled.connect(partial(self.OptionsValue, "SubtitlesOpen"))
        self.TesseractCpu.triggered.connect(partial(self.OptionsValue, "TesseractCpu", Configs.value("TesseractCpu", QThread.idealThreadCount())))
        PowerList["OptionsPowerNoChange"].triggered.connect(partial(self.OptionsValue, "AudioBoost", "NoChange"))
        QualityList["OptionsQualityNoChange"].triggered.connect(partial(self.OptionsValue, "AudioQuality", "NoChange"))
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]: QualityList[nb].triggered.connect(partial(self.OptionsValue, "AudioQuality", nb))
        for nb in [2, 3, 4, 5]: PowerList[nb].triggered.connect(partial(self.OptionsValue, "AudioBoost", nb))


        ### Connexions en lien avec le system tray
        self.SysTrayQuit.triggered.connect(lambda: self.close())
        self.SysTrayIcon.activated.connect(self.SysTrayClick)


        ### Connexions des boutons du bas (au clic)
        self.ui.mkv_stop.clicked.connect(partial(self.WorkStop, "Stop"))
        self.ui.mkv_pause.clicked.connect(lambda: Configs.setValue("WorkPause", True))
        self.ui.mkv_execute.clicked.connect(self.CommandCreate)
        self.ui.soft_quit.__class__ = QuitButton # Utilisation de la class QuitButton pour la prise en charge du clic droit

        ### Connexions du QProcess
        self.process.readyReadStandardOutput.connect(self.WorkReply) # Retours du travail
        self.process.finished.connect(self.WorkFinished) # Fin du travail




    #========================================================================
    def OptionsValue(self, Option, Value):
        """Fonction de mise à jour des options."""
        ### Mise à jour de la variable et envoie de l'info
        Configs.setValue(Option, Value)
        if Configs.value("DebugMode"): self.SetInfo(self.Trad["OptionUpdate"].format(Option, Value), newline=True)


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
            if Value: self.ui.feedback_widget.show()
            else: self.ui.feedback_widget.hide()


        ## Pour bloquer ou débloquer la box de retour d'informations
        elif Option == "FeedbackBlock":
            if Value: self.ui.feedback_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)
            else: self.ui.feedback_widget.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)


        ## Pour choisir le nombre de cpu à utiliser
        elif Option == "TesseractCpu":
            Value = QInputDialog.getInt(self, self.Trad["OptionsCpu1"], self.Trad["OptionsCpu2"], int(Configs.value("TesseractCpu", QThread.idealThreadCount())), 1, 32, 1)
            if Value[1]: Configs.setValue("TesseractCpu", Value[0])


        ## Pour cacher ou afficher l'icone du systray
        elif Option == "SysTray":
            ## Affichage de l'icone
            if Value:
                self.SysTrayIcon.show()

            ## Cache l'icone après avoir affiché la fenêtre principale
            else:
                self.show()
                self.activateWindow()
                self.SysTrayIcon.hide()


    #========================================================================
    def OptionLanguage(self, value):
        """Fonction modifiant en temps réel la traduction."""
        ### Mise à jour de la variable de la langue
        Configs.setValue("Language", value)


        ### Chargement du fichier qm de traduction (anglais utile pour les textes singulier/pluriel)
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
        global translator_qt
        translator_qt = QTranslator() # Création d'un QTranslator
        if translator_qt.load("qt_" + Configs.value("Language"), QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator_qt)


        ### Mise à jour du dictionnaire des textes
        # 008000 : vert                 0000c0 : bleu                           800080 : violet
        effet = """<span style=" color:#000000;">@=====@</span>"""
        self.Trad = {"AboutTitle" : self.tr("About MKV Extractor Gui"),
                    "AboutText" : self.tr("""<html><head/><body><p align="center"><span style=" font-size:12pt; font-weight:600;">MKV Extractor Qt v{}</span></p><p><span style=" font-size:10pt;">GUI to extract/edit/remux the tracks of a matroska (MKV) file.</span></p><p><span style=" font-size:10pt;">This program follows several others that were coded in Bash and it codec in python3 + QT5.</span></p><p><span style=" font-size:8pt;">This software is licensed under </span><span style=" font-size:8pt; font-weight:600;"><a href="{}">GNU GPL v3</a></span><span style=" font-size:8pt;">.</span></p><p>Thanks to the <a href="http://www.developpez.net/forums/f96/autres-langages/python-zope/"><span style=" text-decoration: underline; color:#0057ae;">developpez.net</span></a> python forums for their patience</p><p align="right">Created by <span style=" font-weight:600;">Belleguic Terence</span> (Hizoka), November 2013</p></body></html>"""),

                    "AboutQtesseract5Title" : self.tr("About Qtesseract5"),
                    "AboutQtesseract5Text" : self.tr("""<html><head/><body><p><b>Qtesseract5</b> is a software who converts the IDX/SUB file in SRT (text) file. For that works, it use <i>subp2pgm</i> (export the images files from SUB file), <i>Tesseract</i> (for read their files) and <i>subptools</i> (to create a SRT file).</p><p align="right">Created by <span style=" font-weight:600;">Belleguic Terence</span> <hizo@free.fr>, April 2016</p></body></html>"""),

                    "TheyTalkAboutTitle" : self.tr("They talk about MKV Extractor Gui"),
                    "TheyTalkAboutText" : self.tr("""<html><head/><body><p><a href="http://sysads.co.uk/2014/09/install-mkv-extractor-qt-5-1-4-ubuntu-14-04/"><span style=" text-decoration: underline; color:#0057ae;">sysads.co.uk</span></a> (English)</p><p><a href="http://www.softpedia.com/reviews/linux/mkv-extractor-qt-review-496919.shtml"><span style=" text-decoration: underline; color:#0057ae;">softpedia.com</span></a> (English)</p><p><a href="http://linux.softpedia.com/get/Multimedia/Video/MKV-Extractor-Qt-103555.shtml"><span style=" text-decoration: underline; color:#0057ae;">linux.softpedia.com</span></a> (English)</p><p><a href="http://zenway.ru/page/mkv-extractor-qt"><span style=" text-decoration: underline; color:#0057ae;">zenway.ru</span></a> (Russian)</p><p><a href="http://linuxg.net/how-to-install-mkv-extractor-qt-5-1-4-on-ubuntu-14-04-linux-mint-17-elementary-os-0-3-deepin-2014-and-other-ubuntu-14-04-derivatives/">linuxg.net</span></a> (English)</p><p><a href="http://la-vache-libre.org/mkv-extractor-gui-virer-les-sous-titres-inutiles-de-vos-fichiers-mkv-et-plus-encore/">la-vache-libre.org</span></a> (French)</p><p><a href="http://passionexubuntu.altervista.org/index.php/it/kubuntu/1152-mkv-extractor-qt-vs-5-1-3-kde.html">passionexubuntu.altervista.org</span></a> (Italian)</p></body></html>"""),

                    "SysTrayQuit" : self.tr("Quit"),
                    "SysTrayFinishTitle" : self.tr("The command(s) have finished"),
                    "SysTrayFinishText" : self.tr("The <b>{}</b> command have finished its work."),
                    "SysTrayTotalFinishText" : self.tr("All commands have finished their work."),

                    "QTextEditStatusTip" : self.tr("Use the right click for view options."),

                    "AllFiles" : self.tr("All compatible Files"),
                    "MatroskaFiles" : self.tr("Matroska Files"),
                    "OtherFiles" : self.tr("Other Files"),

                    "Convert0" : self.tr("Do not ask again"),
                    "Convert1" : self.tr("File needs to be converted"),
                    "Convert2" : self.tr("This file is not supported by mkvmerge.\nDo you want convert this file in mkv ?"),
                    "Convert3" : self.tr("MKVMerge Warning"),
                    "Convert4" : self.tr("A warning has occurred during the convertion of the file, read the feedback informations."),
                    "Convert5" : self.tr("Do not warn me"),
                    "Convert6" : self.tr("Choose the out folder of the new mkv file"),

                    "FileExistsTitle" : self.tr("Already existing file"),
                    "FileExistsText" : self.tr("The <b>{}</b> is already existing, overwrite it?"),

                    "Resume1" : self.tr("Awaiting resume"),
                    "Resume2" : self.tr("The software is <b>pausing</b>.<br/>Thanks to clic on the '<b>Resume work</b>' button or '<b>Cancel work</b>' for cancel all the work and remove the temporary files."),
                    "Resume3" : self.tr("Resume work"),
                    "Resume4" : self.tr("Cancel work"),

                    "ErrorLastFileTitle" : self.tr("The last file doesn't exist"),
                    "ErrorLastFileText" : self.tr("You have checked the option who reload the last file to the launch of MKV Extractor Qt, but this last file doesn't exist anymore."),
                    "ErrorArgTitle" : self.tr("Wrong arguments"),
                    "ErrorArgExist" : self.tr("The <b>{}</b> file given as argument does not exist."),
                    "ErrorArgNb" : self.tr("<b>Too many arguments given:</b><br/> - {} "),
                    "ErrorConfigTitle" : self.tr("Wrong value"),
                    "ErrorConfigText" : self.tr("Wrong value for the <b>{}</b> option, MKV Extractor Qt will use the default value."),
                    "ErrorConfigPath" : self.tr("Wrong path for the <b>{}</b> option, MKV Extractor Qt will use the default path."),
                    "ErrorQuoteTitle" : self.tr("No way to open this file"),
                    "ErrorQuoteText" : self.tr("The file to open contains quotes (\") in its name. It's impossible to open a file with this carac. Please rename it."),
                    "ErrorSizeTitle" : self.tr("Space available"),
                    "ErrorSize" : self.tr("Not enough space available in the <b>{}</b> folder.<br/>It is advisable to have at least twice the size of free space on the disk file.<br>Free disk space: <b>{}</b>.<br>File size: <b>{}</b>."),
                    "ErrorSizeAttachement" : self.tr("Not enough space available in <b>{}</b> folder.<br/>Free space in the disk: <b>{}</b><br/>File size: <b>{}</b>."),

                    "HelpTitle" : self.tr("Help me!"),
                    "HelpText" : self.tr("""<html><head/><body><p align="center"><span style=" font-weight:600;">Are you lost? Do you need help? </span></p><p><span style=" font-weight:600;">Normally all necessary information is present: </span></p><p>- Read the information in the status bar when moving the mouse on widgets </p><p><span style=" font-weight:600;">Though, if you need more information: </span></p><p>- Forum Ubuntu-fr.org: <a href="http://forum.ubuntu-fr.org/viewtopic.php?id=1508741"><span style=" text-decoration: underline; color:#0057ae;">topic</span></a></p><p>- My email address: <a href="mailto:hizo@free.fr"><span style=" text-decoration: underline; color:#0057ae;">hizo@free.fr </span></a></p><p><span style=" font-weight:600;">Thank you for your interest in this program.</span></p></body></html>"""),

                    "AlreadyExistsTest" : self.tr("Skip the existing file test."),
                    "AudioQuality" : self.tr("Quality of the ac3 file converted."),
                    "AudioBoost" : self.tr("Power of the ac3 file converted."),
                    "CheckSizeCheckbox" : self.tr("Skip the free space disk test."),
                    "DebugMode" : self.tr("View more informations in feedback box."),
                    "DelTemp" : self.tr("Delete temporary files."),
                    "ConfirmErrorLastFile" : self.tr("Remove the error message if the last file doesn't exist."),
                    "Feedback" : self.tr("Show or hide the information feedback box."),
                    "FeedbackBlock" : self.tr("Anchor or loose information feedback box."),
                    "FolderParentTemp" : self.tr("The folder to use for extract temporaly the attachements file to view them."),
                    "FFMpeg" : self.tr("Use FFMpeg for the conversion."),
                    "LastFile" : self.tr("Keep in memory the last file opened for open it at the next launch of MKV Extractor Qt."),
                    "MMGorMEQ" : self.tr("Software to use for just encapsulate."),
                    "MMGorMEQCheckbox" : self.tr("Skip the proposal to softaware to use."),
                    "ConfirmConvert" : self.tr("Skip the confirmation of the conversion."),
                    "ConfirmWarning" : self.tr("Hide the information of the conversion warning."),
                    "InputFolder" : self.tr("Folder of the MKV files."),
                    "OutputFolder" : self.tr("Output folder for the new MKV files."),
                    "Language" : self.tr("Software language to use."),
                    "RecentInfos" : self.tr("Remove the Qt file who keeps the list of the recent files for the window selection."),
                    "OutputSameFolder" : self.tr("Use the same input and output folder."),
                    "RemuxRename" : self.tr("Automatically rename the output file name in MEG_FileName."),
                    "AudioStereo" : self.tr("Switch to stereo during conversion."),
                    "SubtitlesOpen" : self.tr("Opening subtitles before encapsulation."),
                    "SysTray" : self.tr("Display or hide the system tray icon."),
                    "TesseractCpu" : self.tr("Number of CPU to use with Tesseract, by default: max value."),
                    "WindowAspect" : self.tr("Keep in memory the aspect and the position of the window for the next opened."),

                    "OptionsCpu1" : self.tr("Number of CPU to use"),
                    "OptionsCpu2" : self.tr("Choose the number of CPU to use with Tesseract."),
                    "OptionsDTStoAC31" : self.tr("Convert in AC3"),
                    "OptionsDTStoAC32" : self.tr("Convert audio tracks automatically to AC3."),
                    "OptionsDelTemp1" : self.tr("Delete temporary files"),
                    "OptionsDelTemp2" : self.tr("The temporary files are the extracted tracks."),
                    "OptionsFFMpeg" : self.tr("Use FFMpeg for the conversion."),
                    "OptionsPowerList" : self.tr("Increase the sound power"),
                    "OptionsPower" : self.tr("No power change."),
                    "OptionsPowerX" : self.tr("Multiplying audio power by {}."),
                    "OptionsPowerY" : self.tr("Power x {}"),
                    "OptionsQuality" : self.tr("List of available flow rates of conversion"),
                    "OptionsQualityX" : self.tr("Convert the audio quality in {} kbits/s."),
                    "OptionsQualityY" : self.tr("{} kbits/s"),
                    "OptionsStereo1" : self.tr("Switch to stereo during conversion"),
                    "OptionsStereo2" : self.tr("The audio will not use the same number of channels, the audio will be stereo (2 channels)."),
                    "OptionsSub1" : self.tr("Opening subtitles before encapsulation"),
                    "OptionsSub2" : self.tr("Auto opening of subtitle srt files for correction. The software will be paused."),
                    "OptionUpdate" : self.tr('New value for <span style=" color:#0000c0;">{}</span> option: <span style=" color:#0000c0;">{}</span>'),
                    "OptionsQualityNoChange1" : self.tr("No change the quality"),
                    "OptionsQualityNoChange2" : self.tr("The quality of the audio tracks will not be changed."),
                    "OptionsPowerNoChange1" : self.tr("No change the power"),
                    "OptionsPowerNoChange2" : self.tr("The power of the audio tracks will not be changed."),

                    "SelectedFile" : self.tr("Selected file: {}."),
                    "SelectedFolder1" : self.tr("Selected folder: {}."),
                    "SelectedFolder2" : self.tr('Always use the same output folder as the input MKV file (automatically updated)'),

                    "SelectFileInCheckbox" : self.tr("Keep in memory the last file opened for open it at the next launch of MKV Extractor Qt (to use for tests)"),
                    "SelectFileIn" : self.tr("Select the input MKV File"),
                    "SelectFileOut" : self.tr("Select the output MKV file"),
                    "SelectFolder" : self.tr("Select the output folder"),

                    "UseMMGTitle" : self.tr("MKV Merge Gui or MKV Extractor Qt ?"),
                    "UseMMGText" : self.tr("You want extract and reencapsulate the tracks without use other options.\n\nIf you just need to make this, you should use MMG (MKV Merge gui) who is more adapted for this job.\n\nWhat software do you want use ?\n"),

                    "RemuxRenameCheckBox" : self.tr("Always use the default file rename (MEG_FileName)"),
                    "RemuxRenameTitle" : self.tr("Choose the output file name"),

                    "Audio" : self.tr("audio"),
                    "Subtitles" : self.tr("subtitles"),
                    "Video" : self.tr("video"),

                    "TrackAac" : self.tr("If the remuxed file has reading problems, change this value."),
                    "TrackAudio" : self.tr("Change the language if it's not right. 'und' means 'Undetermined'."),
                    "TrackAttachment" : self.tr("This track can be renamed and must contain an extension to avoid reading errors by doubleclicking."),
                    "TrackChapters" : self.tr("chapters"),
                    "TrackID1" : self.tr("Work with track number {}."), # Pour les pistes normales
                    "TrackID2" : self.tr("Work with attachment number {}."), # Pour les fichiers joints
                    "TrackID3" : self.tr("Work with {}."), # Pour les chapitres et les tags
                    "TrackRename" : self.tr("This track can be renamed by doubleclicking."),
                    "TrackTags" : self.tr("tags"),
                    "TrackType" : self.tr("This track is a {} type and cannot be previewed."),
                    "TrackTypeAttachment" : self.tr("This attachment file is a {} type, it can be extracted (speedy) and viewed by clicking."),
                    "TrackVideo" : self.tr("Change the fps value if needed. Useful in case of audio lag. Normal : 23.976, 25.000 and 30.000."),

                    "WorkCanceled" : effet + self.tr(" All commands were canceled ") + effet,
                    "WorkCmd" : self.tr("""Command execution: <span style=" color:#0000c0;">{}</span>"""),
                    "WorkError" : effet + self.tr(" The last command returned an error ") + effet,
                    "WorkFinished" : effet + self.tr(" {} execution is finished ") + effet,
                    "WorkMerge" : effet + self.tr(" MKV File Tracks ") + effet,
                    "WorkProgress" : effet + self.tr(" {} execution in progress ") + effet,
                    }


        ### Recharge les textes de l'application graphique du fichier ui.py
        self.ui.retranslateUi(self)


        ### Mise au propre du widget de retour d'info et envoie de langue
        if not Configs.value("FirstRun", True): # Variable évitant l'envoie inutile d'info au démarrage
            self.ui.reply_info.clear()
            if Configs.value("DebugMode"): self.SetInfo(self.Trad["OptionUpdate"].format("Language", value), newline=True)

        else:
            Configs.setValue("FirstRun", False)


        ### Recharge le SysTrayQuit
        self.SysTrayQuit.setText(self.Trad["SysTrayQuit"])


        ### Recharge les textes des toolbutton
        ## Ce widget n'existe que s'il y a ffmpeg et avconv d'installés
        try: self.option_ffmpeg.setText(self.Trad["OptionsFFMpeg"])
        except: pass

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

        PowerList["OptionsPowerNoChange"].setText(self.Trad["OptionsPowerNoChange1"])
        PowerList["OptionsPowerNoChange"].setStatusTip(self.Trad["OptionsPowerNoChange2"])
        for nb in [2,3,4,5]:
            PowerList[nb].setText(self.Trad["OptionsPowerY"].format(nb))
            if nb == 1: PowerList[1].setStatusTip(self.Trad["OptionsPower"])
            else: PowerList[nb].setStatusTip(self.Trad["OptionsPowerX"].format(nb))

        QualityList["OptionsQualityNoChange"].setText(self.Trad["OptionsQualityNoChange1"])
        QualityList["OptionsQualityNoChange"].setStatusTip(self.Trad["OptionsQualityNoChange2"])
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
            QualityList[nb].setStatusTip(self.Trad["OptionsQualityX"].format(nb))
            QualityList[nb].setText(self.Trad["OptionsQualityY"].format(nb))

        self.TesseractCpu.setText(self.Trad["OptionsCpu1"])
        self.TesseractCpu.setStatusTip(self.Trad["OptionsCpu2"])


        ### Si un dossier de sortie a déjà été sélectionné, mise à jour du statustip et affiche l'info
        if Configs.value("OutputFolder"):
            self.ui.output_folder.setStatusTip(self.Trad["SelectedFolder1"].format(Configs.value("OutputFolder")))
            self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + str(Configs.value("OutputFolder")) + '</span>'), newline=True)


        ### Si un fichier mkv à déjà été chargé, relance le chargement du fichier pour tout traduire et remet en place les cases et boutons cochés
        if Configs.value("MKVLoaded", False):
            ## Crée lka liste des  boutons cochés
            WidgetsList = []
            for Widget in [self.ui.option_reencapsulate, self.ui.option_vobsub_srt, self.ui.option_audio]:
                if Widget.isChecked(): WidgetsList.append(Widget)

            ## Relance le chargement du fichier mkv pour tout traduire
            self.InputFile(Configs.value("InputFile"))

            ## Recoche les pistes qui l'étaient, crée une liste car MKVDicoSelect sera modifié pendant la boucle
            for x in list(MKVDicoSelect.keys()): self.ui.mkv_tracks.item(x, 1).setCheckState(2)

            ## Recoche les boutons
            for Widget in WidgetsList: Widget.setChecked(True)


    #========================================================================
    def SetInfo(self, text, color="000000", center=False, newline=False):
        """Fonction mettant en page les infos à afficher dans le widget d'information."""
        ### Saut de ligne à la demande si le widget n'est pas vide
        if newline and self.ui.reply_info.toPlainText() != "": self.ui.reply_info.append('')


        ### Envoie du nouveau texte avec mise en page
        if center: self.ui.reply_info.append("""<center><table><tr><td><span style=" color:#{};">{}</span></td></tr></table></center>""".format(color, text))
        else: self.ui.reply_info.append("""<span style=" color:#{};">{}</span>""".format(color, text))


        ### Force l'affichage de la derniere ligne
        self.ui.reply_info.moveCursor(QTextCursor.End)


    #========================================================================
    def Configuration(self):
        """Fonction affichant les options et leur valeurs."""
        # Bloque la connexion pour éviter les messages d'erreur
        self.ui.configuration_table.blockSignals(True)

        # Nécessaire à l'affichage des statustip
        self.ui.configuration_table.setMouseTracking(True)


        ### Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 2: self.ui.stackedMiddle.setCurrentIndex(2)
        while self.ui.configuration_table.rowCount() != 0: self.ui.configuration_table.removeRow(0)


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

            # Envoie du statustip
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

        # Débloque la connexion
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
        # Type de la valeur par défaut
        OptionType = type(DefaultValues[Option])

        ## En cas de type bool
        if OptionType is bool:
            # Pour gérer les vrai
            if Value in ["True", "true"]: self.OptionsValue(Option, True)

            # Pour gérer les faux
            elif Value in ["False", "false"]: self.OptionsValue(Option, False)

            # Si mauvaise valeur, on indique l'erreur et utilise la valeur par défaut
            else:
                # Message d'erreur
                QMessageBox(3, self.Trad["ErrorConfigTitle"], self.Trad["ErrorConfigText"].format(Option), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

                # Modification du texte et donc de la valeur (ça relance cette fonction)
                self.ui.configuration_table.item(x, 1).setText(str(DefaultValues[Option]))

        ## En cas de type int
        elif OptionType is int:
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
        for Key, Value in DefaultValues.items(): self.OptionsValue(Key, Value)


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
        for count in ['Bytes','KB','MB','GB']:
            if Value > -1024.0 and Value < 1024.0:
                HumanValue = "%3.1f%s" % (Value, count)
            Value /= 1024.0

        if not HumanValue: HumanValue = "%3.1f%s" % (Value, 'TB')


        ### Renvoie la valeur finale
        return(HumanValue)


    #========================================================================
    def CheckSize(self, Folder, InputSize, OutputSize, Text):
        """Fonction vérifiant qu'il y a assez de place pour travailler."""
        ### Pas de teste si valeur le demandant
        if Configs.value("CheckSizeCheckbox", False): return(False)


        ### Affiche un message s'il n'y a pas la double de la place
        if ( InputSize * 2 ) > OutputSize:
            HumanInputSize = self.HumanSize(int(InputSize))
            HumanOutputSize = self.HumanSize(int(OutputSize))

            ## Creation de la fenetre d'information
            ChoiceBox = QMessageBox(2, self.Trad["ErrorSizeTitle"], Text.format(Configs.value(Folder), HumanOutputSize, HumanInputSize), QMessageBox.NoButton, self, Qt.WindowSystemMenuHint)
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

            ## Si on veut changer de repertoire
            if Choice == 2:
                ## Affichage de la fenêtre
                FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFolder"], str(Configs.value(Folder)))
                OutputFolder = Path(FileDialogCustom.createWindow("Folder", "Open", None, Qt.Tool))[0]

                if not OutputFolder.is_dir() or OutputFolder == Path(): return(True)


                ## Creation d'un dossier temporaire
                if Folder == "FolderTemp":
                    Configs.setValue("FolderParentTemp", str(OutputFolder))
                    self.FolderTempCreate()

                else:
                    Configs.setValue(Folder, OutputFolder)


            ## Si on continue
            elif Choice == 1: return(False)

            ## Si on stoppe
            elif Choice == 0: return(True)


    #========================================================================
    def FolderTempCreate(self):
        """Fonction créant le dossier temporaire."""
        try:
            Configs.value("FolderTempWidget").remove()
        except:
            pass


        while True:
            self.FolderTempWidget = QTemporaryDir(Configs.value("FolderParentTemp") + "/mkv-extractor-qt5-")

            if self.FolderTempWidget.isValid():
                Configs.setValue("FolderTempWidget", self.FolderTempWidget)
                Configs.setValue("FolderTemp", Path(self.FolderTempWidget.path())) # Dossier temporaire
                break


    #========================================================================
    def AboutQtesseract5(self):
        """Fenetre à propos de Qtesseract5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["AboutQtesseract5Title"], self.Trad["AboutQtesseract5Text"], QMessageBox.Close, self)
        Win.setWindowIcon(QIcon().fromTheme("qtesseract5", QIcon(":/img/qtesseract5.png")))
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("qtesseract5", QIcon(":/img/qtesseract5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def AboutMKVExtractoQt5(self):
        """Fenetre à propos de Qtesseract5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["AboutTitle"], self.Trad["AboutText"].format(app.applicationVersion(), "http://www.gnu.org/copyleft/gpl.html"), QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def HelpMKVExtractoQt5(self):
        """Fenetre à propos de Qtesseract5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["HelpTitle"], self.Trad["HelpText"], QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def TheyTalkAbout(self):
        """Fenetre à propos de Qtesseract5."""
        Win = QMessageBox(QMessageBox.NoIcon, self.Trad["TheyTalkAboutTitle"], self.Trad["TheyTalkAboutText"], QMessageBox.Close, self)
        Win.setIconPixmap(QPixmap(QIcon().fromTheme("mkv-extractor-qt5", QIcon(":/img/mkv-extractor-qt5.png")).pixmap(128)))
        Win.exec()


    #========================================================================
    def MKVInfoGui(self):
        """Fonction ouvrant le fichier mkv avec le logiciel MKVInfo en mode détaché."""
        self.process.startDetached('mkvinfo -g "{}"'.format(Configs.value("InputFile")))


    #========================================================================
    def MKVMergeGui(self):
        """Fonction ouvrant le fichier mkv avec le logiciel mmg (avec le bon nom de commande) en mode détaché."""
        self.process.startDetached('{} "{}"'.format(Configs.value("mmgExec"), Configs.value("InputFile")))


    #========================================================================
    def MKVView(self):
        """Fonction ouvrant le fichier mkv avec le logiciel de lecture par défaut."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Configs.value("InputFile"))))


   #========================================================================
    def MKClean(self):
        """Fonction lançant MKClean sur le fichier mkv."""
        ### On crée automatiquement l'adresse de sorti
        if Configs.value("MKCleanRename") and (Configs.value("MKCleanSameFolder") or Configs.value("MKCleanThisFolder")):
            ## Utilisation du même dossier en entré et sorti
            if Configs.value("MKCleanSameFolder"): MKCleanTemp = "{}/Clean_{}".format(Configs.value("OutputFolder"), Configs.value("InputFile").name)

            ## Utilisation du dossier choisi
            elif Configs.value("MKCleanThisFolder"): MKCleanTemp = "{}/Clean_{}".format(Configs.value("MKCleanFolder"), Configs.value("InputFile").name)


        ### Fenêtre de sélection de sortie du fichier mkv
        else:
            ### Création de la fenêtre
            FileDialogCustom = QFileDialogCustom(self, self.Trad["SelectFileOut"], str(Configs.value("OutputFolder")), "Matroska file (*.mkv *.mks *.mka *.mk3d *.webm *.webmv *.webma)")
            Reply = FileDialogCustom.createWindow("File", "Save", None, Qt.Tool, FileName="Clean_{}".format(Configs.value("InputFile").name), AlreadyExistsTest=Configs.value("AlreadyExistsTest", False))
            MKCleanTemp = Path(Reply[0])
            Configs.setValue("AlreadyExistsTest" , Reply[1])


        ### Arrêt de la fonction s'il n'y a pas de fichier de choisi
        if MKCleanTemp == Path(): return


        ### Code à exécuter
        TempFiles = [MKCleanTemp] # Ajout du fichier de sortie dans le listing des fichiers
        Configs.setValue("Command", ["MKClean", 'mkclean --optimize "{}" "{}"'.format(Configs.value("InputFile"), MKCleanTemp)]) # Code à exécuter


        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(Configs.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(Configs.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.process.start(Configs.value("Command")[1])


    #========================================================================
    def MKValidator(self):
        """Fonction lançant MKValidator sur le fichier mkv."""
        ### Code à exécuter
        Configs.setValue("Command", ["MKValidator", 'mkvalidator "{}"'.format(Configs.value("InputFile"))])


        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(Configs.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(Configs.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.ui.progressBar.setMaximum(0) # Mode pulsation de la barre de progression
        self.process.start(Configs.value("Command")[1])




    #========================================================================
    def MKVConvert(self, File):
        """Fonction de conversion d'une vidéo en fichier mkv."""
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
            if Confirmation != 1024: return


        ### Choix du dossier de sortie
        FileDialogCustom = QFileDialogCustom(self, self.Trad["Convert6"], str(File.parent))
        Reply = FileDialogCustom.createWindow("File", "Save", None, Qt.Tool, FileName="{}.mkv".format(File.stem), AlreadyExistsTest=Configs.value("AlreadyExistsTest", False))
        OutputFile = Path(Reply[0])
        Configs.setValue("AlreadyExistsTest" , Reply[1])


        # En cas d'annulation
        if OutputFile == Path(): return


        ### Nettoyage graphique ici aussi afin de tout nettoyer avant la conversion pour un visuel plus joli
        ## Désactivation des différentes options qui pourraient être activées
        for widget in [self.ui.option_reencapsulate, self.ui.option_vobsub_srt, self.ui.option_audio]:
            widget.setChecked(False)
            widget.setEnabled(False)


        ## Désactivation des widgets
        for widget in [self.ui.mkv_info, self.ui.mkv_view, self.ui.mkv_mkvmerge, self.ui.mk_validator, self.ui.mk_clean, self.ui.mkv_execute_2]: widget.setEnabled(False)


        ## Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 0: self.ui.stackedMiddle.setCurrentIndex(0)
        while self.ui.mkv_tracks.rowCount() != 0: self.ui.mkv_tracks.removeRow(0)


        ## Suppression du titre
        self.ui.mkv_title.setText("")


        ### Mise à jour des varables
        WarningReply.clear() # Réinitialisation des retours de warning de mkvmerge
        TempFiles.clear()
        TempFiles.append(OutputFile) # Ajout du fichier dans la liste en cas d'arrêt
        Configs.setValue("Command", ["FileToMKV", 'mkvmerge -o "{}" "{}"'.format(OutputFile, File) ]) # Commande de conversion


        ### Affichage des retours
        self.SetInfo(self.Trad["WorkProgress"].format(Configs.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(Configs.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande après blocage des widgets
        self.WorkInProgress(True)
        self.process.start(Configs.value("Command")[1])


    #========================================================================
    def RemoveTempFiles(self):
        """Fonction supprimant les fichiers contenu dans la liste des fichiers temporaires."""
        ### Boucle supprimant les fichiers temporaires s'ils existent
        for Item in TempFiles:
            if Item.exists() and Item.is_file(): Item.unlink()

        TempFiles.clear()


    #========================================================================
    def OutputFolder(self, OutputFolderTemp=None):
        """Fonction de sélection du dossier de sortie, est appelée via un clic ou via un déposer de dossier."""
        ### Test
        if OutputFolderTemp == Configs.value("OutputFolder"): return()

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
        if not OutputFolderTemp.is_dir() or (OutputFolderTemp == Path() and not Configs.value("OutputSameFolder")): return()


        ### Suite de la fonction
        # Mise à jour de la variable du dossier de sorti
        Configs.setValue("OutputFolder", OutputFolderTemp)

        # Mis à jour du statustip de l'item de changement de dossier
        self.ui.output_folder.setStatusTip(self.Trad["SelectedFolder1"].format(OutputFolderTemp))

        # Envoie d'information en mode debug
        if Configs.value("DebugMode"): self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + str(OutputFolderTemp) + '</span>'), newline=True)


        ### Modifications graphiques
        # Cela n'a lieu que si un dossier et un fichier mkv sont choisis
        if Configs.value("MKVLoaded", False) and MKVDicoSelect:
            self.ui.option_reencapsulate.setEnabled(True) # Déblocage de widget
            self.ui.mkv_execute.setEnabled(True) # Déblocage de widget
            self.ui.mkv_execute_2.setEnabled(True) # Déblocage de widget
            self.ui.option_audio.setEnabled(False) # Blocage de widget
            self.ui.option_vobsub_srt.setEnabled(False) # Blocage de widget

            for valeurs in MKVDicoSelect.values(): # Boucle sur la liste des lignes
                # Recherche la valeur audio dans les sous listes
                if "audio-x-generic" == valeurs[2]: self.ui.option_audio.setEnabled(True)

                # Recherche la valeur vobsub dans les sous listes
                elif "sub" in valeurs[-1]: self.ui.option_vobsub_srt.setEnabled(True) # Déblocage de widget


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
        if not MKVLinkTemp.is_file(): return


        ### Si le fichier nécessite une conversion en mkv
        if MKVLinkTemp.suffix in (".mp4", ".m4a", ".nut", ".ogg", ".ogm", ".ogv"):
            self.MKVConvert(MKVLinkTemp) # Lancement de la conversion et la fonction sera relancée par WorkFinished


        ### Continuation de la fonction si un fichier est bien sélectionné
        else:
            # Mise à jour de variables
            Configs.setValue("InputFile", MKVLinkTemp)
            Configs.setValue("InputFolder", MKVLinkTemp.parent)

            # Envoie d'information quelque soit le mode de debug
            self.SetInfo(self.Trad["SelectedFile"].format('<span style=" color:#0000c0;">' + str(Configs.value("InputFile")) + '</span>'))

            # Mise à jour du statustip du menu d'ouverture d'un fichier mkv
            self.ui.input_file.setStatusTip(self.Trad["SelectedFile"].format(Configs.value("InputFile")))

            # Dans le cas de l'utilisation de l'option SameFolder qui permet d'utiliser le même dossier en sorti qu'en entré
            if Configs.value("OutputSameFolder"):
                self.OutputFolder(Configs.value("InputFolder"))

            # Envoie d'information en mode debug de l'adresse du dossier de sortie s'il existe
            elif Configs.value("OutputFolder") and Configs.value("DebugMode"):
                self.SetInfo(self.Trad["SelectedFolder1"].format('<span style=" color:#0000c0;">' + Configs.value("OutputFolder") + '</span>'))

            # Chargement du contenu du fichier mkv
            self.TracksLoad()



    #========================================================================
    def ComboModif(self, x, value):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'utilisation des combobox du tableau."""
        ### Si x est une chaîne, c'est que ça traite un fichier aac
        if type(x) is str:
            ## Récupération de la ligne
            x = int(x.split("-")[0])

            ## Mise à jour de variables
            if value != MKVDico[x][6]:
                MKVDico[x][6] = value
                if self.ui.mkv_tracks.item(x, 1).checkState(): MKVDicoSelect[x][6] = value


        ### Pour les autres combobox
        elif value != MKVDico[x][5]:
            ## Mise à jour de variables
            MKVDico[x][5] = value
            if self.ui.mkv_tracks.item(x, 1).checkState(): MKVDicoSelect[x][5] = value



    #========================================================================
    def TracksLoad(self):
        """Fonction de listage et d'affichage des pistes contenues dans le fichier MKV."""
        ### Curseur de chargement
        self.setCursor(Qt.WaitCursor)


        ### Mise à jour des variables
        Configs.setValue("MKVLoaded", True) # Fichier mkv chargé
        Configs.setValue("AllTracks", False) # Mode selection all
        Configs.setValue("SuperBlockTemp", True) # Sert à bloquer les signaux du tableau (impossible d'utiliser blocksignals)
        TracksList.clear() # Liste des pistes du fichier mkv
        x = 0 # Sert à indiquer les numéros de lignes
        self.ComboBoxes = {} # Dictionnaire listant les combobox
        MKVDico.clear() # Mise au propre du dictionnaire
        MKVFPS.clear() # Mise au propre du dictionnaire


        ### Création du dossier temporaire
        self.FolderTempCreate()


        ### Désactivation des différentes options qui pourraient être activés
        for widget in [self.ui.option_reencapsulate, self.ui.option_vobsub_srt, self.ui.option_audio]:
            widget.setChecked(False) # Décoche les boutons
            widget.setEnabled(False) # Grise les widgets


        ### Activation des widgets qui attendaient un fichier mkv valide
        for widget in [self.ui.mkv_info, self.ui.mkv_view, self.ui.mkv_mkvmerge, self.ui.mk_validator, self.ui.mk_clean]: widget.setEnabled(True)


        ### Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 0: self.ui.stackedMiddle.setCurrentIndex(0)
        while self.ui.mkv_tracks.rowCount() != 0: self.ui.mkv_tracks.removeRow(0)


        ### Arrêt de la fonction si le fichier contient des "
        if Configs.value("InputFile").match('*"*'):
            QMessageBox(3, self.Trad["ErrorQuoteTitle"], self.Trad["ErrorQuoteText"], QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()
            self.setCursor(Qt.ArrowCursor)
            return


        ### Récupération du retour de MKVInfo
        for line in self.LittleProcess('env LANGUAGE=en mkvinfo "{}"'.format(Configs.value("InputFile"))):
            # Récupération du titre du fichier MKV
            if "+ Title:" in line: Configs.setValue("TitleFile", line.split(": ")[1])

            # Récupération de la durée du fichier MKV
            elif "+ Duration:" in line: Configs.setValue("DurationFile", int(line.split(": ")[1].split(".")[0]))

            # Récupération de la numero de la piste pour être utilisé pour les fps ci après
            elif "+ Track number:" in line: Configs.setValue("Info", int(line.split(": ")[-1].split(")")[0]))

            # Récupération de la durée du fichier MKV
            elif "+ Default duration:" in line:
                line = line.split("(")[1].split(" ")[0]
                MKVFPS[Configs.value("Info")] = "{}fps".format(line)


        ### Récupération retour de MKVMerge
        for line in self.LittleProcess('env LANGUAGE=en mkvmerge -I "{}"'.format(Configs.value("InputFile"))):
            # Passe la boucle si le retour est vide, ce qui arrive et provoque une erreur
            if line == "": continue

            # Remplacement des \c en :
            line = line.replace("\c", ":")

            # Suppression de l'info codec codec_private_data
            if "codec_private_data" in line:
                CodecAVirer = line.split("codec_private_data:")[1].split(" ")[0]
                line = line.replace(CodecAVirer, "")

            # Si le 1er caractère est une majuscule, on ajoute la piste
            if line[0].isupper():
                TracksList.append(line)

            # Sinon, c'est que les lignes sont découpées, on conserve donc la valeur en mémoire
            else:
                TracksList[-1] = TracksList[-1] + line


        ### Affichage du titre ou du nom du fichier (sans extension) du fichier mkv
        if Configs.contains("TitleFile"): self.ui.mkv_title.setText(Configs.value("TitleFile"))
        else: self.ui.mkv_title.setText(Configs.value("InputFile").stem)


        ### Retours d'information
        self.SetInfo(self.Trad["WorkMerge"], "800080", True, True)
        self.SetInfo(self.Trad["WorkCmd"].format("mkvmerge -I {}".format(Configs.value("InputFile"))))


        ### Boucle traitant les pistes du fichier mkv
        # Il ne faut pas remplacer x par enumerate car il ne faut pas toujours incrémenter
        for Track in TracksList:
            ## Envoie du retour de mkvmerge
            self.SetInfo(Track)

            ## Traitement des pistes normales
            if Track[:5] == "Track":
                # Récupération du type de piste
                TrackType = Track.split(": ")[1].split(" ")[0]

                ## Traitement des pistes normales
                if TrackType in ["video", "audio", "subtitles"]:
                    ID = Track.split(": ")[0].split(" ")[2] # Récupération de l'ID de la piste
                    codec1 = Track.split("codec_id:")[1].split(" ")[0] # Récupération du codec de la piste

                    # Traitement spécifique aux vidéos
                    if TrackType == "video":
                        # Mise à jour des variables
                        TrackTypeName = self.Trad["Video"]
                        icone = 'video-x-generic'

                        # Récupération de l'info1
                        if " track_name:" in Track: info1 = Track.split(" track_name:")[1].split(" ")[0]
                        elif " display_dimensions:" in Track: info1 = Track.split(" display_dimensions:")[1].split(" ")[0]
                        else: info1 = ""

                        # Récupération du FPS de la piste
                        info2 = MKVFPS[int(ID)]

                        # Item servant à remplir la combobox
                        if info2 in ["23.976fps", "25.000fps", "30.000fps"]:
                            ComboItems = ["23.976fps", "25.000fps", "30.000fps"] # Liste normale des fps
                        else:
                            ComboItems = ["23.976fps", "25.000fps", "30.000fps", info2] # Liste normale + valeur trouvée
                            ComboItems.sort()

                        # Texte à afficher
                        Text = self.Trad["TrackVideo"]

                    # Traitement spécifique à l'audio
                    elif TrackType == "audio":
                        # Mise à jour des variables
                        TrackTypeName = self.Trad["Audio"]
                        icone = 'audio-x-generic'

                        # Récupération de l'info
                        if " track_name:" in Track: info1 = Track.split(" track_name:")[1].split(" ")[0]
                        elif " audio_sampling_frequency:" in Track: info1 = Track.split(" audio_sampling_frequency:")[1].split(" ")[0] + " Hz"
                        else: info1 = ""

                        # Récupération de la langue
                        if " language:" in Track: info2 = Track.split(" language:")[1].split(" ")[0]
                        else: info2 = "und"

                        # Item servant à remplir la combobox
                        ComboItems = MKVLanguages

                        # Texte à afficher
                        Text = self.Trad["TrackAudio"]

                    # Traitement spécifique aux sous titres
                    elif TrackType == "subtitles":
                        # Mise à jour des variables
                        TrackTypeName = self.Trad["Subtitles"]
                        icone = 'text-x-generic'

                        # Récupération de l'info
                        if " track_name:" in Track: info1 = Track.split(" track_name:")[1].split(" ")[0]
                        else: info1 = ""

                        # Récupération de la langue
                        if " language:" in Track: info2 = Track.split(" language:")[1].split(" ")[0]
                        else: info2 = "und"

                        # Item servant à remplir la combobox
                        ComboItems = MKVLanguages

                        # Texte à afficher
                        Text = self.Trad["TrackAudio"]

                    # Mise à jour du codec pour plus de lisibilité
                    try: codec = CodecList[codec1][0]
                    except: codec = codec1.replace("/", "_").lower()

                    # Création, remplissage et connexion d'une combobox qui est envoyée dans une nouvelle ligne du tableau
                    self.ui.mkv_tracks.insertRow(x)
                    self.ComboBoxes[x] = QComboBox()
                    self.ui.mkv_tracks.setCellWidget(x, 4, self.ComboBoxes[x])
                    self.ComboBoxes[x].addItems(ComboItems)
                    self.ComboBoxes[x].currentIndexChanged['QString'].connect(partial(self.ComboModif, x))

                    # Envoie de l'info
                    self.ComboBoxes[x].setStatusTip(Text)

                    # Traitement global des pistes simples avec remplacement des caractères spéciaux
                    info1 = info1.replace(r"\s", " ").replace(r"\2", '"').replace(r"\c", ":").replace(r"\h", "#")
                    info2 = info2.replace(r"\s", " ").replace(r"\2", '"').replace(r"\c", ":").replace(r"\h", "#")

                    # Ajout de la piste au dico
                    MKVDico[x] = [ID, "Track", icone, "unknown", info1, info2, codec]

                    # Envoie des informations dans le tableaux
                    self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem(ID)) # Envoie de l'ID
                    self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem("")) # Texte bidon permettant d'envoyer la checkbox
                    self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
                    self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID1"].format(ID)) # StatusTip
                    self.ui.mkv_tracks.setItem(x, 2, QTableWidgetItem(QIcon.fromTheme(icone, QIcon(":/img/{}.png".format(icone))),"")) # Envoie de l'icône
                    self.ui.mkv_tracks.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                    self.ui.mkv_tracks.item(x, 2).setStatusTip(self.Trad["TrackType"].format(TrackTypeName)) # StatusTip
                    self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(info1)) # Envoie de l'information
                    self.ui.mkv_tracks.item(x, 3).setStatusTip(self.Trad["TrackRename"]) # StatusTip

                    # Sélection de la valeur de la combobox
                    self.ComboBoxes[x].setCurrentIndex(self.ComboBoxes[x].findText(info2))

                    # Dans le cas de codec aac
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
                        self.ui.mkv_tracks.item(x, 5).setStatusTip(CodecList[codec1][1])

                    # Incrémentation du numéro de ligne
                    x += 1

            else:
                # Traitement spécifique aux fichiers joints
                if Track[:10] == "Attachment":
                    # mise à jour des variables
                    ID = Track.split(": ")[0].split(" ")[2]
                    typecodec = Track.split(" type '")[1].split("'")[0]
                    typetrack = typecodec.split("/")[0]
                    info2 = Track.split(" size ")[1].split(" ")[0]
                    StatusTip1 = self.Trad["TrackID2"].format(info2)
                    StatusTip2 = self.Trad["TrackTypeAttachment"].format(info2)
                    StatusTip3 = self.Trad["TrackAttachment"]
                    Item1 = ID

                    # Récupération du codec qui peut ne pas être présent (comme dans le cas d'un fichier binaire)
                    try: codec = typecodec.split("/")[1]
                    except: codec = typecodec

                    # Récupération de l'info avec remplacement des \s par des espaces
                    if " description " in Track: info1 = Track.split(" description '")[1].split("'")[0].replace(r"\s", " ")
                    elif " file name " in Track: info1 = Track.split(" file name '")[1].split("'")[0].replace(r"\s", " ")
                    else: info1 = "No info"

                    # Mise à jour du codec pour plus de lisibilité
                    if codec == "x-truetype-font": codec = "font"
                    elif codec == "vnd.ms-opentype": codec = "font OpenType"
                    elif codec == "x-msdos-program": codec = "application msdos"
                    elif codec == "plain": codec = "text"
                    elif codec in ["ogg", "ogm"]: typetrack = "media" # Ils sont reconnus entant qu'applications
                    elif codec == "x-flac": codec = "flac"
                    elif codec == "x-flv": codec = "flv"
                    elif codec == "x-ms-bmp": codec = "bmp"

                    # Icône du type de piste
                    machin = QMimeDatabase().mimeTypeForName(typecodec)
                    icone = QIcon().fromTheme(QMimeType(machin).iconName(), QIcon().fromTheme(QMimeType(machin).genericIconName())).name()

                    # Dans le cas où l'icône n'a pas été déterminée
                    if not icone:
                        if "application" in typetrack: icone = "system-run"
                        elif typetrack == "image": icone = "image-x-generic"
                        elif typetrack == "text": icone = "accessories-text-editor"
                        elif typetrack in ["media", "video", "audio"]: icone = "applications-multimedia"
                        elif typetrack == "web": icone="applications-internet"
                        else: icone = "unknown"

                    # Mise à jour du dictionnaire des pistes du fichier mkv
                    MKVDico[x] = [ID, "Attachment", icone, "document-preview", info1, info2, codec]

                # Traitement spécifique aux chapitres
                elif Track[:8] == "Chapters":
                    # Mise à jour des variables
                    icone = "x-office-address-book"
                    info1 = self.Trad["TrackChapters"]
                    info2 = Track.split(": ")[1].split(" ")[0] + " " + info1
                    StatusTip1 = self.Trad["TrackID3"].format(info2)
                    StatusTip2 = self.Trad["TrackType"].format(info2)
                    StatusTip3 = ""
                    Item1 = "chapters"
                    codec = "" # Texte bidon permettant le blocage

                    # Mise à jour du dictionnaire des pistes du fichier mkv
                    MKVDico[x] = ["NoID", "Chapters", icone, "document-preview", info1, info2, "Chapters"]


                # Traitement spécifique aux tags
                elif Track[:11] == "Global tags":
                    # Mise à jour des variables
                    icone = "text-html"
                    info1 = self.Trad["TrackTags"]
                    info2 = Track.split(": ")[1].split(" ")[0] + " " + info1
                    StatusTip1 = self.Trad["TrackID3"].format(info2)
                    StatusTip2 = self.Trad["TrackType"].format(info2)
                    StatusTip3 = ""
                    Item1 = "tags"
                    codec = "" # Texte bidon permettant le blocage

                    # Mise à jour du dictionnaire des pistes du fichier mkv
                    MKVDico[x] = ["NoID", "Global tags", icone, "document-preview", info1, info2, "Tags"]

                # Dans les autres cas on saute la boucle
                else:
                    continue


                # Création du bouton de visualisation
                Button = QPushButton(QIcon.fromTheme(icone), "")
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
                if Track[:11] == "Global tags": self.ui.mkv_tracks.item(x, 3).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

                # Incrémentation du numéro de ligne
                x += 1


        ### Retours d'information, déblocage, curseur normal
        self.SetInfo(self.Trad["WorkMerge"], "800080", True, False)
        Configs.setValue("SuperBlockTemp", False) # Variable servant à bloquer les signaux du tableau (impossible autrement)
        self.setCursor(Qt.ArrowCursor)


    #========================================================================
    def TrackView(self, x):
        ## Dans le cas d'un fichier de chapitrage
        if MKVDico[x][1] == "Chapters":
            # Fichier de sortie
            Configs.setValue("ChaptersFile", Path(Configs.value("FolderTemp"), "chapters.txt"))

            # Extraction si le fichier n'existe pas
            if not Configs.value("ChaptersFile").exists():
                with Configs.value("ChaptersFile").open('a') as ChaptersFile:
                    for line in self.LittleProcess('mkvextract chapters "{}" -s'.format(Configs.value("InputFile"))):
                        ChaptersFile.write(line+'\n')

            # Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Configs.value("ChaptersFile"))))


        ## Dans le cas de global tags
        elif MKVDico[x][1] == "Global tags":
            # Fichier de sortie
            Configs.setValue("TagsFile", Path(Configs.value("FolderTemp"), "tags.xml"))

            # Extraction si le fichier n'existe pas
            if not Configs.value("TagsFile").exists():
                with Configs.value("TagsFile").open('a') as TagsFile:
                    for line in self.LittleProcess('mkvextract tags "{}"'.format(Configs.value("InputFile"))):
                        TagsFile.write(line+'\n')

            # Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Configs.value("TagsFile"))))


        ## Dans le cas de fichier joint
        elif MKVDico[x][1] == "Attachment":
            # Teste la place disponible avant d'extraire
            FileSize = int(MKVDico[x][5])
            FreeSpaceDisk = disk_usage(str(Configs.value("FolderTemp"))).free

            # Teste de la place restante
            if self.CheckSize("FolderTemp", FileSize, FreeSpaceDisk, self.Trad["ErrorSizeAttachement"]): return()

            # Fichier de sortie
            fichier = Path(Configs.value("FolderTemp"), 'attachement_{0[0]}_{0[4]}'.format(MKVDico[x]))

            # Extraction si le fichier n'existe pas
            if not fichier.exists():
                self.LittleProcess('mkvextract attachments "{}" {}:"{}"'.format(Configs.value("InputFile"), MKVDico[x][0], fichier))

            # Ouverture du fichier
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(fichier)))


    #========================================================================
    def TrackModif(self, info):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'édition des textes."""
        ### Blocage de la fonction pendant le chargement des pistes
        if Configs.value("SuperBlockTemp", False): return


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
            for widget in (self.ui.mkv_execute, self.ui.mkv_execute_2, self.ui.option_audio, self.ui.option_vobsub_srt, self.ui.option_reencapsulate): widget.setEnabled(False)

            ## Déblocage des options si besoin
            if MKVDicoSelect and Configs.value("OutputFolder"):
                # Déblocages des boutons
                for widget in (self.ui.mkv_execute, self.ui.mkv_execute_2, self.ui.option_reencapsulate): widget.setEnabled(True)

                # Boucle sur la liste des lignes
                for valeurs in MKVDicoSelect.values():
                    # Recherche la valeur audio dans les sous listes
                    if "audio-x-generic" == valeurs[2]: self.ui.option_audio.setEnabled(True)

                    # Recherche la valeur vobsub dans les sous listes
                    elif "sub" in valeurs[-1]:  self.ui.option_vobsub_srt.setEnabled(True)

            ## Décoche les boutons s'ils sont grisés
            for widget in [self.ui.option_vobsub_srt, self.ui.option_reencapsulate, self.ui.option_audio]:
                if not widget.isEnabled(): widget.setChecked(False)


        ### Dans le cas d'une modification de texte
        else:
            ## Mise à jour du texte dans le dico des pistes
            MKVDico[x][y] = self.ui.mkv_tracks.item(x, y).text()

            ## Mise à jour du texte dans le dico des pistes sélectionnées si la ligne est sélectionnée
            if self.ui.mkv_tracks.item(x, 1).checkState(): MKVDicoSelect[x][y] = MKVDico[x][y]



    #========================================================================
    def TrackSelectAll(self, Value):
        """Fonction (dé)cochant toutes les pistes avec un clic sur le header."""
        ### Ne traiter que la colonne des coches
        if Value == 1:
            ## Dans le cas où il faut tout cocher
            if not Configs.value("AllTracks", False):
                Configs.setValue("AllTracks", True)

                # Boucle traitant toutes les lignes du tableau
                for x in range(self.ui.mkv_tracks.rowCount()): self.ui.mkv_tracks.item(x, 1).setCheckState(2)

            ## Dans le cas où il faut tout décocher
            else:
                Configs.setValue("AllTracks", False)

                # Boucle traitant toutes les lignes du tableau
                for x in range(self.ui.mkv_tracks.rowCount()): self.ui.mkv_tracks.item(x, 1).setCheckState(0)



    #========================================================================
    def CommandCreate(self):
        """Fonction créant toutes les commandes : mkvextractor, ffmpeg, mkvmerge..."""
        ### Teste de la place restante
        FileSize = Path(Configs.value("InputFile")).stat().st_size
        FreeSpaceDisk = disk_usage(str(Configs.value("OutputFolder"))).free
        if self.CheckSize("OutputFolder", FileSize, FreeSpaceDisk, self.Trad["ErrorSize"]): return()


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


        ### Si on veut uniquement réencapsuler sans rien d'autre, on affiche un message conseillant d'utiliser mmg
        if Configs.value("Reencapsulate", False) and not Configs.value("AudioConvert", False) and not Configs.value("VobsubToSrt") and not Configs.value("SubtitlesOpen"):
            if not Configs.value("MMGorMEQCheckbox"):
                ### Création de la fenêtre
                UseMMG = QMessageBox(4, self.Trad["UseMMGTitle"], self.Trad["UseMMGText"], QMessageBox.Cancel, self, Qt.WindowSystemMenuHint)
                UseMMG.setWindowFlags(Qt.WindowTitleHint | Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.CustomizeWindowHint) # Enleve le bouton de fermeture de la fenêtre

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
                if UseMMG.buttonRole(UseMMG.clickedButton()) == 5: Configs.setValue("MMGorMEQ", "MMG")
                elif UseMMG.buttonRole(UseMMG.clickedButton()) == 6: Configs.setValue("MMGorMEQ", "MEQ")
                else: return

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

            ## Traitement des pistes vidéos, maj de commandes
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
                if Configs.value("AudioConvert", False) and (Configs.value("AudioBoost", "NoChange") != "NoChange" or Configs.value("AudioStereo", False) or Configs.value("AudioQuality", "NoChange") != "NoChange" or Configs.value("AudioToAc3")):
                    # Indique la piste audio
                    dts_ffmpeg += '-vn -map 0:{} '.format(Select[0])

                    # En cas de boost du fichier ac3
                    if Configs.value("AudioBoost", 1) > 1: dts_ffmpeg += '-vol {} '.format(Configs.value("AudioBoost"))

                    # En cas de passage en stéréo
                    if Configs.value("AudioStereo", False): dts_ffmpeg += '-ac 2 '

                    # En cas de modification de qualité
                    if Configs.value("AudioQuality", "NoChange") != "NoChange": dts_ffmpeg += '-ab {0}k '.format(Configs.value("AudioQuality", 128))

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

                    # Dans le cas où il faut ré-encapsuler des fichiers aac, il faut préciser si sbr ou non
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
                    if Configs.value("VobsubToSrt", False):
                        TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_subtitles_{0[4]}.srt".format(Select)))
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_subtitles_{0[4]}.srt" '.format(Select, Configs.value("OutputFolder"))
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)

                        # Différence de nom entre la langue de tesseract et celle de mkvalidator
                        if Select[5] == "fre": Select[5] = "fra"

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
                Configs.setValue("ChaptersFile", Path(Configs.value("OutputFolder"), "chapters.txt"))


            ## Traitement des pistes de tags, maj de commandes
            elif Select[2] == "text-html":
                TempFiles.append(Path(Configs.value("OutputFolder"), "tags.xml"))
                mkvmerge += '--global-tags "{}/tags.xml" '.format(Configs.value("OutputFolder"))
                mkvextract_tag = 'mkvextract tags "{}" '.format(Configs.value("InputFile"))
                Configs.setValue("TagsFile", Path(Configs.value("OutputFolder"), "tags.xml"))


            ## Traitement des pistes jointes, maj de commandes
            else:
                mkvextract_joint += '{0[0]}:"{1}/{0[0]}_{0[4]}" '.format(Select, Configs.value("OutputFolder"))
                TempFiles.append(Path(Configs.value("OutputFolder"), "{0[0]}_{0[4]}".format(Select)))
                mkvmerge += '--attachment-name "{0[4]}" --attach-file "{1}/{0[0]}_{0[4]}" '.format(Select, Configs.value("OutputFolder"))


        ### Ajout de la commande mkvextract_track à la liste des commandes à exécuter
        if mkvextract_track: CommandList.append(["MKVExtract Tracks", 'mkvextract tracks "{}" {}'.format(Configs.value("InputFile"), mkvextract_track)])


        ### Ajout de la commande mkvextract_tag à la liste des commandes à exécuter
        # Si l'option MKV/ChaptersFile n'existe pas, il utilise le path du logiciel qui n'est du coup pas un fichier
        if mkvextract_tag and not Configs.value("ChaptersFile", Path()).is_file(): CommandList.append(["MKVExtract Tags", mkvextract_tag])


        ### Ajout de la commande mkvextract_chap à la liste des commandes à exécuter
        # Si l'option MKV/TagsFile n'existe pas, il utilise le path du logiciel qui n'est du coup pas un fichier
        if mkvextract_chap and not Configs.value("TagsFile", Path()).is_file(): CommandList.append(["MKVExtract Chapters", mkvextract_chap])


        ### Ajout de la commande mkvextract_joint à la liste des commandes à exécuter
        if mkvextract_joint: CommandList.append(["MKVExtract Attachments", 'mkvextract attachments "{}" {}'.format(Configs.value("InputFile"), mkvextract_joint)])


        ### Ajout de la commande mkvextract_joint à la liste des commandes à exécuter
        if dts_ffmpeg:
            if Configs.value("FFMpeg"): ffconv = "ffmpeg"
            else: ffconv = "avconv"

            CommandList.append([ffconv, '{} -y -i "{}" {}'.format(ffconv, Configs.value("InputFile"), dts_ffmpeg)])


        ### Ajout des commandes de conversion des vobsub en srt
        if Configs.value("VobsubToSrt", False):
            ## Pour chaque fichier à convertir
            for SubInfo in SubConvert:
                IDX = Path('{}/{}_subtitles_{}.idx'.format(Configs.value("OutputFolder"), SubInfo[0], SubInfo[1]))
                SRT = IDX.with_suffix(".srt")
                SubToRemove.append(IDX)
                CommandList.append(["Qtesseract", 'qtesseract5 -g -c {} -l "{}" "{}" "{}" '.format(Configs.value("TesseractCpu"), SubInfo[2], IDX, SRT)])


        ### Ajout de la commande mkvmerge à la liste des commandes à exécuter
        if Configs.value("Reencapsulate", False):
            ## Si l'option de renommage automatique n'est pas utilisée
            if not Configs.value("RemuxRename"):
                # Fenêtre de sélection de sortie du fichier mkv
                CheckBox = QCheckBox(self.Trad["RemuxRenameCheckBox"])

                FileDialogCustom = QFileDialogCustom(self, self.Trad["RemuxRenameTitle"], str(Configs.value("OutputFolder")), "{}(*.mka *.mks *.mkv *.mk3d *.webm *.webmv *.webma)".format(self.Trad["MatroskaFiles"]))
                Configs.setValue("OutputFile", Path(FileDialogCustom.createWindow("File", "Save", CheckBox, Qt.Tool, "MEG_{}".format(Configs.value("InputFile").name), AlreadyExistsTest=Configs.value("AlreadyExistsTest", False))))
                Configs.setValue("AlreadyExistsTest" , CheckBox.isChecked())

                # Mise à jour de la variable
                Configs.setValue("RemuxRename", CheckBox.isChecked())

                # Arrêt de la fonction si aucun fichier n'est choisi => utilise . si négatif
                if Configs.value("OutputFile") == Path(): return

            else:
                Configs.setValue("OutputFile", Path(Configs.value("OutputFolder"), "MEG_{}".format(Configs.value("InputFile").name)))

            ## Ajout du fichier mkv à la liste des fichiers
            TempFiles.append(Configs.value("OutputFile"))

            ## Dans le cas où il faut ouvrir les fichiers srt avant leur encapsulage
            if Configs.value("SubtitlesOpen"):
                SubtitlesFiles.clear()

                # Ajout des fichiers sous titres
                for Item in TempFiles:
                    if Item.suffix in (".srt", ".ssa", ".ass", ".idx"): SubtitlesFiles.append(Item)

                # Suppression des fichiers idx qui ont été convertis
                if SubToRemove:
                    for Item in SubToRemove: SubtitlesFiles.remove(Item)

                # Echo bidon pour être sur que la commande se termine bien
                if SubtitlesFiles: CommandList.append(["Open Subtitles", "echo"])


            ## Récupération du titre du fichier dans le cas où il faut réencapsuler,
            Configs.setValue("TitleFile", self.ui.mkv_title.text())

            ## Si le titre est vide, il plante mkvmerge
            if Configs.value("TitleFile"):
                CommandList.append(["MKVMerge", 'mkvmerge -o "{}" --title "{}" {}'.format(Configs.value("OutputFile"), Configs.value("TitleFile"), mkvmerge)])
                mkvextract_merge = 'mkvmerge -o "{}" --title "{}" {}'.format(Configs.value("OutputFile"), Configs.value("TitleFile"), mkvextract_merge)
            else:
                CommandList.append(["MKVMerge", 'mkvmerge -o "{}" {}'.format(Configs.value("OutputFile"), mkvmerge)])
                mkvextract_merge = 'mkvmerge -o "{}" --title "{}" {}'.format(Configs.value("OutputFile"), Configs.value("InputFile").name, mkvextract_merge)


        ### Modifications graphiques
        self.WorkInProgress(True) # Blocage des widgets


        ### Code à executer
        Configs.setValue("Command", CommandList.pop(0)) # Récupération de la 1ere commande


        ### Envoie de textes
        self.SetInfo(self.Trad["WorkProgress"].format(Configs.value("Command")[0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(Configs.value("Command")[1])) # Envoie d'informations


        ### Lancement de la commande
        self.process.start(Configs.value("Command")[1])


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
            if len(CommandList) > 1: self.ui.mkv_pause.show() # Affiche le bouton pause
            for widget in (self.ui.menubar, self.ui.tracks_bloc): widget.setEnabled(False)  # Blocage de widget


        ### Dans le cas où le travail vient de se terminer (bien ou mal)
        else:
            ## Modifications graphiques
            self.ui.mkv_execute.show() # Affiche le bouton exécuter
            self.ui.mkv_execute_2.setEnabled(True) # Dégrise le bouton exécuter
            self.ui.mkv_stop.hide() # Cache le bouton arrêter
            self.ui.mkv_pause.hide() # Cache le bouton pause
            if self.ui.progressBar.format() != "%p %": self.ui.progressBar.setFormat("%p %") # Réinitialisation du bon formatage de la barre de progression
            if self.ui.progressBar.maximum() != 100: self.ui.progressBar.setMaximum(100) # Réinitialisation de la valeur maximale de la barre de progression
            if self.ui.stackedMiddle.currentIndex() != 0: self.ui.stackedMiddle.setCurrentIndex(0) # Réaffiche le tableau des pistes si ce n'est plus lui qui est affiché
            for widget in (self.ui.menubar, self.ui.tracks_bloc): widget.setEnabled(True) # Blocage de widget
            self.setCursor(Qt.ArrowCursor) # Curseur normal


    #========================================================================
    def WorkReply(self):
        """Fonction recevant tous les retours du travail en cours."""
        ### Récupération du retour (les 2 sorties sont sur la standard)
        data = self.process.readAllStandardOutput()


        ### Converti les data en textes et les traite
        for line in bytes(data).decode('utf-8').splitlines():
            ## Passe la boucle si le retour est vide, ce qui arrive et provoque une erreur
            if line == "": continue


            ## Dans le cas d'un encapsulation
            elif Configs.value("Command")[0] == "MKVMerge":
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%": line = int(line.split(": ")[1].strip()[0:-1]) #


            # Dans le cas d'une conversion
            elif Configs.value("Command")[0] == "FileToMKV":
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%": line = int(line.split(": ")[1].strip()[0:-1])


            ## MKVExtract renvoie une progression ou les contenus des fichiers de tags et chapitres. Les fichiers joints ne renvoient rien.
            elif "MKVExtract" in Configs.value("Command")[0]:
                # Récupère le nombre de retour en cas de présence de pourcentage
                if line[-1] == "%": line = int(line.split(": ")[1].strip()[0:-1])


            ## MKValidator ne renvoie pas de pourcentage mais des infos ou des points, on vire les . qui indiquent un travail en cours
            elif Configs.value("Command")[0] == "MKValidator":
                line = line.strip().replace('.','')


            ## MKClean renvoie une progression et des infos, on ne traite que les pourcentages
            elif Configs.value("Command")[0] == "MKClean":
                if line[-1] == "%": line = int(line.split(": ")[1].strip()[0:-1])


            ## FFMpeg ne renvoie pas de pourcentage mais la durée de vidéo encodée en autre
            elif Configs.value("Command")[0] in ["ffmpeg", "avconv"]:
                if "time=" in line and Configs.contains("DurationFile"):
                    # Pour les versions renvoyant : 00:00:00
                    try:
                        value = line.split("=")[2].strip().split(".")[0].split(":")
                        value = timedelta(hours=int(value[0]), minutes=int(value[1]), seconds=int(value[2])).seconds

                    # Pour les versions renvoyant : 00000 secondes
                    except:
                        value = line.split("=")[2].strip().split(".")[0]

                    # Pourcentage maison se basant sur la durée du fichier
                    line = int((value * 100) / Configs.value("DurationFile"))


            ## Qtesseract
            elif Configs.value("Command")[0] == "Qtesseract":
                if "Temporary folder:" in line:
                    Configs.setValue("QtesseractFolder", Path(line.split(": ")[1]))

                try:
                    line = int(line)
                except:
                    pass


            ## Affichage du texte ou de la progression si c'est une nouvelle valeur
            if line and line != Configs.value("WorkOldLine", ""): # Comparaison anti doublon
                Configs.setValue("WorkOldLine", line) # Mise à jour de la variable anti doublon

                # Envoie du pourcentage à la barre de progression si c'est un nombre
                if type(line) is int: self.ui.progressBar.setValue(line)

                # Envoie de l'info à la boite de texte si c'est du texte
                else:
                    # On ajoute le texte dans une variable en cas de conversion (utile pour le ressortir dans une fenêtre)
                    if Configs.value("Command")[0] == "FileToMKV": WarningReply.append(line)

                    self.SetInfo(line)


    #========================================================================
    def WorkFinished(self):
        """Fonction appelée à la fin du travail, que ce soit une fin normale ou annulée."""
        # Configs.value("Command")[0] : Nom de la commande
        # Configs.value("Command")[1] : Commande à executer ou liste de fichiers
        ### Si le travail est annulé (via le bouton stop ou via la fermeture du logiciel) ou a renvoyée une erreur, mkvmerge renvoie 1 s'il y a des warnings
        if (Configs.value("Command")[0] == "FileToMKV" and self.process.exitCode() == 2) or (self.process.exitCode() != 0 and Configs.value("Command")[0] != "FileToMKV"):
            ## Arret du travail
            if Configs.value("Command")[0] == "Qtesseract": self.WorkStop("SrtError")
            else: self.WorkStop("Error")

            ## Arret de la fonction
            return


        ### Traitement différent en fonction de la commande, rien de particulier pour MKValidator, MKClean, FFMpeg
        if Configs.value("Command")[0] == "Open Subtitles":
            # Boucle ouvrant tous les fichiers srt d'un coup
            for Item in SubtitlesFiles: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Item)))


        elif "MKVExtract" in Configs.value("Command")[0] == "MKVExtract" and (CommandList and "MKVExtract" in CommandList[0][0]): # Systeme n'affichant pas la fin tant qu'il y a des extractions
            Configs.setValue("Command", CommandList.pop(0)) # Récupération de la commande suivante à exécuter
            self.SetInfo(self.Trad["WorkCmd"].format(Configs.value("Command")[1]), newline=True) # Envoie d'informations
            self.process.start(Configs.value("Command")[1]) # Lancement de la commande
            return


        ### Indication de fin de pack de commande
        if Configs.value("Command")[0] != "Open Subtitles":
            self.SetInfo(self.Trad["WorkFinished"].format(Configs.value("Command")[0]), "800080", True) # Travail terminé
            self.ui.progressBar.setValue(100) # Mise à 100% de la barre de progression pour signaler la fin ok
            if Configs.value("SysTray"): self.SysTrayIcon.showMessage(self.Trad["SysTrayFinishTitle"], self.Trad["SysTrayFinishText"].format(Configs.value("Command")[0], QSystemTrayIcon.Information, 3000))


        ### Lancement de l'ouverture du fichier mkv, ici pour un soucis esthétique du texte affiché
        # Dans le cas d'une conversion
        if Configs.value("Command")[0] == "FileToMKV":
            ## Si mkvmerge a renvoyé un warning, on l'indique
            if self.process.exitCode() == 1 and not Configs.value("ConfirmWarning"):
                # Création d'une fenêtre de confirmation avec case à cocher pour se souvenir du choix
                dialog = QMessageBox(QMessageBox.Warning, self.Trad["Convert3"], self.Trad["Convert4"], QMessageBox.NoButton, self)
                CheckBox = QCheckBox(self.Trad["Convert5"])
                dialog.setCheckBox(CheckBox)
                dialog.setStandardButtons(QMessageBox.Ok)
                dialog.setDefaultButton(QMessageBox.Ok)
                dialog.setDetailedText("\n".join(WarningReply))
                dialog.exec_()

                # Mise en mémoire de la case à cocher
                Configs.setValue("ConfirmWarning", CheckBox.isChecked())

            ## Lancement de la fonction d'ouverture du fichier mkv créé avec le nom du fichier
            self.InputFile(TempFiles[-1])


        ## Dans le cas ou il faut mettre en pause entre 2 jobs
        if Configs.value("WorkPause", False) or Configs.value("Command")[0] == "Open Subtitles":
            # Remise à False de la variable pause
            Configs.setValue("WorkPause", False)

            # Mise en pause du travail avec arret si besoin
            if not self.WorkPause(): return


        ### S'il reste des commandes, exécution de la commande suivante
        if CommandList:
            ## Cache le bouton de pause s'il n'y a plus qu'une seule commande à lancer
            if len(CommandList) == 1: self.ui.mkv_pause.hide()

            ## Récupération de la commande suivante à exécuter
            Configs.setValue("Command", CommandList.pop(0))

            ## Mise à 0% de la barre de progression pour signaler le début du travail
            self.ui.progressBar.setValue(0)

            ## Évite de dire que la cmd mkmerge se lance et que le log est en pause
            if Configs.value("Command")[0] != "Open Subtitles": self.SetInfo(self.Trad["WorkProgress"].format(Configs.value("Command")[0]), "800080", True, True)

            ## Dans le cas des commandes bidons
            if Configs.value("Command")[1] != "echo": self.SetInfo(self.Trad["WorkCmd"].format(Configs.value("Command")[1]))

            ## Lancement de la commande suivante
            self.process.start(Configs.value("Command")[1])


        ### Si c'était la dernière commande
        else:
            ## Si l'option de suppression des fichiers temporaire est activée lors du merge
            if Configs.value("DelTemp") and Configs.value("Command")[0] == "MKVMerge":
                # Suppression du fichier mkv de sortie de la liste
                TempFiles.remove(Configs.value("OutputFile"))

                # Suppression des fichiers temporaires
                self.RemoveTempFiles()

            ## Remise en état des widgets
            self.WorkInProgress(False)

            if Configs.value("SysTray"): self.SysTrayIcon.showMessage(self.Trad["SysTrayFinishTitle"], self.Trad["SysTrayTotalFinishText"], QSystemTrayIcon.Information, 3000)


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
        Resume.exec_()

        ## Fin de la fonction
        if Resume.clickedButton() != ResumeButton:
            ## Si la reprise n'est pas confirmée, on arrete le travail en cours
            self.WorkStop("Pause")

            return(False)

        else:
            return(True)



    #========================================================================
    def WorkStop(self, Type):
        """Fonction d'arrêt du travail en cours."""
        ### Type : Error (en cas de plantage), Stop (en cas d'arret du travail), Close (en cas de fermeture du logiciel), Pause (en cas d'annulation pendant la pause), SrtError (en cas d'erreur tesseract)
        ### En cas de pause, il n'y a pas de travail en cours
        if not Type in ("Pause", "SrtError"):
            ## Teste l'etat du process pour ne pas le killer plusieurs fois (stop puis error)
            if self.process.state() == 0: return

            ## Kill le boulot en cours
            self.process.kill()
            if not self.process.waitForFinished(1000): self.process.kill() # Attend que le travail soit arrété pdt 1s

        ### Suppression des fichiers temporaires
        self.RemoveTempFiles()

        ### Suppression du dossier temporaire de Qtesseract5
        if Configs.contains("QtesseractFolder"):
            if Configs.value("QtesseractFolder").exists():
                rmtree(str(Configs.value("QtesseractFolder")))
                Configs.remove("QtesseractFolder")

        ### Réinitialisation de la liste des commandes
        CommandList.clear()

        ### Envoie du texte le plus adapté
        if Type in ("Stop", "Pause"): self.SetInfo(self.Trad["WorkCanceled"], "FF0000", True) # Travail annulé
        elif Type in ("Error", "SrtError"): self.SetInfo(self.Trad["WorkError"], "FF0000", True) # Erreur pendant le travail
        elif Type == "Close": return

        ### Modifications graphiques
        self.ui.progressBar.setValue(0) # Remise à 0 de la barre de progression signifiant une erreur
        self.WorkInProgress(False) # Remise en état des widgets



    #========================================================================
    def SysTrayClick(self, event):
        """Fonction gérant les clics sur le system tray."""
        ### Si la fenetre est cachée ou si elle n'a pas la main
        if not self.isVisible() or (not self.isActiveWindow() and self.isVisible()):
            self.show()
            self.activateWindow()


        ### Si la fenetre est visible
        else:
            self.hide()


    #========================================================================
    def dragEnterEvent(self, event):
        """Fonction appelée à l'arrivée d'un fichier à déposer sur la fenetre."""
        # Impossible d'utiliser mimetypes car il ne reconnaît pas tous les fichiers...
        ### Récupération du nom du fichier
        Item = Path(event.mimeData().urls()[0].path())

        ### Acceptation de l'événement en cas de fichier et de fichier valide (pour le fichier d'entrée)
        if Item.is_file() and Item.suffix in (".m4a", ".mk3d", ".mka", ".mks", ".mkv", ".mp4", ".nut", ".ogg", ".ogm", ".ogv", ".webm", ".webma", ".webmv"): event.accept()


        ### Acceptation de l'événement en cas de dossier (pour le dossier de sortie)
        elif Item.is_dir(): event.accept()


    #========================================================================
    def dropEvent(self, event):
        """Fonction appelée à la dépose du fichier/dossier sur la fenêtre."""
        # Impossible d'utiliser mimetypes car il ne reconnaît pas tous les fichiers...
        ### Récupération du nom du fichier
        Item = Path(event.mimeData().urls()[0].path())


        ### En cas de fichier (pour le fichier d'entrée)
        if Item.is_file():
            ## Vérifie que l'extension fasse partie de la liste et lance la fonction d'ouverture du fichier mkv avec le nom du fichier
            if Item.suffix in (".mka", ".mks", ".mkv", ".mk3d", ".webm", ".webmv", ".webma"): self.InputFile(Item)

            ## Nécessite une conversion de la vidéo
            elif Item.suffix in (".mp4", ".nut", ".ogg"): self.MKVConvert(Item)


        ## Lancement de la fonction de gestion du dossier de sorti en cas de dossier (pour le dossier de sortie)
        elif Item.is_dir(): self.OutputFolder(Item) #


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
        ### Bloque les signaux sinon cela save toujours off
        self.ui.feedback_widget.blockSignals(True)


        ### Arrêt du travail en cours
        self.WorkStop("Close")


        ### Si l'option de suppression du fichier des fichiers et url recentes est activée, on l'efface
        if Configs.value("RecentInfos"):
            RecentFile = Path(QDir.homePath(), '.config/MKVExtractorQt5.pyrc')
            if RecentFile.exists(): RecentFile.unlink()


        ### Enregistrement de l'intérieur de la fenêtre (dockwidget)
        Configs.setValue("WinState", self.saveState())


        ### Si on a demandé à conserver l'aspect
        if Configs.value("WindowAspect"): Configs.setValue("WinGeometry", self.saveGeometry())


        ### Si on a rien demandé, on détruit la valeur
        elif Configs.contains("WinGeometry"): Configs.remove("WinGeometry")


        ### Supression du dossier temporaire
        try: Configs.value("FolderTempWidget").remove()
        except: pass


        ### Suppression des clés qu'on ne garde pas
        # Options temporaires seulement
        for Key in ("Reencapsulate", "VobsubToSrt", "DtsToAc3", "MKVLoaded", "ChaptersFile", "TagsFile", "TitleFile", "DurationFile", "Command", "FirstRun", "SuperBlockTemp", "WorkOldLine", "FolderTemp", "FolderTempWidget", "Info", "OutputFile", "AudioQuality", "AudioBoost", "AudioStereo", "SubtitlesOpen", "WorkPause", "AudioConvert", "AllTracks", "QtesseractFolder"): Configs.remove(Key)




#############################################################################
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationVersion("5.4.0")
    app.setApplicationName("MKV Extractor Qt5")

    ### Dossier du logiciel, utile aux traductions et à la liste des codecs
    AppFolder = Path(sys.argv[0]).resolve().parent


    ### Création des dictionnaires et listes facilement modifiables partout
    MKVDico = {} # Dictionnaire qui contiendra toutes les pistes du fichier mkv
    MKVFPS = {} # Dictionnaire qui contiendra les FPS des pistes du fichier mkv
    MD5Dico = {} # Dictionnaire qui contiendra les sous titres à reconnaître manuellement
    MKVDicoSelect = {} # Dictionnaire qui contiendra les pistes sélectionnées
    MKVLanguages = [] # Liste qui contiendra et affichera dans les combobox les langues dispo (audio et sous titres)
    PowerList = {} # Dictionnaire qui contiendra les widgets de gestion de puissance de fichier ac3
    QualityList = {} # Dictionnaire qui contiendra les widgets de gestion de la qualité de fichier ac3
    TempFiles = [] # Liste des fichiers temporaires pré ré-encapsulage ou en cas d'arrêt du travail
    CommandList = [] # Liste des commandes à exécuter
    SubtitlesFiles = [] # Adresse des fichiers sous titres à ouvrir avant l'encapsulage
    TracksList = [] # Liste brute des pistes retournée par MKVMerge -I
    WarningReply = [] # Retour de mkvmerge en cas de warning


    ### Configs du logiciel
    # Valeurs par défaut des options, pas toutes (MMGorMEQ, les valeurs de la fenêtre, l'adresse du dernier fichier ouvert)
    DefaultValues = { "AlreadyExistsTest" : False, # Option ne signalant que le fichier existe déjà
                    "CheckSizeCheckbox" : False, # Option ne signalant pas le manque de place
                    "DebugMode" : False, # Option affichant plus ou d'infos
                    "DelTemp" : False, # Option de suppression des fichiers temporaires
                    "ConfirmErrorLastFile" : False, # Ne plus prévenir en cas d'absence de fichier au demarrage
                    "Feedback" : True, # Option affichant ou non les infos de retours
                    "FeedbackBlock" : False, # Option bloquant les infos de retours
                    "FolderParentTemp" : QDir.tempPath(), # Dossier temporaire dans lequel extraire les pistes pour visualisation
                    "FFMpeg" : False, # Commande de conversion avconv ou ffmpeg
                    "LastFile" : False, # Option conservant en mémoire le dernier mkv ouvert
                    "MMGorMEQ" : "MEQ", # Logiciel à utiliser
                    "MMGorMEQCheckbox" : False, # Valeur sautant la confirmation du choix de logiciel à utiliser
                    "ConfirmConvert" : False, # Valeur sautant la confirmation de conversion
                    "ConfirmWarning" : False, # Valeur sautant l'information du warning de conversion
                    "InputFolder" : Path(QDir.homePath()), # Dossier du fichier mkv d'entrée : Path(MKVLink).name
                    "OutputFolder" : Path(QDir.homePath()), # Dossier de sortie
                    "Language" : QLocale.system().name(), # Langue du système
                    "RecentInfos" : True, # Option de suppression du fichier des fichiers et adresses récentes
                    "RemuxRename" : False, # Renommer automatiquement le fichier de sorti remux
                    "OutputSameFolder" : True, # Option d'utilisation du même dossier de sortie que celui du fichier mkv
                    "AudioStereo" : False, # Option de conversion en canal double
                    "SubtitlesOpen" : False, # Option d'ouverture des sous-titres avant leur ré encapsulage
                    "SysTray" : True, # Option affichant l'icone du system tray
                    "TesseractCpu" : QThread.idealThreadCount(), # Nombre de cpu utilisable par Tesseract
                    "WindowAspect" : True # Conserver la fenêtre et sa géométrie
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
                    if Configs.value(Key) == "true": Configs.setValue(Key, True)
                    else: Configs.setValue(Key, False)

                elif KeyType is int: # Dans le cas de nombre
                    Configs.setValue(Key, int(Configs.value(Key)))

    ## S'il y a eu un problème, on réinitialise tout
    except:
        for Key, Value in DefaultValues.items():
            Configs.setValue(Key, Value)


    MKVExtractorQt5Class = MKVExtractorQt5()
    MKVExtractorQt5Class.setAttribute(Qt.WA_DeleteOnClose)
    sys.exit(app.exec_())