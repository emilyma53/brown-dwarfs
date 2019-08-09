# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Community Tab."""

# yapf: disable

from __future__ import absolute_import, division, print_function

# Standard library imports
import json
import os
import random
import re
import sys

# Third party imports
from qtpy import PYQT4
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import QImage, QPixmap
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout

# Local imports
from anaconda_navigator.api.anaconda_api import AnacondaAPI
from anaconda_navigator.config import (CONF, CONTENT_JSON_PATH, CONTENT_PATH,
                                       IMAGE_DATA_PATH)
from anaconda_navigator.static.content import LINKS_INFO_PATH
from anaconda_navigator.static.images import LOGO_PATH, VIDEO_ICON_PATH
from anaconda_navigator.utils.logs import logger
from anaconda_navigator.utils.py3compat import parse
from anaconda_navigator.utils.styles import load_style_sheet
from anaconda_navigator.widgets import (ButtonBase, FrameTabContent,
                                        FrameTabHeader, SpacerHorizontal,
                                        WidgetBase)
from anaconda_navigator.widgets.helperwidgets import LineEditSearch
from anaconda_navigator.widgets.lists.content import (ListItemContent,
                                                      ListWidgetContent)


# yapf: disable

# --- Widgets used in CSS styling
# -----------------------------------------------------------------------------
class ButtonToggle(ButtonBase):
    """Toggle button used in CSS styling."""

    def __init__(self, *args, **kwargs):
        """Toggle button used in CSS styling."""
        super(ButtonToggle, self).__init__(*args, **kwargs)
        self.setCheckable(True)
        self.clicked.connect(lambda v=None: self._fix_check)

    def _fix_check(self):
        self.setProperty('checked', self.isChecked())
        self.setProperty('unchecked', not self.isChecked())


# --- Main widgets
# -----------------------------------------------------------------------------
class CommunityTab(WidgetBase):
    """Community tab."""
    # Qt Signals
    sig_video_started = Signal(str, int)
    sig_status_updated = Signal(object, int, int, int)
    sig_ready = Signal(object)  # Sender

    # Class variables
    instances = []

    # Maximum item count for different content type
    VIDEOS_LIMIT = 25
    WEBINARS_LIMIT = 25
    EVENTS_LIMIT = 25

    # Google analytics campaigns
    UTM_MEDIUM = 'in-app'
    UTM_SOURCE = 'navigator'

    def __init__(self,
                 parent=None,
                 tags=None,
                 content_urls=None,
                 content_path=CONTENT_PATH,
                 image_path=IMAGE_DATA_PATH,
                 config=CONF,
                 bundle_path=LINKS_INFO_PATH,
                 saved_content_path=CONTENT_JSON_PATH,
                 tab_name=''):
        """Community tab."""
        super(CommunityTab, self).__init__(parent=parent)

        self._tab_name = ''
        self.content_path = content_path
        self.image_path = image_path
        self.bundle_path = bundle_path
        self.saved_content_path = saved_content_path
        self.config = config

        self._parent = parent
        self._downloaded_thumbnail_urls = []
        self._downloaded_urls = []
        self._downloaded_filepaths = []
        self.api = AnacondaAPI()
        self.content_urls = content_urls
        self.content_info = []
        self.step = 0
        self.step_size = 1
        self.tags = tags
        self.timer_load = QTimer()
        self.pixmaps = {}
        self.filter_widgets = []
        self.default_pixmap = QPixmap(VIDEO_ICON_PATH).scaled(
            100, 60, Qt.KeepAspectRatio, Qt.FastTransformation)

        # Widgets
        self.text_filter = LineEditSearch()
        self.list = ListWidgetContent()
        self.frame_header = FrameTabHeader()
        self.frame_content = FrameTabContent()

        # Widget setup
        self.timer_load.setInterval(333)
        self.list.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.text_filter.setPlaceholderText('Search')
        self.text_filter.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setObjectName("Tab")

        self.list.setMinimumHeight(200)
        fm = self.text_filter.fontMetrics()
        self.text_filter.setMaximumWidth(fm.width('M' * 23))

        # Layouts
        self.filters_layout = QHBoxLayout()

        layout_header = QHBoxLayout()
        layout_header.addLayout(self.filters_layout)
        layout_header.addStretch()
        layout_header.addWidget(self.text_filter)
        self.frame_header.setLayout(layout_header)

        layout_content = QHBoxLayout()
        layout_content.addWidget(self.list)
        self.frame_content.setLayout(layout_content)

        layout = QVBoxLayout()
        layout.addWidget(self.frame_header)
        layout.addWidget(self.frame_content)
        self.setLayout(layout)

        # Signals
        self.timer_load.timeout.connect(self.set_content_list)
        self.text_filter.textChanged.connect(self.filter_content)

    def setup(self):
        """Setup tab content."""
        self.download_content()

    def _json_downloaded(self, worker, output, error):
        """Callbacl for download_content."""
        url = worker.url
        if url in self._downloaded_urls:
            self._downloaded_urls.remove(url)

        if not self._downloaded_urls:
            self.load_content()

    def download_content(self):
        """Download content to display in cards."""
        self._downloaded_urls = []
        self._downloaded_filepaths = []

        if self.content_urls:
            for url in self.content_urls:
                url = url.lower()  # Enforce lowecase... just in case
                fname = url.split('/')[-1] + '.json'
                filepath = os.sep.join([self.content_path, fname])
                self._downloaded_urls.append(url)
                self._downloaded_filepaths.append(filepath)
                worker = self.api.download(url, filepath)
                worker.url = url
                worker.sig_finished.connect(self._json_downloaded)
        else:
            self.load_content()

    def load_content(self, paths=None):
        """Load downloaded and bundled content."""
        content = []

        # Load downloaded content
        for filepath in self._downloaded_filepaths:
            fname = filepath.split(os.sep)[-1]
            items = []
            if os.path.isfile(filepath):
                with open(filepath, 'r') as f:
                    data = f.read()
                try:
                    items = json.loads(data)
                except Exception as error:
                    logger.error(str((filepath, error)))
            else:
                items = []

            if 'video' in fname:
                for item in items:
                    try:
                        item['tags'] = ['video']
                        item['uri'] = item.get('video', '')

                        if item['uri']:
                            item['banner'] = item.get('thumbnail')
                            image_path = item['banner'].split('/')[-1]
                            item['image_file'] = image_path
                        else:
                            url = ''
                            item['image_file'] = ''

                        item['banner'] = url
                        item['date'] = item.get('date_start', '')
                    except Exception:
                        logger.debug("Video parse failed: {0}".format(item))
                items = items[:self.VIDEOS_LIMIT]

            elif 'event' in fname:
                for item in items:
                    try:
                        item['tags'] = ['event']
                        item['uri'] = item.get('url', '')
                        if item['banner']:
                            image_path = item['banner'].split('/')[-1]
                            item['image_file'] = image_path
                        else:
                            item['banner'] = ''
                    except Exception:
                        logger.debug('Event parse failed: {0}'.format(item))
                items = items[:self.EVENTS_LIMIT]

            elif 'webinar' in fname:
                for item in items:
                    try:
                        item['tags'] = ['webinar']
                        uri = item.get('url', '')
                        utm_campaign = item.get('utm_campaign', '')
                        item['uri'] = self.add_campaign(uri, utm_campaign)
                        image = item.get('image', '')

                        if image and isinstance(image, dict):
                            item['banner'] = image.get('src', '')
                            if item['banner']:
                                image_path = item['banner'].split('/')[-1]
                                item['image_file'] = image_path
                            else:
                                item['image_file'] = ''
                        else:
                            item['banner'] = ''
                            item['image_file_path'] = ''
                    except Exception:
                        logger.debug('Webinar parse failed: {0}'.format(item))
                items = items[:self.WEBINARS_LIMIT]

            if items:
                content.extend(items)

        # Load bundled content
        with open(self.bundle_path, 'r') as f:
            data = f.read()
        items = []
        try:
            items = json.loads(data)
        except Exception as error:
            logger.error(str((filepath, error)))
        content.extend(items)

        # Add the image path to get the full path
        for i, item in enumerate(content):
            uri = item['uri']
            uri = uri.replace('<p>', '').replace('</p>', '')
            item['uri'] = uri.replace(' ', '%20')
            filename = item.get('image_file', '')
            item['image_file_path'] = os.path.sep.join(
                [self.image_path, filename])

            # if 'video' in item['tags']:
            #     print(i, item['uri'])
            #     print(item['banner'])
            #     print(item['image_file_path'])
            #     print('')

        # Make sure items of the same type/tag are contiguous in the list
        content = sorted(content, key=lambda i: i.get('tags'))

        # But also make sure sticky content appears first
        sticky_content = []
        for i, item in enumerate(content[:]):
            sticky = item.get('sticky')
            if isinstance(sticky, str):
                is_sticky = sticky == 'true'
            elif sticky is None:
                is_sticky = False

            # print(i, sticky, is_sticky, item.get('title'))
            if is_sticky:
                sticky_content.append(item)
                content.remove(item)

        content = sticky_content + content
        self.content_info = content

        # Save loaded data in a single file
        with open(self.saved_content_path, 'w') as f:
            json.dump(content, f)

        self.make_tag_filters()
        self.timer_load.start(random.randint(25, 35))

    def add_campaign(self, uri, utm_campaign):
        """Add tracking analytics campaing to url in content items."""
        if uri and utm_campaign:
            parameters = parse.urlencode({
                'utm_source': self.UTM_SOURCE,
                'utm_medium': self.UTM_MEDIUM,
                'utm_campaign': utm_campaign
            })
            uri = '{0}?{1}'.format(uri, parameters)
        return uri

    def make_tag_filters(self):
        """Create tag filtering checkboxes based on available content tags."""
        if not self.tags:
            self.tags = set()
            for content_item in self.content_info:
                tags = content_item.get('tags', [])
                for tag in tags:
                    if tag:
                        self.tags.add(tag)

        # Get count
        tag_count = {tag: 0 for tag in self.tags}
        for tag in self.tags:
            for content_item in self.content_info:
                item_tags = content_item.get('tags', [])
                if tag in item_tags:
                    tag_count[tag] += 1

        logger.debug("TAGS: {0}".format(self.tags))
        self.filter_widgets = []
        for tag in sorted(self.tags):
            count = tag_count[tag]
            tag_text = "{0} ({1})".format(tag.capitalize(), count).strip()
            item = ButtonToggle(tag_text)
            item.setObjectName(tag.lower())
            item.setChecked(self.config.get('checkboxes', tag.lower(), True))
            item.clicked.connect(self.filter_content)
            self.filter_widgets.append(item)
            self.filters_layout.addWidget(item)
            self.filters_layout.addWidget(SpacerHorizontal())

    def filter_content(self, text=None):
        """
        Filter content by a search string on all the fields of the item.

        Using comma allows the use of several keywords, e.g. Peter,2015.
        """
        text = self.text_filter.text().lower()
        text = [t for t in re.split('\W', text) if t]

        selected_tags = []
        for item in self.filter_widgets:
            tag_parts = item.text().lower().split()
            tag = tag_parts[0]
            # tag_count = tag_parts[-1]

            if item.isChecked():
                selected_tags.append(tag)
                self.config.set('checkboxes', tag, True)
            else:
                self.config.set('checkboxes', tag, False)

        for i in range(self.list.count()):
            item = self.list.item(i)

            all_checks = []
            for t in text:
                t = t.strip()
                checks = (t in item.title.lower() or t in item.venue.lower() or
                          t in ' '.join(item.authors).lower() or
                          t in item.summary.lower())
                all_checks.append(checks)
            all_checks.append(
                any(tag.lower() in selected_tags for tag in item.tags))

            if all(all_checks):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def set_content_list(self):
        """
        Add items to the list, gradually.

        Called by a timer.
        """
        for i in range(self.step, self.step + self.step_size):
            if i < len(self.content_info):
                item = self.content_info[i]
                banner = item.get('banner', '')
                path = item.get('image_file_path', '')
                content_item = ListItemContent(
                    title=item['title'],
                    subtitle=item.get('subtitle', "") or "",
                    uri=item['uri'],
                    date=item.get('date', '') or "",
                    summary=item.get('summary', '') or "",
                    tags=item.get('tags', []),
                    banner=banner,
                    path=path,
                    pixmap=self.default_pixmap, )
                self.list.addItem(content_item)
                #                self.update_style_sheet(self.style_sheet)

                # This allows the content to look for the pixmap
                content_item.pixmaps = self.pixmaps

                # Use images shipped with Navigator, if no image try the
                # download
                image_file = item.get('image_file', 'NaN')
                local_image = os.path.join(LOGO_PATH, image_file)
                if os.path.isfile(local_image):
                    self.pixmaps[path] = QPixmap(local_image)
                else:
                    self.download_thumbnail(content_item, banner, path)
            else:
                self.timer_load.stop()
                self.sig_ready.emit(self._tab_name)
                break
        self.step += self.step_size
        self.filter_content()

    def download_thumbnail(self, item, url, path):
        """Download all the video thumbnails."""
        # Check url is not an empty string or not already downloaded
        if url and url not in self._downloaded_thumbnail_urls:
            self._downloaded_thumbnail_urls.append(url)
            # For some content the app segfaults (with big files) so
            # we dont use chunks
            worker = self.api.download(url, path, chunked=True)
            worker.url = url
            worker.item = item
            worker.path = path
            worker.sig_finished.connect(self.convert_image)
            logger.debug('Fetching thumbnail {}'.format(url))

    def convert_image(self, worker, output, error):
        """
        Load an image using PIL, and converts it to a QPixmap.

        This was needed as some image libraries are not found in some OS.
        """
        path = output
        if path in self.pixmaps:
            return

        try:
            if sys.platform == 'darwin' and PYQT4:
                from PIL.ImageQt import ImageQt
                from PIL import Image

                if path:
                    image = Image.open(path)
                    image = ImageQt(image)
                    qt_image = QImage(image)
                    pixmap = QPixmap.fromImage(qt_image)
                else:
                    pixmap = QPixmap()
            else:
                if path and os.path.isfile(path):
                    extension = path.split('.')[-1].upper()
                    if extension in ['PNG', 'JPEG', 'JPG']:
                        # This might be producing an error message on windows
                        # for some of the images
                        pixmap = QPixmap(path, format=extension)
                    else:
                        pixmap = QPixmap(path)
                else:
                    pixmap = QPixmap()

            self.pixmaps[path] = pixmap
        except (IOError, OSError) as error:
            logger.error(str(error))

    def update_style_sheet(self, style_sheet=None):
        """Update custom CSS stylesheet."""
        if style_sheet is None:
            self.style_sheet = load_style_sheet()
        else:
            self.style_sheet = style_sheet

        self.setStyleSheet(self.style_sheet)
        self.list.update_style_sheet(self.style_sheet)

    def ordered_widgets(self, next_widget=None):
        """Fix tab order of UI widgets."""
        ordered_widgets = []
        ordered_widgets += self.filter_widgets
        ordered_widgets += [self.text_filter]
        ordered_widgets += self.list.ordered_widgets()
        return ordered_widgets


# --- Local testing
# -----------------------------------------------------------------------------
def dev_endpoints():
    """Return content endpoints for development server."""
    dev = 'http://api-dev-continuum-content.pantheonsite.io/api/'
    VIDEOS_URL = dev + 'videos'
    EVENTS_URL = dev + 'events'
    WEBINARS_URL = dev + 'webinars'
    return [EVENTS_URL, VIDEOS_URL, WEBINARS_URL]


def production_endpoints():
    """Return content endpoints for production server."""
    VIDEOS_URL = "http://anaconda.com/api/videos"
    EVENTS_URL = "http://anaconda.com/api/events"
    WEBINARS_URL = "http://anaconda.com/api/webinars"
    return [EVENTS_URL, VIDEOS_URL, WEBINARS_URL]


def test_json_endpoint(dev=False):
    """Test production and development json content endpoints."""
    content = dev_endpoints() if dev else production_endpoints()
    widget = CommunityTab(content_urls=content)
    widget.update_style_sheet(load_style_sheet())
    widget.setup()
    return widget


def local_test():  # pragma: no cover
    """Run local test."""
    import tempfile
    from anaconda_navigator.utils.qthelpers import qapplication
    from anaconda_navigator.utils.logs import setup_logger

    log_folder = tempfile.mkdtemp()
    log_filename = 'testlog.log'
    setup_logger(log_folder=log_folder, log_filename=log_filename)
    log_path = os.path.join(log_folder, log_filename)

    app = qapplication()
    widget_development = test_json_endpoint(dev=True)
    widget_development.show()

    widget_production = test_json_endpoint(dev=False)
    widget_production.show()

    ex = app.exec_()

    with open(log_path) as f:
        text = f.read()

    if "No JSON object could be decoded" in text:
        sys.exit(1)
    sys.exit(ex)


if __name__ == "__main__":  # pragma: no cover
    local_test()
