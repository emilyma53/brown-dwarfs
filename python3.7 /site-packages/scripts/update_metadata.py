# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 Continuum Analytics, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Script to download and bundle the latest metadata while the mechanism
is implemented on bith repo and cloud.
"""

# Standard library imports
import bz2
import os
import tempfile

# Third party imports
import requests

HERE_PATH = os.path.dirname(os.path.realpath(__file__))
NAVIGATOR_PATH = os.path.dirname(HERE_PATH)
METADATA_PATH = os.path.join(
    NAVIGATOR_PATH, 'anaconda_navigator', 'static', 'content',
    'metadata.json.bz2'
)


def update_bundled_metadata():
    """Download latest metadata.json file, compress it and budnle it."""
    # url = 'https://repo.anaconda.com/pkgs/free/metadata.json'
    url = 'https://repo.anaconda.com/pkgs/metadata.json'
    filepath = METADATA_PATH
    response = requests.get(url, stream=True)
    handle, temppath = tempfile.mkstemp()

    print('Downloading:', url)
    print('File:', filepath)
    print('Status:', response.status_code)

    with open(temppath, 'wb') as handle:
        for chunk in response.iter_content(chunk_size=512):
            if chunk:  # filter out keep-alive new chunks
                handle.write(chunk)

    # Compress it
    compression_level = 9
    with open(temppath, 'rb') as f:
        data = f.read()
        print('Compressing file')
        compressed_contents = bz2.compress(data, compression_level)

    print('Writing compressed file')
    with open(filepath, 'wb') as f:
        f.write(compressed_contents)

    print('Finished!')


if __name__ == '__main__':
    update_bundled_metadata()
