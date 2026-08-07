# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed
# Copyright (C) 2026 Arindam Chaudhuri <arindamsoft94@gmail.com>
import os
import csv, glob
from PyQt5.QtCore import QObject, QTimer, Qt, QSettings
from PyQt5.QtWidgets import (QMessageBox, QDialog, QGridLayout, QCheckBox,
        QLabel, QSpinBox, QDialogButtonBox)
from app_data import App, Settings
from fileformat_ccdx import Ccdx

# ------------------------- AUTOSAVE MANAGER --------------------------

class AutosaveManager(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.autosave_dir = os.path.join(App.DATA_DIR, "autosaves")
        os.makedirs(self.autosave_dir, exist_ok=True)

        # timer that triggers autosave_all
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.autosave_all)
        self.timer.start(Settings.autosave_interval * 1000)


    def autosave_all(self):
        try:
            autosave_data = [] # list of (tab_id, unsaved, original_filepath)
            # iterate over tabs in the window's tabWidget
            for tab in self.window.tabs:
                canvas = tab.canvas
                if not canvas.objects:# skip if empty canvas
                    continue
                # if file saved, just backup the filename only
                if canvas.is_saved:
                    autosave_data.append([str(tab.id), str(False), tab.filename])
                    continue
                # build filename
                tid = tab.id
                backup_path = self.autosave_dir + f"/{tid}.ccdx"
                # write using Ccdx writer
                try:
                    writer = Ccdx()
                    doc = canvas.getDocument()
                    writer.write(doc, backup_path)
                    autosave_data.append([str(tab.id), str(True), tab.filename])
                except Exception as e:
                    print(e)
            with open(self.autosave_dir + "/autosaves.csv", "w") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(autosave_data)
        except Exception as e: # we don't want to interrupt the app
            print(e)


    def remove_backup_for_tab(self, tab):
        tid = tab.id
        filepath = self.autosave_dir + f"/{tid}.ccdx"
        try:
            os.remove(filepath)
        except Exception as e:
            print(e)


    def remove_all_backups(self):
        try:
            os.remove(self.autosave_dir + "/autosaves.csv")
        except:
            pass
        pattern = self.autosave_dir + "/*.ccdx"
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except:
                pass

    def check_and_offer_restore(self):
        """Call at startup: if autosaves exist, offer to restore them."""
        # load autosave info
        autosave_data = []
        try:
            with open(self.autosave_dir + "/autosaves.csv", "r") as csvfile:
                reader = csv.reader(csvfile)
                autosave_data = [row for row in reader]
        except:
            pass
        if not autosave_data:
            return
        msg = "Autosaves from previous session were found.\nWould you like to restore them now?"
        if QMessageBox.question(self.window, "Restore Autosaves?", msg,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
            return
        for tab_id, unsaved, filepath in autosave_data:
            try:
                if unsaved=="True":
                    path = self.autosave_dir + f"/{tab_id}.ccdx"
                    tab = self.window.newTab()
                    self.window.openFile(path, is_backup=True)
                    tab.setFilename(filepath)
                else:
                    if os.path.exists(filepath):
                        self.window.newTab()
                        self.window.openFile(filepath)
            except Exception as e:
                print(e)
        # first tab is empty, as it was created at window startup
        self.window.closeTab(0)
        # to update tab ids, we have to autosave again
        self.remove_all_backups()
        self.autosave_all()


    def show_settings(self):
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


