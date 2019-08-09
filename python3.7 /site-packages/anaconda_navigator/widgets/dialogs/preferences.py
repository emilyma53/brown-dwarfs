# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Preferences dialog."""

# yapf: disable

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import QPoint, Qt, Signal
from qtpy.QtGui import QCursor, QPixmap
from qtpy.QtWidgets import (QCheckBox, QGridLayout, QHBoxLayout, QLabel,
                            QLineEdit, QVBoxLayout, QWidget)

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import CONF, WIN7
from anaconda_navigator.static.images import INFO_ICON, WARNING_ICON
from anaconda_navigator.widgets import (ButtonNormal, ButtonPrimary,
                                        SpacerHorizontal, SpacerVertical)
from anaconda_navigator.widgets.dialogs import DialogBase
from anaconda_navigator.widgets.dialogs.offline import DialogOfflineMode


# yapf: enable


class PreferencesDialog(DialogBase):
    """Application preferences dialog."""

    sig_urls_updated = Signal(str, str)
    sig_check_ready = Signal()
    sig_reset_ready = Signal()

    def __init__(self, config=CONF, **kwargs):
        """Application preferences dialog."""
        super(PreferencesDialog, self).__init__(**kwargs)

        self.api = AnacondaAPI()
        self.widgets_changed = set()
        self.widgets = []
        self.widgets_dic = {}
        self.config = config

        # Widgets
        self.button_ok = ButtonPrimary('Apply')
        self.button_cancel = ButtonNormal('Cancel')
        self.button_reset = ButtonNormal('Reset to defaults')
        self.row = 0

        # Widget setup
        self.setWindowTitle("Preferences")

        # Layouts
        self.grid_layout = QGridLayout()

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.button_reset)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.button_cancel)
        buttons_layout.addWidget(SpacerHorizontal())
        buttons_layout.addWidget(self.button_ok)

        main_layout = QVBoxLayout()
        main_layout.addLayout(self.grid_layout)
        main_layout.addWidget(SpacerVertical())
        main_layout.addWidget(SpacerVertical())
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

        # Signals
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)
        self.button_reset.clicked.connect(self.reset_to_defaults)
        self.button_reset.clicked.connect(
            lambda: self.button_ok.setEnabled(True)
        )

        # Setup
        self.grid_layout.setSpacing(0)
        self.setup()
        self.button_ok.setDisabled(True)
        self.widgets[0].setFocus()
        self.button_ok.setDefault(True)
        self.button_ok.setAutoDefault(True)

    # --- Helpers
    # -------------------------------------------------------------------------
    def get_option(self, option):
        """Get configuration option from `main` section."""
        return self.config.get('main', option, None)

    def set_option(self, option, value):
        """Set configuration option in `main` section."""
        self.config.set('main', option, value)

    def get_option_default(self, option):
        """Get configuration option default value in `main` section."""
        return self.config.get_default('main', option)

    def set_option_default(self, option):
        """Set configuration option default value in `main` section."""
        self.set_option(option, self.get_option_default(option))

    def create_widget(
        self,
        widget=None,
        label=None,
        option=None,
        hint=None,
        check=None,
        info=None,
    ):
        """Create preference option widget and add to layout."""
        config_value = self.get_option(option)
        widget._text = label
        widget.label = QLabel(label)
        widget.option = option
        widget.set_value(config_value)
        widget.label_information = QLabel()
        widget.label_information.setMinimumWidth(16)
        widget.label_information.setMaximumWidth(16)

        form_widget = QWidget()
        h_layout = QHBoxLayout()
        h_layout.addSpacing(4)
        h_layout.addWidget(widget.label_information, 0, Qt.AlignRight)
        h_layout.addWidget(widget, 0, Qt.AlignLeft)
        h_layout.addWidget(QLabel(hint or ''), 0, Qt.AlignLeft)
        form_widget.setLayout(h_layout)

        if check:
            widget.check_value = lambda value: check(value)
        else:
            widget.check_value = lambda value: (True, '')

        if info:
            label = widget.label_information
            label = PreferencesDialog.update_icon(label, INFO_ICON)
            label.setToolTip(info)

        self.widgets.append(widget)
        self.widgets_dic[option] = widget
        self.grid_layout.addWidget(
            widget.label, self.row, 0, Qt.AlignRight | Qt.AlignCenter
        )
        self.grid_layout.addWidget(
            form_widget, self.row, 1, Qt.AlignLeft | Qt.AlignCenter
        )
        self.row += 1

    def create_textbox(self, label, option, hint=None, check=None, info=None):
        """Create textbox (QLineEdit) preference option."""
        widget = QLineEdit()
        widget.setAttribute(Qt.WA_MacShowFocusRect, False)
        widget.setMinimumWidth(250)

        widget.get_value = lambda w=widget: w.text()
        widget.set_value = lambda value, w=widget: w.setText(value)
        widget.set_warning = lambda w=widget: w.setSelection(0, 1000)
        widget.textChanged.connect(
            lambda v=None, w=widget: self.options_changed(widget=w)
        )

        self.create_widget(
            widget=widget,
            option=option,
            label=label,
            hint=hint,
            check=check,
            info=info,
        )

    def create_checkbox(self, label, option, check=None, hint=None, info=None):
        """Create checkbox preference option."""
        widget = QCheckBox()
        widget.get_value = lambda w=widget: bool(w.checkState())
        widget.set_value = lambda value, w=widget: bool(
            w.setCheckState(Qt.Checked if value else Qt.Unchecked)
        )

        api_widget = self.widgets_dic['anaconda_api_url']
        widget.set_warning = lambda w=widget: api_widget
        widget.stateChanged.connect(
            lambda v=None, w=widget: self.options_changed(widget=w)
        )
        self.create_widget(
            widget=widget,
            option=option,
            label=label,
            hint=hint,
            check=check,
            info=info,
        )

    def options_changed(self, value=None, widget=None):
        """Callback helper triggered on preference value change."""
        config_value = self.get_option(widget.option)

        if config_value != widget.get_value():
            self.widgets_changed.add(widget)
        else:
            if widget in self.widgets_changed:
                self.widgets_changed.remove(widget)

        self.button_ok.setDisabled(not bool(len(self.widgets_changed)))

    def widget_for_option(self, option):
        """Return the widget for the given option."""
        return self.widgets_dic[option]

    # --- API
    # -------------------------------------------------------------------------
    def set_initial_values(self):
        """
        Set configuration values found in other config files.

        Some options of configuration are found in condarc or in
        anaconda-client configuration.
        """
        self.config.set(
            'main', 'anaconda_api_url', self.api.client_get_api_url()
        )

        # See https://conda.io/docs/install/central.html
        # ssl_verify overloads True/False/<Path to certificate>
        # Navigator splits that into 2 separate options for clarity
        ssl_verify = self.api.client_get_ssl()
        if isinstance(ssl_verify, bool):
            self.config.set('main', 'ssl_verification', ssl_verify)
            self.config.set('main', 'ssl_certificate', None)
        else:
            self.config.set('main', 'ssl_verification', True)
            self.config.set('main', 'ssl_certificate', ssl_verify)

    def setup(self):
        """Setup the preferences dialog."""

        def api_url_checker(value):
            """
            Custom checker to use selected ssl option instead of stored one.

            This allows to set an unsafe api url directly on the preferences
            dialog. Without this, one would have to first disable, click
            accept, then open preferences again and change api url for it to
            work.
            """
            # Ssl widget
            ssl_widget = self.widgets_dic.get('ssl_verification')
            verify = ssl_widget.get_value() if ssl_widget else True

            # Certificate path
            ssl_cert_widget = self.widgets_dic.get('ssl_certificate')
            if ssl_cert_widget:
                verify = ssl_cert_widget.get_value()

            # Offline mode
            offline_widget = self.widgets_dic.get('offline_mode')
            if ssl_widget or ssl_cert_widget:
                offline_mode = offline_widget.get_value()
            else:
                offline_mode = False

            if offline_mode:
                basic_check = (
                    False,
                    'API Domain cannot be modified when '
                    'working in <b>offline mode</b>.<br>',
                )
            else:
                basic_check = self.is_valid_api(value, verify=verify)

            return basic_check

        def ssl_checker(value):
            """Counterpart to api_url_checker."""
            api_url_widget = self.widgets_dic.get('anaconda_api_url')
            api_url = api_url_widget.get_value()
            return self.is_valid_api(api_url, verify=value)

        def ssl_certificate_checker(value):
            """Check if certificate path is valid/exists."""
            ssl_widget = self.widgets_dic.get('ssl_verification')
            verify = ssl_widget.get_value() if ssl_widget else True
            ssl_cert_widget = self.widgets_dic.get('ssl_certificate')
            path = ssl_cert_widget.get_value()
            return self.is_valid_cert_file(path, verify)

        self.set_initial_values()
        self.create_textbox(
            'Anaconda API domain',
            'anaconda_api_url',
            check=api_url_checker,
        )
        self.create_checkbox(
            'Enable SSL verification',
            'ssl_verification',
            check=ssl_checker,
            hint=(
                '<i>Disabling this option is not <br>'
                'recommended for security reasons</i>'
            ),
        )
        self.create_textbox(
            'SSL certificate path (Optional)',
            'ssl_certificate',
            check=ssl_certificate_checker,
        )
        info = '''To help us improve Anaconda Navigator, fix bugs,
and make it even easier for everyone to use Python,
we gather anonymized usage information, just like
most web browsers and mobile apps.'''
        self.create_checkbox(
            'Quality improvement reporting',
            'provide_analytics',
            info=info,
        )
        info_offline = DialogOfflineMode.MESSAGE_PREFERENCES
        extra = '<br><br>' if WIN7 else ''
        self.create_checkbox(
            'Enable offline mode',
            'offline_mode',
            info=info_offline + extra,
        )
        self.create_checkbox('Hide offline mode dialog', 'hide_offline_dialog')
        self.create_checkbox('Hide quit dialog', 'hide_quit_dialog')
        self.create_checkbox(
            'Hide update dialog on startup', 'hide_update_dialog'
        )
        self.create_checkbox(
            'Hide running applications dialog', 'hide_running_apps_dialog'
        )
        self.create_checkbox(
            'Enable high DPI scaling', 'enable_high_dpi_scaling'
        )
        self.create_checkbox(
            'Show application startup error messages', 'show_application_launch_errors'
        )

        ssl_ver_widget = self.widgets_dic.get('ssl_verification')
        ssl_ver_widget.stateChanged.connect(self.enable_disable_cert)
        ssl_cert_widget = self.widgets_dic.get('ssl_certificate')
        ssl_cert_widget.setPlaceholderText(
            'Certificate to verify SSL connections'
        )

        # Refresh enabled/disabled status of certificate textbox
        self.enable_disable_cert()

    def enable_disable_cert(self, value=None):
        """Refresh enabled/disabled status of certificate textbox."""
        ssl_cert_widget = self.widgets_dic.get('ssl_certificate')
        if value:
            value = bool(value)
        else:
            ssl_ver_widget = self.widgets_dic.get('ssl_verification')
            value = bool(ssl_ver_widget.checkState())
        ssl_cert_widget.setEnabled(value)

    @staticmethod
    def update_icon(label, icon):
        """Update icon for information or warning."""
        pixmap = QPixmap(icon)
        label.setScaledContents(True)
        label.setPixmap(
            pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        return label

    @staticmethod
    def warn(widget, text=None):
        """Display warning for widget in preferences."""
        label = widget.label_information
        if text:
            label = PreferencesDialog.update_icon(label, WARNING_ICON)
            label.setToolTip(str(text))
            w = widget.label_information.width() / 2
            h = widget.label_information.height() / 2
            position = widget.label_information.mapToGlobal(QPoint(w, h))
            QCursor.setPos(position)
        else:
            label.setPixmap(QPixmap())
            label.setToolTip('')

    # --- Checkers
    # -------------------------------------------------------------------------
    def is_valid_url(self, url):
        """Check if a given URL returns a 200 code."""
        output = self.api.download_is_valid_url(url, non_blocking=False)
        error = ''
        if not output:
            error = 'Invalid api url.'
        return output, error

    def is_valid_cert_file(self, path, verify):
        """"Check if ssl certificate file in given path exists."""
        output = True
        error = ''

        # Only validate if it is not empty and if ssl_verification is checked
        if path.strip() and verify:
            output = os.path.isfile(path)
            if not output:
                error = 'File not found.'
        return output, error

    def is_valid_api(self, url, verify=True):
        """Check if a given URL is a valid anaconda api endpoint."""
        output = self.api.download_is_valid_api_url(
            url,
            non_blocking=False,
            verify=verify,
        )
        error = ''
        if not output:
            url_api_1 = ''
            url_api_2 = ''

            if '/api' not in url and self.is_valid_url(url)[0]:
                url_api_1 = url.replace('https://', 'https://api.')
                url_api_1 = url_api_1.replace('http://', 'http://api.')

                if url.endswith('/'):
                    url_api_2 = url + 'api'
                else:
                    url_api_2 = url + '/api'

                error = (
                    'Invalid Anaconda API url. <br>'
                    '<br>Try using:<br><b>{0}</b> or <br>'
                    '<b>{1}</b>'.format(url_api_1, url_api_2)
                )
            else:
                error = (
                    'Invalid Anaconda API url.<br><br>'
                    'Check the url is valid and corresponds to the api '
                    'endpoint.'
                )
        return output, error

    def run_checks(self):
        """
        Run all check functions on configuration options.

        This method checks and warns but it does not change/set values.
        """
        checks = []
        for widget in self.widgets_changed:
            value = widget.get_value()
            check, error = widget.check_value(value)
            checks.append(check)

            if check:
                self.warn(widget)
            else:
                self.button_ok.setDisabled(True)
                widget.set_warning()
                self.warn(widget, error)
                break

        # Emit checks ready
        self.sig_check_ready.emit()
        return checks

    def reset_to_defaults(self):
        """Reset the preferences to the default values."""
        for widget in self.widgets:
            option = widget.option
            default = self.get_option_default(option)
            widget.set_value(default)

            # Flag all values as updated
            self.options_changed(widget=widget, value=default)
        self.sig_reset_ready.emit()

    def accept(self):
        """Override Qt method."""
        sig_updated = False
        anaconda_api_url = None
        checks = self.run_checks()

        # Update values
        if checks and all(checks):
            for widget in self.widgets_changed:
                value = widget.get_value()
                self.set_option(widget.option, value)

                # Settings not stored on Navigator config, but taken from
                # anaconda-client config
                if widget.option == 'anaconda_api_url':
                    anaconda_api_url = value  # Store it to be emitted
                    self.api.client_set_api_url(value)
                    sig_updated = True

                # ssl_verify/verify_ssl handles True/False/<Path to cert>
                # On navi it is split in 2 options for clarity
                if widget.option in ['ssl_certificate', 'ssl_verification']:
                    ssl_veri = self.widgets_dic.get('ssl_verification')
                    ssl_cert = self.widgets_dic.get('ssl_certificate')
                    verify = ssl_veri.get_value()
                    path = ssl_cert.get_value()

                    if path.strip() and verify:
                        value = path
                    else:
                        value = verify

                    self.api.client_set_ssl(value)

            if sig_updated and anaconda_api_url:

                def _api_info(worker, output, error):
                    conda_url = output.get('conda_url')
                    try:
                        self.sig_urls_updated.emit(anaconda_api_url, conda_url)
                        super(PreferencesDialog, self).accept()
                    except RuntimeError:
                        # Some tests on appveyor/circleci fail
                        pass

                worker = self.api.api_urls()
                worker.sig_chain_finished.connect(_api_info)

            super(PreferencesDialog, self).accept()


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Main local testing."""
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication()
    widget = PreferencesDialog(parent=None)
    widget.show()
    app.exec_()


if __name__ == '__main__':  # pragma: no cover
    local_test()
