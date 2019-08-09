# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Tests for community tab.
"""

# yapf: disable

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt  # analysis:ignore
import pytest
import pytestqt.qtbot as qtbot  # analysis:ignore

# Local imports
from anaconda_navigator.utils.fixtures import tmpfile  # analysis:ignore
from anaconda_navigator.utils.fixtures import tmpfolder
from anaconda_navigator.widgets.tabs.community import CommunityTab


# yapf: enable

PY3 = sys.version_info >= (3, 4)


class TestCommunityTab:
    @pytest.mark.skipif(
        PY3, reason="Travis CI Py3 problem. Local works."
    )  # analysis:ignore
    def test_campaign_uri(self, qtbot):  # analysis:ignore
        widget = CommunityTab()
        widget.show()
        qtbot.addWidget(widget)
        test_uri = 'http://go.continuum.io/navigator-testing/'
        campaign_name = 'navigator-testing'
        valid_uri = (
            'http://go.continuum.io/navigator-testing/'
            '?utm_campaign=navigator-testing&'
            'utm_medium=in-app&utm_source=navigator'
        )
        utm_uri = widget.add_campaign(test_uri, campaign_name)
        assert utm_uri == valid_uri

    def test_bundled_content(self, qtbot, tmpfile):  # analysis:ignore
        widget = CommunityTab(saved_content_path=tmpfile)
        widget.showMaximized()
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.sig_ready, timeout=10000):
            widget.load_content()

        assert widget.list.count() > 0
