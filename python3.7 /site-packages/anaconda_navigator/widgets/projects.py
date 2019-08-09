# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Projects Tab."""

# yapf: disable

# Standard library imports
import os
import shutil

# Third party imports
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (QHBoxLayout, QPlainTextEdit, QTabWidget,
                            QVBoxLayout, QWidget)

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import CONF, HOME_PATH
from anaconda_navigator.static.images import WARNING_ICON
from anaconda_navigator.widgets import (ButtonDanger, ButtonNormal,
                                        ButtonPrimary, FrameBase, LabelBase,
                                        SpacerHorizontal, SpacerVertical,
                                        WidgetBase)
from anaconda_navigator.widgets.dialogs.projects import DialogProblems
from anaconda_navigator.widgets.explorer import ExplorerWidget


# yapf: enable


class FrameProjectDetailsHeader(FrameBase):
    pass


class FrameProjectDetailsFooter(FrameBase):
    pass


class LabelProjectLocation(LabelBase):
    pass


class TextProjectLocation(LabelBase):
    pass


class ButtonProjectProblems(ButtonDanger):
    pass


class ButtonProjectSuggestions(ButtonNormal):
    pass


class EditorBase(QPlainTextEdit):
    sig_saved = Signal()

    def keyPressEvent(self, event):
        super(EditorBase, self).keyPressEvent(event)


class ProjectEditor(QWidget):
    sig_dirty_state = Signal(bool)
    sig_saved = Signal()

    def __init__(self, *args, **kwargs):
        super(ProjectEditor, self).__init__(*args, **kwargs)

        # Widgets
        self.editor = EditorBase(self)
        self.button_save = ButtonPrimary('Save')
        self.button_problems = ButtonProjectProblems('Problems')
        self.button_suggestions = ButtonProjectSuggestions('Suggestions')
        self.original_text = None
        self.problems = None
        self.suggestions = None

        # Layouts
        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.button_save)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.button_problems)
        layout_buttons.addWidget(SpacerHorizontal())
        layout_buttons.addWidget(self.button_suggestions)

        layout = QVBoxLayout()
        layout.addLayout(layout_buttons)
        layout.addWidget(self.editor)

        self.setLayout(layout)

        # Signals
        self.editor.textChanged.connect(self.text_changed)
        self.button_save.clicked.connect(self.save)
        self.button_problems.clicked.connect(self.show_problems)
        self.button_suggestions.clicked.connect(self.show_suggestions)

    def show_problems(self):
        """Display problems in a dialog."""
        dlg = DialogProblems(parent=self, problems=self.problems)
        geo_tl = self.button_problems.geometry().topRight()
        tl = self.button_problems.parentWidget().mapToGlobal(geo_tl)
        x = tl.x() - dlg.width()
        y = tl.y() + self.button_problems.height()
        dlg.move(x, y)
        dlg.show()

    def show_suggestions(self):
        """Display suggestions in a dialog."""
        dlg = DialogProblems(parent=self, problems=self.suggestions)
        geo_tl = self.button_suggestions.geometry().topRight()
        tl = self.button_suggestions.parentWidget().mapToGlobal(geo_tl)
        x = tl.x() - dlg.width()
        y = tl.y() + self.button_suggestions.height()
        dlg.move(x, y)
        dlg.show()

    def save(self):
        """Save test to editor."""
        text = self.editor.toPlainText()
        self.original_text = text
        self.button_save.setDisabled(True)
        self.sig_saved.emit()

    def text_changed(self):
        """Callback on text change."""
        dirty = self.is_dirty()
        self.sig_dirty_state.emit(dirty)
        self.button_save.setEnabled(dirty)

    def is_dirty(self):
        """Return if the document is dirty."""
        current_text = self.editor.toPlainText()
        return current_text != self.original_text

    def text(self):
        """Return current plain text from editor."""
        return self.editor.toPlainText()

    def set_info(self, problems, suggestions):
        """Store problems and suggestions for display."""
        self.button_problems.setVisible(False)
        self.button_suggestions.setVisible(False)
        self.problems = None
        self.suggetsions = None

        if problems:
            self.problems = problems
            self.button_problems.setVisible(True)

        if suggestions:
            self.suggestions = suggestions
            self.button_suggestions.setVisible(True)

    def set_text(self, text):
        """Set editor text."""
        self.editor.setPlainText(text)
        self.original_text = text
        self.button_save.setDisabled(True)

    def scroll_value(self):
        """Get scroll value for vertical bar."""
        return self.editor.verticalScrollBar().value()

    def set_scroll_value(self, value):
        """Set scroll value for vertical bar."""
        return self.editor.verticalScrollBar().setValue(value)

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        ordered_widgets = [
            self.button_save, self.button_problems, self.button_suggestions,
            self.editor
        ]
        return ordered_widgets


class ProjectsWidget(WidgetBase):
    """Main projects widget."""

    sig_saved = Signal()
    sig_login_requested = Signal()

    def __init__(self, *args, **kwargs):
        super(ProjectsWidget, self).__init__(*args, **kwargs)

        self.api = AnacondaAPI()
        self.timer = None
        self.timer_content_changed = QTimer()
        self.project_path = None
        self.original_content = None
        self.config = CONF
        self.timer = None

        # Widgets
        self.frame_projects_header = FrameProjectDetailsHeader()
        self.frame_projects_footer = FrameProjectDetailsFooter()
        self.button_upload = ButtonPrimary('Upload to Anaconda Cloud')
        self.button_cancel = ButtonDanger('Cancel')
        self.label_project_location = LabelProjectLocation(
            '<b>Project location</b>'
        )
        self.label_status_message = LabelBase('')
        self.text_project_location = TextProjectLocation()
        self.tab_details = QTabWidget()
        self.file_explorer = ExplorerWidget()
        self.editor = ProjectEditor(parent=self)

        # Wigets setup
        tabbar = self.tab_details.tabBar()
        tabbar.setFocusPolicy(Qt.StrongFocus)
        self.tab_details.addTab(self.file_explorer, 'Files')
        self.tab_details.addTab(self.editor, 'Edit')
        self.timer_content_changed.setInterval(2000)
        self.timer_content_changed.timeout.connect(self.check_content_change)
        self.timer_content_changed.start()

        # Layouts

        layout_upload = QHBoxLayout()
        layout_upload.addWidget(SpacerHorizontal())
        layout_upload.addWidget(SpacerHorizontal())
        layout_upload.addWidget(self.label_status_message)
        layout_upload.addStretch()
        layout_upload.addWidget(self.button_cancel)
        layout_upload.addWidget(SpacerHorizontal())
        layout_upload.addWidget(self.button_upload)
        layout_upload.addWidget(SpacerHorizontal())
        layout_upload.addWidget(SpacerHorizontal())

        layout_footer = QVBoxLayout()
        layout_footer.addWidget(SpacerVertical())
        layout_footer.addWidget(self.tab_details)
        layout_footer.addLayout(layout_upload)
        layout_footer.addWidget(SpacerVertical())
        layout_footer.addWidget(SpacerVertical())
        self.frame_projects_footer.setLayout(layout_footer)

        layout = QVBoxLayout()
        layout.addWidget(self.frame_projects_footer)
        self.setLayout(layout)

        # Signals
        self.editor.sig_dirty_state.connect(self.set_dirty)
        self.editor.sig_saved.connect(self.save)
        self.button_upload.clicked.connect(self.upload)
        self.button_cancel.clicked.connect(self.cancel)
        self.file_explorer.sig_add_to_project.connect(self.add_to_project)
        self.button_cancel.setVisible(False)

        self.file_explorer.set_current_folder(HOME_PATH)

    def update_brand(self, brand):
        """Update brand."""
        self.button_upload.setText('Upload to {0}'.format(brand))

    def add_to_project(self, fname):
        """Add selected file to project."""
        file_path = os.path.join(
            self.project_path,
            os.path.basename(fname),
        )
        try:
            shutil.copyfile(fname, file_path)
        except Exception:
            pass

    def check_content_change(self):
        """Check if content of anaconda-project changed outside."""
        if self.project_path:
            project_config_path = os.path.join(
                self.project_path, 'anaconda-project.yml'
            )
            if os.path.isfile(project_config_path):
                current_content = self.editor.text()
                with open(project_config_path, 'r') as f:
                    data = f.read()

                if (current_content != data and data != self.original_content):
                    self.load_project(self.project_path)

    def set_dirty(self, state):
        """Set dirty state editor tab."""
        text = 'Edit*' if state else 'Edit'
        self.tab_details.setTabText(1, text)

    def before_delete(self):
        """Before deleting a folder, ensure it is not the same as the cwd."""
        self.file_explorer.set_current_folder(HOME_PATH)

    def clear(self):
        """Reset view for proect details."""
        self.text_project_location.setText('')
        self.editor.set_text('')

    def cancel(self):
        """Cancel ongoing project process."""
        # TODO: when running project. Cancel ongoing process!
        self.button_cancel.setVisible(False)
        self.button_upload.setEnabled(True)

    def _upload(self, worker, output, error):
        """Upload callback."""
        error = error if error else ''
        errors = []
        if output is not None:
            errors = output.errors
        # print(output.status_description)
        # print(output.logs)
        # print(errors)
        if error or errors:
            if errors:
                error_msg = error or '\n'.join(errors)
            elif error:
                error_msg = 'Upload failed!'
            self.update_status(error_msg)
        else:
            self.update_status(
                'Project <b>{0}</b> upload successful'.format(worker.name)
            )

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(10000)
        self.timer.timeout.connect(lambda: self.update_status(''))
        self.timer.start()
        self.button_upload.setEnabled(True)
        self.button_cancel.setVisible(False)

    def update_status(self, message):
        """Update Status Bar message."""
        self.label_status_message.setText(message)

    def upload(self):
        """Upload project to Anaconda Cloud."""
        # Check if is logged in?
        if not self.api.is_logged_in():
            self.update_status('You need to log in to Anaconda Cloud')
            self.sig_login_requested.emit()
            self.update_status('')
            return

        project = self.api.project_load(self.project_path)
        name = project.name or os.path.basename(self.project_path)

        # Check if saved?
        if self.editor.is_dirty():
            self.update_status(
                'Saving project <b>{0}</b>'.format(project.name)
            )
            self.editor.save()

        project = self.api.project_load(self.project_path)

        if not project.problems:
            username, token = self.api.get_username_token()
            self.button_cancel.setVisible(True)
            worker = self.api.project_upload(
                project,
                username=username,
                token=token,
            )
            worker.sig_finished.connect(self._upload)
            worker.name = project.name
            self.button_upload.setEnabled(False)
            msg = 'Uploading project <b>{0}</b> to Anaconda Cloud.'.format(
                project.name
            )
            self.update_status(msg)
        else:
            self.update_status(
                'Problems must be fixed before uploading <b>{0}</b>'
                ''.format(name)
            )

    def save(self):
        """Save current edited project."""
        project_config_path = os.path.join(
            self.project_path, 'anaconda-project.yml'
        )
        data = self.editor.text()
        if os.path.isfile(project_config_path):
            with open(project_config_path, 'w') as f:
                data = f.write(data)
        self.load_project(self.project_path, overwrite=False)
        self.sig_saved.emit()

    def load_project(self, project_path, overwrite=True):
        """Load a conda project located at path."""
        self.project_path = project_path
        project = self.api.project_load(project_path)
        self.project = project
        self.text_project_location.setText(project_path)
        self.file_explorer.set_current_folder(project_path)

        project_config_path = os.path.join(
            project_path, 'anaconda-project.yml'
        )
        data = ''
        if os.path.isfile(project_config_path):
            with open(project_config_path, 'r') as f:
                data = f.read()

        self.original_content = data
        if overwrite:
            self.editor.set_text(data)

        self.set_dirty(False)
        self.file_explorer.set_home(project_path)
        self.update_error_status(project)
        self.update_status('')

    def ordered_widgets(self):
        """Return a list of the ordered widgets."""
        tabbar = self.tab_details.tabBar()
        ordered_widgets = [tabbar]
        ordered_widgets += self.file_explorer.ordered_widgets()
        ordered_widgets += self.editor.ordered_widgets()
        ordered_widgets += [self.button_upload]
        return ordered_widgets

    def update_error_status(self, project):
        """Update problems and suggestions."""
        if project:
            problems = project.problems
            suggestions = project.suggestions
            if problems or suggestions:
                icon = QIcon(WARNING_ICON)
                self.tab_details.setTabIcon(1, icon)
            else:
                self.tab_details.setTabIcon(1, QIcon())
            self.editor.set_info(problems, suggestions)


def local_test():
    """Run local test for project widget."""
    from anaconda_navigator.utils.qthelpers import qapplication
    app = qapplication()
    w = ProjectsWidget()
    w.showMaximized()
    w.ordered_widgets()
    app.exec_()


if __name__ == "__main__":
    local_test()
