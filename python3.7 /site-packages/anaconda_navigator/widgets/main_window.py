# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Main Application Window."""

# yapf: disable

from __future__ import absolute_import, division

# Standard library imports
# import json
import os
import pickle
import shutil
import sys
import tempfile

# Third party imports
from qtpy.QtCore import QPoint, QSize, Qt, QTimer, QUrl, Signal
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                            QVBoxLayout, QWidget)
import psutil
import yaml

# Local imports
from anaconda_navigator import __version__
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import (CHANNELS_PATH, CONF, DEFAULT_BRAND,
                                       GLOBAL_VSCODE_APP, LINUX, MAC, WIN)
from anaconda_navigator.static import images
from anaconda_navigator.utils import constants as C
from anaconda_navigator.utils.analytics import GATracker
from anaconda_navigator.utils.launch import get_package_logs, launch
from anaconda_navigator.utils.logs import logger
from anaconda_navigator.utils.misc import set_windows_appusermodelid
from anaconda_navigator.utils.py3compat import is_text_string
from anaconda_navigator.utils.qthelpers import create_action
from anaconda_navigator.utils.styles import BLUR_SIZE, load_style_sheet
from anaconda_navigator.widgets import (ButtonBase, ButtonLabel, ButtonLink,
                                        ButtonPrimary, FrameBase, LabelBase,
                                        QSvgWidget, SpacerHorizontal)
from anaconda_navigator.widgets.dialogs import (MessageBoxError,
                                                MessageBoxInformation,
                                                MessageBoxQuestion, projects)
from anaconda_navigator.widgets.dialogs.about import AboutDialog
from anaconda_navigator.widgets.dialogs.channels import DialogChannels
from anaconda_navigator.widgets.dialogs.environment import (CloneDialog,
                                                            ConflictDialog,
                                                            CreateDialog,
                                                            ImportDialog,
                                                            RemoveDialog)
from anaconda_navigator.widgets.dialogs.license import LicenseManagerDialog
from anaconda_navigator.widgets.dialogs.logger import LogViewerDialog
from anaconda_navigator.widgets.dialogs.login import AuthenticationDialog
from anaconda_navigator.widgets.dialogs.offline import DialogOfflineMode
from anaconda_navigator.widgets.dialogs.packages import PackagesDialog
from anaconda_navigator.widgets.dialogs.password import PasswordDialog
from anaconda_navigator.widgets.dialogs.preferences import PreferencesDialog
from anaconda_navigator.widgets.dialogs.quit import (ClosePackageManagerDialog,
                                                     QuitApplicationDialog,
                                                     QuitBusyDialog,
                                                     QuitRunningAppsDialog)
from anaconda_navigator.widgets.dialogs.update import DialogUpdateApplication
from anaconda_navigator.widgets.tabs.community import CommunityTab
from anaconda_navigator.widgets.tabs.environments import EnvironmentsTab
from anaconda_navigator.widgets.tabs.home import HomeTab
# from anaconda_navigator.widgets.tabs.projects import ProjectsTab
from anaconda_navigator.widgets.tabs.tabwidget import TabWidget


# yapf: enable


# --- Widgets used with CSS styling
# -----------------------------------------------------------------------------
class ButtonLinkLogin(ButtonLink):
    """Button used in CSS styling."""


class ButtonLabelLogin(ButtonLabel):
    """Button used in CSS styling."""


class ButtonHeaderUpdate(ButtonBase):
    """Button used in CSS styling."""


class ButtonLogin(ButtonPrimary):
    """Button used in CSS styling."""


class FrameHeader(FrameBase):
    """
    Frame used in CSS styling.

    Top application header.
    """


class FrameBody(FrameBase):
    """Frame used in CSS styling."""


class LabelHeaderLogo(LabelBase):
    """Label used in CSS styling."""


class LabelOfflineMode(LabelBase):
    """Label used in CSS styling."""


class LabelHeaderUpdate(LabelBase):
    """Label used in CSS styling."""


class LabelBeta(LabelBase):
    """Label used in CSS styling."""


# --- Main widget
# -----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    """Main window widget."""

    sig_ready = Signal()
    sig_conda_ready = Signal()
    sig_setup_ready = Signal()
    sig_logged_in = Signal()
    sig_logged_out = Signal()

    DOCS_URL = 'https://docs.anaconda.com/anaconda/navigator'
    FEATURED_CHANNELS = ()  # ('anaconda-fusion', )

    # Web content
    VIDEOS_URL = "https://www.anaconda.com/api/videos"
    EVENTS_URL = "https://www.anaconda.com/api/events"
    WEBINARS_URL = "https://www.anaconda.com/api/webinars"

    # Web content development site
    TEST_URL = "http://api-dev-continuum-content.pantheonsite.io/"
    TEST_VIDEOS_URL = TEST_URL + "api/videos"
    TEST_EVENTS_URL = TEST_URL + "api/events"
    TEST_WEBINARS_URL = TEST_URL + "api/webinars"

    # VIDEOS_URL = TEST_VIDEOS_URL
    # EVENTS_URL = TEST_EVENTS_URL
    # WEBINARS_URL = TEST_WEBINARS_URL

    def __init__(
        self,
        splash=None,
        config=CONF,
        tab_home=True,
        tab_environments=True,
        tab_project=True,
        tab_learning=True,
        tab_community=True
    ):
        """Main window widget."""
        super(MainWindow, self).__init__()

        # Variables (Global)
        self.api = AnacondaAPI()
        self.initial_setup = True
        self.setup_ready = False
        self.tracker = None
        self.config = config
        self.fullscreen_flag = False
        self.maximized_flag = True
        self.style_sheet = None
        self.first_run = self.config.get('main', 'first_run')
        self.application_update_version = None
        self.restart_required = None
        self._toobar_setup_ready = False  # See issue 1142

        # Variables (Testing)
        self._dialog_about = None
        self._dialog_logs = None
        self._dialog_preferences = None
        self._dialog_update = None
        self._dialog_message_box = None
        self._dialog_quit = None
        self._dialog_quit_busy = None
        self._dialog_quit_running_apps = None
        self._dialog_welcome = None
        self._dialog_offline = None

        self._dialog_channels = None
        self._dialog_licenses = None
        self._dialog_environment_action = None
        self._dialog_project_action = None

        self.busy_community = None
        self.busy_learning = None

        # Variables (Conda handling)
        self.licenses = None
        self.environments = None
        self.busy_conda = False
        self.current_prefix = os.environ.get(
            'CONDA_PREFIX', self.api.ROOT_PREFIX
        )
        self.running_processes = []

        # Variables (Client handling)
        self._anaconda_url = None  # To be used by open_login_url
        self._brand = DEFAULT_BRAND
        self._login_text = 'Sign in to '
        self.logged = False
        self.username = ''
        self.token = self.api._client_api.load_token()

        # Variables (Projects handling)
        self.projects = None
        self.busy_projects = False
        self.current_project = None
        self.projects_path = None

        projects_path = self.config.get('main', 'projects_path')
        if (projects_path and is_text_string(projects_path) and
                os.path.isdir(projects_path)):
            self.projects_path = projects_path
        else:
            self.config.set('main', 'projects_path', None)

        # Fix windows displaying the right icon
        # See https://github.com/ContinuumIO/navigator/issues/1340
        if WIN:
            res = set_windows_appusermodelid()
            logger.info("appusermodelid: {0}".format(res))

        # Widgets (Refresh timers, milliseconds)
        self._timer_environments = QTimer()  # Check for new environments
        self._timer_environments.setInterval(16000)
        self._timer_projects = QTimer()  # Check for new projects
        self._timer_projects.setInterval(14000)
        self._timer_licenses = QTimer()  # Check for available licenses
        self._timer_licenses.setInterval(15000)
        self._timer_client = QTimer()  # Check for logged status
        self._timer_client.setInterval(5000)
        self._timer_offline = QTimer()  # Check for connectivity
        self._timer_offline.setInterval(4713)

        # Widgets
        self.tab_home = None
        self.tab_environments = None
        self.tab_projects = None
        self.tab_learning = None
        self.tab_community = None
        self.splash = splash
        self.frame_header = FrameHeader(self)
        self.frame_body = FrameBody(self)
        self.label_logo = QSvgWidget(images.ANACONDA_NAVIGATOR_LOGO)
        self.label_offline_mode = LabelOfflineMode('')
        self.button_logged_text = ButtonLabelLogin('')
        self.button_logged_username = ButtonLinkLogin('')
        self.button_update_available = ButtonHeaderUpdate('Upgrade Now')
        self.button_login = ButtonLogin()
        self.widget = QWidget()
        self.stack = TabWidget(self)

        # Widgets setup
        self.setWindowTitle("Anaconda Navigator")
        self.button_update_available.setVisible(False)
        self.button_logged_text.setFocusPolicy(Qt.NoFocus)
        self.button_login.setDefault(True)
        self.update_login_button_text()
        self.label_logo.setFixedSize(QSize(395, 50))

        # Load custom API URL on batch installs and set it
        self.set_initial_batch_config()

        # Load custom config links if any
        youtube_url = self.config.get('main', 'youtube_url')
        twitter_url = self.config.get('main', 'twitter_url')
        github_url = self.config.get('main', 'github_url')

        self.stack.add_link(
            'Documentation',
            url=self.DOCS_URL,
        )
        self.stack.add_link(
            'Developer Blog',
            url="https://www.anaconda.com/blog/developer-blog",
        )
        # self.stack.add_link(
        #    'Feedback',
        #    url="https://continuum.typeform.com/to/ABe8FA",  # FIXME:
        # )
        if twitter_url:
            self.stack.add_social('Twitter', url=twitter_url)
        if youtube_url:
            self.stack.add_social('Youtube', url=youtube_url)  # FIXME:
        if github_url:
            self.stack.add_social('Github', url=github_url)  # FIXME:

        if tab_home:
            self.tab_home = HomeTab(parent=self)
            self.stack.addTab(self.tab_home, text='Home')

            # Signals
            self.tab_home.sig_item_selected.connect(self.select_environment)
            self.tab_home.sig_channels_requested.connect(self.show_channels)
            self.tab_home.sig_url_clicked.connect(self.open_url)
            self.tab_home.sig_launch_action_requested.connect(
                self.launch_application
            )
            self.tab_home.sig_conda_action_requested.connect(
                self.conda_application_action
            )
        if tab_environments:
            self.tab_environments = EnvironmentsTab(parent=self)
            self.stack.addTab(self.tab_environments, text='Environments')

            # Signals
            self.tab_environments.sig_channels_requested.connect(
                self.show_channels
            )
            self.tab_environments.sig_update_index_requested.connect(
                self.update_index
            )
            self.tab_environments.sig_item_selected.connect(
                self.select_environment
            )
            self.tab_environments.sig_create_requested.connect(
                self.show_create_environment
            )
            self.tab_environments.sig_clone_requested.connect(
                self.show_clone_environment
            )
            self.tab_environments.sig_import_requested.connect(
                self.show_import_environment
            )
            self.tab_environments.sig_remove_requested.connect(
                self.show_remove_environment
            )
            self.tab_environments.sig_packages_action_requested.connect(
                self.show_conda_packages_action
            )
            self.tab_environments.sig_ready.connect(
                lambda: self.set_busy_status(conda=False)
            )
            self.tab_environments.sig_cancel_requested.connect(
                self.show_cancel_process
            )
        # if tab_project:
        #     self.tab_projects = ProjectsTab(parent=self)
        #     self.stack.addTab(self.tab_projects, text='Projects')
        #     self.tab_projects.sig_create_requested.connect(
        #         self.show_create_project
        #     )
        #     self.tab_projects.sig_import_requested.connect(
        #         self.show_import_project
        #     )
        #     self.tab_projects.sig_remove_requested.connect(
        #         self.show_remove_project
        #     )
        #     self.tab_projects.sig_item_selected.connect(self.select_project)
        #     self.tab_projects.sig_login_requested.connect(self.handle_login)
        #     self.tab_projects.sig_ready.connect(
        #         lambda: self.set_busy_status(projects=False)
        #     )

        if tab_learning:
            self.tab_learning = CommunityTab(
                parent=self,
                tags=['webinar', 'documentation', 'video', 'training'],
                content_urls=[self.VIDEOS_URL, self.WEBINARS_URL],
                tab_name=C.TAB_LEARNING,
                config=self.config,
            )
            self.stack.addTab(self.tab_learning, text='Learning')
            self.tab_learning.sig_ready.connect(
                lambda: self.set_busy_status(learning=False)
            )
        if tab_community:
            self.tab_community = CommunityTab(
                parent=self,
                tags=['event', 'forum', 'social'],
                content_urls=[self.EVENTS_URL],
                tab_name=C.TAB_COMMUNITY,
                config=self.config,
            )
            self.tab_community.sig_ready.connect(
                lambda: self.set_busy_status(community=False)
            )
            self.stack.addTab(self.tab_community, text='Community')

        self.all_tab_widgets = [
            self.tab_home,
            self.tab_environments,
            self.tab_projects,
            self.tab_community,
            self.tab_learning,
        ]

        # Layout
        layout_header = QHBoxLayout()
        layout_header.addWidget(self.label_logo)
        layout_header.addStretch()
        layout_header.addWidget(self.label_offline_mode)
        layout_header.addWidget(SpacerHorizontal())
        layout_header.addWidget(self.button_update_available)
        layout_header.addWidget(SpacerHorizontal())
        layout_header.addWidget(self.button_logged_text)
        layout_header.addWidget(self.button_logged_username)
        layout_header.addWidget(SpacerHorizontal())
        layout_header.addWidget(self.button_login)
        self.frame_header.setLayout(layout_header)

        layout_body = QHBoxLayout()
        layout_body.addWidget(self.stack)
        layout_body.setContentsMargins(0, 0, 0, 0)
        layout_body.setSpacing(0)
        self.frame_body.setLayout(layout_body)

        layout_main = QVBoxLayout()
        layout_main.addWidget(self.frame_header)
        layout_main.addWidget(self.frame_body)
        layout_main.setContentsMargins(0, 0, 0, 0)
        layout_main.setSpacing(0)
        self.widget.setLayout(layout_main)
        self.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.widget)

        # Signals
        self._timer_client.timeout.connect(self.check_for_new_login)
        self._timer_environments.timeout.connect(
            self.check_for_new_environments
        )
        self._timer_licenses.timeout.connect(self.check_for_new_licenses)
        self._timer_projects.timeout.connect(self.check_for_new_projects)
        self._timer_offline.timeout.connect(self.check_internet_connectivity)
        self.button_login.clicked.connect(self.handle_login)
        self.button_logged_username.clicked.connect(self.open_login_page)
        self.button_update_available.clicked.connect(self.update_application)
        self.stack.sig_current_changed.connect(self._track_tab)
        self.stack.sig_current_changed.connect(self.fix_tab_order)
        self.stack.sig_url_clicked.connect(self.open_url)
        self.sig_setup_ready.connect(self.check_package_cache)
        self.sig_setup_ready.connect(self.check_internet_connectivity)

        # Setup
        self.config.set('main', 'last_status_is_offline', None)
        self.api.set_data_directory(CHANNELS_PATH)
        self.update_style_sheet()

        # Add featured_channels
        worker = self.api.conda_config(prefix=self.current_prefix)
        worker.sig_chain_finished.connect(self.add_featured_channels)

        worker_data = self.api.conda_data(prefix=self.current_prefix)
        worker_data.sig_chain_finished.connect(self.setup)

    # Helpers
    # -------------------------------------------------------------------------
    def _track_tab(self, index=None):
        """Track the active tab by index, or set `Home` when index is None."""
        logger.debug('index: {}'.format(index))
        if index is None:
            index = self.stack.currentIndex()

        text = self.stack.currentText()
        if text:
            text = text.lower()

        if self.tracker and text:
            page = '/{0}'.format(text)
            self.tracker.track_page(page)

    # --- Public API
    # -------------------------------------------------------------------------
    def set_initial_batch_config(self):
        """
        Set configuration settings that force conda and client config update.
        """

        def is_valid_api(url, verify):
            """Check if a given URL is a valid anaconda api endpoint."""
            output = self.api.download_is_valid_api_url(
                url,
                non_blocking=False,
                verify=verify,
            )
            return output

        verify = True

        # SSL certificate
        default_ssl_certificate = self.config.get(
            'main', 'default_ssl_certificate'
        )
        if default_ssl_certificate is not None:
            # Check if it is a valid path, and check if it is boolean
            if isinstance(default_ssl_certificate, bool
                          ) or os.path.isfile(default_ssl_certificate):
                self.api.client_set_ssl(default_ssl_certificate)
                # self.config.set('main', 'default_ssl_certificate', None)
                verify = default_ssl_certificate

        # API URL
        default_anaconda_api_url = self.config.get(
            'main', 'default_anaconda_api_url'
        )
        if default_anaconda_api_url is not None:
            if is_valid_api(default_anaconda_api_url, verify=verify):
                self.api.client_set_api_url(default_anaconda_api_url)
                # self.config.set('main', 'default_anaconda_api_url', None)

    def setup(self, worker, output, error):
        """
        Perform initial setup and configuration.

        This is the first method called after the main window has been created.
        """
        logger.debug('output: {}, error: {}'.format(output, error))
        self.check_internet_connectivity()

        if self.initial_setup:
            logger.info('Initial setup')

            # Get user info if it has previously logged in via anaconda client
            self.set_splash('Loading user...')
            user = self.api.client_user()
            self.update_login_status(user)

            self.set_splash('Preparing interface...')
            self.setup_toolbars()

            self.set_splash('Loading bundled metadata...')
            self.api.load_bundled_metadata()

            conda_data = output
            self.post_setup(conda_data=conda_data)

            # Check for initial values of envs, projects and licenses
            self.licenses = self.api.load_licenses()
            info = conda_data.get('processed_info', {})
            self.environments = info.get('__environments')
            self.projects = self.api.get_projects(paths=[self.projects_path])
            self.initial_setup = False
        else:
            logger.info('Normal setup')

            # Reset home and environment tab
            if self.tab_home:
                self.tab_home.setup(output)
            if self.tab_environments:
                self.tab_environments.setup(output)

            # Check for updates
            packages = output['packages']
            info = output.get('processed_info', {})
            is_root_writable = info.get('root_writable', False)
            self.check_for_updates(
                packages=packages, is_root_writable=is_root_writable
            )

            self.fix_tab_order()

    def post_setup(self, conda_data):
        """Setup tab widgets."""
        logger.debug('conda_data: {}'.format(conda_data))

        self.setup_ready = True
        self.config.set('main', 'first_run', False)

        if self.tab_home:
            self.set_busy_status(conda=True)
            self.set_splash('Loading applications...')
            self.tab_home.setup(conda_data)
        if self.tab_environments:
            self.set_busy_status(conda=True)
            self.set_splash('Loading environments...')
            self.tab_environments.setup(conda_data)
        if self.tab_projects:
            self.set_busy_status(projects=True)
            self.set_splash('Loading projects...')
            projects = self.api.get_projects([self.projects_path])
            self.tab_projects.setup(projects)
            self.select_project()
        if self.tab_community:
            self.set_busy_status(community=True)
            self.set_splash('Loading content...')
            self.tab_community.setup()
        if self.tab_learning:
            self.set_busy_status(learning=True)
            self.set_splash('Loading content...')
            self.tab_learning.setup()
        self.update_style_sheet()

        geo = self.config.get('main', 'geo', None)
        if geo:
            # In case Navigator is installed in an env that has a different
            # python version than root (root == py3, env == py2 or viceversa)
            try:
                self.restoreGeometry(pickle.loads(geo))
                self.show()
            except Exception:
                self.showMaximized()
        else:
            self.showMaximized()
        self.post_visible_setup(conda_data)

    def setup_toolbars(self):
        """Setup toolbar menus and actions."""
        logger.debug('')

        # See issue #1142
        if self._toobar_setup_ready:
            return

        menubar = self.menuBar()

        file_menu = menubar.addMenu('&File')
        file_menu.addAction(
            create_action(
                self,
                "&Preferences",
                triggered=self.show_preferences,
                shortcut="Ctrl+P"
            )
        )
        file_menu.addAction(
            create_action(
                self, "&Restart", triggered=self.restart, shortcut="Ctrl+R"
            )
        )
        file_menu.addAction(
            create_action(
                self, "&Quit", triggered=self.close, shortcut="Ctrl+Q"
            )
        )

        helpmenu = menubar.addMenu('&Help')
        helpmenu.addAction(
            create_action(
                self,
                "&Online Documentation",
                triggered=lambda: self.open_url(self.DOCS_URL)
            )
        )
        # Disabled due to _license package removal
        # helpmenu.addAction(
        #     create_action(
        #         self, "License &manager", triggered=self.show_license_manager
        #     )
        # )
        helpmenu.addAction(
            create_action(
                self,
                "&Logs viewer",
                triggered=self.show_log_viewer,
                shortcut="F6"
            )
        )
        helpmenu.addSeparator()
        helpmenu.addAction(
            create_action(self, "&About", triggered=self.show_about)
        )
        self._toobar_setup_ready = True

    def post_visible_setup(self, conda_data):
        """Setup after show method has been applied."""
        logger.debug('conda_data: {}'.format(conda_data))

        if self.splash:
            self.splash.hide()

        self.config.set('main', 'first_run', False)

        # Start the tracker only after post_visible_setup
        self.tracker = GATracker()
        self._track_tab(0)  # Start tracking home
        self.show_welcome_screen()

        packages = conda_data.get('packages')
        info = conda_data.get('processed_info', {})
        is_root_writable = info.get('root_writable', False)
        self.check_for_updates(
            packages=packages, is_root_writable=is_root_writable
        )

        # Fix tab order
        self.fix_tab_order(0)
        buttons = self.stack.tabbar.buttons
        if buttons:
            buttons[0].setFocus()

        worker = self.api.conda_config_and_sources(prefix=self.current_prefix)
        worker.sig_chain_finished.connect(self.check_outdated_channels)

        # print('Setup ready')
        self.check_internet_connectivity()
        self.sig_setup_ready.emit()

    def set_widgets_enabled(self, value):
        """Set the widgets enabled/disabled status for subwidgets and tabs."""
        logger.debug('value: {}'.format(value))
        if self.tab_home:
            self.tab_home.set_widgets_enabled(value)
        if self.tab_environments:
            self.tab_environments.set_widgets_enabled(value)

    def update_style_sheet(self):
        """Update custom CSS style sheet."""
        logger.debug('')
        self.style_sheet = load_style_sheet()
        for tab in self.all_tab_widgets:
            if tab:
                tab.update_style_sheet(style_sheet=self.style_sheet)
        self.setStyleSheet(self.style_sheet)

    # --- Update Navigator
    # -------------------------------------------------------------------------
    def check_for_updates(
        self, packages=None, version=None, is_root_writable=False
    ):
        """Check for application updates."""
        logger.debug('packages: {}, version: {}'.format(packages, version))

        from distutils.version import LooseVersion as lv
        # Check if there is an update for navigator!
        navi_version = version or __version__

        # Temporal mock test
        # mock_versions = [version, '1.9.0']
        # packages['anaconda-navigator'] = {'versions': mock_versions}
        self.button_update_available.setEnabled(False)
        self.button_update_available.setVisible(False)

        if packages:
            package_data = packages.get('anaconda-navigator')
            if package_data:
                versions = package_data.get('versions')
                if versions and (
                    lv(versions[-1]) > lv(navi_version)
                    or 'dev' in navi_version
                    and versions[-1] == navi_version.replace('dev', '')
                ):
                    self.application_update_version = versions[-1]
                    self.button_update_available.setEnabled(True)
                    self.button_update_available.setVisible(True)
                    if not self.config.get('main', 'hide_update_dialog'):
                        self.update_application(
                            center_dialog=True,
                            is_root_writable=is_root_writable,
                        )

    def _update_application(self, worker, output, error):
        """Update application callback."""
        logger.debug('output: {}, error: {}'.format(output, error))

        if error:
            self.button_update_available.setEnabled(True)
            text = 'Anaconda Navigator Update error:'
            dlg = MessageBoxError(
                text=text, error=error, title='Application Update Error'
            )
            self.tracker.track_page(
                '/update/error',
                pagetitle='Update Application Error '
                'Message Box'
            )
            dlg.exec_()
        else:
            self.button_update_available.setEnabled(False)
            text = (
                'Anaconda Navigator Updated succefully.\n\n'
                'Please restart the application'
            )
            dlg = MessageBoxInformation(text=text, title='Application Update')
            self.tracker.track_page(
                '/update/successful',
                pagetitle='Application Update Succesful '
                'Message Box'
            )
            dlg.exec_()
            self.update_busy_status(False)
        self.update_status()
        self._track_tab()

    def update_application(self, center_dialog=False, is_root_writable=False):
        """Update application to latest available version."""
        logger.debug('center_dialog: {}'.format(center_dialog))

        version = self.application_update_version
        qa_testing = version == '1000.0.0'

        if version:
            dlg = DialogUpdateApplication(
                version=version,
                startup=center_dialog,
                qa_testing=qa_testing,
                is_root_writable=is_root_writable,
            )
            # Only display one dialog at a time
            if self._dialog_update is None:

                self._dialog_update = dlg
                if not center_dialog:
                    height = self.button_update_available.height()
                    width = self.button_update_available.width()
                    point = self.button_update_available.mapToGlobal(
                        QPoint(-dlg.WIDTH + width, height)
                    )
                    dlg.move(point)

                if self.tracker:
                    self.tracker.track_page(
                        '/update', pagetitle='Update Application Dialog'
                    )

                if dlg.exec_():
                    self.tracker.track_event('application', 'updated', version)
                    # Returns a pid or None if failed
                    pid = self.open_updater(
                        version, is_root_writable=is_root_writable
                    )
                    if pid is not None:
                        self.close()

            self._dialog_update = None
            self._track_tab()

    def open_updater(self, version, is_root_writable=False):
        """Open the Anaconda Navigator Updater"""
        logger.debug('version: {}'.format(version))

        self.tracker.track_event('application', 'updater-requested', version)
        leave_path_alone = True
        root_prefix = self.api.ROOT_PREFIX
        prefix = os.environ.get('CONDA_PREFIX', root_prefix)
        command = [
            'navigator-updater',
            '--latest-version',
            version,
            '--prefix',
            prefix,
        ]

        as_admin = WIN and not is_root_writable

        return launch(
            prefix,
            command,
            leave_path_alone,
            package_name='anaconda-navigator-updater',
            root_prefix=root_prefix,
            non_conda=True,
            as_admin=as_admin,
        )

    # --- Url handling
    # -------------------------------------------------------------------------
    # TODO: Route ALL url handling to this method? or Make a global func?
    def open_url(self, url, category=None, action=None):
        """Open url and track event."""
        logger.debug(
            'url: {}, category: {}, action: {}'.format(url, category, action)
        )

        # print(url, category, action)
        qurl = QUrl(url)
        QDesktopServices.openUrl(qurl)
        self.tracker.track_event('help', 'documentation', url)

    def open_login_page(self):
        """Open logged in user anaconda page."""
        logger.debug('')
        url = "{0}/{1}".format(self._anaconda_url, self.username)
        qurl = QUrl(url)
        QDesktopServices.openUrl(qurl)
        self.tracker.track_event('content', 'clicked', url)

    # --- Client (Login)
    # -------------------------------------------------------------------------
    @property
    def conda_url(self):
        """Return the conda url based on the api info from config url."""
        logger.debug('')
        api_info = self.api.download_get_api_info()
        url = api_info.get('conda_url', 'https://conda.anaconda.org')
        url = url[:-1] if url[-1] == '/' else url
        return url

    @property
    def api_url(self):
        """Return the api url from anaconda client config."""
        logger.debug('')
        return self.api.client_get_api_url()

    def update_login_status(self, user_data=None):
        """Update login button and information."""
        logger.debug('user_data: {}'.format(user_data))

        def _update_tool_tip(worker, output, error):
            logger.debug('output: {}, error: {}'.format(output, error))
            anaconda_main_url = output.get('main_url', 'https://anaconda.org')
            self._anaconda_url = anaconda_main_url
            self._brand = output.get('brand', DEFAULT_BRAND)
            if worker.username:
                url = "{0}/{1}".format(anaconda_main_url, worker.username)
                try:
                    self.button_logged_username.setToolTip(url)
                except RuntimeError:
                    # On appveyor: wrapped C/C++ object of type ButtonLinkLogin
                    # has been deleted
                    pass
            self.update_login_button_text()

            try:
                self.button_login.setEnabled(True)
            except RuntimeError:
                # On CI: wrapped C/C++ object of type ButtonLinkLogin
                # has been deleted
                pass

        if user_data:
            self.username = user_data.get('login', '')
            self.logged = True

        if self.logged:
            self.button_login.setEnabled(False)
            username = self.username
            worker = self.api.api_urls()
            worker.username = username
            worker.sig_chain_finished.connect(_update_tool_tip)
            self.button_logged_username.setVisible(True)
            self.button_logged_username.setText(username)
            self.button_logged_text.setVisible(True)
            self.button_logged_text.setText('Signed in as ')
        else:
            username = None
            self.button_logged_text.setText('')
            self.button_logged_username.setText('')
            self.button_logged_text.setVisible(False)
            self.button_logged_username.setVisible(False)

        # See: https://github.com/ContinuumIO/navigator/issues/1325
        self.api.client_reload()

        self.button_login.setEnabled(False)
        worker = self.api.api_urls()
        worker.username = username
        worker.sig_chain_finished.connect(_update_tool_tip)
        QApplication.restoreOverrideCursor()

    def update_login_button_text(self):
        """Update login button text based on `brand` from api."""
        if self.logged:
            text = 'Sign out'
        else:
            text = self._login_text + self._brand

        if self.tab_projects:
            self.tab_projects.update_brand(self._brand)

        try:
            self.button_login.setText(text)
        except RuntimeError:
            # On appveyor: wrapped C/C++ object of type ButtonLinkLogin
            # has been deleted
            pass

    def handle_login(self, logout=False):
        """Open up login dialog or log out depending on logged status."""
        logger.debug('logout: {}'.format(logout))

        if logout:  # Force a logout
            self.logged = True

        if self.logged:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.api.logout()
            self.logged = False
            self.sig_logged_out.emit()
            self.tracker.track_event(
                'authenticate', 'logout', label=self.username
            )
        else:
            dlg = AuthenticationDialog(
                self.api, parent=self, brand=self._brand
            )

            if self.tracker:
                self.tracker.track_page('/login', pagetitle='Login dialog')

            if dlg.exec_():
                self.username = dlg.username
                self.logged = True
                self.sig_logged_in.emit()

                if self.tracker:
                    self.tracker.track_event(
                        'authenticate', 'login', label=self.username
                    )
            self._track_tab()

        self.update_login_status()
        logger.debug(str((self.logged, self.username)))

    # --- Dialogs
    # -------------------------------------------------------------------------
    def show_preferences(self):
        """Display the preferences dialog and apply the needed actions."""
        logger.debug('')
        if self.tracker:
            self.tracker.track_page(
                '/preferences', pagetitle='Preferences dialog'
            )
        self._dialog_preferences = PreferencesDialog(
            parent=self, config=self.config
        )

        # If the api url was changed by the user, a logout is triggered
        self._dialog_preferences.sig_urls_updated.connect(
            lambda au, cu: self.handle_login(logout=True)
        )
        self._dialog_preferences.exec_()
        self._dialog_preferences = None
        self._track_tab()

    def show_about(self):
        """Display the `About` dialog with information on the project."""
        logger.debug('')
        self._dialog_about = AboutDialog(self)
        if self.tracker:
            self.tracker.track_page('/about', pagetitle='About dialog')
        self._dialog_about.sig_url_clicked.connect(self.open_url)
        self._dialog_about.exec_()
        self._dialog_about = None
        self._track_tab()

    def show_welcome_screen(self):
        """Show initial splash screen."""
        logger.debug('')
        if (getattr(self, 'showme', True) and
                self.config.get('main', 'show_startup', True)):
            from anaconda_navigator.widgets.dialogs.splash import FirstSplash

            self.showme = False
            if self.splash:
                self.splash.hide()
                self._dialog_welcome = FirstSplash()
                if self.tracker:
                    self.tracker.track_page(
                        '/welcome', pagetitle='Welcome dialog'
                    )
                self._dialog_welcome.raise_()
                self._dialog_welcome.exec_()
                self._dialog_welcome = None
        self._track_tab()

    def show_license_manager(self):
        """Show license manager dialog."""
        logger.debug('')
        self._dialog_licenses = LicenseManagerDialog(parent=self)
        if self.tracker:
            self.tracker.track_page('/licenses', pagetitle='Licenses dialog')
        self._dialog_licenses.sig_url_clicked.connect(self.open_url)

        if self._dialog_licenses.exec_():
            self.tab_home.update_items()

        self._dialog_licenses = None
        self._track_tab()

    def show_log_viewer(self):
        """Display the logs viewer to the user."""
        logger.debug('')
        self._dialog_logs = LogViewerDialog()
        if self.tracker:
            self.tracker.track_page('/logs', pagetitle='Log Viewer Dialog')
        self._dialog_logs.exec_()
        self._dialog_logs = None
        self._track_tab()

    def show_error_message(self, error_name, error_text):
        """Display application error message."""
        logger.debug(
            'error_name: {}, error_text: {}'.format(error_name, error_text)
        )

        self.set_busy_status(conda=True)
        if 'UnsatisfiableSpecifications' in error_name:
            report = False
        else:
            report = True

        if report:
            title = 'Conda process error'
            text = "The following errors occurred:"
            error_msg = error_text
        else:
            title = "Unsatisfiable package specifications:"
            text = (
                "The following specifications were found to be "
                "in conflict:"
            )
            package_errors = [
                e.strip() for e in error_text.split('\n') if '-' in e
            ]
            error_msg = '\n'.join(package_errors)
            error_msg += (
                '\n\n\nA package you tried to install '
                'conflicts with another.'
            )

        # Check if offline mode and provide a custom message
        if self.api.is_offline():
            report = False
            if 'PackagesNotFoundError' in error_name:
                title = 'Package not available in offline mode'
                error_msg = (
                    "Some of the functionality of Anaconda Navigator "
                    "will be limited in <b>offline mode</b>. <br><br>"
                    "Installation and upgrade of packages will "
                    "be subject to the packages currently available "
                    "on your package cache."
                )

        if self.tracker:
            self.tracker.track_page(
                '/messagebox/error', pagetitle='Conda error message box'
            )
        dlg = MessageBoxError(
            text=text,
            error=error_msg,
            title=title,
            report=False,  # Disable reporting on github
            learn_more='http://conda.pydata.org/docs/'
            'troubleshooting.html#unsatisfiable'
        )
        self._dialog_message_box = dlg
        dlg.setMinimumWidth(400)
        dlg.exec_()
        self.set_busy_status(conda=False)
        self.update_status()
        self._track_tab()

    def show_offline_mode_dialog(self):
        """Show offline mode dialog"""
        if self._dialog_offline is not None:
            # Dialog currently open
            return

        logger.debug('')
        show_dialog = not self.config.get('main', 'hide_offline_dialog')
        first_time_offline = self.config.get('main', 'first_time_offline')

        if show_dialog or first_time_offline:
            self._dialog_offline = DialogOfflineMode(parent=self)
            if self.tracker:
                self.tracker.track_page('/offline', pagetitle='Offline dialog')

            if self._dialog_offline.exec_():
                pass

            self.config.set('main', 'first_time_offline', False)
            self._dialog_offline = None
            self._track_tab()

    # --- Conda (Dialogs)
    # -------------------------------------------------------------------------
    def add_default_channels(self, conda_data):
        """Add defaults to user condarc if it does not exist."""
        logger.debug('conda_data: {}'.format(conda_data))
        config_sources = conda_data.get('config_sources', {})
        user_rc = self.api._conda_api.user_rc_path
        user_config = config_sources.get(user_rc, {})
        user_channels = user_config.get('channels', [])
        if len(user_channels) == 0 or not os.path.isfile(user_rc):
            worker = self.api.conda_config_add('channels', 'defaults')
            worker.communicate()
        self.api.client_get_ssl()

    def check_outdated_channels(self, worker, conda_data, error):
        """Check if the user has binstar channels as part of the config."""
        logger.debug('conda_data: {}, error: {}'.format(conda_data, error))
        self.set_busy_status(conda=True)
        config = conda_data.get('config', {})
        current_channels = config.get('channels', [])
        self.add_default_channels(conda_data)
        outdated_channels = []
        if 'anaconda.org' in self.api_url:
            for channel in current_channels:
                if 'binstar.org' in channel:
                    outdated_channels.append(channel)

        if outdated_channels:
            chs = ['- <b>{0}</b><br>'.format(ch) for ch in outdated_channels]
            chs = ''.join(chs)
            text = (
                "We detected some outdated channels making use of "
                "<b>binstar.org</b><br><br>{chs}<br><br>"
                "Do you want to update them?"
            ).format(chs=chs)

            self.tracker.track_page(
                '/channels/outdated',
                pagetitle='Show outdated channels check dialog',
            )
            self._dialog_message_box = MessageBoxQuestion(
                text=text, title='Outdated channels detected'
            )
            self._dialog_message_box.setMinimumWidth(300)

            if self._dialog_message_box.exec_():
                for channel in outdated_channels:
                    new_channel = channel.replace(
                        'binstar.org', 'anaconda.org'
                    )
                    worker = self.api.conda_config_add('channels', new_channel)
                    worker.communicate()
                    worker = self.api.conda_config_remove('channels', channel)
                    worker.communicate()
            self._dialog_message_box = None
            self._track_tab()
        self.set_busy_status(conda=False)

    def show_channels(self, button=None, sender=None):
        """Show the conda channels configuration dialog."""
        logger.debug('button: {}, sender: {}'.format(button, sender))

        def _accept_channels_dialog(button):
            logger.debug('button: {}, '.format(button))
            button.setEnabled(True)
            button.setFocus()
            button.toggle()
            self._dialog_channels = None  # for testing

        if sender == C.TAB_HOME:
            pass
        elif sender == C.TAB_ENVIRONMENT:
            pass

        self.tracker.track_page('/channels', pagetitle='Show channels dialog')
        dlg = DialogChannels(parent=self)
        self._dialog_channels = dlg  # For testing
        dlg.update_style_sheet(style_sheet=self.style_sheet)
        worker = self.api.conda_config_sources(prefix=self.current_prefix)
        worker_api_info = self.api.api_urls()
        worker.sig_chain_finished.connect(dlg.setup)
        worker_api_info.sig_finished.connect(dlg.update_api)
        dlg.sig_channels_updated.connect(self.update_channels)

        if button:
            button.setDisabled(True)
            dlg.rejected.connect(lambda: button.setEnabled(True))
            dlg.rejected.connect(button.toggle)
            dlg.rejected.connect(button.setFocus)
            dlg.accepted.connect(
                lambda v=None: _accept_channels_dialog(button)
            )

            geo_tl = button.geometry().topLeft()
            tl = button.parentWidget().mapToGlobal(geo_tl)
            x = tl.x() - BLUR_SIZE
            y = tl.y() + button.height() - BLUR_SIZE

            # Ensure channels dialog stays visible
            # See https://github.com/ContinuumIO/navigator/issues/1254
            x_right_dialog = x + dlg.WIDTH
            x_right_screen = QApplication.desktop().availableGeometry().width()
            if x_right_dialog > x_right_screen:
                x = x - (x_right_dialog - x_right_screen)
            elif x < 0:
                x = 0

            dlg.move(x, y)

        if dlg.exec_():
            pass

        dlg.button_add.setFocus()
        self._track_tab()

    def show_create_environment(self):
        """Create new basic environment with selectable python version."""
        logger.debug('')
        self.tracker.track_page(
            '/environments/create',
            pagetitle='Create new environment dialog',
        )

        dlg = CreateDialog(parent=self, api=self.api)
        self._dialog_environment_action = dlg
        worker_info = self.api.conda_data()
        worker_info.sig_chain_finished.connect(dlg.setup)
        if dlg.exec_():
            prefix = dlg.prefix
            name = dlg.name
            python_version = dlg.python_version
            install_python = dlg.install_python
            install_r = dlg.install_r
            r_type = dlg.r_type

            if name and prefix:
                pkgs = []
                logger.debug(str('{0}, {1}'.format(name, python_version)))

                if install_python:
                    pkgs.append('python={0}'.format(python_version))

                if install_r:
                    if r_type == dlg.MRO:
                        pkgs.append('mro-base')
                    elif r_type == dlg.R:
                        pkgs.append('r-base')

                    pkgs.append('r-essentials')

                self.set_busy_status(conda=True)
                logger.debug(str((prefix, name, pkgs)))
                worker = self.api.create_environment(
                    prefix=prefix, packages=pkgs
                )
                worker.sig_partial.connect(self._conda_partial_output_ready)
                worker.sig_finished.connect(self._conda_output_ready)

                # Common tasks for tabs and widgets on tabs
                self.update_status(
                    action=worker.action_msg,
                    value=0,
                    max_value=0,
                )
                self.current_prefix = prefix
                self.set_widgets_enabled(False)
                self.tab_environments.add_temporal_item(name)

        self._dialog_environment_action = None
        self.tracker.track_page('/environments')

    def show_import_environment(self):
        """Create environment based on specfile or environment YAML."""
        logger.debug('')
        self.tracker.track_page(
            '/environments/import',
            pagetitle='Create new environment by import'
        )

        dlg = ImportDialog(parent=self)
        self._dialog_environment_action = dlg
        worker_info = self.api.conda_data()
        worker_info.sig_chain_finished.connect(dlg.setup)
        if dlg.exec_():
            data = None
            file = dlg.path
            name = dlg.name
            prefix = dlg.prefix
            selected_filter = dlg.selected_file_filter

            try:
                with open(file, 'r') as f:
                    raw = f.read()
            except Exception:
                raw = ''

            if selected_filter == dlg.CONDA_SPEC_FILES:
                # Its using a conda spec file
                pass
            else:
                if selected_filter == dlg.CONDA_ENV_FILES:
                    # Its using a conda env specification
                    try:
                        data = yaml.load(raw)
                        data['name'] = name
                    except Exception:
                        pass
                elif selected_filter == dlg.PIP_REQUIREMENT_FILES:
                    # Its using a pip requirement file
                    ls = raw.split('\n')
                    deps = [
                        l for l in ls if l and not l.strip().startswith('#')
                    ]
                    data = {
                        'name': name,
                        'dependencies': ['python', {
                            'pip': deps
                        }]
                    }

                if data:
                    fd, file = tempfile.mkstemp(suffix='.yaml')
                    with open(file, 'w') as f:
                        yaml.dump(data, f, default_flow_style=False)

            logger.debug(str("{0}, {1}".format(prefix, file)))
            self.set_busy_status(conda=True)
            worker = self.api.import_environment(prefix=prefix, file=file)
            worker.sig_partial.connect(self._conda_partial_output_ready)
            worker.sig_finished.connect(self._conda_output_ready)

            # Common tasks for tabs and widgets on tabs
            self.update_status(
                action=worker.action_msg,
                value=0,
                max_value=0,
            )

            # Common tasks for tabs and subwidgets
            self.tab_environments.add_temporal_item(name)
            self.set_widgets_enabled(False)

        self._dialog_environment_action = None
        self.tracker.track_page('/environments')

    def show_remove_environment(self):
        """Clone currently selected environment."""
        logger.debug('')
        prefix = self.current_prefix
        name = os.path.basename(prefix)

        if prefix != self.api.ROOT_PREFIX:
            self.tracker.track_page(
                '/environments/remove',
                pagetitle='Remove environment dialog',
            )
            dlg = RemoveDialog(parent=self, name=name, prefix=prefix)
            self._dialog_environment_action = dlg
            if dlg.exec_():
                logger.debug(str(name))
                self.set_busy_status(conda=True)
                worker = self.api.remove_environment(prefix=prefix)
                worker.sig_partial.connect(self._conda_partial_output_ready)
                worker.sig_finished.connect(self._conda_output_ready)

                # Actions on tabs and subwidgets
                self.update_status(
                    action=worker.action_msg,
                    value=0,
                    max_value=0,
                )
                self.set_widgets_enabled(False)
#                self.stop_refreshing_timer()
            self._dialog_environment_action = None
            self.tracker.track_page('/environments')

    def show_clone_environment(self):
        """Clone currently selected environment."""
        logger.debug('')
        clone_from_prefix = self.current_prefix
        clone_from_name = os.path.basename(clone_from_prefix)
        self.tracker.track_page(
            '/environments/clone', pagetitle='Clone environment dialog'
        )
        dlg = CloneDialog(parent=self, clone_from_name=clone_from_name)
        self._dialog_environment_action = dlg
        worker_info = self.api.conda_data()
        worker_info.sig_chain_finished.connect(dlg.setup)

        if dlg.exec_():
            name = dlg.name
            prefix = dlg.prefix

            if name and prefix:
                logger.debug(str("{0}, {1}".format(clone_from_prefix, prefix)))
                self.set_busy_status(conda=True)
                worker = self.api.clone_environment(
                    clone_from_prefix=clone_from_prefix, prefix=prefix
                )
                worker.sig_partial.connect(self._conda_partial_output_ready)
                worker.sig_finished.connect(self._conda_output_ready)

                # Actions on tabs and subwidgets
                self.update_status(
                    action=worker.action_msg,
                    value=0,
                    max_value=0,
                )
                self.set_widgets_enabled(False)
                self.tab_environments.add_temporal_item(name)

        self._dialog_environment_action = None
        self.tracker.track_page('/environments')

    def show_conda_packages_action(
        self, conda_packages_actions, pip_packages_actions
    ):
        """Process the coda actions on the packages for current environment."""
        logger.debug(
            'conda_packages_actions: {}, pip_packages_actions: {}'
            ''.format(conda_packages_actions, pip_packages_actions)
        )
        install_packages = []
        remove_packages = []
        update_packages = []
        remove_pip_packages = []
        for action in [C.ACTION_DOWNGRADE, C.ACTION_INSTALL, C.ACTION_UPGRADE]:
            pkgs_action = conda_packages_actions[action]
            for pkg in pkgs_action:
                name = pkg['name']
                version = pkg['version_to']
                if version:
                    spec = name + '==' + version
                else:
                    spec = name
                install_packages.append(spec)

        for pkg in conda_packages_actions[C.ACTION_REMOVE]:
            remove_packages.append(pkg['name'])

        for pkg in conda_packages_actions[C.ACTION_UPDATE]:
            update_packages.append(pkg['name'])

        for pkg in pip_packages_actions[C.ACTION_REMOVE]:
            remove_pip_packages.append(pkg['name'])

        self.tracker.track_page(
            '/environments/packages', pagetitle='Packages actions dialog'
        )
        self.set_busy_status(conda=True)
        if install_packages:
            pkgs = install_packages
            dlg = PackagesDialog(parent=self, packages=pkgs)
            worker_deps = self.api.install_packages(
                prefix=self.current_prefix, pkgs=pkgs, dry_run=True
            )
        elif update_packages:
            pkgs = update_packages
            dlg = PackagesDialog(parent=self, packages=pkgs, update_only=True)
            worker_deps = self.api.update_packages(
                prefix=self.current_prefix, pkgs=pkgs, dry_run=True
            )
        elif remove_packages:
            pkgs = remove_packages
            dlg = PackagesDialog(
                parent=self,
                packages=pkgs,
                remove_only=True,
                pip_packages=remove_pip_packages,
            )
            worker_deps = self.api.remove_packages(
                prefix=self.current_prefix, pkgs=pkgs, dry_run=True
            )
        self._dialog_environment_action = dlg
        worker_deps.prefix = self.current_prefix
        worker_deps.sig_finished.connect(dlg.setup)

        if dlg.exec_():
            worker = None
            if remove_packages:
                worker = self.api.remove_packages(
                    prefix=self.current_prefix, pkgs=pkgs
                )
            elif install_packages:
                worker = self.api.install_packages(
                    prefix=self.current_prefix, pkgs=pkgs
                )
            elif update_packages:
                worker = self.api.update_packages(
                    prefix=self.current_prefix, pkgs=pkgs
                )
            elif remove_pip_packages:
                pass
                # Run pip command :-p?

            if worker:
                worker.sig_partial.connect(self._conda_partial_output_ready)
                worker.sig_finished.connect(self._conda_output_ready)
                self.set_widgets_enabled(False)
                self.set_busy_status(conda=True)
                self.update_status(
                    action=worker.action_msg,
                    value=0,
                    max_value=0,
                )
        else:
            if not worker_deps.is_finished():
                self.api.conda_terminate()
            self.set_busy_status(conda=False)

        self.tracker.track_page('/environments')

    def show_cancel_process(self):
        """Allow user to cancel an ongoing process."""
        logger.debug('')
        logger.debug(str('process canceled by user.'))
        if self.is_busy():
            dlg = ClosePackageManagerDialog(parent=self)
            self._dialog_quit_busy = dlg

            if self._dialog_quit_busy.exec_():
                self.update_status(action='Process cancelled', message=None)
                self.api.conda_terminate()
                self.api.download_terminate()
                self.api.conda_clear_lock()

            self.current_prefix = self.api.ROOT_PREFIX
            self.set_busy_status(conda=False, projects=False)
            self.select_environment(prefix=self.api.ROOT_PREFIX)

    # --- Conda
    # -------------------------------------------------------------------------
    def select_environment(self, name=None, prefix=None, sender=None):
        """Select the active conda environment of the application."""
        logger.debug(
            'name: {}, prefix: {}, sender: {}'.format(name, prefix, sender)
        )

        self.set_busy_status(conda=True)
        self.current_prefix = prefix
        if self.tab_environments:
            self.tab_environments.set_loading(prefix=prefix, value=True)
        msg = 'Loading packages of <b>{0}</b>...'.format(prefix)
        self.update_status(action=msg, value=0, max_value=0)
        self.set_widgets_enabled(False)
        worker = self.api.conda_data(prefix=self.current_prefix)
        worker.sig_chain_finished.connect(self.setup)

    def check_package_cache(self):
        """Check if package cache is not empty and run index update."""
        repodata = self.api._conda_api.get_repodata()
        if not repodata or len(repodata) == 0:
            self.update_index(self)

    def update_index(self, sender):
        """Update conda repodata index."""
        logger.debug('sender: {}'.format(sender))
        self.set_busy_status(conda=True)
        self.update_status(
            'Updating package index and metadata...', '', value=0, max_value=0
        )
        worker = self.api.update_index_and_metadata(prefix=self.current_prefix)
        worker.sig_chain_finished.connect(self._conda_output_ready)

    def update_channels(self, sources_added, sources_removed):
        """Save updated channels to the conda config."""
        logger.debug(
            'soruces_added: {}, sources_removed: {}'.
            format(sources_added, sources_removed)
        )
        self.update_status(
            action='Updating channel configuration...',
            value=0,
            max_value=0,
        )

        for (source, channel) in sources_added:
            worker = self.api.conda_config_add(
                'channels', channel, file=source
            )
            worker.communicate()
        for (source, channel) in sources_removed:
            worker = self.api.conda_config_remove(
                'channels', channel, file=source
            )
            worker.communicate()

        worker = self.api.update_index_and_metadata(prefix=self.current_prefix)
        worker.sig_chain_finished.connect(self._conda_output_ready)

    def add_featured_channels(self, worker, conda_config, error):
        """Automatically add featured channels on startup if not found."""
        logger.debug('conda_config: {}, error: {}'.format(conda_config, error))
        self.set_splash('Adding featured channels...')
        add_channels = self.config.get('main', 'add_default_channels')
        current_channels = conda_config.get('channels', [])
        if 'anaconda.org' in self.api_url and add_channels:
            for ch in self.FEATURED_CHANNELS:
                if ch not in current_channels:
                    worker = self.api.conda_config_add('channels', ch)
                    worker.communicate()
            self.config.set('main', 'add_default_channels', False)

    def _conda_partial_output_ready(self, worker, output, error):
        """Callback."""
        logger.debug('output: {}, error: {}'.format(output, error))
        # print('Output partial:', [output])
        self.set_busy_status(conda=True)

        action_msg = worker.action_msg
        # Get errors and data from ouput if it exists
        if not isinstance(output, dict):
            output = {}

        name = output.get('name')  # Linking step gone?
        fetch = output.get('fetch')  # Fetching step
        value = output.get('progress', 0)
        max_value = output.get('maxval', 0)

        if fetch:
            message = 'Fetching <b>{0}</b>...'.format(fetch)
            self.update_status(
                action=action_msg,
                message=message,
                value=value,
                max_value=max_value
            )

        if name:
            "Linking <b>{0}</b>...".format(name)

    def _conda_output_ready(self, worker, output, error):
        """Callback for handling action finished."""
        # print('Output:', [output])
        # print('Error:', [error])
        logger.debug('output: {}, error: {}'.format(output, error))
        self.set_busy_status(conda=False)

        action = worker.action
        if not isinstance(output, dict):
            output = {}

        error_text = output.get('error', '')
        exception_type = output.get('exception_type', '')
        exception_name = output.get('exception_name', '')
        # import from yaml provides empty dic, hence the True
        success = output.get('success', True)
        # actions = output.get('actions', {})
        # op_order = output.get('op_order', [])
        # action_check_fetch = actions.get('CHECK_FETCH', [])
        # action_rm_fetch = actions.get('RM_FETCHED', [])
        # action_fetch = actions.get('FETCH', [])
        # action_check_extract = actions.get('CHECK_EXTRACT', [])
        # action_rm_extract = actions.get('RM_EXTRACTED', [])
        # action_extract = actions.get('EXTRACT', [])
        # action_unlink = actions.get('UNLINK', [])
        # action_link = actions.get('LINK', [])
        # action_symlink_conda = actions.get('SYMLINK_CONDA', [])

        # Check if environment was created. Conda env does not have --json
        # output, so we check if folder was created
        if action == C.ACTION_IMPORT:
            success = os.path.isdir(worker.prefix)

        is_error = error_text or exception_type or exception_name

        # Set the current prefix to the prefix stablihsed by worker
        old_prefix = getattr(worker, 'old_prefix', None)
        prefix = getattr(worker, 'prefix', old_prefix)

        # Set as current environment only if a valid environment
        if prefix and self.api.conda_environment_exists(prefix=prefix):
            self.current_prefix = prefix
        elif (old_prefix and
              self.api.conda_environment_exists(prefix=old_prefix)):
            # If there is an error when installing an application in a new
            # environment due to conflicts, restore the previous prefix
            self.current_prefix = old_prefix
        else:
            self.current_prefix = self.api.ROOT_PREFIX

        if is_error or error or not success:
            logger.error(error_text)
            self.show_error_message(exception_name, error_text)
            self.select_environment(prefix=self.current_prefix)
        else:
            if action == C.ACTION_REMOVE_ENV:
                self.select_environment(prefix=self.api.ROOT_PREFIX)
            else:
                self.select_environment(prefix=self.current_prefix)

    # --- Conda launch
    # -------------------------------------------------------------------------
    def launch_application(
        self,
        package_name,
        command,
        leave_path_alone,
        prefix,
        sender,
        non_conda,
    ):
        """Launch application from home screen."""
        logger.debug(
            'package_name: {0}, command: {1}, leave_path_alone: {2}, '
            'prefix: {3}, sender:{4}'.format(
                package_name, command, leave_path_alone, prefix, sender
            )
        )

        self.update_status(
            action='Launching <b>{0}</b>'.format(package_name),
            value=0,
            max_value=0
        )

        if non_conda:
            if package_name == GLOBAL_VSCODE_APP:
                self.api.vscode_update_config(prefix=self.current_prefix)

                def _finished(worker, output, error):
                    # print(output)
                    # print(error)
                    self.launch_application_2(
                        package_name, command, leave_path_alone, prefix,
                        sender, non_conda
                    )

                # Install extensions first!
                worker = self.api.vscode_install_extensions()
                worker.sig_finished.connect(_finished)
                worker.start()
        else:
            self.launch_application_2(
                package_name,
                command,
                leave_path_alone,
                prefix,
                sender,
                non_conda,
            )

    def launch_application_2(
        self,
        package_name,
        command,
        leave_path_alone,
        prefix,
        sender,
        non_conda,
    ):
        environment = None
        if MAC:
            environment = os.environ.copy()
            # See https://github.com/ContinuumIO/anaconda-issues/issues/3287
            LANG = os.environ.get('LANG')
            LC_ALL = os.environ.get('LC_ALL')
            if bool(LANG) and not bool(LC_ALL):
                LC_ALL = LANG
            elif not bool(LANG) and bool(LC_ALL):
                LANG = LC_ALL
            else:
                LANG = LC_ALL = 'en_US.UTF-8'

            environment['LANG'] = LANG
            environment['LC_ALL'] = LC_ALL

            # See https://github.com/ContinuumIO/navigator/issues/1233
            if package_name in ['orange3', 'spyder']:
                environment['EVENT_NOKQUEUE'] = '1'

        if non_conda:
            pass

        process, id_ = launch(
            prefix,
            command,
            leave_path_alone,
            package_name=package_name,
            root_prefix=self.api.ROOT_PREFIX,
            environment=environment,
            non_conda=non_conda,
        )
        # Find process and subprocesses after launching it
        if not non_conda:
            pids = [process]
            if psutil.pid_exists(process):
                proc = psutil.Process(process)
                for p in proc.children(recursive=True):
                    pids.append(p.pid)
            worker = self.api.check_pid(pids, package_name, command, prefix)
            worker.sig_finished.connect(self.handle_pid_check)

        # Set timer
        time_seconds = 15 if WIN else 10
        self._launch_timer = QTimer()
        self._launch_timer.setSingleShot(True)
        self._launch_timer.setInterval(time_seconds * 1000)
        self._launch_timer.timeout.connect(lambda: self.update_status())
        self._launch_timer.timeout.connect(
            lambda: self.
            check_application_launch_errors(prefix, package_name, id_)
        )
        self._launch_timer.start()

    def handle_pid_check(self, worker, output, error):
        """Check for pid and children pids."""
        if output:
            data = output
            self.running_processes.append(data)

    def check_application_launch_errors(self, prefix, package_name, id_):
        """Check if application launched correctly by looking at the logs."""
        logger.debug(
            'prefix: {}, package_name: {}'.format(prefix, package_name)
        )
        root_prefix = self.api.ROOT_PREFIX
        out_path, err_path, id_ = get_package_logs(
            package_name,
            prefix=prefix,
            root_prefix=root_prefix,
            id_=id_,
        )
        err_log = ''
        if os.path.isfile(err_path):
            with open(err_path, 'r') as f:
                err_log = f.read()

        # Only show the message box error dialog if the words were found in
        # the error log
        e_low = err_log.lower()
        display_msg = e_low and 'error' in e_low or 'exception' in e_low
        if display_msg and self.config.get('main', 'show_application_launch_errors'):

            self.tracker.track_page(
                '/home/errors',
                pagetitle='Launch errors dialog.',
            )

            self._dialog_message_box = MessageBoxError(
                text='Application <b>{}</b> launch may have '
                'produced errors.'.format(package_name),
                title='Application launch error',
                error=err_log,
                report=False,
                learn_more=None
            )
            self._dialog_message_box.exec_()
            self._dialog_message_box = None
            self.tracker.track_page('/home')

    def check_dependencies_before_install(self, worker, output, error):
        """
        Check if the package to be installed changes navigator dependencies.

        This check is made for Orange3 which is not qt5 compatible.
        """
        logger.debug('output: {}, error: {}'.format(output, error))
        if isinstance(output, dict):
            exception_type = str(output.get('exception_type', ''))
            actions = output.get('actions', {})
        else:
            exception_type = ''
            actions = {}

        conflicts = False
        nav_deps_conflict = self.api.check_navigator_dependencies(
            actions, self.current_prefix
        )
        conflict_message = ''

        # Try to install in a new environment
        if 'UnsatisfiableError' in exception_type or nav_deps_conflict:
            conflicts = True
            # Try to set the default python to None to avoid issues that
            # prevent a package to be installed in a new environment due to
            # python pinning, fusion for 2.7, rstudio on win for 2.7 etc.
            self.api.conda_config_set('default_python', None)

        if conflicts:
            self.tracker.track_page(
                '/environments/create/conflict',
                pagetitle='Create new environment due to conflict import'
            )
            dlg = ConflictDialog(
                parent=self,
                package=worker.pkgs[0],
                extra_message=conflict_message,
                current_prefix=self.current_prefix,
            )
            self._dialog_environment_action = dlg
            worker_info = self.api.conda_data(prefix=self.current_prefix)
            worker_info.sig_chain_finished.connect(dlg.setup)

            if dlg.exec_():
                env_prefix = dlg.prefix
                action_msg = (
                    'Installing application <b>{0}</b> on new'
                    'environment <b>{1}</b>'
                ).format(worker.pkgs[0], env_prefix)

                if env_prefix not in dlg.environments:
                    new_worker = self.api.create_environment(
                        prefix=env_prefix,
                        packages=worker.pkgs,
                        no_default_python=True,
                    )
                    # Save the old prefix in case of errors
                    new_worker.old_prefix = worker.prefix

                    new_worker.action_msg = action_msg
                    new_worker.sig_finished.connect(self._conda_output_ready)
                    new_worker.sig_partial.connect(
                        self._conda_partial_output_ready
                    )
                else:
                    new_worker = self.api.install_packages(
                        prefix=env_prefix,
                        pkgs=worker.pkgs,
                        no_default_python=True,
                    )
                    # Save the old prefix in case of errors
                    new_worker.old_prefix = worker.prefix

                    new_worker.action = C.ACTION_INSTALL
                    new_worker.action_msg = action_msg
                    new_worker.pkgs = worker.pkgs
                    new_worker.sig_finished.connect(self._conda_output_ready)
                    new_worker.sig_partial.connect(
                        self._conda_partial_output_ready
                    )
                self.update_status(action_msg, value=0, max_value=0)
            else:
                self.set_widgets_enabled(True)
                self.set_busy_status(conda=False)
                self.update_status()

            self._dialog_environment_action = None
            self.tracker.track_page('/environments')
        else:
            if worker.action == C.APPLICATION_INSTALL:
                action_msg = (
                    'Install application <b>{0}</b> on '
                    '<b>{1}</b>'
                ).format(worker.pkgs[0], worker.prefix)
            elif worker.action == C.APPLICATION_UPDATE:
                action_msg = (
                    'Updating application <b>{0}</b> on '
                    '<b>{1}</b>'
                ).format(worker.pkgs[0], worker.prefix)
            new_worker = self.api.install_packages(
                prefix=worker.prefix,
                pkgs=worker.pkgs,
            )
            new_worker.action_msg = action_msg
            new_worker.action = worker.action
            new_worker.sender = worker.sender
            new_worker.non_conda = worker.non_conda
            new_worker.pkgs = worker.pkgs
            new_worker.sig_finished.connect(self._conda_output_ready)
            new_worker.sig_partial.connect(self._conda_partial_output_ready)
            self.update_status(action_msg, value=0, max_value=0)

#    def _check_license_requirements(self, worker, output, error):
#        """Check license requirement callback."""
#        logger.debug('output: {}, error: {}'.format(output, error))
#
#        if output:
#            temp_license_dir = tempfile.mkdtemp()
#            file_name = 'license_bundle_trial.txt'
#            temp_license_path = os.path.join(temp_license_dir, file_name)
#            with open(temp_license_path, 'w') as f:
#                f.write(json.dumps(output))
#            self.api.add_license([temp_license_path])
#        else:
#            question = (
#                'There was a problem requesting a trial license for '
#                '<b>{package}</b>. <br><br>'
#                '<a style="color: #43B02A" href="{url}">'
#                'Contact us</a>'.format(
#                    url='mailto:sales@continuum.io', package=worker.pkgs[0]
#                )
#            )
#            msg_box = MessageBoxInformation(
#                text=question, title='Trial license request'
#            )
#            msg_box.sig_url_clicked.connect(self.open_url)
#            msg_box.exec_()
#
#        self.check_dependencies_before_install(worker, worker.output, error)

    def check_license_requirements(self, worker, output, error):
        """Check if package requires licensing and try to get a trial."""
        # PACKAGES_WITH_LICENSE
        # logger.debug('output: {}, error: {}'.format(output, error))
        # package_name = worker.pkgs[0]
        #
        # # package name might include version
        # parts = package_name.split('=')
        # package_name = parts[0] if parts else package_name
        #
        # # See if there is a license and if it has expired
        # package_with_license = package_name.lower() in PACKAGES_WITH_LICENSE
        # license_info = self.api.get_package_license(package_name)
        # license_days = self.api.get_days_left(license_info)
        # expired = license_days == 0
        #
        # if package_with_license and self.logged and expired:
        #     question = (
        #         'Do you want to install <b>{package}</b> and <br>'
        #         'get a trial license valid for <b>{days} days</b>?'
        #         ''.format(
        #             package=package_name, days=60
        #         )
        #     )
        #     msg_box = MessageBoxQuestion(
        #         text=question, title='Request trial license'
        #     )
        #     action_msg = 'Installing package requiring a license...'
        #     self.update_status(action_msg, value=0, max_value=0)
        #     accept = msg_box.exec_() if package_with_license else False
        #
        #     if accept:
        #         new_worker = self.api.client_get_user_licenses()
        #         new_worker.prefix = worker.prefix
        #         new_worker.action = worker.action
        #         new_worker.action_msg = worker.action_msg
        #         new_worker.sender = worker.sender
        #         new_worker.pkgs = worker.pkgs
        #         new_worker.output = output
        #         new_worker.sig_finished.connect(
        #             self._check_license_requirements
        #         )
        #     else:
        #         self.update_status()
        #         self.tab_home.set_widgets_enabled(True)
        #         self.tab_environments.set_widgets_enabled(True)
        # elif package_with_license and not self.logged:
        #     dlg = AuthenticationDialog(self.api, parent=self)
        #     dlg.update_links()
        #     anaconda_register_url = dlg.base_url
        #
        #     question = (
        #         'To get a license trial for <b>{package}</b>, '
        #         'you need to login to <b>{brand}</b>.<br><br>'
        #         'If you do not have an account, you can register at '
        #         '<a style="color: #43B02A" href="{url}">'
        #         '{brand}</a>'
        #         ''.format(
        #             brand=self._brand,
        #             package=package_name,
        #             url=anaconda_register_url,
        #         )
        #     )
        #     msg_box = MessageBoxInformation(
        #         text=question, title='Login/Register with ' + self._brand
        #     )
        #     msg_box.sig_url_clicked.connect(self.open_url)
        #     msg_box.exec_()
        #     self.update_status()
        #     self.tab_home.set_widgets_enabled(True)
        #     self.tab_environments.set_widgets_enabled(True)
        # else:
        #     worker.output = output
        #     self.check_dependencies_before_install(worker, output, error)

        worker.output = output
        self.check_dependencies_before_install(worker, output, error)

    def conda_application_action(
        self, action, package_name, version, sender, non_conda
    ):
        """FIXME:."""
        logger.debug(
            'action: {0}, package_name: {1}, version: {2}, sender: {3}'
            ''.format(action, package_name, version, sender)
        )
        self.tab_home.set_widgets_enabled(False)
        self.tab_environments.set_widgets_enabled(False)
        self.set_busy_status(conda=True)
        current_version = self.api.conda_package_version(
            pkg=package_name, prefix=self.current_prefix
        )

        # TODO: Needs to change if there a conda package for vscode eventually
        if non_conda and package_name == GLOBAL_VSCODE_APP:
            if action == C.APPLICATION_INSTALL:
                self.install_vscode()
            elif action == C.APPLICATION_REMOVE:
                self.remove_vscode()
            return

        if version:
            pkgs = ['{0}=={1}'.format(package_name, version)]
        else:
            pkgs = ['{0}'.format(package_name)]

        if action == C.APPLICATION_INSTALL:
            worker = self.api.install_packages(
                prefix=self.current_prefix, pkgs=pkgs, dry_run=True
            )
            text_action = 'Installing'

            if current_version:
                try:
                    from distutils.version import LooseVersion
                    cur_ver = LooseVersion(current_version)
                    ver = LooseVersion(version)
                    if cur_ver > ver:
                        text_action = 'Downgrading'
                    elif cur_ver < ver:
                        text_action = 'Upgrading'
                except Exception:
                    pass

            action_msg = ('{0} application <b>{1}</b> on '
                          '<b>{2}</b>').format(
                              text_action, package_name, self.current_prefix
                          )
            worker.prefix = self.current_prefix
            worker.action = action
            worker.action_msg = action_msg
            worker.sender = sender
            worker.pkgs = pkgs
            worker.non_conda = non_conda
            worker.sig_finished.connect(self.check_license_requirements)
            worker.sig_partial.connect(self._conda_partial_output_ready)
        elif action == C.APPLICATION_UPDATE:
            worker = self.api.install_packages(
                prefix=self.current_prefix, pkgs=pkgs, dry_run=True
            )
            action_msg = ('Updating application <b>{0}</b> on '
                          '<b>{1}</b>').format(
                              package_name, self.current_prefix
                          )
            worker.prefix = self.current_prefix
            worker.action = action
            worker.action_msg = action_msg
            worker.sender = sender
            worker.pkgs = pkgs
            worker.non_conda = non_conda
            worker.sig_finished.connect(self.check_license_requirements)
            worker.sig_partial.connect(self._conda_partial_output_ready)
        elif action == C.APPLICATION_REMOVE:
            worker = self.api.remove_packages(
                prefix=self.current_prefix, pkgs=pkgs
            )
            action_msg = (
                'Removing application <b>{0}</b> from '
                '<b>{1}</b>'
            ).format(package_name, self.current_prefix)
            worker.action = action
            worker.action_msg = action_msg
            worker.sender = sender
            worker.pkgs = pkgs
            worker.non_conda = non_conda
            worker.sig_finished.connect(self._conda_output_ready)
            worker.sig_partial.connect(self._conda_partial_output_ready)
        self.update_status(action_msg, value=0, max_value=0)

    # --- VSCode
    # -------------------------------------------------------------------------
    def _output_vscode_ready(self, worker, output, error):
        """Callback for handling vscode actions."""
        if not isinstance(output, dict):
            output = {}
        error_text = output.get('error', '')
        exception_type = output.get('exception_type', '')
        exception_name = output.get('exception_name', '')
        success = output.get('success', True)
        is_error = error_text or exception_type or exception_name

        # Set the current prefix to the prefix stablihsed by worker
        prefix = getattr(worker, 'prefix', None)
        if prefix:
            self.current_prefix = prefix

        if is_error or not success:
            logger.error(error_text)
            self.show_error_message(exception_name, error_text)
            self.set_widgets_enabled(True)
            self.set_busy_status(conda=False)
        self.select_environment(prefix=self.current_prefix)

    def _partial_vscode_ready(self, worker, output, error):
        """Callback for handling vscode actions."""
        if isinstance(output, dict):
            path = output.get('path')
            progress = output.get('progress_size')
            total = output.get('total_size')
            message = output.get('message')
            if total and progress and GLOBAL_VSCODE_APP in path:
                self.update_status(
                    'Installing <b>vscode<b>',
                    'Downloading...',
                    value=progress,
                    max_value=total,
                )
            elif message:
                self.update_status(
                    'Installing <b>vscode<b>',
                    message,
                    value=0,
                    max_value=0,
                )
        elif isinstance(output, (str)):
            pass
            # parts = output.split('\n')
            # print(parts[-1])

    def install_vscode(self):
        """Installing VSCode."""
        self.update_status(
            'Installing <b>vscode<b>',
            '',
            value=0,
            max_value=0,
        )
        password = None

        if LINUX:
            dlg = PasswordDialog(parent=self)
            if dlg.exec_():
                password = dlg.password
            else:
                password = ''  # Not None, but cancelled!
                self.set_busy_status(conda=False)
                self.select_environment(prefix=self.current_prefix)

        worker = self.api.vscode_install(password=password)
        worker.sig_partial.connect(self._partial_vscode_ready)
        worker.sig_finished.connect(self._output_vscode_ready)

    def remove_vscode(self):
        """Removing VSCode."""
        self.update_status(
            'Removing <b>vscode<b>',
            '',
            value=0,
            max_value=0,
        )
        password = None
        cancelled = False

        if LINUX:
            dlg = PasswordDialog(parent=self)
            if dlg.exec_():
                password = dlg.password
                cancelled = False
            else:
                cancelled = True
                self.set_busy_status(conda=False)
                self.select_environment(prefix=self.current_prefix)

        if not cancelled:
            worker = self.api.vscode_remove(password=password)
            worker.sig_partial.connect(self._partial_vscode_ready)
            worker.sig_finished.connect(self._output_vscode_ready)

    # --- Anaconda Projects
    # -------------------------------------------------------------------------
    def select_project(self, name=None, path=None):
        """Select the project and set as current."""
        logger.debug('name: {0}, path: {1}'.format(name, path))
        self.set_busy_status(projects=True)
        projects = self.api.get_projects([self.projects_path])
        if projects:
            if path is None:
                self.current_project = list(projects.items())[0][0]
            else:
                self.current_project = path
        else:
            self.current_project = None

        if self.tab_projects:
            self.tab_projects.set_projects(projects, self.current_project)
            self.fix_tab_order()

    # --- Anaconda Projects (Dialogs)
    # -------------------------------------------------------------------------
    def _project_created(self, worker, output, error):
        """Project created callback."""
        logger.debug('output: {}, error: {}'.format(output, error))
        if worker.type == 'create':
            project_type = 'creation'
        else:
            project_type = 'import'

        if error or (output and output.problems):
            error = ''
            if output and output.problems:
                error = '\n'.join(output.problems)
            else:
                error = error
            logger.error(str(error))
            shutil.rmtree(output.directory_path)
            msg_box = MessageBoxError(
                title='Project {0} '
                'error'.format(worker.type),
                text='Project {0} failed due to:'
                ''.format(project_type),
                error=error,
            )
            msg_box.exec_()
        else:
            self.current_project = output.directory_path
        self.select_project(path=self.current_project)

    def show_create_project(self):
        """Create new basic project."""
        logger.debug('')

        self.tracker.track_page(
            '/projects/create', pagetitle='Create new project dialog'
        )
        dlg = projects.CreateDialog(
            parent=self,
            projects=self.api.get_projects([self.projects_path]),
        )
        if self.projects_path is None:
            self.show_project_folder()

        self._dialog_project_action = dlg
        if dlg.exec_() and self.projects_path:
            name = dlg.name
            path = os.path.join(self.projects_path, name)

            if self.tab_projects:
                self.tab_projects.add_temporal_item(name)

            if os.path.isdir(path):
                return
            else:
                os.makedirs(path)

            worker = self.api.project_create(
                path, name=name, make_directory=False
            )
            worker.sig_finished.connect(self._project_created)
            worker.type = 'create'

        self.tracker.track_page('/projects')

    def show_import_project(self):
        """Create new basic project."""
        logger.debug('')

        dlg = projects.ImportDialog(
            parent=self,
            projects=self.api.get_projects([self.projects_path]),
        )
        self.tracker.track_page(
            '/projects/import', pagetitle='Import project dialog'
        )

        if self.projects_path is None:
            self.show_project_folder()

        if dlg.exec_() and self.projects_path:
            name = dlg.name
            path = os.path.join(self.projects_path, name)
            folder_file_path = dlg.path
            if self.tab_projects:
                self.tab_projects.add_temporal_item(name)

            if os.path.isdir(path):
                return
            else:
                if os.path.isdir(folder_file_path):
                    shutil.copytree(folder_file_path, path)
                else:
                    os.mkdir(path)
                    file_path = os.path.join(
                        path,
                        os.path.basename(folder_file_path),
                    )
                    shutil.copyfile(folder_file_path, file_path)

                worker = self.api.project_create(
                    path, name=name, make_directory=False
                )
                worker.sig_finished.connect(self._project_created)
                worker.type = 'import'

        self.tracker.track_page('/projects')

    def show_remove_project(self):
        """Create new basic project."""
        logger.debug('')

        if self.current_project is not None:
            dlg = projects.RemoveDialog(
                parent=self, project=self.current_project
            )
            self.tracker.track_page(
                '/projects/remove', pagetitle='Remove project dialog'
            )

            if dlg.exec_():
                path = self.current_project

                if self.tab_projects:
                    self.tab_projects.set_loading(prefix=path, value=True)
                    self.tab_projects.before_delete()
                    try:
                        shutil.rmtree(path)
                    except Exception:
                        pass
                    self.select_project()

        self.tracker.track_page('/projects')

    def show_project_folder(self):
        """Create projects folder if it has not been set up."""
        logger.debug('')
        if self.projects_path is None:
            # Ask to create folder
            dlg = projects.ProjectsPathDialog(parent=self)

            if self.tracker:
                self.tracker.track_page(
                    '/projects/path', pagetitle='Project local folder.'
                )

            self._dialog_project_action = dlg
            while True:
                if dlg.exec_() == dlg.Accepted:
                    self.config.set('main', 'projects_path', dlg.path)

                    if not os.path.isdir(dlg.path):
                        os.makedirs(dlg.path)
                    self.projects_path = dlg.path
                    self.select_project()
                    break

        if self.tracker:
            self.tracker.track_page('/projects')

    # --- Other
    # -------------------------------------------------------------------------
    def check_for_new_licenses(self):
        """Check for new licenses periodically on the system."""
        new_licenses = self.api.load_licenses()
        if new_licenses != self.licenses:
            logger.debug('')
            self.licenses = new_licenses
            self.tab_home.update_items()

    def check_for_new_environments(self):
        """Check for new environments periodically on the system."""

        def _process(worker, output, error):
            new_envs = output.get('__environments')
            if self.environments != new_envs:
                logger.debug('')
                self.environments = new_envs
                self.select_environment(prefix=self.current_prefix)

        worker = self.api.conda_info(prefix=self.current_prefix)
        worker.sig_chain_finished.connect(_process)

    def check_for_new_projects(self):
        """Check for new projects periodically on the system."""
        logger.debug('')

        # Check that project path is a valid path and not a list??
        projects_path = self.config.get('main', 'projects_path')
        if (projects_path and is_text_string(projects_path) and
                os.path.isdir(projects_path)):
            self.projects_path = projects_path
        else:
            self.config.set('main', 'projects_path', None)

        new_projects = self.api.get_projects([self.projects_path])
        if new_projects != self.projects:
            self.projects = new_projects
            self.select_project(path=self.current_project)

    def check_for_new_login(self):
        """
        Check for new login status periodically on the system.

        Also checks for internet connectivity and updates.
        """
        new_token = self.api._client_api.load_token()
        if new_token != self.token:
            logger.debug('')
            self.token = new_token
            if new_token is None:
                self.handle_login(logout=True)
            else:
                # TODO: How to relog if logged from command line??
                pass

    def check_internet_connectivity(self):
        """Check if there is internet available."""
        last_status_is_offline = self.config.get(
            'main', 'last_status_is_offline'
        )
        is_offline = self.api.is_offline()

        if is_offline != last_status_is_offline and self.setup_ready:
            last_status_is_offline = self.config.set(
                'main', 'last_status_is_offline', is_offline
            )

            if is_offline:
                # Disable login/logout button
                self.button_login.setDisabled(True)
                self.button_logged_username.setDisabled(True)

                # Include label to indicate mode
                offline_text = '<i>Working in offline mode</i>'
                tooltip = DialogOfflineMode.MESSAGE_TOOL
                self.label_offline_mode.setText(offline_text)
                self.label_offline_mode.setToolTip(tooltip)
                self.show_offline_mode_dialog()
            else:
                # Restore buttons and text
                self.button_login.setEnabled(True)
                self.button_logged_username.setEnabled(True)
                self.label_offline_mode.setText('')
                self.label_offline_mode.setToolTip('')

    def stop_timers(self):
        """Stop all refreshing timers."""
        logger.debug('')
        self._timer_client.stop()
        self._timer_environments.stop()
        self._timer_projects.stop()
        self._timer_licenses.stop()
        self._timer_offline.stop()

    def start_timers(self):
        """Start all refreshing timers."""
        logger.debug('')
        self._timer_client.start()
        self._timer_environments.start()
        self._timer_projects.start()
        self._timer_licenses.start()
        self._timer_offline.start()

    def fix_tab_order(self, tab_index=None):
        """Fix tab order of UI widgets."""
        logger.debug('')
        current_widget = self.stack.currentWidget()
        if current_widget is not None:
            # print('\n\n{}\n'.format(current_widget))
            ordered_widgets = [
                self.button_update_available,
                self.button_logged_username,
                self.button_login,
            ]
            ordered_widgets += self.stack.tabbar.buttons
            next_widdget = self.stack.tabbar.links[0]
            ordered_widgets += current_widget.ordered_widgets(next_widdget)
            ordered_widgets += self.stack.tabbar.links
            ordered_widgets += self.stack.tabbar.links_social
            ordered_widgets += [self.button_update_available]

            for i, widget in enumerate(ordered_widgets[:-1]):
                try:
                    text = widget.text()
                except Exception:
                    text = ''

                # Remove any ellipsis character
                try:
                    text = text.replace(u'\u2026', '')
                except Exception:
                    pass

                logger.debug('{0}, {1}, {2}'.format(i, widget, text))

                # print('{0}, {1}, {2}'.format(i, widget, text))
                # print('{0}, {1}'.format(i + 1, ordered_widgets[i + 1]))
                self.setTabOrder(ordered_widgets[i], ordered_widgets[i + 1])
                # print()

        if self.tab_projects and current_widget is self.tab_projects:
            self.show_project_folder()

    def restart(self):
        """Restart application."""
        logger.debug('')
        root_prefix = self.api.ROOT_PREFIX
        prefix = os.environ.get('CONDA_PREFIX', root_prefix)
        leave_path_alone = True
        command = ['anaconda-navigator']
        self.restart_required = False
        if self.closing():
            launch(
                prefix,
                command,
                leave_path_alone,
                package_name='anaconda-navigator-restart',
                root_prefix=root_prefix,
            )
            self.restart_required = True
            self.close()

    def set_splash(self, message):
        """Set splash dialog message."""
        logger.debug('message: {}'.format(message))
        if self.splash:
            self.splash.show_message(message)
        QApplication.processEvents()

    def toggle_fullscreen(self):
        """Toggle fullscreen status."""
        logger.debug('')
        if self.isFullScreen():
            self.fullscreen_flag = False

            if self.maximized_flag:
                self.showMaximized()
            else:
                self.showNormal()
        else:
            self.maximized_flag = self.isMaximized()
            self.fullscreen_flag = True
            self.showFullScreen()

    def set_busy_status(
        self, conda=None, projects=None, learning=None, community=None
    ):
        """
        Update the busy status of conda and anaconda projects the application.

        Conda status is defined by actions taken on Home/Environments tab.
        (Anaconda) Project status is defined by actions taken on Projects tab.

        The value will only update if True or False, if None, the current value
        set will remain.
        """
        logger.debug('conda: {}, project: {}'.format(conda, projects))

        if conda is not None and isinstance(conda, bool):
            self.busy_conda = conda
            if self.busy_conda:
                self.stop_timers()
            else:
                self.start_timers()

        if projects is not None and isinstance(projects, bool):
            self.busy_projects = projects

        if learning is not None and isinstance(learning, bool):
            self.busy_learning = learning

        if community is not None and isinstance(community, bool):
            self.busy_community = community

        if (not self.busy_projects and not self.busy_conda):
            self.sig_conda_ready.emit()

        if (not self.busy_projects and not self.busy_conda and
                not self.busy_learning and not self.busy_community):
            # print('Not busy')
            self.sig_ready.emit()

        # print('Conda busy:', [self.busy_conda])
        # print('Projects busy:', [self.busy_projects])
        # print('Community busy:', [self.busy_community])
        # print('Learning busy:', [self.busy_learning])
        # print()

    def is_busy(self):
        """Return if the application is currently busy."""
        logger.debug('')
        return self.busy_conda or self.busy_projects

    def update_status(
        self, action=None, message=None, value=None, max_value=None
    ):
        """Update status bar."""
        logger.debug(
            'action: {0}, message: {1}, value: {2}, max_value: {3}'
            ''.format(action, message, value, max_value)
        )
        for tab in [self.tab_home, self.tab_environments]:
            if tab:
                tab.update_status(
                    action=action,
                    message=message,
                    value=value,
                    max_value=max_value
                )

    def closing(self):
        """Closing helper method to reuse on close event and restart."""
        logger.debug('')
        close = True
        if not self.is_busy():
            show_apps_dialog = not self.config.get(
                'main', 'hide_running_apps_dialog'
            )

            # Check if any of the stored processes is still alive and if not
            # remove from the list of processes
            pids_exist = []
            if self.running_processes:
                for process_data in self.running_processes[:]:
                    pids = process_data['pids']

                    for pid in pids:
                        if psutil.pid_exists(pid):
                            pids_exist.append(pid)
                            proc = psutil.Process(pid)
                            for p in proc.children(recursive=True):
                                pids_exist.append(psutil.pid_exists(p.pid))

                    if not any(pids_exist):
                        self.running_processes.remove(process_data)

            if any(pids_exist) and show_apps_dialog:
                self.tracker.track_page(
                    '/quit/running',
                    pagetitle='Quit running applications dialog'
                )
                dlg = QuitRunningAppsDialog(
                    parent=self, running_processes=self.running_processes
                )
                self._dialog_quit_running_apps = dlg
                if dlg.exec_():
                    close_apps = self.config.get(
                        'main', 'running_apps_to_close'
                    )
                    for process_data in self.running_processes[:]:
                        if process_data['package'] in close_apps:
                            pids = list(
                                sorted(process_data['pids'], reverse=True)
                            )
                            for pid in pids:
                                if psutil.pid_exists(pid):
                                    proc = psutil.Process(pid)
                                    for p in proc.children(recursive=True):
                                        # logger.debug(str((p.name(), p.pid)))
                                        try:
                                            p.kill()
                                        except Exception:
                                            pass
                                    # logger.debug(str((proc.name(),
                                    #              proc.pid)))
                                    try:
                                        proc.kill()
                                    except Exception:
                                        pass

                                    if process_data in self.running_processes:
                                        self.running_processes.remove(
                                            process_data,
                                        )
                else:
                    close = False
                self._dialog_quit_running_apps = None
                self._track_tab()

        if close:
            if self.is_busy():
                if self.tracker:
                    self.tracker.track_page(
                        '/quit/busy', pagetitle='Quit busy dialog'
                    )
                self._dialog_quit_busy = QuitBusyDialog(parent=self)
                if not self._dialog_quit_busy.exec_():
                    close = False
                self._dialog_quit_busy = None
                self._track_tab()
            else:
                show_dialog = not self.config.get('main', 'hide_quit_dialog')
                if show_dialog:
                    if self.tracker:
                        self.tracker.track_page(
                            '/quit', pagetitle='Quit dialog'
                        )
                    self._dialog_quit = QuitApplicationDialog(parent=self)
                    if not self._dialog_quit.exec_():
                        close = False
                        self._track_tab()
                    self._dialog_quit = None

        return close

    # --- Qt methods
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        """Catch close event."""
        logger.debug('')
        # If a restart was required dont ask self.closing again
        if not self.restart_required and not self.closing():
            event.ignore()

        try:
            geo = pickle.dumps(self.saveGeometry())
            self.config.set('main', 'geo', geo)
        except Exception as e:
            logger.error(e)

    def keyPressEvent(self, event):
        """Override Qt method."""
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key_F5:
            logger.debug('Refreshing stylesheets')
            self.update_style_sheet()
        elif key == Qt.Key_F11 and not MAC:
            self.toggle_fullscreen()
        elif key == Qt.Key_F and modifiers & Qt.ControlModifier and MAC:
            self.toggle_fullscreen()

        super(MainWindow, self).keyPressEvent(event)


# --- Local testing
# -----------------------------------------------------------------------------
def local_test():  # pragma: no cover
    """Run local test."""
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication()
    w = MainWindow(
        #        tab_home=True,
        #        tab_environments=True,
        #        tab_project=False,
        #        tab_community=False,
        #        tab_learning=False,
    )
    app.w = w
    w.show()
    # w.close()
    sys.exit(app.exec_())


if __name__ == "__main__":  # pragma: no cover
    local_test()
