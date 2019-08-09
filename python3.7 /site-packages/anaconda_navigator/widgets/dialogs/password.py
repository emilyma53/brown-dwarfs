# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Password Anaconda Navigator dialog."""

# yapf: disable

# Third party imports
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout

# Local imports
from anaconda_navigator.api.process import WorkerManager
from anaconda_navigator.utils.py3compat import to_binary_string
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonNormal, ButtonPrimary, LabelBase,
                                        LineEditBase, SpacerHorizontal,
                                        SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase
from anaconda_navigator.widgets.helperwidgets import PasswordEdit


# yapf: enable


class PasswordDialog(DialogBase):
    """Password dialog."""

    def __init__(self, *args, **kwargs):
        """About dialog."""
        super(PasswordDialog, self).__init__(*args, **kwargs)
        self.wm = WorkerManager()

        # Widgets
        self.label_text = LabelBase(
            'VSCode will be installed through your system <br> package '
            'manager.<br><br>'
            'This action requires elevated privileges. Please <br>provide a '
            'password to forward to sudo'
        )
        self.lineedit = PasswordEdit()
        self.label_info = LabelBase()
        self.button_cancel = ButtonNormal('Cancel')
        self.button_ok = ButtonPrimary('Ok')
        self.worker = None
        self._valid = False
        self._timer = QTimer()
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self.check)

        # Widgets setup
        self.button_ok.setMinimumWidth(70)
        self.button_ok.setDefault(True)
        self.setWindowTitle("Privilege Elevation Required")
        self.lineedit.setEchoMode(LineEditBase.Password)

        # Layouts
        layout_content = QVBoxLayout()
        layout_content.addWidget(self.label_text)
        layout_content.addWidget(SpacerVertical())
        layout_content.addWidget(self.lineedit, 0, Qt.AlignBottom)
        layout_content.addWidget(SpacerVertical())
        layout_content.addWidget(self.label_info, 0, Qt.AlignTop)
        layout_content.addWidget(SpacerVertical())

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_ok)

        layout_main = QVBoxLayout()
        layout_main.addLayout(layout_content)
        layout_main.addWidget(SpacerVertical())
        layout_main.addWidget(SpacerVertical())
        layout_main.addLayout(layout_buttons)
        self.setLayout(layout_main)

        # Signals
        self.button_ok.clicked.connect(self.accept2)
        self.button_cancel.clicked.connect(self.reject2)
        self.lineedit.textChanged.connect(self.refresh)

        # Setup
        self.lineedit.setFocus()
        self.refresh()

    def refresh(self):
        """Refresh state of buttons."""
        self.button_ok.setEnabled(bool(self.password))

    def _output(self, worker, output, error):
        """Callback."""
        self._valid = True

    def check(self):
        """Check password."""
        if self.worker._started and self._valid:
            self.lineedit.setEnabled(False)
            self.label_info.setText('')
            self.accept()
        elif self.worker._started:
            self._timer.stop()
            self.lineedit.setEnabled(True)
            self.button_ok.setEnabled(True)
            self.lineedit.setFocus()
            self.lineedit.selectAll()
            self.label_info.setText('<i>Invalid password</i>')

    def reject2(self):
        """Handle reject."""
        if self.worker is not None:
            self.worker.terminate()
        self.reject()

    def accept2(self):
        """Handle accept."""
        stdin = to_binary_string(self.password + '\n')
        if self.worker is not None:
            self.worker.terminate()

        self.worker = self.wm.create_process_worker(['sudo', '-kS', 'ls'])
        self.worker.sig_partial.connect(self._output)
        self.worker.sig_finished.connect(self._output)
        self._valid = False
        self._timer.start()
        self.worker.start()
        self.worker.write(stdin)
        self.lineedit.setEnabled(False)
        self.button_ok.setEnabled(False)

    @property
    def password(self):
        """Return password."""
        return self.lineedit.text()


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication

    app = qapplication()
    widget = PasswordDialog(parent=None)
    widget.setStyleSheet(load_style_sheet())
    widget.show()
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
