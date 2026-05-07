# -*- coding: utf-8 -*-

from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAction,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from qgis.utils import iface

from kart.gui import icons
from kart.kartapi import executeskart
from kart.utils import confirm, tr, waitcursor


class KartCommitPanel(QWidget):
    commitSuccess = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.repo = None
        self._last_repo_path = None

        self.main_dock = parent
        while self.main_dock and not hasattr(self.main_dock, "showChanges"):
            self.main_dock = self.main_dock.parent()

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 5)
        layout.setSpacing(4)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: rgba(0,0,0,60);")
        layout.addWidget(line)

        header_layout = QHBoxLayout()
        self.lblTitle = QLabel(f"<b>{tr('Pending Changes')}</b>")
        header_layout.addWidget(self.lblTitle)
        header_layout.addStretch()

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(self.toolbar.iconSize() / 1.5)

        self.actionRefresh = QAction(icons.refreshIcon, tr("Refresh Changes"), self)
        self.actionRefresh.triggered.connect(self.refresh_list)

        self.actionRollback = QAction(icons.discardIcon, tr("Discard Checked Changes"), self)
        self.actionRollback.triggered.connect(self.do_rollback)

        self.actionDiff = QAction(icons.diffIcon, tr("View Differences"), self)
        self.actionDiff.triggered.connect(self.view_diff)

        self.toolbar.addActions([self.actionRefresh, self.actionRollback, self.actionDiff])
        header_layout.addWidget(self.toolbar)
        layout.addLayout(header_layout)

        self.fileList = QListWidget()
        self.fileList.setAlternatingRowColors(True)
        self.fileList.setStyleSheet("QListWidget { border: 1px solid #ccd0d4; }")
        self.fileList.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.fileList)

        input_layout = QVBoxLayout()
        self.commitMessage = QLineEdit()
        self.commitMessage.setPlaceholderText(tr("Enter commit message here..."))

        self.btnCommit = QPushButton(tr("Commit"))
        self.btnCommit.setMinimumHeight(30)
        self.btnCommit.setStyleSheet("font-weight: bold;")
        self.btnCommit.setEnabled(False)
        self.btnCommit.clicked.connect(self.do_commit)

        input_layout.addWidget(self.commitMessage)
        input_layout.addWidget(self.btnCommit)
        layout.addLayout(input_layout)

    def setRepository(self, repo):
        new_path = repo.path if repo else None
        if repo == self.repo and self._last_repo_path == new_path:
            return

        self.repo = repo
        self._last_repo_path = new_path

        if self.isVisible():
            self.refresh_list()
        else:
            self.fileList.clear()

    def refresh_list(self):
        if not self.isVisible():
            return

        self.fileList.clear()
        self.btnCommit.setEnabled(False)

        if not self.repo:
            self._add_info_item(tr("Select a repository or dataset in the tree to see changes"))
            return

        try:
            changes = self.repo.changes()
            if not changes:
                self._add_info_item(tr("Working tree clean"))
            else:
                for dataset_name in changes.keys():
                    item = QListWidgetItem(dataset_name)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Checked)
                    self.fileList.addItem(item)
                self.btnCommit.setEnabled(True)
        except Exception:
            self._add_info_item(tr("Error fetching changes"), color=Qt.GlobalColor.red)

    def _add_info_item(self, text, color=Qt.GlobalColor.gray):
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setForeground(color)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fileList.addItem(item)

    def get_checked_datasets(self):
        checked = []
        for i in range(self.fileList.count()):
            item = self.fileList.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())
        return checked

    @executeskart
    def do_rollback(self, checked=False):
        datasets = self.get_checked_datasets()
        if not datasets or not self.repo:
            return

        if confirm(tr(f"Discard changes for: {', '.join(datasets)}?")):
            for name in datasets:
                self.repo.restore("HEAD", name)

            iface.messageBar().pushMessage(
                "Kart", tr("Changes discarded"), level=Qgis.MessageLevel.Info
            )
            self.refresh_list()
            if self.main_dock:
                self.main_dock.fillTree()

    def view_diff(self, checked=False):
        if not self.repo:
            return

        selected_item = self.fileList.currentItem()
        if selected_item:
            dataset_name = selected_item.text()
            diff = self.repo.diff(dataset=dataset_name)
            from kart.gui.diffviewer import DiffViewerDialog

            dialog = DiffViewerDialog(
                iface.mainWindow(), diff, self.repo, showRecoverNewButton=False
            )
            dialog.exec()
        elif self.main_dock:
            self.main_dock.showChanges()

    @waitcursor
    @executeskart
    def do_commit(self, checked=False):
        if not self.repo:
            return

        msg = self.commitMessage.text().strip()
        if not msg:
            iface.messageBar().pushMessage(
                tr("Kart"), tr("Enter a message"), level=Qgis.MessageLevel.Warning
            )
            return

        datasets = self.get_checked_datasets()
        if not datasets:
            return

        success = True
        try:
            for dataset in datasets:
                if not self.repo.commit(msg, dataset=dataset):
                    success = False

            if success:
                iface.messageBar().pushMessage(
                    tr("Kart"), tr("Committed successfully"), level=Qgis.MessageLevel.Info
                )
                self.commitMessage.clear()
                self.refresh_list()
                if self.main_dock:
                    self.main_dock.fillTree()
        except Exception as e:
            iface.messageBar().pushMessage(tr("Kart"), str(e), level=Qgis.MessageLevel.Critical)
