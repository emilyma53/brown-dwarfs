#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""Application entry point."""

# Standard library imports
import sys

# Local imports
from navigator_updater import __version__
from navigator_updater.app.cli import parse_arguments


def main():  # pragma: no cover
    """Main application entry point."""
    # Parse CLI arguments
    options = parse_arguments()

    # Return information on version
    if options.version:
        print(__version__)
        sys.exit(0)

    # Import app
    from navigator_updater.app.start import start_app
    start_app(options)


if __name__ == '__main__':  # pragma: no cover
    main()
