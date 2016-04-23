#!/usr/bin/python3
# -*- coding: utf-8 -*-


# L'icone de la barre des taches n'est pas celle du logiciel


from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import sys
import os
import shutil # Utilisé pour tester la présence d'executable : which, disk_usage, move
import hashlib # Utilisé pour détecter les doublons lors de la traduction des sous titres
from tempfile import TemporaryDirectory # Utilisé pour la creation du dossier temporaire
from functools import partial # Utilisé pour envoyer plusieurs infos via les connexions
import datetime # utile pour le calcul de la progression de la conversion en ac3
from pathlib import Path # Necessaire pour la recherche de fichier
import configparser # Pour charger les informations de config

from ui_MKVExtractorQt import Ui_mkv_extractor_qt # Utilisé pour la fentre pricniaple

Version = "5.3.0"

### Creation des dictionnaires et listes facilement modifiables partout
MKVDico = {} # Dictionnaire qui contiendra toutes les pistes du fichier mkv
MKVFPS = {} # Dictionnaire qui contiendra les FPS des pistes du fichier mkv
MD5Dico = {} # Dictionnaire qui contiendra les sous titres à reconnaitre manuellement
MKVSubSrt = {} # Dictionnaire d'information utiles pour la conversion SUB => SRT
MKVDicoSelect = {} # Dictionnaire qui contiendra les pistes séléctionnées
MKVLanguages = [] # Liste qui contiendra et affichera dans les combobox les langues dispo (audio et sous titres)
PowerList = {} # Dictionnaire qui contiendra les widgets de gestion de puissance de fichier ac3
QualityList = {} # Dictionnaire qui contiendra les widgets de gestion de la qualité de fichier ac3
TesseractLanguages = [] # Liste qui contiendra les langues disponibles pour Tesseract


### Dictionnaire contenant les autres infos utiles
Variables = {"Cmd" : "", # Commande à éxecuter
             "CmdList" : [], # Liste des commandes à executer
             "ConfigFile" : Path(QDir.homePath(), '.config/MKV-Extractor-PyQt5.cfg'), # Fichier de configuration
             "FirstRun" : True, # Variable bloquante pour le chargement des textes au demarrage
             "ImgFilesNb" : "", # Nombre de sous titres images
             "ImgFiles" : [], # Liste des fichiers sous titres images
             "MKVChapters" : "", # Adresse du fichier de chapitrage
             "MKVFileNameIn" : "", # Nom du fichier mkv d'entrée : os.path.basename(MKVLink)
             "MKVLinkOut" : "", # Adresse du fichier mkv de sortie (mkclean et mkvmerge)
             "MKVLinkIn" : "", # Adresse du fichier mkv d'entrée
             "MKVLoad" : False, # Indication sur le chargement d'un fichier mkv (chgt de langue, choix dossier de sortie)
             "MKVTags" : "", # Adresse du fichier de tags
             "MKVSubtitles" : [], # Adresse des fichiers sous titres à ouvrir avant l'encapsulage
             "MKVTitle" : "", # Titre du fichier mkv
             "MKVTime" : 0, # Durée du fichier mkv
             "SubNb" : 0, # Nombre de sous titres à reconnaitre manuellement
             "SubNum" : 0, # Numero du sous titre à reconnaitre manuellement
             "SuperBlock" : False, # Bloqueur manuel des signaux du tableau (impossible autrement)
             "TempFolder" : "", # Dossier de travail temporaire, obligation qu'il soit là sinon se ferme en fin de fonction
             "TempFolderName" : "", # Nom du dossier temporaire
             "TempFiles" : [], # Liste des fichiers temporraires pré ré-encapsulage ou en cas d'arret du travail
             "TempInfo" : "", # Variable pouvant etre utiliséee un tour sur l'autre
             "Tracks" : [], # Liste brute des pistes retournée par MKVMerge -I
             "WorkOldLine" : "", # Variable anti doublon pendant le travail
             "WorkPause" : False, # Variable indiquantla mise en pause du travail en court
             "WorkStop" : False, # Variable indiquant l'arret du travail en court
             "VobsubToSrt" : False, # Option de conversion des vobsub en srt
             "Reencapsulate" : False, # Option de ré encapsulage
             "DtsToAc3" : False, # Option de conversion des dts en ac3
             "subp2pgm" : None, # Adresse de l'executable
             "subptools" : None, # Adresse de l'executable
            }


### Création du dossier de configuration s'il n'existe pas (il ne stockera que le fichier config)
if not Variables["ConfigFile"].parent.exists():
    Variables["ConfigFile"].parent.mkdir(parents=True)


### Configs du logiciel
# Pas de try car avec optionxform on a une liste vide, pas une erreur
# Chargement des configs
Config = configparser.ConfigParser() # Chargement du fichier de cfg
Config.optionxform = lambda option: option # Conserve le nom des variables
Config.read(str(Variables["ConfigFile"])) # Lecture du fichier de cfg

# Vérifie le nom d'item
if len(Config['DEFAULT']) == 16:
    Configs = {}

    for Item, Value in Config['DEFAULT'].items():
        if Item in ["DelConfig", "DelTemp", "FFMpeg", "SameFolder", "Stereo", "SubtitlesOpen", "ViewInfo", "WinMax"]:
            Configs[Item] = Config['DEFAULT'].getboolean(Item)

        elif Item in ["Ac3Kbits", "Ac3Boost", "WinWidth", "WinHeight"]:
            Configs[Item] = int(Value)

        elif Item in ["MKVDirNameIn", "MKVDirNameOut"]:
            Configs[Item] = Path(Value)

        elif Item == "Language":
            Configs[Item] = Value

        elif Item == "SplitterSizes":
            Configs[Item] = []
            for Int in Value.replace("[", "").replace("]", "").replace(" ", "").split(","):
                Configs[Item].append(int(Int))

else:
    # Valeurs par defaut
    Configs = { "Ac3Kbits" : 128, # Qualité des fichiers ac3 convertis
                "Ac3Boost" : 1, # Puissance des fichiers ac3 convertis
                "DelConfig" : False, # Option de reinitialisation des config (au prochain reboot)
                "DelTemp" : False, # Option de suppression des fichiers temporaires
                "FFMpeg" : False, # Commande de conversion aconv ou ffmpeg
                "MKVDirNameIn" : Path().resolve(), # Dossier du fichier mkv d'entrée : Path(MKVLink).name
                "MKVDirNameOut" : Path().resolve(), # Dossier de sortie
                "Language" : QLocale.system().name(), # Langue du systeme
                "SameFolder" : True, # Option d'utilisation du même dossier de sortie que celui du fichier mkv
                "Stereo" : False, # Option de conversion en canal double
                "SplitterSizes" : None, # Permet de sauvegarder et de charger l'aspect du splitter
                "SubtitlesOpen" : False, # Option d'ouverture des sous-titres avant leur ré encapsulage
                "ViewInfo" : True, # Affichage du retour d'info
                "WinMax" : False, # Fenetre maximisée ou non
                "WinWidth" : 615, # Largeur de la fenetre
                "WinHeight" : 510 # Hauteur de la fenetre
                }


### Dictionnaire listant les codecs connu par mkvmerge
CodecList = {"V_MS/VFW/FOURCC": ["vfw", "Microsoft Video Codec Manager"],
             "V_UNCOMPRESSED": ["raw", "Raw Uncompressed Video Frames"],
             "V_MPEG4/ISO/AVC": ["mpeg4", "MPEG4 ISO (x264)"],
             "V_MPEG4/ISO/SP": ["mpeg4", "MPEG4 ISO simple profile (DivX4)"],
             "V_MPEG4/ISO/ASP": ["mpeg4", "MPEG4 ISO advanced simple profile (DivX5, XviD, FFMPEG)"],
             "V_MPEG4/ISO/AP": ["mpeg4", "MPEG4 ISO advanced profile"],
             "V_MPEG4/MS/V3": ["mpeg4", "Microsoft MPEG4 V3"],
             "V_MPEG1": ["mpeg1", "MPEG 1"],
             "V_MPEG2": ["mpeg1", "MPEG 2"],
             "V_REAL/RV10": ["rv", "RealVideo 1.0 aka RealVideo 5"],
             "V_REAL/RV20": ["rv", "RealVideo G2 and RealVideo G2+SVT"],
             "V_REAL/RV30": ["rv", "RealVideo 8"],
             "V_REAL/RV40": ["rv", "RealVideo 9"],
             "V_QUICKTIME": ["qt", "QuickTime"],
             "V_THEORA": ["ogv", "Theora"],
             "V_PRORES": ["prores", "Apple ProRes"],
             "V_SNOW": ["snow", "Opaque codec init data"],
             "V_VP8": ["vp8", "After vp7 and before vp9 owned by Google"],
             "V_VP9": ["vp9", "After vp8 owned by Google"],
             "V_DIRAC": ["drc", "Developed by BBC Research"],
             "V_MPEGH/ISO/HEVC": ["mpegh", "future replacement of MPEG"],
             "A_MPEG/L1": ["mp1", "MPEG Audio 1, 2 Layer I"],
             "A_MPEG/L2": ["mp2", "MPEG Audio 1, 2 Layer II"],
             "A_MPEG/L3": ["mp3", "MPEG Audio 1, 2, 2.5 Layer III"],
             "A_PCM/INT/BIG": ["pcm", "Integer Big Endian"],
             "A_PCM/INT/LIT": ["pcm", "Integer Little Endian"],
             "A_PCM/FLOAT/IEEE": ["pcm", "Floating Point, IEEE compatible"],
             "A_MPC": ["mpc", "MPC (musepack) SV8"],
             "A_AC3": ["ac3", "Dolby AC3"],
             "A_AC3/BSID9": ["ac3", "Dolby AC3"],
             "A_AC3/BSID10": ["ac3", "Dolby AC3"],
             "A_EAC3": ["eac3", "Enhanced AC-3 - Dolby Digital Plus"],
             "A_ALAC": ["alac", "Apple Lossless Audio Codec"],
             "A_DTS": ["dts", "Digital Theatre System"],
             "A_DTS/EXPRESS": ["dts", "Digital Theatre System Express"],
             "A_DTS/LOSSLESS": ["dts", "Digital Theatre System Lossless"],
             "A_VORBIS": ["ogg", "Vorbis"],
             "A_FLAC": ["flac", "Free Lossless Audio Codec"],
             "A_REAL/14_4": ["ra", "Real Audio 1"],
             "A_REAL/28_8": ["ra", "Real Audio 2"],
             "A_REAL/COOK": ["ra", "Real Audio Cook Codec (codename: Gecko)"],
             "A_REAL/SIPR": ["ra", "Sipro Voice Codec"],
             "A_REAL/RALF": ["ra", "Real Audio Lossless Format"],
             "A_REAL/ATRC": ["ra", "Sony Atrac3 Codec"],
             "A_MS/ACM": ["acm", "Microsoft Audio Codec Manager"],
             "A_AAC": ["aac", "No more information"],
             "A_AAC/MPEG2/MAIN": ["aac", "MPEG2 Main Profile"],
             "A_AAC/MPEG2/LC": ["aac", "Low Complexity"],
             "A_AAC/MPEG2/LC/SBR": ["aac sbr", "Low Complexity with Spectral Band Replication"],
             "A_AAC/MPEG2/SSR": ["aac", "Scalable Sampling Rate"],
             "A_AAC/MPEG4/MAIN": ["aac", "MPEG4 Main Profile"],
             "A_AAC/MPEG4/LC": ["aac", "Low Complexity"],
             "A_AAC/MPEG4/LC/SBR": ["aac sbr", "Low Complexity with Spectral Band Replication"],
             "A_AAC/MPEG4/SSR": ["aac", "Scalable Sampling Rate"],
             "A_AAC/MPEG4/LTP": ["aac", "Long Term Prediction"],
             "A_QUICKTIME": ["qta", "Audio taken from QuickTime files"],
             "A_QUICKTIME/QDMC": ["qdmc", "QuickTime QDesign Music"],
             "A_OPUS": ["opus", "A lossy audio coding format"],
             "A_MLP": ["mlp", "Meridian Lossless Packing"],
             "A_TTA1": ["tta", "The True Audio lossles audio compressor"],
             "A_WAVPACK4": ["wv", "WavPack lossles audio compressor"],
             "A_TRUEHD": ["thd", "Dolby TrueHD Lossless Audio"],
             "S_TEXT/UTF8": ["srt", "UTF-8 Plain Text"],
             "S_TEXT/SSA": ["ssa", "Subtitles Format"],
             "S_TEXT/ASS": ["ass", "Advanced Subtitles Format"],
             "S_TEXT/USF": ["usf", "Universal Subtitle Format"],
             "S_TEXT/ASCII": ["asc", "American Standard Code of Information Interchange"],
             "S_IMAGE/BMP": ["bmp", "Bitmap"],
             "S_VOBSUB": ["sub", "VobSub subtitles"],
             "S_VOBSUB/ZLIB": ["sub", "VobSub subtitles compressed"],
             "S_KATE": ["kate", "Karaoke And Text Encapsulation"],
             "S_HDMV/PGS": ["pgs", "Presentation Grapic Stream"]}



#========================================================================
def IconBis(Icon, Type):
    """Fonction créant le code pour afficher l'icone du theme avec une icone des ressources si la 1ere n'existe pas."""
    # http://standards.freedesktop.org/icon-theme-spec/icon-theme-spec-latest.html
    # http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html

    # Si l'icone existe dans le theme
    if QIcon().hasThemeIcon(Icon):
        # S'il faut un pixmap
        if Type == "Pixmap":
            return QPixmap(QIcon().fromTheme(Icon).pixmap(24))

        # S'il faut une icone
        elif Type == "Icon":
            return QIcon().fromTheme(Icon)

    # Si l'icone n'existe pas, on utilise celle des ressources
    else:
        # S'il faut un pixmap
        if Type == "Pixmap":
            return QPixmap(":/img/{}.png".format(Icon))

        # S'il faut une icone
        elif Type == "Icon":
            return QIcon(QPixmap(":/img/{}.png".format(Icon)))


#############################################################################
# Class et fonction permettant la prise en charge du clic droit sur le bouton quitter
class QuitButton(QPushButton):
    def mousePressEvent(self, event):
        """Fonction de reccup des touches souris utilisées."""
        MKVExtractorQt.ui.soft_quit.animateClick()

        ### Récupp du bouton utilisé
        if event.button() == Qt.RightButton:
            python = sys.executable
            os.execl(python, python, * sys.argv)

        # Acceptation de l'evenement
        return super(type(self), self).mousePressEvent(event)



#############################################################################
class MKVExtractorQt(QMainWindow):
    def __init__(self, parent=None):
        """Fonction d'initialisation appellée au lancement de la classe."""
        ### Commandes à ne pas toucher
        super(MKVExtractorQt, self).__init__(parent)
        self.ui = Ui_mkv_extractor_qt()
        self.ui.setupUi(self) # Lance la fonction definissant tous les widgets du fichier UI
        self.show() # Affichage de la fenêtre principale
        
        # Nom de la fenetre
        self.setWindowTitle('MKV Extractor Qt v{}'.format(Version))

        ### Gestion de la fenetre
        # Resolution de la fenetre
        if Configs["WinWidth"] != 615 or Configs["WinHeight"] != 510:
            self.resize(Configs["WinWidth"], Configs["WinHeight"]) # Resize de la fenetre si les valeurs ont été save

        # Aspect du splitter
        if Configs["SplitterSizes"]:
            self.ui.splitter.setSizes(Configs["SplitterSizes"])
        else:
            height = self.ui.splitter.geometry().height() # Recup de la hauteur du splitter
            self.ui.splitter.setSizes([100, height - 150])

        # Centrage de la fenêtre
        if Configs["WinMax"]:
            size_ecran = QDesktopWidget().screenGeometry() # Taille de l'ecran
            self.showMaximized() # Maximise la fenetre
        else:
            size_ecran = QDesktopWidget().screenGeometry() # Taille de l'ecran
            self.move((size_ecran.width() - self.geometry().width()) / 2, (size_ecran.height() - self.geometry().height()) / 2) # Place la fenetre en fonction de sa taille et de la taille de l'ecran


        ### Modifications graphiques de boutons
        self.ui.mkv_stop.setVisible(False) # Cache le bouton d'arret
        self.ui.mkv_resume.setVisible(False) # Cache le bouton de pause

        ### Recherche les différents logiciels complémentaires
        ffconv = False
        if not shutil.which("mkvalidator"):
            self.ui.mk_validator.setVisible(False) # Cache l'option mkvinfo si le l'executable n'existe pas

        if not shutil.which("mkclean"):
            self.ui.mk_clean.setVisible(False) # Cache l'option mkvinfo si le l'executable n'existe pas

        for executable in ["tesseract", "subp2pgm", "subptools"]:
            if not shutil.which(executable) and not Path(executable).exists():
                self.ui.option_vobsub_srt.setVisible(False) # Cache l'option de conversion si le l'executable n'existe pas
                break

            if executable in ["subp2pgm", "subptools"]:
                if shutil.which(executable): # Definit l'adresse du programme
                    Variables[executable] = shutil.which(executable)

                if Path(executable).exists(): # Definit l'adresse du programme
                    Variables[executable] = "{}/{}".format(QDir.currentPath(), executable)

        # Recherche ffmpeg et avconv qui font la même chose
        if not shutil.which("ffmpeg") and not shutil.which("avconv"):
            ### Cache les radiobutton et l'option de conversion
            self.ui.option_dts_ac3.setVisible(False)

        elif shutil.which("ffmpeg") and not shutil.which("avconv"):
            ### Selection automatique ffmpeg
            Configs["FFMpeg"] = True

        elif not shutil.which("ffmpeg") and shutil.which("avconv"):
            ### Selection automatique avconv
            Configs["FFMpeg"] = False

        else:
            ### Charge la valeur sauvegardée ou avconv par defaut
            ffconv = True # Les deux sont dispo


        ### Menu du bouton de conversion DTS => AC3
        menulist = QMenu() # Creation d'un menu

        if ffconv:
            self.option_ffmpeg = QAction(IconBis("ffmpeg", "Icon"), '', self, checkable=True) # Creation d'un item sans texte
            menulist.addAction(self.option_ffmpeg) # Ajout de l'action à la liste

            if Configs["FFMpeg"]:
                self.option_ffmpeg.setChecked(True)

            self.option_ffmpeg.toggled.connect(partial(self.OptionsValue, "FFMpeg")) # Au clic sur la coche

        self.option_stereo = QAction(IconBis("audio-headphones", "Icon"), '', self, checkable=True) # Creation d'un item sans texte
        menulist.addAction(self.option_stereo) # Ajout de l'action à la liste

        self.RatesMenu = QMenu(self) # Creation d'un sous menu
        ag = QActionGroup(self, exclusive=True) # Creation d'un actiongroup
        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]: # Qualités utilisables
            QualityList[nb] = QAction('', self, checkable=True) # Creation d'un item radio sans nom
            self.RatesMenu.addAction(ag.addAction(QualityList[nb])) # Ajout de l'item radio dans la sous liste
            QualityList[nb].triggered.connect(partial(self.OptionsValue, "Ac3Kbits", nb)) # Connection de l'item
        menulist.addMenu(self.RatesMenu) # Ajout du sous menu dans le menu

        self.PowerMenu = QMenu(self) # Creation d'un sous menu
        ag = QActionGroup(self, exclusive=True) # Creation d'un actiongroup
        for nb in [1, 2, 3, 4, 5]: # Puissances utilisables
            PowerList[nb] = QAction('', self, checkable=True) # Creation d'un item radio sans nom
            self.PowerMenu.addAction(ag.addAction(PowerList[nb])) # Ajout de l'item radio dans la sous liste
            PowerList[nb].triggered.connect(partial(self.OptionsValue, "Ac3Boost", nb)) # Connection de l'item
        menulist.addMenu(self.PowerMenu) # Ajout du sous menu dans le menu

        self.ui.option_dts_ac3.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Menu du bouton de reencapsulage
        self.option_del_temp = QAction(IconBis("edit-delete", "Icon"), '', self, checkable=True) # Creation d'une action cochable sans texte
        self.option_subtitles_open = QAction(IconBis("document-edit", "Icon"), '', self, checkable=True) # Creation d'une action cochable sans texte
        menulist = QMenu() # Creation d'un menu
        menulist.addAction(self.option_del_temp) # Ajout de l'action à la liste
        menulist.addAction(self.option_subtitles_open) # Ajout de l'action à la liste
        self.ui.option_reencapsulate.setMenu(menulist) # Envoie de la liste dans le bouton


        ### Activation et modifications des préférences
        QualityList[Configs["Ac3Kbits"]].setChecked(True) # Coche de la bonne valeur
        PowerList[Configs["Ac3Boost"]].setChecked(True) # Coche de la bonne valeur

        if Configs["DelTemp"]: # Coche la case si l'option est true
            self.option_del_temp.setChecked(True)

        if Configs["SubtitlesOpen"]: # Coche la case si l'option est true
            self.option_subtitles_open.setChecked(True)

        if Configs["Stereo"]: # Coche la case si l'option est true
            self.option_stereo.setChecked(True)

        if Configs["SameFolder"]: # Coche la case si l'option est true
            self.ui.option_mkv_folder.setChecked(True)

        # Ce try evite les plantage en cas de passage de l'ancienne version à la nouvelle
        try:
            if not Configs["MKVDirNameOut"].exists(): # Réinitialisation du dossier de sortie s'il n'existe pas
                Configs["MKVDirNameOut"] = Path().resolve()

                # Activation de l'option meme dossier afin qu'un dossier de sortie soit pris en compte au prochain mkv
                self.ui.option_mkv_folder.setChecked(True)

        except:
            Configs["MKVDirNameOut"] = Path().resolve()

            # Activation de l'option meme dossier afin qu'un dossier de sortie soit pris en compte au prochain mkv
            self.ui.option_mkv_folder.setChecked(True)

        ### QProcess (permet de lancer les jobs en fond de taches)
        self.process = QProcess() # Creation du QProcess
        self.process.setProcessChannelMode(1) # Unification des 2 sorties (normale + erreur) du QProcess


        ### Connexions de la grande partie des widgets (les autres sont ci-dessus ou via le fichier ui)
        self.connectActions() # Création des connexions


        ### Cache la box de retour d'info
        self.ui.view_info.setChecked(Configs["ViewInfo"])


        ### Listage des langues disponibles dans mkvmerge
        Variables["Cmd"] = ["MKVMerge", "LanguagesList", "mkvmerge --list-languages"] # Commande de listage
        self.process.start(Variables["Cmd"][2]) # Lancement de la commande de listage
        self.process.waitForFinished() # Attend la fin du travail avant de continuer
        MKVLanguages.sort() # Range les langues dans l'ordre alphabetique


        ### Gestion la traduction
        if "fr_" in Configs["Language"]:
            self.ui.lang_fr.setChecked(True) # Selection de la langue français
            self.OptionLanguage("fr_FR") # Necessaire car l'item ci-dessus n'est pas encore connecté
        elif "cs_" in Configs["Language"]:
            self.ui.lang_cs.setChecked(True) # Selection de la langue tchéque
            self.OptionLanguage("cs_CZ") # Necessaire car l'item ci-dessus n'est pas encore connecté
        else:
            self.OptionLanguage("en_US") # Force le chargement de traduction si c'est la langue english (par defaut)


        ### Définition de la taille des colonnes du tableau des pistes
        largeur = (self.ui.mkv_tracks.size().width() - 75) / 3 # Calcul pour definir la taille des colones
        self.ui.mkv_tracks.setMouseTracking(True) # Necessaire à l'affichage des statustip
        self.ui.mkv_tracks.hideColumn(0) # Cache la 1ere colonne
        self.ui.mkv_tracks.setColumnWidth(1, 25) # Definit la colonne 1 à 20px
        self.ui.mkv_tracks.setColumnWidth(2, 25) # Definit la colonne 2 à 20px
        self.ui.mkv_tracks.setColumnWidth(3, 25) # Definit la colonne 3 à 20px
        self.ui.mkv_tracks.setColumnWidth(4, largeur + 5) # Definit la colonne 4
        self.ui.mkv_tracks.setColumnWidth(5, largeur + 5) # Definit la colonne 5
        self.ui.mkv_tracks.horizontalHeader().setStretchLastSection(True) # Definit la place restante à la derniere colonne


        ### Dans le cas du lancement du logiciel avec arguments
        # Un seul argument
        if len(sys.argv) == 2:
            if Path(sys.argv[1]).exists(): # Teste le fichier donné
                Variables["MKVLinkIn"] = Path(sys.argv[1]) # Mise à jour de la variable
            else:
                QMessageBox(3, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgExist"].format(sys.argv[1]), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()

        # Dans le cas de plusieurs arguments
        elif len(sys.argv) > 2:
            QMessageBox(3, self.Trad["ErrorArgTitle"], self.Trad["ErrorArgNb"].format("\n".join(sys.argv[1:])), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()


        ### Dans le cas du lancement du logiciel avec un argument
        if Variables["MKVLinkIn"]: # Si le fichier donné est bon
            self.MKVOpen(Variables["MKVLinkIn"]) # Lancement de la fonction de chargement du fichier mkv



    #========================================================================
    def connectActions(self):
        """Fonction faisant les connexions non faites par qtdesigner."""
        ### Connexions des actions du menu (pas les options)
        self.ui.mkv_info.triggered.connect(self.MKVInfoGui) # Au clic sur le menu
        self.ui.mkv_view.triggered.connect(self.MKVView) # Au clic sur le menu
        self.ui.mkv_mkvmerge.triggered.connect(self.MKVMergeGui) # Au clic sur le menu
        self.ui.mk_validator.triggered.connect(self.MKValidator) # Au clic sur le menu
        self.ui.mk_clean.triggered.connect(self.MKClean) # Au clic sur le menu
        self.ui.option_clean.triggered.connect(lambda: self.ui.reply_info.clear()) # Nettoyage de la box du retour d'infos
        self.ui.lang_en.triggered.connect(partial(self.OptionLanguage, "en_US")) # Au clic sur le menu
        self.ui.lang_fr.triggered.connect(partial(self.OptionLanguage, "fr_FR")) # Au clic sur le menu
        self.ui.lang_cs.triggered.connect(partial(self.OptionLanguage, "cs_CZ")) # Au clic sur le menu
        self.ui.mkv_folder.triggered.connect(self.MKVFolder) # Au clic sur le bouton
        self.ui.mkv_open.triggered.connect(self.MKVOpen) # Au clic sur le bouton


        ### Connexions des fenetres d'infos et d'aides
        self.ui.about_qt.triggered.connect(lambda: QMessageBox.aboutQt(MKVExtractorQt)) # A propos de Qt
        self.ui.help.triggered.connect(lambda: QMessageBox.about(self, self.Trad["Help_title"], self.Trad["Help"])) # Aide
        self.ui.about.triggered.connect(lambda: QMessageBox.about(self, self.Trad["About_title"] , self.Trad["About"].format(Version, "http://www.gnu.org/copyleft/gpl.html"))) # A propos de MKV Extractor Gui


        ### Connexions des options, redirige tous ces widgets vers une même fonction
        self.ui.option_reencapsulate.toggled.connect(partial(self.VariablesValue, "Reencapsulate")) # Au clic sur la coche
        self.ui.option_vobsub_srt.toggled.connect(partial(self.VariablesValue, "VobsubToSrt")) # Au clic sur la coche
        self.ui.option_dts_ac3.toggled.connect(partial(self.VariablesValue, "DtsToAc3")) # Au clic sur la coche
        self.ui.option_mkv_folder.toggled.connect(partial(self.OptionsValue, "SameFolder")) # Au clic sur la coche
        self.ui.option_del_config.toggled.connect(partial(self.OptionsValue, "DelConfig")) # Au clic sur la coche
        self.ui.view_info.toggled.connect(self.ViewInfo) # Au clic sur la coche
        self.option_stereo.toggled.connect(partial(self.OptionsValue, "Stereo")) # Au clic sur la coche
        self.option_del_temp.toggled.connect(partial(self.OptionsValue, "DelTemp")) # Au clic sur la coche
        self.option_subtitles_open.toggled.connect(partial(self.OptionsValue, "SubtitlesOpen")) # Au clic sur la coche


        ### Connexions du tableau listant les pistes du fichier mkv
        self.ui.mkv_tracks.cellClicked.connect(self.TrackView) # Au clic sur une cellule
        self.ui.mkv_tracks.itemChanged.connect(self.TrackModif) # Au changement du contenu d'un item
        self.ui.mkv_tracks.itemSelectionChanged.connect(self.TrackModif) # Au changement de séléction


        ### Connexion du bouton d'exportation des infos
        self.ui.out_info.clicked.connect(self.OutInfo) # Au clic sur le bouton


        ### Connexions des widgets de la partie basse
        self.ui.mkv_stop.clicked.connect(self.WorkStop) # Au clic sur le bouton
        self.ui.mkv_execute.clicked.connect(self.MKVExecute) # Au clic sur le bouton
        self.ui.mkv_resume.clicked.connect(self.WorkPause) # Au clic sur le bouton
        self.ui.soft_quit.__class__ = QuitButton # Utilisation de la class QuitButton pour la prise en charge du clic droit

        ### Connexions du QProcess
        self.process.readyReadStandardOutput.connect(self.WorkReply) # Retours du travail
        self.process.finished.connect(self.WorkFinished) # Fin du travail


        ### Connexions de la frame de reconnaissance des sous titres
        self.ui.sub_next.clicked.connect(lambda: (self.TextUpdate(), self.IMGViewer(1))) # Au clic sur le bouton
        self.ui.sub_previous.clicked.connect(lambda: (self.TextUpdate(), self.IMGViewer(-1))) # Au clic sur le bouton


    #========================================================================
    def CheckSize(self):
        """Fonction verifiant qu'il y a assez de place pour travailler."""
        # Si l'une des valeurs est vide, on arrete là
        if not Configs["MKVDirNameOut"] or not Variables["MKVLinkIn"]:
            return

        # Récupération de la taille du fichier et de la place libre
        filesize = Variables["MKVLinkIn"].stat().st_size
        disksize = shutil.disk_usage(str(Configs["MKVDirNameOut"])).free

        if ( filesize * 2 ) > disksize: # Affiche un message s'il n'y a pas beaucoup de place
            QMessageBox(2, self.Trad["ErrorSizeTitle"], self.Trad["ErrorSize"], QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()


    #========================================================================
    def SetInfo(self, text, color="000000", center=False, newline=False):
        """Fonction mettant en page les infos à afficher dans le widget d'information."""
        # Saut de ligne à la demande
        if newline and self.ui.reply_info.toPlainText() != "": # Vérifie que le widget n'est pas vide
            self.ui.reply_info.append('') # Saute une ligne avant d'ajouter le texte

        # Mise en page des textes
        if center: # Centrage + couleur du texte
            self.ui.reply_info.append("""<center><table><tr><td><span style=" color:#{};">{}</span></td></tr></table></center>""".format(color, text))
        else: # Couleur du texte
            self.ui.reply_info.append("""<span style=" color:#{};">{}</span>""".format(color, text))


    #========================================================================
    def OutInfo(self):
        """Fonction exportant les informations retournées dans le fichier ~/InfoMKVExtractorQt.txt"""
        text = self.ui.reply_info.toPlainText()
        file = Path(QDir.homePath(), 'InfoMKVExtractorQt.txt')

        # Ne travaille que si le texte n'est pas vide
        if text:
            with file.open("w") as info_file:
                for line in text:
                    info_file.write(line)


    #========================================================================
    def MKVInfoGui(self):
        """Fonction ouvrant le fichier mkv avec le logiciel MKVInfo en mode detaché."""
        self.process.startDetached('mkvinfo -g "{}"'.format(Variables["MKVLinkIn"]))


    #========================================================================
    def MKVMergeGui(self):
        """Fonction ouvrant le fichier mkv avec le logiciel MKVInfo en mode detaché."""
        self.process.startDetached('mmg "{}"'.format(Variables["MKVLinkIn"]))


    #========================================================================
    def MKVView(self):
        """Fonction ouvrant le fichier mkv avec le logiciel par defaut en mode detaché."""
        # Impossible d'utiliser QDesktopServices qui plante avec les caracteres speciaux
        self.process.startDetached('xdg-open "{}"'.format(Variables["MKVLinkIn"]))


    #========================================================================
    def MKClean(self):
        """Execution de la classe faisant tourner MKClean."""
        ### Fenetre de séléction de sortie du fichier mkv, avec modification stdout pour eviter les messages
        stdout_sav = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        MKCleanTemp = Path(QFileDialog.getSaveFileName(self, self.Trad["SelectFileOut"], QDir.path(QDir("{}/clean_{}".format(Configs["MKVDirNameOut"], Variables['MKVFileNameIn']))), "Matroska Files(*.mka *.mks *.mkv *.mk3d *.webm *.webmv *.webma)")[0])
        sys.stdout = stdout_sav

        ### Dans le cas où il y a un fichier de sortie
        if not MKCleanTemp.is_dir():
            Variables["TempFiles"] = [MKCleanTemp] # Ajout du fichier de sortie dans le listing des fichiers
            Variables["Cmd"] = ["MKClean", "", 'mkclean --optimize "{}" "{}"'.format(Variables['MKVLinkIn'], MKCleanTemp)] # Code à executer

            self.SetInfo(self.Trad["WorkProgress"].format(Variables["Cmd"][0]), "800080", True, True) # Nom de la commande
            self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2])) # Envoie d'informations
            self.WorkInProgress(True) # Bloquage des widgets

            self.process.start(Variables["Cmd"][2]) # Lancement de la commande


    #========================================================================
    def MKValidator(self):
        """Execution de la classe faisant tourner MKValidator."""
        Variables["Cmd"] = ["MKValidator", "", 'mkvalidator "{}"'.format(Variables['MKVLinkIn'])] # Code à executer

        self.SetInfo(self.Trad["WorkProgress"].format(Variables["Cmd"][0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2])) # Envoie d'informations
        self.WorkInProgress(True) # Bloquage des widgets
        self.ui.progressBar.setMaximum(0) # Mode pulsation de la barre de progression

        self.process.start(Variables["Cmd"][2]) # Lancement de la commande


    #========================================================================
    def MKVConvert(self, file):
        """Fonction appelée lors du besoin de convertir une video en mkv."""
        # Proposition de conversion de la vidéo
        test = QMessageBox(2, self.Trad["Convert1"], self.Trad["Convert2"], QMessageBox.Ok | QMessageBox.Cancel, self, Qt.WindowSystemMenuHint).exec()

        # En cas de refus
        if test != 1024:
            return

        # Dossier dans lequel mettre le nouveau fichier mkv
        FolderTemp = QFileDialog.getExistingDirectory(self, self.Trad["SelectFolderTemp"], QDir.path(QDir(str(file.parent))))

        # En cas de refus
        if not FolderTemp: return

        # Code à executer
        Variables["TempFiles"] = [Path(FolderTemp, file.stem + ".mkv")]
        Variables["Cmd"] = ["MKVMerge", "FileToMKV", 'mkvmerge -o "{}" "{}"'.format(Variables["TempFiles"][0], file) ] # Commande de listage

        self.SetInfo(self.Trad["WorkProgress"].format(Variables["Cmd"][0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2])) # Envoie d'informations

        self.process.start(Variables["Cmd"][2]) # Lancement de la commande de listage


    #========================================================================
    def OptionsValue(self, option, value):
        """Fonction de mise à jour des options."""
        ### Mise à jour de la variable et envoie de l'info
        Configs[option] = value
        self.SetInfo(self.Trad["OptionUpdate"].format(option, value), newline=True)

        ### Dans le cas de l'option d'utilisation du dossier du fichier mkv
        if option == "SameFolder" and value:
            if Variables["MKVLinkIn"]: # Vérifie qu'un fichier a déjà été chargé
                Configs["MKVDirNameOut"] = Configs["MKVDirNameIn"] # Mise à jour de la variable
                self.ui.mkv_folder.setStatusTip(self.Trad["SelectedFolder"].format(Configs["MKVDirNameOut"])) # Changement statustip
                self.SetInfo(self.Trad["SelectedFolder2"].format(Configs["MKVDirNameOut"]), newline=True) # Envoie d'information


    #========================================================================
    def VariablesValue(self, variable, value):
        """Fonction de mise à jour des variables."""
        ### Mise à jour de la variable et envoie de l'info
        Variables[variable] = value
        self.SetInfo(self.Trad["OptionUpdate"].format(variable, value), newline=True)


    #========================================================================
    def ViewInfo(self, value):
        """Fonction d'affichage ou masquage de la box de retour d'information."""
        ### Mise à jour de la variable et envoie de l'info
        if Configs["ViewInfo"] != value: # Permet d'etre lancé au demarrage ainsi
            Configs["ViewInfo"] = value
            self.SetInfo(self.Trad["OptionUpdate"].format("ViewInfo", value), newline=True)

        self.ui.reply_info.setVisible(value) # Affiche ou cache la box

        height = self.ui.splitter.geometry().height() # Recup de la hauteur du splitter

        ### Modifications graphiques
        if value:
            self.ui.feedback_frame.setMinimumSize(QSize(0, 150))
            self.ui.splitter.setSizes([100, height - 150])
        else:
            self.ui.feedback_frame.setMinimumSize(QSize(0, 45))
            self.ui.splitter.setSizes([45, height - 45])


    #========================================================================
    def OptionLanguage(self, value):
        """Fonction modifiant en temps réel la traduction."""
        # Mise à jour de la variable de la langue
        Configs["Language"] = value

        ### Chargement du fichier qm de traduction (anglais utile pour les textes singulier/pluriel)
        appTranslator = QTranslator() # Création d'un QTranslator
        folder = Path(sys.argv[0]).resolve().parent # Dossier des traductions

        if Configs["Language"] == "fr_FR":
            find = appTranslator.load("MKVExtractorQt_fr_FR", str(folder))

            # Si le fichier n'a pas été trouvé,relance la fonction en US
            if not find:
                QMessageBox(3, "Erreur de traduction", "Aucun fichier de traduction <b>française</b> trouvé.<br/>Utilisation de la langue <b>anglaise</b>.", QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()
                self.ui.lang_en.setChecked(True)
                Configs["Language"] = "en_US"

            else:
                ### Chargement de la traduction
                app.installTranslator(appTranslator)

        elif Configs["Language"] == "cs_CZ":
            find = appTranslator.load("MKVExtractorQt_cs_CZ", str(folder))

            # Si le fichier n'a pas été trouvé,relance la fonction en US
            if not find:
                QMessageBox(3, "Chyba překladu", "No translation file <b>Czech</b> found. Use <b>English</b> language. Soubor s překladem do <b>češtiny</b> nenalezen. Použít <b>anglický</b> jazyk.", QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec()
                self.ui.lang_en.setChecked(True)
                Configs["Language"] = "en_US"

            else:
                ### Chargement de la traduction
                app.installTranslator(appTranslator)


        ### Mise à jour du fichier langage de Qt
        global translator_qt
        translator_qt = QTranslator() # Création d'un QTranslator
        if translator_qt.load("qt_" + Configs["Language"], QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator_qt)


        ### Mise à jour du dictionnaire des textes
        # 008000 : vert                 0000c0 : bleu                           800080 : violet
        effet = """<span style=" color:#000000;">@=====@</span>"""
        self.Trad = {"About_title" : self.tr("About MKV Extractor Gui"),
                    "About" : self.tr("""<html><head/><body><p align="center"><span style=" font-size:12pt; font-weight:600;">MKV Extractor Qt v{}</span></p><p><span style=" font-size:10pt;">GUI to extract/edit/remux the tracks of a matroska (MKV) file.</span></p><p><span style=" font-size:10pt;">This program follows several others that were coded in Bash and it codec in python3 + QT5.</span></p><p><span style=" font-size:8pt;">This software is licensed under </span><span style=" font-size:8pt; font-weight:600;"><a href="{}">GNU GPL v3</a></span><span style=" font-size:8pt;">.</span></p><p>Thanks to the <a href="http://www.developpez.net/forums/f96/autres-langages/python-zope/"><span style=" text-decoration: underline; color:#0057ae;">developpez.net</span></a> python forums for their patience</p><p align="right">Created by <span style=" font-weight:600;">Belleguic Terence</span> (Hizoka), November 2013</p></body></html>"""),

                    "Convert1" : self.tr("Not supported file"),
                    "Convert2" : self.tr("This file is not supported by mkvmerge.\nDo you want convert this file in mkv ?"),

                    "ErrorArgTitle" : self.tr("Wrong arguments"),
                    "ErrorArgExist" : self.tr("The <b>{}</b> file given as argument does not exist."),
                    "ErrorArgNb" : self.tr("<b>Too many arguments given:</b> {}"),
                    "ErrorSizeTitle" : self.tr("Space available"),
                    "ErrorSize" : self.tr("Not enough space available.\n\nIt is advisable to have at least twice the size of free space on the disk file."),
                    "ErrorTesseractTitle" : self.tr("Tesseract langs error"),
                    "ErrorTesseract" : self.tr("The subtitle language is not avaible in Tesseract list langs: {}"),

                    "Help_title" : self.tr("Help me!"),
                    "Help" : self.tr("""<html><head/><body><p align="center"><span style=" font-weight:600;">Are you lost? Do you need help? </span></p><p><span style=" font-weight:600;">Normally all necessary information is present: </span></p><p>- Read the information in the status bar when moving the mouse on widgets </p><p><span style=" font-weight:600;">Though, if you need more information: </span></p><p>- Forum Ubuntu-fr.org: <a href="http://forum.ubuntu-fr.org/viewtopic.php?id=1508741"><span style=" text-decoration: underline; color:#0057ae;">topic</span></a></p><p>- My email address: <a href="mailto:hizo@free.fr"><span style=" text-decoration: underline; color:#0057ae;">hizo@free.fr </span></a></p><p><span style=" font-weight:600;">Thank you for your interest in this program.</span></p></body></html>"""),

                    "IMGViewerMD5" : self.tr("Edition of files who have the md5: {}"),
                    "IMGProgression" : self.tr("Image progression : {} on {}"),

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

                    "SelectedFile" : self.tr("Selected file: {}."),
                    "SelectedFile2" : self.tr('Selected file: <span style=" color:#0000c0;">{}</span>'),
                    "SelectedFolder" : self.tr("Selected folder: {}."),
                    "SelectedFolder2" : self.tr('Selected folder: <span style=" color:#0000c0;">{}</span>'),

                    "SelectFileIn" : self.tr("Select the input MKV File"),
                    "SelectFileOut" : self.tr("Select the output MKV file"),
                    "SelectFolder" : self.tr("Select the output folder"),
                    "SelectFolderTemp" : self.tr("Select the output folder to use for convert the file"),

                    "SubtitlesConvert" : self.tr("Subtitle converter to images."),
                    "SubtitlesCreation" : self.tr("SRT subtitle creation."),
                    "SubtitlesWait" : self.tr("All subtitles images could not be recognized.\nWe must therefore specify the missing texts."),

                    "UseMMGTitle" : self.tr("MKV Merge Gui or MKV Extractor Qt ?"),
                    "UseMMGText" : self.tr("You want extract and reencapsulate the tracks without use other options.\n\nIf you just need to make this, you should use MMG (MKV Merge gui) who is more adapted for this job.\n\nWhat software do you want use ?"),

                    "Audio" : self.tr("audio"),
                    "Subtitles" : self.tr("subtitles"),
                    "Video" : self.tr("video"),

                    "TrackAac" : self.tr("If the remuxed file has reading problems, change this value."),
                    "TrackAudio" : self.tr("Change the language if it's not right. 'und' means 'Undetermined'."),
                    "TrackAttachment" : self.tr("This track can be renamed and must contain an extension to avoid reading errors."),
                    "TrackChapters" : self.tr("chapters"),
                    "TrackDislay" : self.tr("This track can be displayed via an icon click."),
                    "TrackNoDislay" : self.tr("This track can not be displayed."),
                    "TrackID" : self.tr("Work with track number {}."),
                    "TrackID2" : self.tr("Work with attachment number {}."),
                    "TrackID3" : self.tr("Work with {}."),
                    "TrackNoInfo" : self.tr("No information."),
                    "TrackRename" : self.tr("This track can be renamed."),
                    "TrackTags" : self.tr("tags"),
                    "TrackType" : self.tr("This track is a {} type."),
                    "TrackVideo" : self.tr("Change the fps value if needed. Useful in case of audio lag. Normal : 23.976, 25.000 and 30.000."),

                    "WorkCanceled" : effet + self.tr(" All commands were canceled ") + effet,
                    "WorkCmd" : self.tr("""Command execution: <span style=" color:#0000c0;">{}</span>"""),
                    "WorkError" : effet + self.tr(" The last command returned an error ") + effet,
                    "WorkFinished" : effet + self.tr(" {} execution is finished ") + effet,
                    "WorkMerge" : effet + self.tr(" MKV File Tracks ") + effet,
                    "WorkPaused" : effet + self.tr(" Paused software time to read the subtitles ") + effet,
                    "WorkProgress" : effet + self.tr(" {} execution in progress ") + effet,
                    }


        ### Recharge les textes de l'application graphique du fichier ui.py
        self.ui.retranslateUi(self)


        ### Mise au propre du widget de retour d'info et envoie de langue
        if not Variables["FirstRun"]: # Variable evitant l'envoie inutile d'info au demarrage
            self.ui.reply_info.clear()
            self.SetInfo(self.Trad["OptionUpdate"].format("Language", value), newline=True)

        else:
            Variables["FirstRun"] = False


        ### Recharge les textes des toolbutton
        try:
            # Ce widget n'existe que si il y affmpeg et avconv d'installés
            self.option_ffmpeg.setText(self.Trad["OptionsFFMpeg"])
        except:
            pass

        self.option_stereo.setText(self.Trad["OptionsStereo1"])
        self.PowerMenu.setTitle(self.Trad["OptionsPowerList"])
        self.RatesMenu.setTitle(self.Trad["OptionsQuality"])
        self.option_del_temp.setText(self.Trad["OptionsDelTemp1"])
        self.option_subtitles_open.setText(self.Trad["OptionsSub1"])
        self.option_subtitles_open.setStatusTip(self.Trad["OptionsSub2"])
        self.option_stereo.setStatusTip(self.Trad["OptionsStereo2"])
        self.option_del_temp.setStatusTip(self.Trad["OptionsDelTemp2"])

        for nb in [1,2,3,4,5]:
            PowerList[nb].setText(self.Trad["OptionsPowerY"].format(nb))
            if nb == 1:
                PowerList[1].setStatusTip(self.Trad["OptionsPower"])
            else:
                PowerList[nb].setStatusTip(self.Trad["OptionsPowerX"].format(nb))

        for nb in [128, 192, 224, 256, 320, 384, 448, 512, 576, 640]:
            QualityList[nb].setStatusTip(self.Trad["OptionsQualityX"].format(nb))
            QualityList[nb].setText(self.Trad["OptionsQualityY"].format(nb))


        ### Si un dossier de sortie a déjà été séléctionné
        if Configs["MKVDirNameOut"]:
            self.ui.mkv_folder.setStatusTip(self.Trad["SelectedFolder"].format(Configs["MKVDirNameOut"])) # StatusTip
            self.SetInfo(self.Trad["SelectedFolder2"].format(Configs["MKVDirNameOut"]), newline=True) # Envoie d'information


        ### Si un fichier mkv à déjà été chargé
        if Variables["MKVLoad"]:
            self.TracksLoad() # Relance le chargement des pistes pour traduire les textes
            self.ui.mkv_open.setStatusTip(self.Trad["SelectedFile"].format(Variables["MKVLinkIn"])) # StatusTip
            self.SetInfo(self.Trad["SelectedFile2"].format(Variables["MKVLinkIn"]), newline=True) # Envoie d'information

            ### Recoche les pistes qui l'étaient, crée une liste car MKVDicoSelect sera modifié pendant la boucle
            for x in list(MKVDicoSelect.keys()):
                self.ui.mkv_tracks.item(x, 1).setCheckState(2)


    #========================================================================
    def MKVFolder(self, MKVFolderTemp=None):
        """Fonction de séléction du dossier de sortie."""
        # Fenetre de séléction du dossier de sortie
        if not MKVFolderTemp:
            MKVFolderTemp = Path(QFileDialog.getExistingDirectory(self, self.Trad["SelectFolder"], QDir.path(QDir(str(Configs["MKVDirNameOut"])))))

        # Continuation de la fonction si un fichier est bien séléctionné
        if MKVFolderTemp != Path():
            # Réinitialisation de l'option de meme dossier
            if Configs["SameFolder"]: # Coche la case si l'option est true
                Configs["SameFolder"] = False
                self.ui.option_mkv_folder.setChecked(False)

            Configs["MKVDirNameOut"] = MKVFolderTemp # Mise à jour de la variable
            self.ui.mkv_folder.setStatusTip(self.Trad["SelectedFolder"].format(MKVFolderTemp)) # StatusTip
            self.SetInfo(self.Trad["SelectedFolder2"].format(MKVFolderTemp), newline=True) # Envoie d'information
            self.CheckSize() # Vérifie la place disponible

            # Deblocage des widgets dans le cas ou un mkv a déjà été chargé et qu'une selection de piste est faite
            # Les widgets n'ont pas été debloqué avant car pas de dossier de sortie de donné
            if Variables["MKVLoad"] and MKVDicoSelect:
                self.ui.option_reencapsulate.setEnabled(True) # Deblocage du bouton de reencapsulage
                self.ui.mkv_execute.setEnabled(True)
                self.ui.mkv_execute_2.setEnabled(True)
                self.ui.option_dts_ac3.setEnabled(False) # Deblocage du widget
                self.ui.option_vobsub_srt.setEnabled(False) # Deblocage de widget

                for valeurs in MKVDicoSelect.values(): # Boucle sur la liste des lignes
                    if "dts" in valeurs[-1]: # Recherche la valeur dts dans les sous listes
                        self.ui.option_dts_ac3.setEnabled(True) # Deblocage du widget

                    elif "sub" in valeurs[-1]: # Recherche la valeur vobsub dans les sous listes
                        self.ui.option_vobsub_srt.setEnabled(True) # Deblocage de widget


    #========================================================================
    def MKVOpen(self, MKVLinkTemp=None):
        """Fonction de séléction du fichier mkv."""
        ### Fenetre de séléction du fichier mkv
        if not MKVLinkTemp:
            MKVLinkTemp = Path(QFileDialog.getOpenFileName(self, self.Trad["SelectFileIn"], QDir.path(QDir(str(Configs["MKVDirNameIn"]))), "Matroska Files: *.mka *.mks *.mkv *.mk3d *.webm *.webmv *.webma(*.mka *.mks *.mkv *.mk3d *.webm *.webmv *.webma);;Other Video Files: *.mp4 *.m4a *.nut *.ogg *.ogm *.ogv(*.mp4 *.m4a *.nut *.ogg *.ogm *.ogv)")[0])

            # Si pas de séléction, on arrete la
            if MKVLinkTemp == Path("."): return

        ### S'il est necessaire de convertir la vidéo
        if MKVLinkTemp.suffix in (".mp4", ".m4a", ".nut", ".ogg", ".ogm", ".ogv"):
            # Lancement de la conversion et la fonction sera appelée par WorkFinished
            self.MKVConvert(MKVLinkTemp)

        ### Continuation de la fonction si un fichier est bien séléctionné
        elif MKVLinkTemp.exists():
            self.ui.reply_info.clear() # Mise au propre des retours
            Variables["MKVLinkIn"] = MKVLinkTemp # Mise à jour de la variable
            Variables["MKVFileNameIn"] = MKVLinkTemp.name # Mise à jour de la variable
            Configs["MKVDirNameIn"] = MKVLinkTemp.parent # Mise à jour de la variable

            self.SetInfo(self.Trad["SelectedFile2"].format(Variables["MKVLinkIn"])) # Envoie d'information
            self.ui.mkv_open.setStatusTip(self.Trad["SelectedFile"].format(Variables["MKVLinkIn"])) # StatusTip
            self.ui.out_info.setEnabled(True) # Debloquage du bouton d'exportation d'info

            if Configs["SameFolder"]: # Dans le cas de l'utilisation de l'option SameFolder
                Configs["MKVDirNameOut"] = Configs["MKVDirNameIn"] # Mise à jour de la variable
                self.ui.mkv_folder.setStatusTip(self.Trad["SelectedFolder"].format(Configs["MKVDirNameOut"])) # StatusTip
                self.SetInfo(self.Trad["SelectedFolder2"].format(Configs["MKVDirNameOut"])) # Envoie d'information

            else:
                if Configs["MKVDirNameOut"]: # Envoie de l'adresse du dossier de sortie s'il existe
                    self.SetInfo(self.Trad["SelectedFolder2"].format(Configs["MKVDirNameOut"])) # Envoie d'information

            self.TracksLoad() # Chargement du contenu du fichier mkv


    #========================================================================
    def TracksLoad(self):
        """Fonction de listge et d'affichage des pistes contenues dans le fichier MKV."""
        self.setCursor(Qt.WaitCursor) # Curseur de chargement

        ### Mise à jour des variables
        Variables["MKVLoad"] = True # Travail en cours
        Variables["MKVTime"] = 0 # Durée du fichier mkv
        Variables["MKVTitle"] = "" # Titre du fichier mkv
        Variables["Tracks"] = [] # Liste des pistes du fichier mkv
        x = 0 # Sert à indiquer les numeros de lignes
        Variables["SuperBlock"] = True # Sert à bloquer les signaux du tableau (impossible d'utiliser blocksignals)
        self.ComboBoxes = {} # Dictionnaire listant les combobox
        MKVDico.clear() # Mise au propre du dictionnaire
        MKVFPS.clear() # Mise au propre du dictionnaire

        ### Vérifie la place disponible
        self.CheckSize()

        ### (Re)Creation d'un dossier temporaire qui s'effacera tout seul lors de la destruction de la variable
        Variables["TempFolder"] = TemporaryDirectory(prefix="MKV-Extractor-Qt5-")
        Variables["TempFolderName"] = Variables["TempFolder"].name # Récupération du nom du dossier
        Path(Variables["TempFolderName"], "SUB2SRT").mkdir(parents=True) # Création du dossier de conversion des sous titres

        ### Désactivation des différentes options qui pourraient être activés
        for widget in [self.ui.option_reencapsulate, self.ui.option_vobsub_srt, self.ui.option_dts_ac3]:
            widget.setChecked(False) # Décoche les boutons
            widget.setEnabled(False) # Grise les widgets

        ### Activation des widgets qui attendaient un fichier mkv valide
        for widget in [self.ui.mkv_info, self.ui.mkv_view, self.ui.mkv_mkvmerge, self.ui.mk_validator, self.ui.mk_clean]:
            widget.setEnabled(True)

        ### Affichage et nettoyage du tableau des pistes
        if self.ui.stackedMiddle.currentIndex() != 0:
            self.ui.stackedMiddle.setCurrentIndex(0)

        while self.ui.mkv_tracks.rowCount() != 0:
            self.ui.mkv_tracks.removeRow(0)

        ### Récupération du retour de MKVInfo
        Variables["Cmd"] = ["MKVInfo", "", 'env LANGUAGE=en mkvinfo "{}"'.format(Variables["MKVLinkIn"])] # Commande de MKVInfo
        self.process.start(Variables["Cmd"][2]) # Lancement de la commande de MKVInfo
        self.process.waitForFinished() # Attend la fin du travail avant de continuer

        ### Récupération brut du retour de MKVMerge
        Variables["Cmd"] = ["MKVMerge", "TracksList", 'env LANGUAGE=en mkvmerge -I "{}"'.format(Variables["MKVLinkIn"])] # Commande de MKVInfo
        self.process.start(Variables["Cmd"][2]) # Lancement de la commande de MKVInfo
        self.process.waitForFinished() # Attend la fin du travail avant de continuer

        ### Nettoyage de la liste de piste
        for val in range(len(Variables["Tracks"])):
            if "codec_private_data:" in  Variables["Tracks"][val]: # Suppression de l'info codec codec_private_data
                CodecAVirer = Variables["Tracks"][val].split("codec_private_data:")[1].split(" ")[0]
                Variables["Tracks"][val] = Variables["Tracks"][val].replace(CodecAVirer, "")

        ### Affichage du titre ou du nom du fichier (sans extension) du fichier mkv
        if Variables["MKVTitle"]:
            self.ui.mkv_title.setText(Variables["MKVTitle"])
        else:
            self.ui.mkv_title.setText(Variables["MKVFileNameIn"][:-4])

        ### Retours d'information
        self.SetInfo(self.Trad["WorkMerge"], "800080", True, True)
        self.SetInfo(self.Trad["WorkCmd"].format("mkvmerge -I {}".format(Variables["MKVLinkIn"])))

        ### Boucle traitant les pistes du fichier mkv
        # Impossible d'e remplacer x par enumerate car il ne faut pas toujours incrémenter
        for Track in Variables["Tracks"]:
            self.SetInfo(Track) # Envoie du retour de mkvmerge

            ### Traitement des pistes normales
            if Track[:5] == "Track":
                TrackType = Track.split(": ")[1].split(" ")[0] # Récupération du type de piste
                
                ### Traitement des pistes normales
                if TrackType in ["video", "audio", "subtitles"]:
                    ID = Track.split(": ")[0].split(" ")[2] # Récupération de l'ID de la piste
                    codec1 = Track.split("codec_id:")[1].split(" ")[0] # Récupération du codec de la piste

                    ### Traitement spécifique aux vidéos
                    if TrackType == "video":
                        TrackTypeName = self.Trad["Video"]
                        icone = 'video-x-generic' # Icone video

                        ### Récupération de l'info1
                        if " track_name:" in Track:
                            info1 = Track.split(" track_name:")[1].split(" ")[0]
                        elif " display_dimensions:" in Track:
                            info1 = Track.split(" display_dimensions:")[1].split(" ")[0]
                        else:
                            info1 = ""

                        ### Récupération du FPS de la piste
                        info2 = MKVFPS[int(ID)]

                        ### Mise à jour du codec pour plus de lisibilité
                        try:
                            codec = CodecList[codec1][0]
                        except:
                            codec = codec1.replace("/", "_").lower()

                        ### Envoie des informations dans le tableaux
                        self.ui.mkv_tracks.insertRow(x) # Création de la ligne
                        self.ComboBoxes[x] = QComboBox() # Création de la combobox et ajout d'un element dans le dico
                        self.ui.mkv_tracks.setCellWidget(x, 5, self.ComboBoxes[x]) # Envoie de la combobox

                        if info2 in ["23.976fps", "25.000fps", "30.000fps"]:
                            FPSList = ["23.976fps", "25.000fps", "30.000fps"] # Liste normale des fps
                        else:
                            FPSList = ["23.976fps", "25.000fps", "30.000fps", info2] # Liste normale + valeur trouvée
                            FPSList.sort()

                        self.ComboBoxes[x].addItems(FPSList) # Remplissage de la combobox
                        self.ComboBoxes[x].setStatusTip(self.Trad["TrackVideo"]) # StatusTip
                        self.ComboBoxes[x].currentIndexChanged['QString'].connect(partial(self.ComboModif, x)) # Connexion + ligne

                    ### Traitement spécifique à l'audio
                    elif TrackType == "audio":
                        TrackTypeName = self.Trad["Audio"]
                        icone = 'audio-x-generic' # Icone audio

                        ### Récupération de l'info
                        if " track_name:" in Track:
                            info1 = Track.split(" track_name:")[1].split(" ")[0]
                        elif " audio_sampling_frequency:" in Track:
                            info1 = Track.split(" audio_sampling_frequency:")[1].split(" ")[0] + " Hz"
                        else:
                            info1 = ""

                        ### Récupération de la langue
                        if " language:" in Track:
                            info2 = Track.split(" language:")[1].split(" ")[0]
                        else:
                            info2 = "und"

                        ### Mise à jour du codec pour plus de lisibilité
                        try:
                            codec = CodecList[codec1][0]
                        except:
                            codec = codec1.replace("/", "_").lower()

                        ### Envoie des informations dans le tableaux
                        self.ui.mkv_tracks.insertRow(x) # Création de la ligne
                        self.ComboBoxes[x] = QComboBox() # Création de la combobox et ajout d'un element dans le dico
                        self.ui.mkv_tracks.setCellWidget(x, 5, self.ComboBoxes[x]) # Envoie de la combobox
                        self.ComboBoxes[x].addItems(MKVLanguages) # Remplissage de la combobox
                        self.ComboBoxes[x].setStatusTip(self.Trad["TrackAudio"]) # StatusTip
                        self.ComboBoxes[x].currentIndexChanged['QString'].connect(partial(self.ComboModif, x)) # Connexion + ligne

                    ### Traitement spécifique aux sous titres
                    elif TrackType == "subtitles":
                        TrackTypeName = self.Trad["Subtitles"]
                        icone = 'text-x-generic' # Icone sous titres

                        ### Récupération de l'info
                        if " track_name:" in Track:
                            info1 = Track.split(" track_name:")[1].split(" ")[0]
                        else:
                            info1 = ""

                        ### Récupération de la langue
                        if " language:" in Track:
                            info2 = Track.split(" language:")[1].split(" ")[0]
                        else:
                            info2 = "und"

                        ### Mise à jour du codec pour plus de lisibilité
                        try:
                            codec = CodecList[codec1][0]
                        except:
                            codec = codec1.replace("/", "_").lower()

                        self.ui.mkv_tracks.insertRow(x) # Création de la ligne
                        self.ComboBoxes[x] = QComboBox() # Création de la combobox et ajout d'un element dans le dico
                        self.ui.mkv_tracks.setCellWidget(x, 5, self.ComboBoxes[x]) # Envoie de la combobox
                        self.ComboBoxes[x].addItems(MKVLanguages) # Remplissage de la combobox
                        self.ComboBoxes[x].setStatusTip(self.Trad["TrackAudio"]) # StatusTip
                        self.ComboBoxes[x].currentIndexChanged['QString'].connect(partial(self.ComboModif, x)) # Connexion + ligne de la combobox

                    ### Traitement global des pistes simples avec remplacement des caracteres speciaux
                    info1 = info1.replace(r"\s", " ").replace(r"\2", '"').replace(r"\c", ":").replace(r"\h", "#")
                    info2 = info2.replace(r"\s", " ").replace(r"\2", '"').replace(r"\c", ":").replace(r"\h", "#")

                    ### Ajout de la piste au dico
                    MKVDico[x] = [ID, "Track", icone, "layer-visible-off", info1, info2, codec]

                    ### Envoie des informations dans le tableaux
                    self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem(ID)) # Envoie de l'ID
                    self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem("")) # Texte bidon permettant d'envoyer la checkbox
                    self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
                    self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID"].format(ID)) # StatusTip
                    self.ui.mkv_tracks.setItem(x, 2, QTableWidgetItem(IconBis(icone, "Icon"),"")) # Envoie de l'icône
                    self.ui.mkv_tracks.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                    self.ui.mkv_tracks.item(x, 2).setStatusTip(self.Trad["TrackType"].format(TrackTypeName)) # StatusTip
                    self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(IconBis("layer-visible-off", "Icon"),"")) # Envoie de l'icone de visualisation
                    self.ui.mkv_tracks.item(x, 3).setStatusTip(self.Trad["TrackNoDislay"]) # StatusTip
                    self.ui.mkv_tracks.item(x, 3).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                    self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info1)) # Envoie de l'information
                    self.ui.mkv_tracks.item(x, 4).setStatusTip(self.Trad["TrackRename"]) # StatusTip

                    self.ComboBoxes[x].setCurrentIndex(self.ComboBoxes[x].findText(info2)) # Séléction de la valeur de la combobox

                    if "aac" in codec: # Dans le cas de codec aac
                        name = "{}-aac".format(x)
                        self.ComboBoxes[name] = QComboBox() # Création de la combobox et ajout d'un element dans le dico
                        self.ui.mkv_tracks.setCellWidget(x, 6, self.ComboBoxes[name]) # Envoie de la combobox
                        self.ComboBoxes[name].addItems(['aac', 'aac sbr']) # Remplissage de la combobox
                        self.ComboBoxes[name].setStatusTip(self.Trad["TrackAac"]) # StatusTip
                        self.ComboBoxes[name].currentIndexChanged['QString'].connect(partial(self.ComboModif, name)) # Connexion + ligne de la combobox
                        self.ComboBoxes[name].setCurrentIndex(self.ComboBoxes[name].findText(codec)) # Séléction de la valeur de la combobox

                    else:
                        self.ui.mkv_tracks.setItem(x, 6, QTableWidgetItem(codec))
                        self.ui.mkv_tracks.item(x, 6).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                        self.ui.mkv_tracks.item(x, 6).setStatusTip(CodecList[codec1][1]) # StatusTip

                    x += 1 # Incrémentation du numero de ligne


            ### Traitement spécifique aux fichiers joints
            elif Track[:10] == "Attachment":
                ID = Track.split(": ")[0].split(" ")[2] # Récupération de l'ID de la piste
                typecodec = Track.split(" type '")[1].split("'")[0] # Récupération du codec de la piste
                typetrack = typecodec.split("/")[0] # Récupération du type
                info2 = Track.split(" size ")[1].split(" ")[0] # Récupération de l'information numero 2

                ### Récupération du codec qui peut ne pas etre présent (comme dans le cas d'un fichier binaire)
                try:
                    codec = typecodec.split("/")[1]
                except:
                    codec = typecodec

                ### Récupération de l'info
                if " description " in Track:
                    info1 = Track.split(" description '")[1].split("'")[0]
                elif " file name " in Track:
                    info1 = Track.split(" file name '")[1].split("'")[0]
                else:
                    info1 = "No info"

                info1 = info1.replace(r"\s", " ") # Remplacement des \s par des espaces

                ### Mise à jour du codec pour plus de lisibilité
                if codec == "x-truetype-font":
                    codec = "font"
                elif codec == "vnd.ms-opentype":
                    codec = "font OpenType"
                elif codec == "x-msdos-program":
                    codec = "application msdos"
                elif codec == "plain":
                    codec = "text"
                elif codec in ["ogg", "ogm"]: # Ils sont reconnus entant qu'applications
                    typetrack = "media"
                elif codec == "x-flac":
                    codec = "flac"
                elif codec == "x-flv":
                    codec = "flv"
                elif codec == "x-ms-bmp":
                    codec = "bmp"

                ### Icone du type de piste
                machin = QMimeDatabase().mimeTypeForName(typecodec)
                icone = QIcon().fromTheme(QMimeType(machin).iconName(), QIcon().fromTheme(QMimeType(machin).genericIconName())).name()

                if not icone:
                    # Dans le cas où l'icône n'a pas été détériminée
                    if "application" in typetrack:
                        icone = "system-run"
                    elif typetrack == "image":
                        icone = "image-x-generic"
                    elif typetrack == "text":
                        icone = "accessories-text-editor"
                    elif typetrack in ["media", "video", "audio"]:
                        icone = "applications-multimedia"
                    elif typetrack == "web":
                        icone="applications-internet"
                    else:
                        icone = "image-missing"

                ### Mise à jour du dictionnaire des pistes du fichier mkv
                MKVDico[x] = [ID, "Attachment", icone, "layer-visible-on", info1, info2, codec]

                ### Envoie des informations dans le tableaux
                self.ui.mkv_tracks.insertRow(x) # Création de ligne
                self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem(ID)) # Envoie de l'ID
                self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem("")) # Texte bidon permettant d'envoyer la checkbox
                self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
                self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID2"].format(ID)) # StatusTip
                self.ui.mkv_tracks.setItem(x, 2, QTableWidgetItem(IconBis(icone, "Icon"),"")) # Envoie de l'icône
                self.ui.mkv_tracks.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.item(x, 2).setStatusTip(self.Trad["TrackType"].format(typetrack)) # StatusTip
                self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(IconBis("layer-visible-on", "Icon"),"")) # Envoie de l'icone de visualisation
                self.ui.mkv_tracks.item(x, 3).setStatusTip(self.Trad["TrackDislay"]) # StatusTip
                self.ui.mkv_tracks.item(x, 3).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info1)) # Envoie de l'information
                self.ui.mkv_tracks.item(x, 4).setStatusTip(self.Trad["TrackAttachment"]) # StatusTip
                self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem(info2)) # Envoie de l'information
                self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 6, QTableWidgetItem(codec))
                self.ui.mkv_tracks.item(x, 6).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification

                x += 1 # Incrémentation du numero de ligne


            ### Traitement spécifique aux chapitres
            elif Track[:8] == "Chapters":
                icone = "x-office-address-book" # Icone de chapitrage
                info1 = Track.split(": ")[1].split(" ")[0] # Récupération de l'info 1
                info2 = self.Trad["TrackChapters"] # Récupération de l'info 2
                mixe = info1 + " " + info2

                ### Mise à jour du dictionnaire des pistes du fichier mkv
                MKVDico[x] = ["NoID", "Chapters", icone, "layer-visible-on", info2, mixe, "Chapters"]

                ### Envoie des informations dans le tableaux
                self.ui.mkv_tracks.insertRow(x) # Création de ligne
                self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem("chapters")) # Envoie du type de piste
                self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem("")) # Texte bidon permettant d'envoyer la checkbox
                self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
                self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID3"].format(info2)) # StatusTip
                self.ui.mkv_tracks.setItem(x, 2, QTableWidgetItem(IconBis(icone, "Icon"),"")) # Envoie de l'icône
                self.ui.mkv_tracks.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.item(x, 2).setStatusTip(self.Trad["TrackType"].format(info2)) # StatusTip
                self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(IconBis("layer-visible-on", "Icon"),"")) # Envoie de l'icone de visualisation
                self.ui.mkv_tracks.item(x, 3).setStatusTip(self.Trad["TrackDislay"]) # StatusTip
                self.ui.mkv_tracks.item(x, 3).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2)) # Envoie de l'information
                self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem(mixe)) # Envoie de l'information
                self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 6, QTableWidgetItem("")) # Texte bidon permettant le blocage
                self.ui.mkv_tracks.item(x, 6).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification

                x += 1 # Incrémentation du numero de ligne


            ### Traitement spécifique aux tags
            elif Track[:11] == "Global tags":
                icone = "text-html" # Icone de global tags
                info1 = Track.split(": ")[1].split(" ")[0] # Récupération de l'info 1
                info2 = self.Trad["TrackTags"] # Récupération de l'info 2
                mixe = info1 + " " + info2

                ### Mise à jour du dictionnaire des pistes du fichier mkv
                MKVDico[x] = ["NoID", "Global tags", icone, "layer-visible-on", info2, mixe, "Tags"]

                ### Envoie des informations dans le tableaux
                self.ui.mkv_tracks.insertRow(x) # Création de ligne
                self.ui.mkv_tracks.setItem(x, 0, QTableWidgetItem("tags")) # Envoie du type de piste
                self.ui.mkv_tracks.setItem(x, 1, QTableWidgetItem("")) # Texte bidon permettant d'envoyer la checkbox
                self.ui.mkv_tracks.item(x, 1).setCheckState(0) # Envoie de la checkbox
                self.ui.mkv_tracks.item(x, 1).setStatusTip(self.Trad["TrackID3"].format(info2)) # StatusTip
                self.ui.mkv_tracks.setItem(x, 2, QTableWidgetItem(IconBis(icone, "Icon"),"")) # Envoie de l'icône
                self.ui.mkv_tracks.item(x, 2).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.item(x, 2).setStatusTip(self.Trad["TrackType"].format(info2)) # StatusTip
                self.ui.mkv_tracks.setItem(x, 3, QTableWidgetItem(IconBis("layer-visible-on", "Icon"),"")) # Envoie de l'icone de visualisation
                self.ui.mkv_tracks.item(x, 3).setStatusTip(self.Trad["TrackDislay"]) # StatusTip
                self.ui.mkv_tracks.item(x, 3).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 4, QTableWidgetItem(info2)) # Envoie de l'information
                self.ui.mkv_tracks.item(x, 4).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 5, QTableWidgetItem(mixe)) # Envoie de l'information
                self.ui.mkv_tracks.item(x, 5).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification
                self.ui.mkv_tracks.setItem(x, 6, QTableWidgetItem("")) # Texte bidon permettant le blocage
                self.ui.mkv_tracks.item(x, 6).setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled) # Blocage de la modification

                x += 1 # Incrémentation du numero de ligne


        ### Retours d'information, deblocage, curseur normal
        self.SetInfo(self.Trad["WorkMerge"], "800080", True, False)
        Variables["SuperBlock"] = False # Variable servant à bloquer les signaux du tableau (impossible autrement)
        self.setCursor(Qt.ArrowCursor)


    #========================================================================
    def TrackView(self, x, y):
        """Fonction ouvrant les pistes jointes visualisables."""
        ### Dans le cas d'un clic sur l'icone avec l'oeil = colonne 3
        if y == 3:
            ### Ne traite pas les icones off
            if MKVDico[x][3] == "layer-visible-off":
                return

            ### Dans le cas d'un fichier de chapitrage
            if MKVDico[x][1] == "Chapters":
                Variables["MKVChapters"] = Path(Variables["TempFolderName"], "chapters.txt") # Fichier de sortie

                ### Extraction si le fichier n'existe pas
                if not Variables["MKVChapters"].exists():
                    Variables["Cmd"] = ["MKVExtract", "Chapters", 'mkvextract chapters "{}" -s'.format(Variables["MKVLinkIn"])]
                    self.process.start(Variables["Cmd"][2]) # Lancement de la commande d'extraction
                    self.process.waitForFinished() # Attend la fin du travail avant de continuer

                ### Ouverture du fichier
                self.process.startDetached('xdg-open "{}"'.format(Variables["MKVChapters"]))

            ### Dans le cas de global tags
            elif MKVDico[x][1] == "Global tags":
                Variables["MKVTags"] = Path(Variables["TempFolderName"], "tags.xml") # Fichier de sortie

                ### Extraction si le fichier n'existe pas
                if not Variables["MKVTags"].exists():
                    Variables["Cmd"] = ["MKVExtract", "Tags", 'mkvextract tags "{}"'.format(Variables["MKVLinkIn"])]
                    self.process.start(Variables["Cmd"][2]) # Lancement de la commande d'extraction
                    self.process.waitForFinished() # Attend la fin du travail avant de continuer

                ### Ouverture du fichier
                self.process.startDetached('xdg-open "{}"'.format(Variables["MKVTags"]))

            ### Dans le cas de fichier joint
            elif MKVDico[x][1] == "Attachment":
                fichier = Path(Variables["TempFolderName"], 'attachement_{0[0]}_{0[4]}'.format(MKVDico[x])) # Fichier de sortie

                ### Extraction si le fichier n'existe pas
                if not fichier.exists():
                    Variables["Cmd"] = ["MKVExtract", "Attachments", 'mkvextract attachments "{}" {}:"{}"'.format(Variables["MKVLinkIn"], MKVDico[x][0], fichier)]
                    self.process.start(Variables["Cmd"][2]) # Lancement de la commande d'extraction
                    self.process.waitForFinished() # Attend la fin du travail avant de continuer

                ### Ouverture du fichier
                self.process.startDetached('xdg-open "{}"'.format(fichier))


    #========================================================================
    def ComboModif(self, x, value):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'utilisation des comboboxes du tableau."""
        ### Si x est une chaine, c'est que ça traite un fichier aac
        if type(x) is str:
            x = int(x.split("-")[0]) # Récupération de la ligne
            if value != MKVDico[x][6]:
                MKVDico[x][6] = value # Met à jour la valeur du dictionnaire

                ### Dans le cas où la piste est séléctionée
                if self.ui.mkv_tracks.item(x, 1).checkState():
                    MKVDicoSelect[x][6] = value # Met à jour le dico des pistes séléctionnée

        ### Pour les autres combobox
        elif value != MKVDico[x][5]:
            MKVDico[x][5] = value # Met à jour la valeur du dictionnaire

            ### Dans le cas où la piste est séléctionée
            if self.ui.mkv_tracks.item(x, 1).checkState():
                MKVDicoSelect[x][5] = value # Met à jour le dico des pistes séléctionnée



    #========================================================================
    def TrackModif(self, info):
        """Fonction mettant à jour les dictionnaires des pistes du fichier MKV lors de l'edition des textes."""
        ### Blocage de la fonction pendant le chargement des pistes
        if Variables["SuperBlock"]:
            return

        ### Récupération de la cellule modifiée
        x, y = self.ui.mkv_tracks.row(info), self.ui.mkv_tracks.column(info)

        ### Dans le cas de la modification d'une checkbox
        if y == 1:
            ### Mise au propre du tableau
            MKVDicoSelect.clear() # Mise au propre du dictionnaire
            for x in range(self.ui.mkv_tracks.rowCount()): # Boucle traitant toutes les lignes du tableau
                if self.ui.mkv_tracks.item(x, 1).checkState(): # Teste si la ligne est cochée
                    MKVDicoSelect[x] = MKVDico[x] # mise à jour de la liste des pistes cochées

            ### Blocage des boutons par defaut
            self.ui.mkv_execute.setEnabled(False)
            self.ui.mkv_execute_2.setEnabled(False)
            self.ui.option_dts_ac3.setEnabled(False)
            self.ui.option_vobsub_srt.setEnabled(False)
            self.ui.option_reencapsulate.setEnabled(False)

            ### Arret de la fonction si pas de séléction ou pas de dossier de sortie
            if MKVDicoSelect and Configs["MKVDirNameOut"]:
                self.ui.mkv_execute.setEnabled(True) # Debloquage du bouton d'execution
                self.ui.mkv_execute_2.setEnabled(True) # Debloquage du bouton d'execution
                self.ui.option_reencapsulate.setEnabled(True)

                for valeurs in MKVDicoSelect.values(): # Boucle sur la liste des lignes
                    if "dts" in valeurs[-1]: # Recherche la valeur dts dans les sous listes
                        self.ui.option_dts_ac3.setEnabled(True) # Deblocage du widget

                    elif "sub" in valeurs[-1]: # Recherche la valeur vobsub dans les sous listes
                        self.ui.option_vobsub_srt.setEnabled(True) # Deblocage de widget

            ### Décoche les boutons s'ils sont grisés
            for widget in [self.ui.option_vobsub_srt, self.ui.option_reencapsulate, self.ui.option_dts_ac3]:
                if not widget.isEnabled():
                    widget.setChecked(False)


        ### Dans le cas d'une modification de texte
        else:
            ### Mise à jour du texte dans le dico des pistes
            MKVDico[x][y] = self.ui.mkv_tracks.item(x, y).text() # Récupération du nouveau texte de la cellule

            ### Mise à jour du texte dans le dico des pistes séléctionnées
            if self.ui.mkv_tracks.item(x, 1).checkState(): # Verifie si la ligne est séléctionnée
                MKVDicoSelect[x][y] = MKVDico[x][y]


    #========================================================================
    def MKVExecute(self):
        """Fonction créant toutes les commandes : mkvextractor, ffmpeg, mkvmerge..."""
        ### Mise au propre et initialisation de variables
        Variables["CmdOld"] = "" # Garde en mémoire le nom du dernier pack de commande lancé
        Variables["TempFiles"] = [] # Fichiers temporaires à effacer en cas d'arret
        Variables["CmdList"] = [] # Liste des commandes à éxecuter à la suite
        Variables["MKVLinkOut"] = Path("Bidon") # Fichier mkv de sortie en cas de réencapsulage
        Variables["MKVChapters"] = Path("Bidon") # Fichier de sortie des chapitres
        Variables["MKVTags"] = Path("Bidon") # Fichier de sortie des tags
        mkvextract_merge = ""
        mkvextract_track = "" # Commande d'extraction des pistes normales
        mkvextract_joint = "" # Commande d'extraction des fichiers joints
        mkvextract_chap = "" # Commande d'extraction des chapitres
        mkvextract_tag = "" # Commande d'extraction des tags
        dts_ffmpeg = "" # Commande de conversion DTS vers AC3
        mkvmerge = "" # Commande de réencapsulage
        subconvert = [] # Liste pour la conversion des sous titres SUB en SRT


        ### Si on veut uniquement réencapsuler sans rien d'autre, on affiche un message conseillant d'utiliser mmg
        if Variables["Reencapsulate"] and not Variables["DtsToAc3"] and not Variables["VobsubToSrt"] and not Configs["SubtitlesOpen"]:
            UseMMG = QMessageBox(4, self.Trad["UseMMGTitle"], self.Trad["UseMMGText"], QMessageBox.NoButton, self, Qt.WindowSystemMenuHint)
            UseMMG.setWindowFlags(Qt.WindowTitleHint | Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.CustomizeWindowHint) # Enleve le bouton de fermeture de la fenetre
            MMG = QPushButton(IconBis("mkvmerge", "Icon"), "MKV Merge Gui") # Création du bouton MKV Merge Gui
            MEQ = QPushButton(IconBis("mkv-extractor-qt5", "Icon"), "MKV Extracor Qt 5") # Création du bouton MKV Extracor Qt
            UseMMG.addButton(MMG, QMessageBox.YesRole) # Ajout du bouton
            UseMMG.addButton(MEQ, QMessageBox.NoRole) # Ajout du bouton
            UseMMG.setDefaultButton(MEQ) # Bouton par defaut : MKV Extracor Qt
            UseMMG.exec() # Message d'information

            # Recupération du résultat
            if UseMMG.buttonRole(UseMMG.clickedButton()) == 5:
                self.MKVMergeGui()
                return


        ### Boucle traitant les pistes une à une
        for Select in MKVDicoSelect.values():
            # Select[0] : ID
            # Select[1] : Type de pyste : Track, Attachment, Chapters, Global
            # Select[2] : Icone
            # Select[3] : Icone de visualisation
            # Select[4] : Nom de la piste
            # Select[5] : Info : fps, langue...
            # Select[6] : Info : codec

            ### Traitement des pistes videos, maj de commandes
            if Select[2] == "video-x-generic":
                Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_video_{0[4]}.mkv".format(Select)))
                mkvextract_track += '{0[0]}:"{1}/{0[0]}_video_{0[4]}.mkv" '.format(Select, Configs["MKVDirNameOut"])
                mkvmerge += '--track-name "0:{0[4]}" --default-duration "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_video_{0[4]}.mkv" '.format(Select, Configs["MKVDirNameOut"])
                mkvextract_merge += '--track-name "0:{0[4]}" --default-duration "0:{0[5]}" --compression "0:none" '.format(Select)


            ### Traitement des pistes audios
            elif Select[2] == "audio-x-generic":
                ### Dans le cas où il y aura conversion des dts en ac3, maj de commandes
                if Variables["DtsToAc3"]:
                    Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_audio_{0[4]}.ac3".format(Select)))
                    dts_ffmpeg += '-vn -map 0:{} '.format(Select[0])

                    ### En cas de boost du fichier ac3
                    if Configs["Ac3Boost"] > 1:
                        dts_ffmpeg += '-vol {} '.format(Configs["Ac3Boost"])

                    ### En cas de passage en stereo
                    if Configs["Stereo"]:
                        dts_ffmpeg += '-ac 2 '

                    dts_ffmpeg += '-ab {0}k -f ac3 "{1}/{2[0]}_audio_{2[4]}.ac3" '.format(Configs["Ac3Kbits"], Configs["MKVDirNameOut"], Select)
                    mkvmerge += '--language "0:{0[5]}" --compression "0:none" --track-name "0:{0[4]}" "{1}/{0[0]}_audio_{0[4]}.ac3" '.format(Select, Configs["MKVDirNameOut"])
                    mkvextract_merge += '--language "0:{0[5]}" --compression "0:none" --track-name "0:{0[4]}" '.format(Select)


                ### Dans le cas où il n'y aura pas de conversion des dts en ac3, maj de commandes
                else:
                    Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_audio_{0[4]}.{0[6]}".format(Select)))
                    mkvextract_track += '{0[0]}:"{1}/{0[0]}_audio_{0[4]}.{0[6]}" '.format(Select, Configs["MKVDirNameOut"])

                    ### Dans le cas où il faut ré-encapsuler des fichiers aac, il faut preciser si sbr ou non
                    if "aac" in Select[6]:
                        if Select[6] == "aac sbr":
                            mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:0" --compression "0:none" "{1}/{0[0]}_audio_{0[4]}.{0[6]}" '.format(Select, Configs["MKVDirNameOut"])
                            mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:0" --compression "0:none" '.format(Select)
                        else:
                            mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:1" --compression "0:none" "{1}/{0[0]}_audio_{0[4]}.{0[6]}" '.format(Select, Configs["MKVDirNameOut"])
                            mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --aac-is-sbr "0:1" --compression "0:none" '.format(Select)

                    ### Dans le cas où il n'y a pas de fichier aac
                    else:
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_audio_{0[4]}.{0[6]}" '.format(Select, Configs["MKVDirNameOut"])
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)


            ### Traitement des pistes sous titres
            elif Select[2] == "text-x-generic":
                ### Dans le cas de sous titres de fichiers sub
                if Select[6] == "sub":
                    Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_subtitles_{0[4]}.idx".format(Select)))
                    Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_subtitles_{0[4]}.sub".format(Select)))
                    mkvextract_track += '{0[0]}:"{1}/{0[0]}_subtitles_{0[4]}.idx" '.format(Select, Configs["MKVDirNameOut"])

                    ### Dans le cas d'un conversion SUB => AC3, maj de commandes
                    if Variables["VobsubToSrt"]:
                        Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_subtitles_{0[4]}.srt".format(Select)))
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_subtitles_{0[4]}.srt" '.format(Select, Configs["MKVDirNameOut"])
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)

                        ### Difference de nom entre la langue de tesseract et celle de mkvalidator
                        if Select[5] == "fre":
                            Select[5] = "fra"

                        subconvert.append([Select[0], Select[4], Select[5]])

                    ### Dans le cas ou il n'y a pas de conversion, maj de commande
                    else:
                        mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_subtitles_{0[4]}.idx" '.format(Select, Configs["MKVDirNameOut"])
                        mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)


                ### Dans le cas de sous titres autre que de type sub, maj de commandes
                else:
                    mkvmerge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" "{1}/{0[0]}_subtitles_{0[4]}.{0[6]}" '.format(Select, Configs["MKVDirNameOut"])
                    mkvextract_merge += '--track-name "0:{0[4]}" --language "0:{0[5]}" --compression "0:none" '.format(Select)
                    Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_subtitles_{0[4]}.{0[6]}".format(Select)))
                    mkvextract_track += '{0[0]}:"{1}/{0[0]}_subtitles_{0[4]}.{0[6]}" '.format(Select, Configs["MKVDirNameOut"])


            ### Traitement des pistes chapitrage, maj de commandes
            elif Select[2] == "x-office-address-book":
                Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "chapters.txt"))
                mkvmerge += '--chapters "{}/chapters.txt" '.format(Configs["MKVDirNameOut"])
                mkvextract_chap = 'mkvextract chapters "{}" -s '.format(Variables["MKVLinkIn"])
                Variables["MKVChapters"] = Path(Configs["MKVDirNameOut"], "chapters.txt")


            ### Traitement des pistes de tags, maj de commandes
            elif Select[2] == "text-html":
                Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "tags.xml"))
                mkvmerge += '--global-tags "{}/tags.xml" '.format(Configs["MKVDirNameOut"])
                mkvextract_tag = 'mkvextract tags "{}" '.format(Variables["MKVLinkIn"])
                Variables["MKVTags"] = Path(Configs["MKVDirNameOut"], "tags.xml")


            ### Traitement des pistes jointes, maj de commandes
            else:
                mkvextract_joint += '{0[0]}:"{1}/{0[0]}_{0[4]}" '.format(Select, Configs["MKVDirNameOut"])
                Variables["TempFiles"].append(Path(Configs["MKVDirNameOut"], "{0[0]}_{0[4]}".format(Select)))
                mkvmerge += '--attachment-name "{0[4]}" --attach-file "{1}/{0[0]}_{0[4]}" '.format(Select, Configs["MKVDirNameOut"])


        ### Ajout de la commande mkvextract_track à la liste des commandes à executer
        if mkvextract_track:
            Variables["CmdList"].append(["MKVExtract", "Tracks", 'mkvextract tracks "{}" {}'.format(Variables["MKVLinkIn"], mkvextract_track)])


        ### Ajout de la commande mkvextract_tag à la liste des commandes à executer
        if mkvextract_tag and not Variables["MKVChapters"].exists():
            Variables["CmdList"].append(["MKVExtract", "Tags", mkvextract_tag])


        ### Ajout de la commande mkvextract_chap à la liste des commandes à executer
        if mkvextract_chap and not Variables["MKVTags"].exists():
            Variables["CmdList"].append(["MKVExtract", "Chapters", mkvextract_chap])


        ### Ajout de la commande mkvextract_joint à la liste des commandes à executer
        if mkvextract_joint:
            Variables["CmdList"].append(["MKVExtract", "Attachments", 'mkvextract attachments "{}" {}'.format(Variables["MKVLinkIn"], mkvextract_joint)])


        ### Ajout des commandes de conversion des vobsub en srt
        if Variables["VobsubToSrt"]:
            MKVSubSrt.clear() # Nettoyage du dictionnaire

            ### Pour chaque fichier à convertir
            for SubInfo in subconvert:
                ### Initialisation de variables
                ID = SubInfo[0]
                Name = SubInfo[1]
                Lang = SubInfo[2]
                BaseFile = '{}/{}_subtitles_{}'.format(Configs["MKVDirNameOut"], ID, Name)
                IDX = '{}.idx'.format(BaseFile)
                SUB = '{}.sub'.format(BaseFile)
                SRT = '{}.srt'.format(BaseFile)
                Folder = '{}/SUB2SRT'.format(Variables["TempFolderName"])
                Files = '{}/{}_subtitles_{}'.format(Folder, ID, Name)
                IDXNew = '{}/{}_subtitles_{}.idx'.format(Folder, ID, Name)

                MKVSubSrt[ID] = [] # Creation du dictionnaire listant les differentes infos
                for info in [Lang, IDX, SUB, Folder, IDXNew]:
                    MKVSubSrt[ID].append(info)

                ### Envoie des commandes dans la liste
                Variables["CmdList"].append(["Sub2Srt", "Demarrage", 'echo', ID])
                Variables["CmdList"].append(["Sub2Srt", "Subp2Pgm", '"{}" -n "{}/{}_subtitles_{}"'.format(Variables["subp2pgm"], Folder, ID, Name), ID])
                Variables["CmdList"].append(["Sub2Srt", "Tesseract", "", ID])
                Variables["CmdList"].append(["Sub2Srt", "SubpTools", '"{}" -s -w -t srt -i "{}.xml" -o "{}"'.format(Variables["subptools"], Files, SRT), ID])


        ### Ajout de la commande mkvextract_joint à la liste des commandes à executer
        if dts_ffmpeg:
            if Configs["FFMpeg"]: ffconv = "ffmpeg"
            else: ffconv = "avconv"

            Variables["CmdList"].append([ffconv, "", '{} -y -i "{}" {}'.format(ffconv, Variables["MKVLinkIn"], dts_ffmpeg)])


        ### Ajout de la commande mkvmerge à la liste des commandes à executer
        if Variables["Reencapsulate"]:
            ### Fenetre de séléction de sortie du fichier mkv
            Variables["MKVLinkOut"] = Path(QFileDialog.getSaveFileName(self, self.Trad["SelectFileOut"], QDir.path(QDir("{}/MEG_{}".format(Configs["MKVDirNameOut"], Variables["MKVFileNameIn"]))), "Matroska Files(*.mka *.mks *.mkv *.mk3d *.webm *.webmv *.webma)")[0])

            ### Arret de la fonction si aucun fichier n'est choisi => utilise . si negatif
            if Variables["MKVLinkOut"] == Path():
                return

            ### Ajout du fichier mkv à la liste des fichiers
            Variables["TempFiles"].append(Variables["MKVLinkOut"])

            ### Dans le cas où il faut ouvrir les fichiers srt avant leur encapsulage
            if Configs["SubtitlesOpen"]:
                Variables["MKVSubtitles"] = []
                for file in Variables["TempFiles"]:
                    if file.suffix == ".srt":
                        Variables["MKVSubtitles"].append(file)

                if Variables["MKVSubtitles"]:
                    Variables["CmdList"].append(["MKVMerge", "Open SRT", "echo"]) # Echo bidon pour être sur que la commande se termine bien

            ### Dans le cas où il faut réencapsuler
            Variables["MKVTitle"] = self.ui.mkv_title.text() # Récupération du titre du fichier

            # Si le titre est vide, il plante mkvmerge
            if Variables["MKVTitle"]:
                Variables["CmdList"].append(["MKVMerge", "Merge", 'mkvmerge -o "{}" --title "{}" {}'.format(Variables["MKVLinkOut"], Variables["MKVTitle"], mkvmerge)])
                mkvextract_merge = 'mkvmerge -o "{}" --title "{}" {}'.format(Variables["MKVLinkOut"], Variables["MKVTitle"], mkvextract_merge)
            else:
                Variables["CmdList"].append(["MKVMerge", "Merge", 'mkvmerge -o "{}" {}'.format(Variables["MKVLinkOut"], mkvmerge)])
                mkvextract_merge = 'mkvmerge -o "{}" --title "{}" {}'.format(Variables["MKVLinkOut"], Variables["MKVTitle"], mkvextract_merge)


        ### Code à executer
        Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la 1ere commande

        ### Modifications graphiques
        self.SetInfo(self.Trad["WorkProgress"].format(Variables["Cmd"][0]), "800080", True, True) # Nom de la commande
        self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2])) # Envoie d'informations
        self.WorkInProgress(True) # Bloquage des widgets

        ### Lancement de la commande
        self.process.start(Variables["Cmd"][2])



    #========================================================================
    def WorkInProgress(self, value):
        """Fonction de modifications graphiques en fonction d'un travail en cours ou non."""
        ### Dans le cas d'un lancement de travail
        if value:
            self.ui.mkv_execute.hide() # Cache le bouton executer
            self.ui.mkv_execute_2.setEnabled(False) # Grise le bouton executer
            self.ui.mkv_stop.show() # Affiche le bouton arreter

            for widget in (self.ui.menubar, self.ui.tracks_bloc, self.ui.view_info, self.ui.out_info):
                widget.setEnabled(False) # Blocage de widget


        ### Dans le cas où le travail vient de se terminer (bien ou mal)
        else:
            Variables["CmdList"] = [] # Réinitialisation de la liste des commandes (pouvant ne pas etre vide en cas d'annulation)

            ### Modifications graphiques
            self.ui.mkv_execute.show() # Affiche le bouton executer
            self.ui.mkv_execute_2.setEnabled(True) # Dégrise le bouton executer
            self.ui.mkv_stop.hide() # Cache le bouton arreter

            for widget in (self.ui.menubar, self.ui.tracks_bloc, self.ui.view_info, self.ui.out_info):
                widget.setEnabled(True) # Blocage de widget

            ### Réinitialisation du bon formatage de la barre de progression (dans le cas de IMGViewer)
            if self.ui.progressBar.format() != "%p %":
                self.ui.progressBar.setFormat("%p %") # Affichage simple du pourcentage

            ### Réinitialisation de la valeur maximale de la barre de progression (dans le cas de MKValidator)
            if self.ui.progressBar.maximum() != 100:
                self.ui.progressBar.setMaximum(100) # Retour à un maxmimum de 100

            ### Réaffiche le tableau des pistes si ce n'est plus lui qui est affiché (dans le cas de IMGViewer)
            if self.ui.stackedMiddle.currentIndex() != 0:
                self.ui.stackedMiddle.setCurrentIndex(0) # Affichage du 1er item du widget stackedMiddle

            ### Réinitialise la variable bloquante si elle a été utilisée
            if Variables["WorkStop"]:
                Variables["WorkStop"] = False


    #========================================================================
    def WorkReply(self):
        """Fonction recevant tous les retours du travail en cours."""
        ### Si variable stop activée, arret brutal du travail en cours
        if Variables["WorkStop"]:
            self.setCursor(Qt.ArrowCursor) # Curseur normal
            self.process.kill() # Kill du process
            return

        ### Récupération du retour (les 2 sorties sont sur la standard)
        data = self.process.readAllStandardOutput()

        ### Converti les data en textes et les traite
        for line in bytes(data).decode('utf-8').splitlines():
            ### Passe la boucle si le retour est vide, ce qui arrive et provoque une erreur
            if line == "":
                continue # Relance la boucle

            ### Traitement des retours de MKVMerge
            elif Variables["Cmd"][0] == "MKVMerge":
                if Variables["Cmd"][1] in ["LanguagesList", "TracksList"]:
                    if Variables["Cmd"][1] == "LanguagesList": # Dans le cas du listage des langues
                        if line[0] != "-": # Exclue la ligne contenant les ---
                            line = line.split('|')[1].strip() # Recupere la 2eme colonne, la langue en 3 lettres

                            if len(line) == 3: # Verifie que le resultat est bien de 3 caracteres
                                MKVLanguages.append(line) # Ajout de la langue

                    elif Variables["Cmd"][1] == "TracksList": # Dans le cas du listage des pistes
                        line = line.replace("\c", ":") # Remplacement des \c en :

                        # Si le 1er caractere est une majuscule, on ajoute la piste
                        if line[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            Variables["Tracks"].append(line)

                        # Sinon, c'est que les lignes sont découpées, on conserve donc la valeur en memoire
                        else:
                            Variables["Tracks"][-1] = Variables["Tracks"][-1] + line

                    # Relance la boucle pour récuper les valeurs suivantes
                    continue


                ### Dans le cas d'un encapsulation
                elif Variables["Cmd"][1] == "Merge":
                    if line[-1] == "%": # Traiter le retour en cas de presence de pourcentage
                        line = int(line.split(": ")[1].strip()[0:-1]) # Récupere le nombre


                ### Dans le cas d'une conversion
                elif Variables["Cmd"][1] == "FileToMKV":
                    if line[-1] == "%": # Traiter le retour en cas de presence de pourcentage
                        line = int(line.split(": ")[1].strip()[0:-1]) # Récupere le nombre


            ### MKVInfo sert à récupérer quelques infos sur le fichier mkv
            elif Variables["Cmd"][0] == "MKVInfo":
                # Récupération du titre du fichier MKV
                if "+ Title:" in line:
                    Variables["MKVTitle"] = line.split(": ")[1]

                # Récupération de la durée du fichier MKV
                elif "+ Duration:" in line:
                    Variables["MKVTime"] = int(line.split(": ")[1].split(".")[0])

                # Récupération de la numero de la piste pour être utilisé pour les fps ci après
                elif "+ Track number:" in line:
                    Variables["TempInfo"] = int(line.split(": ")[-1].split(")")[0])

                # Récupération de la durée du fichier MKV
                elif "+ Default duration:" in line:
                    line = line.split("(")[1].split(" ")[0]
                    MKVFPS[Variables["TempInfo"]] = "{}fps".format(line)

                # Relance la boucle pour récuper les valeurs suivantes
                continue


            ### MKVExtract renvoie une progression ou les contenus des fichiers de tags et chapitres. Les fichiers joints ne renvoient rien.
            elif Variables["Cmd"][0] == "MKVExtract":
                # Dans le cas de l'extraction de pistes simples
                if Variables["Cmd"][1] == "Tracks":
                    if line[-1] == "%": # Traiter le retour en cas de presence de pourcentage
                        line = int(line.split(": ")[1].strip()[0:-1]) # Récupere le nombre

                else:
                    # En cas d'extraction de chapitres
                    if Variables["Cmd"][1] == "Chapters":
                        with Variables["MKVChapters"].open('a') as ChaptersFile:
                            ChaptersFile.write(line+'\n')

                    # En cas d'extraction de tags
                    elif Variables["Cmd"][1] == "Tags":
                        with Variables["MKVTags"].open('a') as TagsFile:
                            TagsFile.write(line+'\n')

                    # Relance la boucle pour récuper les valeurs suivantes
                    continue


            ### MKValidator ne renvoie pas de pourcentage mais des infos ou des points
            elif Variables["Cmd"][0] == "MKValidator":
                line = line.strip().replace('.','') # Suppression des . qui servent à indiquer un travail en cours


            ### MKClean renvoie une progression et des infos
            elif Variables["Cmd"][0] == "MKClean":
                if line[-1] == "%": # Traiter le retour en cas de presence de pourcentage
                    line = int(line.split(": ")[1].strip()[0:-1])


            ### FFMpeg ne renvoie pas de pourcentage mais la durée de vidéo encodée en autre
            elif Variables["Cmd"][0] in ["ffmpeg", "avconv"]:
                if "time=" in line and Variables["MKVTime"]:
                    # Pour les versions renvoyant : 00:00:00
                    try:
                        value = line.split("=")[2].strip().split(".")[0].split(":")
                        value = datetime.timedelta(hours=int(value[0]), minutes=int(value[1]), seconds=int(value[2])).seconds

                    # Pour les versions renvoyant : 00000 secondes
                    except:
                        value = line.split("=")[2].strip().split(".")[0]

                    # Pourcentage maison se basant sur la durée du fichier
                    line = int((value * 100) / Variables["MKVTime"])


            ### Sub2Srt est en fait un ensemble de commande mais seul Tesseract à besoin d'être traité
            elif Variables["Cmd"][0] == "Sub2Srt":
                # Récupération des langues (3 carac) dispo dans Tesseract
                if Variables["Cmd"][1] == "TesseractLang":
                    if len(line) == 3:
                        TesseractLanguages.append(line) # Ajout de la langue

                    # Relance la boucle pour récuper les valeurs suivantes
                    continue

                # Pourcentage maison se basant sur le nombre de fichier fait et restant
                elif Variables["Cmd"][1] == "Tesseract":
                    NbFiles = len(Variables["ImgFiles"])
                    line = int(100 - ((NbFiles * 100) / Variables["ImgFilesNb"]))


            ### Affichage du texte ou de la progression si c'est une nouvelle valeur
            if line and line != Variables["WorkOldLine"]: # Comparaison anti doublon
                Variables["WorkOldLine"] = line # Mise à jour de la variable anti doublon

                # Envoie du pourcentage à la barre de progression si c'est un nombre
                if type(line) is int:
                    self.ui.progressBar.setValue(line)

                # Envoie de l'info à la boite de texte si c'est du texte
                else:
                    self.SetInfo(line)


    #========================================================================
    def WorkFinished(self):
        """Fonction appellée à la fin du travail, que ce soit une fin normale ou annulée."""
        # Variables["Cmd"][0] : Nom de la commande
        # Variables["Cmd"][1] : Argument (tags, chapters...)
        # Variables["Cmd"][2] : Commande à executer ou liste de fichiers

        ### Si le travail est annulé (via le bouton stop ou via la fermeture du logiciel) ou a renvoyée une erreur
        if Variables["WorkStop"] or self.process.exitCode() != 0:
            # Suppression des fichiers temporaires
            self.RemoveTempFiles()

            # Envoie du texte le plus adapté
            if Variables["WorkStop"]:
                self.SetInfo(self.Trad["WorkCanceled"], "FF0000", True) # Travail annulé
            else:
                self.SetInfo(self.Trad["WorkError"], "FF0000", True) # Erreur pendant le travail

            ### Modifications graphiques
            self.ui.progressBar.setValue(0) # Remise à 0 de la barre de progression signifiant une erreur
            self.WorkInProgress(False) # Remise en état des widgets


        ### Traitement different en fonction de la commande
        # Rien de particulier pour MKValidator, MKClean, FFMpeg
        else:
            if Variables["Cmd"][0] == "MKVMerge":
                if Variables["Cmd"][1] == "Open SRT":
                    Variables["WorkPause"] = True  # Mise en pause du logiciel
                    self.ui.mkv_resume.show() # Affiche le bouton de reprise
                    self.SetInfo(self.Trad["WorkPaused"], "FF0000", True, True) # Info de mise en pause

                    for file in Variables["MKVSubtitles"]: # Boucle ouvrant tous les fichiers srt d'un coup
                        self.process.startDetached('xdg-open "{}"'.format(file))

                elif not Variables["Cmd"][1] in ("Merge", "FileToMKV"): # Soit pause soit recup de variable
                    return # Arrete la fonction

            elif Variables["Cmd"][0] == "MKVInfo": # Simple réccupération de variable
                return # Arrete la fonction

            elif Variables["Cmd"][0] == "MKVExtract": # Systeme n'affichant pas la fin tant qu'il y a des extractions
                if Variables["CmdList"] and Variables["CmdList"][0][0] == "MKVExtract":
                    Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la commande suivante à executer
                    self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2]), newline=True) # Envoie d'informations
                    self.process.start(Variables["Cmd"][2]) # Lancement de la commande
                    return

                elif Variables["Cmd"][1] == "Attachments":
                    self.WorkInProgress(False) # Remise en état des widgets
                    return


            elif Variables["Cmd"][0] == "Sub2Srt": # Systeme n'affichant pas la fin tant que la conversion n'est pas finie
                if Variables["CmdList"] and Variables["CmdList"][0][0] == "Sub2Srt":
                    self.Sub2SrtFinished()
                    return


            ### Indication de fin de pack de commande
            self.SetInfo(self.Trad["WorkFinished"].format(Variables["Cmd"][0]), "800080", True) # Travail terminé
            self.ui.progressBar.setValue(100) # Mise à 100% de la barre de progression pour signaler la fin ok


            ### Lancement de l'ouverture du fichier mkv, ici pour un soucis esthetique du texte affiché
            if Variables["Cmd"][1] == "FileToMKV":
                # Dans le cas d'une conversion
                self.MKVOpen(Variables["TempFiles"][-1]) # Lancement de la fonction d'ouverture du fichier mkv créé avec le nom du fichier


            ### S'il reste des commandes, execution de la commande suivante
            if Variables["CmdList"]:
                Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la commande suivante à executer
                self.ui.progressBar.setValue(0) # Mise à 0% de la barre de progression pour signaler le debut du travail

                if Variables["Cmd"][1] != "Open SRT": # Evite de dire que la cmd mkmerge se lance et que le log est en pause
                    self.SetInfo(self.Trad["WorkProgress"].format(Variables["Cmd"][0]), "800080", True, True) # Nom de la commande

                if Variables["Cmd"][2] != "echo": # Cas des commandes bidons
                    self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2])) # Envoie d'informations

                self.process.start(Variables["Cmd"][2]) # Lancement de la commande


            ### Si c'était la derniere commande
            else:
                if Configs["DelTemp"] and Variables["Cmd"][0] == "MKVMerge": # Si l'option de suppression des fichiers temporaire est active
                    Variables["TempFiles"].remove(Variables["MKVLinkOut"]) # Suppression du fichier mkv de sortie de la liste
                    self.RemoveTempFiles() # Suppression des fichiers temporaires

                self.WorkInProgress(False) # Remise en état des widgets


    #========================================================================
    def Sub2SrtFinished(self):
        """Fonction terminant le travail de Sub2Srt."""
        ### Récupération des variables servant à lancer d'autres commandes
        ID = Variables["Cmd"][3]
        Lang = MKVSubSrt[ID][0]
        IDX = Path(MKVSubSrt[ID][1])
        SUB = MKVSubSrt[ID][2]
        Folder = MKVSubSrt[ID][3]
        IDXNew = Path(MKVSubSrt[ID][4])

        ### La 1ere commande sert à mettre les bases du systeme
        if Variables["Cmd"][1] == "Demarrage":
            if not TesseractLanguages: # Récupération si besoin de la liste des langues de Tesseract
                Variables["Cmd"] = ["Sub2Srt", "TesseractLang", "tesseract --list-langs", ID]
                self.process.start(Variables["Cmd"][2]) # Lancement de la commande
                self.process.waitForFinished() # Attend la fin de la commande

            if not Lang in TesseractLanguages: # Arret du travail si la langue n'est pas supportée par Tesseract
                QMessageBox(3, self.Trad["ErrorTesseractTitle"], self.Trad["ErrorTesseract"].format(" - ".join(TesseractLanguages)), QMessageBox.Close, self, Qt.WindowSystemMenuHint).exec() # Message d'information
                Variables["WorkStop"] = True
                self.WorkFinished()
                return

            # Suppression des fichiers du dossier de conversion
            for file in Path(Folder).glob("*"):
                file.unlink()

            with IDX.open("r") as fichier_idx: # Lit le fichier idx original ligne par ligne et renvoie le tout (ligne + la ligne modifiée) dans un nouveau fichier
                with IDXNew.open("w") as new_fichier_idx:
                    for ligne in fichier_idx:
                        if "custom colors:" in ligne:
                            new_fichier_idx.write("custom colors: ON, tridx: 0000, colors: 000008, 300030, FFFFFF, 9332c8")
                        else:
                            new_fichier_idx.write(ligne)

            IDX.unlink() # Suppression du fichier idx original
            shutil.move(SUB, Folder) # Deplace le fichier dans le dossier temporaire

            Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la commande suivante à executer
            self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2])) # Envoie d'informations
            self.process.start(Variables["Cmd"][2]) # Lancement de la commande


        ### La 2e commande est la transformation sub en images
        elif Variables["Cmd"][1] == "Subp2Pgm":
            ### Creation d'une liste des fichiers sous titres
            Variables["ImgFiles"] = []
            for File in ["*.pgm", "*.tif"]:
                Variables["ImgFiles"].extend(Path(Folder).glob(File))

            # Récupération du nombre totale de sous titre à traiter
            Variables["ImgFilesNb"] = len(Variables["ImgFiles"])

            text = "tesseract -l {} * *".format(Lang)
            Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la commande suivante à executer
            self.SetInfo(self.Trad["WorkCmd"].format(text), newline=True) # Envoie d'informations
            self.Sub2SrtFinished() # Passe à la commande suivante (pas de commande dans cmd[2])


        ### La 3e commande est la reconnaissance des images en textes
        elif Variables["Cmd"][1] == "Tesseract":
            ### Boucle qui traite les images une à une tant qu'il y en a
            if Variables["ImgFiles"]:
                File = Variables["ImgFiles"].pop() # Récupération du dernier fichier
                self.process.start('tesseract -l {0} "{1}" "{1}"'.format(Lang, File)) # Reconnaissance de l'image suivante

            ### Un fois le travail de la boucle terminé
            else:
                # Dictionnaire listant les sous titres à travailler
                MD5Dico.clear()

                ### Recherche des fichiers txt
                for File in Path(Variables["TempFolderName"], "SUB2SRT").glob("*.txt"):
                    if File.stat().st_size == 0: # Si le fichier est vide 0ko
                        # Récupere le nom du fichier image (enleve l'extension .txt)
                        image = Path(File.parent, File.stem)

                        # Hash le fichier
                        hash = hashlib.md5(image.open("rb").read()).hexdigest()

                        # Si le hash existe deja, c'est une image doublon
                        if hash in MD5Dico.keys():
                            # Ajout du fichier a la liste en lien avec le hash si le fichier n'est pas déjà dans la liste
                            if not image in MD5Dico[hash]:
                                MD5Dico[hash].append(image)

                        # Si le hash n'existe pas, ajout d'une nouvelle paire hash : fichier
                        else:
                            MD5Dico[hash] = [image]

                ### Si le dico contient des fichiers à reconnaitre manuellement
                if MD5Dico:
                    ### Modification de variables
                    Variables["WorkPause"] = True # Variable qui indique l'etat du logiciel
                    Variables["SubNb"] = len(MD5Dico) # Nombre de soustitres à traiter
                    Variables["SubNum"] = 0 # Numero de base

                    self.SetInfo(self.Trad["SubtitlesWait"], "008000", True, True) # Envoie d'informations

                    # Appelle de la fonction qui affiche le texte et l'image
                    self.IMGViewer(0)

                    ### Modifications graphiques
                    self.ui.mkv_resume.show() # Affiche le bouton de reprise
                    self.ui.stackedMiddle.setCurrentIndex(1) # Affichage du widget d'identification de sous titres

                    # La suite des commandes sera lancé lors de la reprise du travail post pause

                ### S'il n'y pas de fichier à reconnaitre manuellement
                else:
                    ### Modifications graphiques
                    self.SetInfo(self.Trad["SubtitlesCreation"], "008000") # Envoie d'informations
                    Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la commande suivante à executer
                    self.process.start(Variables["Cmd"][2]) # Lancement de la commande


        # La 4e commande est la création d'un fichier srt depuis les reconnaissances : SubpTools


    #========================================================================
    def RemoveTempFiles(self):
        """Fonction supprimant les fichiers contenu dans la liste des fichiers temporaires."""
        ### Boucle supprimant les fichiers temporaires s'ils existent
        for file in Variables["TempFiles"]:
            if file.exists():
                file.unlink()


    #========================================================================
    def WorkStop(self):
        """Fonction d'arret du travail en cours, met simplement à jour une variable d'arret."""
        # Curseur travail
        self.setCursor(Qt.WaitCursor)

        # Variable d'arret
        Variables["WorkStop"] = True

        # Dans le cas ou le logiciel est en pause, celle-ci est levée, le travail relancé mais va s'arreter avec la variable WorkStop
        if Variables["WorkPause"]:
            self.WorkPause()


    #========================================================================
    def WorkPause(self):
        """Fonction d'arret du travail en cours, met simplement à jour une variable d'arret."""
        # Deblocage de la pause
        Variables["WorkPause"] = False

        # Cache le bouton de reprise
        self.ui.mkv_resume.hide()

        ### Recup de la commande à exécuter
        if Variables["Cmd"][1] == "Open SRT":
            self.SetInfo(self.Trad["WorkProgress"].format(Variables["Cmd"][0]), "800080", True, True) # Nom de la commande
            Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la commande suivante à executer
            self.SetInfo(self.Trad["WorkCmd"].format(Variables["Cmd"][2])) # Envoie d'informations

        else:
            Variables["Cmd"] = Variables["CmdList"].pop(0) # Récupération de la commande suivante à executer

        # Lancement de la commande
        self.process.start(Variables["Cmd"][2])


    #========================================================================
    def IMGViewer(self, change):
        """Fonction de gestion de conversion manuelle des sous titres."""
        # Mise à le numero à traiter (0 , +1, -1)
        Variables["SubNum"] += change

        # Récupération d'une clée
        md5 = list(MD5Dico.keys())[Variables["SubNum"]]

        # Selectionne la 1ere image de la clée
        img = MD5Dico[md5][0]

        # Adresse du fichier texte
        txt = Path("{}.txt".format(img))

        # Affichage de l'image
        self.ui.image_viewer.setPixmap(QPixmap(str(img)))

        ### Progression du travail
        progression = int(((Variables["SubNum"] + 1) * 100) / Variables["SubNb"])
        self.ui.progressBar.setValue(progression) # Envoie de la valeur à la barre de progression
        self.ui.progressBar.setFormat(self.Trad["IMGProgression"].format(Variables["SubNum"] + 1, Variables["SubNb"])) # Texte change en fonction du nombre d'image

        ### Modifications graphiques
        self.SetInfo(self.Trad["IMGViewerMD5"].format(md5))

        if Variables["SubNum"] + 1 == Variables["SubNb"]:
            self.ui.sub_next.setEnabled(False) # Blocage du bouton suivant
        else:
            self.ui.sub_next.setEnabled(True) # Delocage du bouton suivant

        if Variables["SubNum"] == 0:
            self.ui.sub_previous.setEnabled(False) # Deblocage du bouton precedant
        else:
            self.ui.sub_previous.setEnabled(True) # Deblocage du bouton precedant

        ### Si le fichier texte n'est plus vide (en cas de retour en arriere)
        if txt.stat().st_size > 0:
            with txt.open("r") as SubFile:
                text = SubFile.read()
                self.ui.sub_text.setPlainText(text)


    #========================================================================
    def TextUpdate(self):
        """Fonction d'écriture du texte de la conversion manuelle des sous titres."""
        ### Récupération du texte et de la clée
        SubText, md5 = self.ui.sub_text.toPlainText(), list(MD5Dico.keys())[Variables["SubNum"]]

        ### Si le texte n'est pas vide, on met à jour les fichiers txt
        if SubText:
            ### Traite les images ayant le même md5
            for ImgFile in MD5Dico[md5]:
                with open("{}.txt".format(ImgFile), "w") as SubFile:
                    SubFile.write(SubText)

            self.ui.sub_text.clear() # Mise au propre du texte


    #========================================================================
    def resizeEvent(self, event):
        """Fonction qui resize le tableau à chaque modification de la taille de la fenêtre."""
        ### Calcul pour definir la taille des colones
        largeur = (self.ui.mkv_tracks.size().width() - 75) / 3

        ### Modification de la largeur des colonnes
        self.ui.mkv_tracks.setColumnWidth(4, largeur + 5)
        self.ui.mkv_tracks.setColumnWidth(5, largeur + 5)


    #========================================================================
    def dragEnterEvent(self, event):
        """Fonction appelée à l'arrivée d'un fichier à déposer sur la fenetre."""
        # Impossible d'utiliser mimetypes car il ne reconnait pas tous les fichiers...
        ### Récupération du nom du fichier
        file = Path(event.mimeData().urls()[0].path())

        ### En cas de fichier (pour le fichier d'entrée)
        if file.is_file():
            # Vérifie que l'extension fasse partie de la liste
            if file.suffix in [".mka", ".mks", ".mkv", ".mk3d", ".webm", ".webmv", ".webma"]:
                event.accept()

            elif file.suffix in [".mp4", ".nut", ".ogg"]:
                event.accept()

        ### En cas de dossier (pour le dossier de sortie)
        elif file.is_dir():
            event.accept()


    #========================================================================
    def dropEvent(self, event):
        """Fonction appelée à la dépose du fichier/dossier sur la fenetre."""
        # Impossible d'utiliser mimetypes car il ne reconnait pas tous les fichiers...
        ### Récupération du nom du fichier
        file = Path(event.mimeData().urls()[0].path())

        ### En cas de fichier (pour le fichier d'entrée)
        if file.is_file():
            # Vérifie que l'extension fasse partie de la liste
            if file.suffix in [".mka", ".mks", ".mkv", ".mk3d", ".webm", ".webmv", ".webma"]:
                self.MKVOpen(file) # Lancement de la fonction d'ouverture du fichier mkv avec le nom du fichier

            elif file.suffix in [".mp4", ".nut", ".ogg"]:
                # Necessite une conversion de la vidéo
                self.MKVConvert(file)


        ### En cas de dossier (pour le dossier de sortie)
        elif file.is_dir():
            self.MKVFolder(file) # Lancement de la fonction d'ouverture du fichier mkv avec le nom du fichier


    #========================================================================
    def closeEvent(self, event):
        """Fonction exécutée à la fermeture de la fenêtre quelqu'en soit la méthode."""
        ### Arret du travail en cours
        Variables["WorkStop"] = True

        if not self.process.waitForFinished(3000): # Attend que le travail soit arrété pdt 3s
            self.process.kill()

        ### Si l'option de suppression de config est activé, on supprime le fichier et on ne save pas les valeurs
        if Configs["DelConfig"]:
            if Variables["ConfigFile"].exists():
                Variables["ConfigFile"].unlink()

        ### Dans le cas normal, les valeurs sont saves
        else:
            ### Sauvegarde des préférences
            Config = configparser.ConfigParser()
            Config.optionxform = lambda option: option # Conserve le nom des variables

            Config['DEFAULT'] = { "Ac3Kbits" : str(Configs["Ac3Kbits"]),
                                  "Ac3Boost" : str(Configs["Ac3Boost"]),
                                  "DelConfig" : Configs["DelConfig"],
                                  "DelTemp" : Configs["DelTemp"],
                                  "FFMpeg" : Configs["FFMpeg"],
                                  "MKVDirNameIn" : str(Configs["MKVDirNameIn"]),
                                  "MKVDirNameOut" : str(Configs["MKVDirNameOut"]),
                                  "Language" : Configs["Language"],
                                  "SameFolder" : Configs["SameFolder"],
                                  "Stereo" : Configs["Stereo"],
                                  "SplitterSizes" : str(self.ui.splitter.sizes()),
                                  "SubtitlesOpen" : Configs["SubtitlesOpen"],
                                  "ViewInfo" : Configs["ViewInfo"],
                                  "WinMax" : self.isMaximized(),
                                  "WinWidth" : self.geometry().width(),
                                  "WinHeight" : self.geometry().height() }

            with Variables["ConfigFile"].open('w') as file:
                Config.write(file)

        ### Acceptation de l'arret du logiciel
        event.accept()



#############################################################################
if __name__ == '__main__':
    app = QApplication(sys.argv)
    MKVExtractorQt = MKVExtractorQt()
    app.exec_()