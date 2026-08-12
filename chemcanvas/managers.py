# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os
import csv, glob
from PyQt5.QtCore import QObject, QTimer, Qt, QSettings, QLockFile
from PyQt5.QtWidgets import (QMessageBox, QDialog, QGridLayout, QCheckBox,
        QLabel, QSpinBox, QDialogButtonBox)
from app_data import App, Settings
from fileformat_ccdx import Ccdx

# ------------------------- AUTOSAVE MANAGER --------------------------

class AutosaveManager(QObject):
    """ Saves and restores session for crash recovery. Restores both saved
    and unsaved tabs. Saves backup data in DATA_DIR/autosaves dirctory.
    Saves metadata as autosaves-<pid>.ccdx and documents as <pid>-<tab_id>.ccdx
    To avoid name collision between different window, process id (pid) is used.
    A companion lock file is created using QLockFile so that other app instances
    can check if the app crashed or still running"""
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        if not self.is_supported:
            return
        self.autosave_dir = App.DATA_DIR + "/autosaves"
        os.makedirs(self.autosave_dir, exist_ok=True)
        self.id = str(os.getpid())
        self.lockfile = None
        # timer that triggers autosave_all
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.autosave_all)
        self.timer.start(Settings.autosave_interval * 1000)

    @property
    def is_supported(self):
        return not os.path.exists("/.flatpak-info")


    def autosave_all(self):
        # remove previous autosaved files, before autosaving again
        self.remove_all_backups()
        # metadata is list of [tab_id, unsaved, original_filepath]
        metadata = []
        canvas_dict = {} # <tab_id: canvas> dictionary
        # iterate over tabs in the window's tabWidget
        for tab in self.window.tabs:
            canvas = tab.canvas
            if not canvas.objects:# skip if empty canvas
                continue
            # if file saved, just backup the filename only
            unsaved = str(not canvas.is_saved) # must be string for csv writer to work
            metadata.append([str(tab.id), unsaved, tab.filename])
            canvas_dict[str(tab.id)] = canvas
        # nothing to write
        if not metadata:
            return
        try:
            # write metadata file before writing ccdx files. otherwise if failed to write
            # the metadata, ccdx files will be left forever
            metapath = self.autosave_dir + f"/autosaves-{self.id}.csv"
            # without newline="" csv writer adds blank lines between rows under windows os
            with open(metapath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(metadata)
                # create a lockfile to ensure other instance of this program
                # knows if it is being used, and does not prompt for restore
                lock_path = self.autosave_dir + f"/autosaves-{self.id}.lock"
                self.lockfile = QLockFile(lock_path)
                self.lockfile.setStaleLockTime(0)
                if not self.lockfile.tryLock(0):
                    print("could not lock file", lock_path)
        except Exception as e:
            print(e)

        for tab_id, unsaved, filepath in metadata:
            if unsaved=="False":
                continue
            backup_path = self.autosave_dir + f"/{self.id}-{tab_id}.ccdx"
            try:
                writer = Ccdx()
                doc = canvas_dict[tab_id].getDocument()
                writer.write(doc, backup_path)
            except Exception as e:
                print(e)


    def remove_backup_for_tab(self, tab):
        if not self.is_supported:
            return
        filepath = self.autosave_dir + f"/{self.id}-{tab.id}.ccdx"
        try:
            os.remove(filepath)
        except:
            pass


    def remove_all_backups(self):
        if not self.is_supported:
            return
        self.remove_backups_for_id(self.id)

    def remove_backups_for_id(self, uid):
        try:
            os.remove(self.autosave_dir + f"/autosaves-{uid}.csv")
            # release the lockfile
            if uid==self.id:
                self.lockfile.unlock()
            else:
                lockfile = QLockFile(self.autosave_dir + f"/autosaves-{uid}.lock")
                lockfile.unlock()
        except:
            pass
        # delete backup drawing files
        for f in glob.glob(self.autosave_dir + f"/{uid}-*.ccdx"):
            try:
                os.remove(f)
            except:
                pass

    def check_and_offer_restore(self):
        """ Called at startup: if autosaves exist, offer to restore them.
        returns True if restored """
        if not self.is_supported:
            return
        metadata = [] # list of [uid, tab_id, unsaved, filepath]
        # find autosaves
        files = [f for f in glob.glob(self.autosave_dir + "/autosaves-*.csv")]
        for f in files:
            basename = os.path.basename(f)
            uid = basename[10:-4]
            if uid==self.id:
                continue
            lockfile = QLockFile(self.autosave_dir + f"/autosaves-{uid}.lock")
            if not lockfile.tryLock(0):# program created this still running
                continue
            lockfile.unlock()
            # load autosave info
            try:
                with open(self.autosave_dir + f"/autosaves-{uid}.csv", "r") as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        metadata.append([uid]+row)
            except:
                pass

        if not metadata:
            return False
        msg = "Autosaves from previous session were found.\nWould you like to restore them now?"
        if QMessageBox.question(self.window, "Restore Autosaves?", msg,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
            return False
        for uid, tab_id, unsaved, filepath in metadata:
            try:
                if unsaved=="True":
                    path = self.autosave_dir + f"/{uid}-{tab_id}.ccdx"
                    tab = self.window.newTab()
                    self.window.openFile(path, is_backup=True)
                    tab.setFilename(filepath)
                else:
                    if os.path.exists(filepath):
                        self.window.newTab()
                        self.window.openFile(filepath)
            except Exception as e:
                print(e)
        # to update tab ids, we have to autosave again
        uids = set([item[0] for item in metadata])
        for uid in uids:
            self.remove_backups_for_id(uid)
        self.autosave_all()
        return True

    def show_settings(self):
        if not self.is_supported:
            QMessageBox.information(self.window, "AutoSave not Supported",
            "AutoSave features does not work on Flatpak. \nYou can use other formats like snap, deb package \nor pip-install to use this feature")
            return
        dlg = AutosaveSettingsDialog(self.window)
        if dlg.exec()==QDialog.Accepted:
            enable, interval = dlg.getValues()
            if enable:
                self.timer.start(interval*1000)
            elif self.timer.isActive():
                self.timer.stop()
            Settings.autosave = enable
            Settings.autosave_interval = interval
            settings = QSettings("chemcanvas", "chemcanvas", self)
            settings.setValue("AutoSave", Settings.autosave)
            settings.setValue("AutoSaveInterval", Settings.autosave_interval)


class AutosaveSettingsDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setWindowTitle("AutoSave Settings")
        self.resize(240,100)
        layout = QGridLayout(self)

        self.enableBtn = QCheckBox("Enable AutoSave", self)
        self.enableBtn.setChecked(Settings.autosave)

        self.intervalLabel = QLabel("AutoSave Interval", self)
        self.intervalSpin = QSpinBox(self)
        self.intervalSpin.setSuffix(" s")
        self.intervalSpin.setAlignment(Qt.AlignCenter)
        self.intervalSpin.setRange(10, 1000)
        self.intervalSpin.setSingleStep(20)
        self.intervalSpin.setValue(Settings.autosave_interval)

        self.btnBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)

        layout.addWidget(self.enableBtn, 0,0,1,2)
        layout.addWidget(self.intervalLabel, 1,0,1,1)
        layout.addWidget(self.intervalSpin, 1,1,1,1)
        layout.addWidget(self.btnBox, 2,0,1,2)

        self.btnBox.accepted.connect(self.accept)
        self.btnBox.rejected.connect(self.reject)


    def getValues(self):
        return self.enableBtn.isChecked(), self.intervalSpin.value()


