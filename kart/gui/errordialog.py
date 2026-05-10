import re

from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QLabel, QLayout, QMessageBox
from qgis.utils import iface

from kart.utils import tr


class KartErrorDialog:
    """
    Handles Kart errors by displaying a friendly message in the QGIS
    """

    def __init__(self, raw_error):
        """
        Args:
            raw_error (str): The raw error string (stderr) from Kart.
        """
        self.raw_error = raw_error
        self.cleaned_error = KartErrorDialog._clean_error_text(raw_error)
        self.friendly_message = KartErrorDialog._translate_error(self.cleaned_error)

    def exec(self):
        """
        Main entry point used by kartapi.py.
        """
        # self.show_message_bar()
        self.show_message_box()

    def show_message_bar(self):
        """
        Displays a message to the QGIS Message Bar.
        Technical details are logged to the QGIS Message Log panel.
        """
        msg_bar = iface.messageBar().createMessage(tr("Kart Error"), self.friendly_message)

        link_label = QLabel(f'<a href="openLog">{tr("View Log")}</a>')
        link_label.setToolTip(tr("Open the Log Messages panel to see technical details"))
        link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        link_label.linkActivated.connect(lambda _: self._open_log_panel())

        msg_bar.layout().addWidget(link_label)
        iface.messageBar().pushWidget(msg_bar, Qgis.MessageLevel.Critical, 10)

    def show_message_box(self):
        """
        Displays a standard modal QMessageBox.
        The technical error is placed in the 'Detailed Text' expandable area.
        """
        msg_box = QMessageBox(iface.mainWindow())
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(tr("Kart Error"))
        msg_box.setText(self.friendly_message)

        msg_box.setDetailedText(self.cleaned_error)

        if msg_box.layout():
            msg_box.layout().setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        msg_box.exec()

    def _open_log_panel(self):
        """
        Opens the QGIS Message Log dock and switches to the Kart tab.
        """
        from qgis.PyQt.QtWidgets import QDockWidget, QTabWidget

        log_dock = iface.mainWindow().findChild(QDockWidget, "MessageLog")
        if not log_dock:
            return

        log_dock.setVisible(True)
        log_dock.raise_()

        tab_widget = log_dock.findChild(QTabWidget)
        if tab_widget:
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i).lower() == "kart":
                    tab_widget.setCurrentIndex(i)
                    break

    @staticmethod
    def _get_error_map():
        return {
            r"Could not resolve host": tr(
                "Could not locate the server. Check your connection or VPN."
            ),
            r"Invalid value for directory:.*isn't empty": tr(
                "The selected folder is not empty. Choose an empty directory."
            ),
            r"Invalid value for '\[DIRECTORY\]': Directory '.*' is not readable": tr(
                "The directory is not readable. Check your folder permissions."
            ),
        }

    @staticmethod
    def _clean_error_text(text):
        lines = text.splitlines()
        msglines = []
        for line in lines:
            if line.startswith("ERROR 1: Can't load") or ".dylib" in line:
                continue
            if "The specified procedure could not be found" in line:
                continue
            if line.strip():
                msglines.append(line.strip())
        return "\n".join(msglines)

    @staticmethod
    def _translate_error(error_text):
        for pattern, replacement in KartErrorDialog._get_error_map().items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return replacement
        return tr("An unexpected error occurred in Kart.")
