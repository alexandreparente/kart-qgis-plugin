import os

from qgis.gui import QgsMessageBar
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QSizePolicy
from qgis.utils import iface

from kart.utils import (
    AUTOCOMMIT,
    CURRENT_COLOR_ADDED,
    CURRENT_COLOR_MODIFIED,
    CURRENT_COLOR_REMOVED,
    CURRENT_COLOR_UNCHANGED,
    DIFFSTYLES,
    HELPERMODE,
    KARTPATH,
    PALETTES,
    setSetting,
    setting,
    tr,
)

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), "settingsdialog.ui"))


class SettingsDialog(BASE, WIDGET):
    def __init__(self):
        super(QDialog, self).__init__(iface.mainWindow())
        self.setupUi(self)

        self.retranslateUi()

        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.layout().addWidget(self.bar)

        self.btnBrowsePath.clicked.connect(lambda: self.browse(self.txtKartPath))

        self.buttonBox.accepted.connect(self.okClicked)
        self.buttonBox.rejected.connect(self.reject)

        # Appearance setup
        self.comboDiffStyles.clear()
        self.comboDiffStyles.addItems(list(PALETTES.keys()) + [tr("Custom")])

        # Connect color buttons to switch to Custom mode
        self.btnColorAdded.colorChanged.connect(self.setToCustom)
        self.btnColorRemoved.colorChanged.connect(self.setToCustom)
        self.btnColorModified.colorChanged.connect(self.setToCustom)
        self.btnColorUnchanged.colorChanged.connect(self.setToCustom)

        self.comboDiffStyles.currentTextChanged.connect(self.onStyleChanged)

        self.setValues()

        # Shrink window to fit content
        self.adjustSize()

    def setValues(self):
        # Load General settings
        self.txtKartPath.setText(setting(KARTPATH) or "")
        self.chkHelperMode.setChecked(setting(HELPERMODE))
        self.chkAutoCommit.setChecked(setting(AUTOCOMMIT))

        # Block signals to prevent "auto-switching" to Custom during load
        self.comboDiffStyles.blockSignals(True)
        self.btnColorAdded.blockSignals(True)
        self.btnColorRemoved.blockSignals(True)
        self.btnColorModified.blockSignals(True)
        self.btnColorUnchanged.blockSignals(True)

        # Load the saved style name
        saved_style = setting(DIFFSTYLES) or "Standard"
        self.comboDiffStyles.setCurrentText(saved_style)

        # Use Palette defaults if not Custom, else use saved colors
        if saved_style in PALETTES:
            p = PALETTES[saved_style]
            self.btnColorAdded.setColor(QColor(p["ADDED"]))
            self.btnColorRemoved.setColor(QColor(p["REMOVED"]))
            self.btnColorModified.setColor(QColor(p["MODIFIED"]))
            self.btnColorUnchanged.setColor(QColor(p["UNCHANGED"]))
        else:
            # Custom mode: Load individual colors saved in QSettings
            self.btnColorAdded.setColor(QColor(setting(CURRENT_COLOR_ADDED) or "#54c35f"))
            self.btnColorRemoved.setColor(QColor(setting(CURRENT_COLOR_REMOVED) or "#e8718d"))
            self.btnColorModified.setColor(QColor(setting(CURRENT_COLOR_MODIFIED) or "#ffbe64"))
            self.btnColorUnchanged.setColor(QColor(setting(CURRENT_COLOR_UNCHANGED) or "#ffffff"))

        # Unblock signals
        self.comboDiffStyles.blockSignals(False)
        self.btnColorAdded.blockSignals(False)
        self.btnColorRemoved.blockSignals(False)
        self.btnColorModified.blockSignals(False)
        self.btnColorUnchanged.blockSignals(False)

    def onStyleChanged(self, style_name):
        # Update buttons colors only if a preset (not Custom) is selected
        if style_name in PALETTES:
            p = PALETTES[style_name]
            # Block signals to avoid triggering setToCustom when applying a preset
            self.btnColorAdded.blockSignals(True)
            self.btnColorRemoved.blockSignals(True)
            self.btnColorModified.blockSignals(True)
            self.btnColorUnchanged.blockSignals(True)

            self.btnColorAdded.setColor(QColor(p["ADDED"]))
            self.btnColorRemoved.setColor(QColor(p["REMOVED"]))
            self.btnColorModified.setColor(QColor(p["MODIFIED"]))
            self.btnColorUnchanged.setColor(QColor(p["UNCHANGED"]))

            self.btnColorAdded.blockSignals(False)
            self.btnColorRemoved.blockSignals(False)
            self.btnColorModified.blockSignals(False)
            self.btnColorUnchanged.blockSignals(False)

        self.adjustSize()

    def setToCustom(self):
        # Change combo to Custom if a color is manually modified
        if self.comboDiffStyles.currentText() != tr("Custom"):
            self.comboDiffStyles.setCurrentText(tr("Custom"))

    def browse(self, textbox):
        folder = QFileDialog.getExistingDirectory(iface.mainWindow(), tr("Select Folder"), "")
        if folder:
            textbox.setText(folder)

    def okClicked(self):
        selected_style = self.comboDiffStyles.currentText()

        setSetting(KARTPATH, self.txtKartPath.text())
        setSetting(HELPERMODE, self.chkHelperMode.isChecked())
        setSetting(AUTOCOMMIT, self.chkAutoCommit.isChecked())
        setSetting(DIFFSTYLES, selected_style)

        # Save colors as hex strings
        setSetting(CURRENT_COLOR_ADDED, self.btnColorAdded.color().name())
        setSetting(CURRENT_COLOR_REMOVED, self.btnColorRemoved.color().name())
        setSetting(CURRENT_COLOR_MODIFIED, self.btnColorModified.color().name())
        setSetting(CURRENT_COLOR_UNCHANGED, self.btnColorUnchanged.color().name())

        self.accept()

    def retranslateUi(self, *args):
        """Update translations for UI elements from the .ui file"""
        super().retranslateUi(self)

        # Window Title
        self.setWindowTitle(tr("Kart Settings"))

        # Kart Executable Section
        self.grpKartExecution.setTitle(tr("Kart execution"))
        self.lblPath.setText(tr("Path to Kart executable"))
        self.txtKartPath.setPlaceholderText(
            tr("[Leave empty to use default Kart installation path]")
        )
        self.chkHelperMode.setText(tr("Use helper mode"))

        # Auto Commit Section
        self.grpAutoCommit.setTitle(tr("Auto commit"))
        self.chkAutoCommit.setText(tr("Commit automatically after closing editing"))

        # Diff Styles Section
        self.grpDiffStyles.setTitle(tr("Diff styles"))
        self.lblStyleProfile.setText(tr("Styles to use for geometry diffs"))
