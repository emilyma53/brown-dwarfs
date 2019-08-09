# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Anaconda Cloud login dialog."""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Standard library imports
import ast

# Third party imports
from qtpy.QtCore import QRegExp, Qt, QUrl, Signal
from qtpy.QtGui import QDesktopServices, QRegExpValidator
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
                            QVBoxLayout)

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import CONF, DEFAULT_BRAND
from anaconda_navigator.static.fonts import load_fonts
from anaconda_navigator.utils.analytics import GATracker
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonLabel, ButtonLink, ButtonNormal,
                                        ButtonPrimary, SpacerHorizontal,
                                        SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase


# yapf: enable


class AuthenticationDialog(DialogBase):
    """Login dialog."""

    # See https://github.com/Anaconda-Platform/anaconda-server settings
    USER_RE = QRegExp(r'^[A-Za-z0-9_\.][A-Za-z0-9_\.\-]+$')
    FORGOT_USERNAME_URL = 'account/forgot_username'
    FORGOT_PASSWORD_URL = 'account/forgot_password'

    sig_authentication_succeeded = Signal()
    sig_authentication_failed = Signal()
    sig_url_clicked = Signal(object)

    def __init__(self, api, parent=None, brand=DEFAULT_BRAND):
        """Login dialog."""
        super(AuthenticationDialog, self).__init__(parent)

        self._parent = parent
        self._brand = brand
        self.config = CONF
        self.api = api
        self.token = None
        self.error = None
        self.tracker = GATracker()
        self.forgot_username_url = None
        self.forgot_password_url = None

        # Widgets
        self.label_username = QLabel('Username:')
        self.label_password = QLabel('Password:')
        self.text_username = QLineEdit()
        self.text_password = QLineEdit()
        self.label_signin_text = QLabel(
            '<hr><br><b>Already a member? '
            'Sign in!</b><br>'
        )
        # For styling purposes the label next to a ButtonLink is also a button
        # so they align adequately
        self.button_register_text = ButtonLabel(
            'You can register by '
            'visiting the '
        )
        self.button_register = ButtonLink(brand)
        self.button_register_after_text = ButtonLabel(' website.')
        self.label_information = QLabel(
            '''
            <strong>{brand}</strong> is where packages, notebooks,
            and <br> environments are shared. It provides powerful <br>
            collaboration and package management for open <br>
            source and private projects.<br>
            '''.format(brand=brand)
        )
        self.label_message = QLabel('')
        self.button_forgot_username = ButtonLink('I forgot my username')
        self.button_forgot_password = ButtonLink('I forgot my password')
        self.button_login = ButtonPrimary('Login')
        self.button_cancel = ButtonNormal('Cancel')

        # Widgets setup
        self.button_login.setDefault(True)
        username_validator = QRegExpValidator(self.USER_RE)
        self.text_username.setValidator(username_validator)

        self.setMinimumWidth(260)
        self.setWindowTitle('Sign in')

        # This allows to completely style the dialog with css using the frame
        self.text_password.setEchoMode(QLineEdit.Password)
        self.label_message.setVisible(False)

        # Layout
        grid_layout = QVBoxLayout()
        grid_layout.addWidget(self.label_username)
        # grid_layout.addWidget(SpacerVertical())
        grid_layout.addWidget(self.text_username)
        grid_layout.addWidget(SpacerVertical())
        grid_layout.addWidget(self.label_password)
        # grid_layout.addWidget(SpacerVertical())
        grid_layout.addWidget(self.text_password)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.label_information)

        register_layout = QHBoxLayout()
        register_layout.addWidget(self.button_register_text)
        register_layout.addWidget(self.button_register)
        register_layout.addWidget(self.button_register_after_text)
        register_layout.addStretch()
        main_layout.addLayout(register_layout)
        main_layout.addWidget(self.label_signin_text)
        main_layout.addLayout(grid_layout)
        main_layout.addWidget(SpacerVertical())
        main_layout.addWidget(self.label_message)
        main_layout.addWidget(self.button_forgot_username, 0, Qt.AlignRight)
        main_layout.addWidget(self.button_forgot_password, 0, Qt.AlignRight)

        layout_buttons = QHBoxLayout()
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_cancel)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_login)

        main_layout.addWidget(SpacerVertical())
        main_layout.addWidget(SpacerVertical())
        main_layout.addLayout(layout_buttons)

        self.setLayout(main_layout)

        # Signals
        self.text_username.textEdited.connect(self.check_text)
        self.text_password.textEdited.connect(self.check_text)
        self.button_login.clicked.connect(self.login)
        self.button_cancel.clicked.connect(self.reject)

        # Setup
        self.check_text()
        self.update_style_sheet()
        self.text_username.setFocus()
        self.setup()

    def setup(self):
        """Setup login dialog."""
        self.update_links()

    def update_links(self):
        """Update links."""
        for button in [
            self.button_forgot_username,
            self.button_forgot_password,
            self.button_register,
        ]:
            try:
                button.disconnect()
            except TypeError:  # pragma: no cover
                pass

        # TODO, get this from anaconda client directly?
        # from binstar_client.utils import get_config, set_config
        # config = get_config()
        anaconda_api_url = self.config.get(
            'main', 'anaconda_api_url', self.api.client_get_api_url()
        )
        # print([anaconda_api_url], [self.api.client_get_api_url()])
        if anaconda_api_url:
            # Remove api if using a subdomain
            base_url = anaconda_api_url.lower().replace('//api.', '//')
            self.base_url = base_url

            # Remove api if not using a subdomain
            parts = base_url.lower().split('/')
            if parts[-1] == 'api':
                base_url = '/'.join(parts[:-1])

            self.forgot_username_url = (
                base_url + '/' + self.FORGOT_USERNAME_URL
            )
            self.forgot_password_url = (
                base_url + '/' + self.FORGOT_PASSWORD_URL
            )

            self.button_register.clicked.connect(
                lambda: self.open_url(base_url)
            )
            self.button_forgot_username.clicked.connect(
                lambda: self.open_url(self.forgot_username_url)
            )
            self.button_forgot_password.clicked.connect(
                lambda: self.open_url(self.forgot_password_url)
            )

    @property
    def username(self):
        """Return the logged username."""
        return self.text_username.text().lower()

    def update_style_sheet(self, style_sheet=None):
        """Update custom css style sheet."""
        if style_sheet is None:
            style_sheet = load_style_sheet()
        self.setStyleSheet(style_sheet)

    def check_text(self):
        """Check that `username` and `password` are valid.

        If not empty and disable/enable buttons accordingly.
        """
        username = self.text_username.text()
        password = self.text_password.text()

        if len(username) == 0 or len(password) == 0:
            self.button_login.setDisabled(True)
        else:
            self.button_login.setDisabled(False)

    def login(self):
        """Try to log the user in the specified anaconda api endpoint."""
        self.button_login.setEnabled(False)
        self.text_username.setText(self.text_username.text().lower())
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.label_message.setText('')
        worker = self.api.login(
            self.text_username.text().lower(), self.text_password.text()
        )
        worker.sig_finished.connect(self._finished)

    def _finished(self, worker, output, error):
        """Callback for the login procedure after worker has finished."""
        token = output
        if token:
            self.token = token
            self.sig_authentication_succeeded.emit()
            self.accept()
        elif error:
            username = self.text_username.text().lower()
            bold_username = '<b>{0}</b>'.format(username)

            # The error might come in (error_message, http_error) format
            try:
                error_message = ast.literal_eval(str(error))[0]
            except Exception:  # pragma: no cover
                error_message = str(error)

            error_message = error_message.lower().capitalize()
            error_message = error_message.split(', ')[0]
            error_text = '<i>{0}</i>'.format(error_message)
            error_text = error_text.replace(username, bold_username)
            self.label_message.setText(error_text)
            self.label_message.setVisible(True)

            if error_message:
                domain = self.api.client_domain()
                label = '{0}/{1}: {2}'.format(
                    domain, username, error_message.lower()
                )
                self.tracker.track_event(
                    'authenticate',
                    'login failed',
                    label=label,
                )
                self.text_password.setFocus()
                self.text_password.selectAll()
            self.sig_authentication_failed.emit()

        self.button_login.setDisabled(False)
        self.check_text()
        QApplication.restoreOverrideCursor()

    def open_url(self, url):
        """Open given url in the default browser and log the action."""
        self.tracker.track_event('content', 'click', url)
        self.sig_url_clicked.emit(url)
        QDesktopServices.openUrl(QUrl(url))


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication(test_time=3)
    load_fonts(app)
    widget = AuthenticationDialog(AnacondaAPI())
    widget.update_style_sheet()
    widget.show()
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
