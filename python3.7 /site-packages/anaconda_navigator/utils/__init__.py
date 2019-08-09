# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2017 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""This module contains several utilities for Anaconda Navigator package."""

# Standard library imports
import os
import os.path as osp

# Third party imports
from qtpy.QtGui import QIcon

# Local imports
from anaconda_navigator.static.images import IMAGE_PATH
from anaconda_navigator.utils import encoding
from anaconda_navigator.utils.py3compat import is_unicode, u


def get_home_dir():
    """Return user home directory."""
    try:
        # expanduser() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent file paths.
        path = encoding.to_unicode_from_fs(osp.expanduser('~'))
    except Exception:
        path = ''
    for env_var in ('HOME', 'USERPROFILE', 'TMP'):
        if osp.isdir(path):
            break
        # os.environ.get() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent environment
        # variables.
        path = encoding.to_unicode_from_fs(os.environ.get(env_var, ''))
    if path:
        return path
    else:
        raise RuntimeError('Please define environment variable $HOME')


def get_image_path(filename):
    """Return image full path based on filename."""
    img_path = os.path.join(IMAGE_PATH, filename)

    if os.path.isfile(img_path):
        return img_path
    else:
        return None


def get_icon(filename):
    """Return icon based on filename."""
    icon = get_image_path(filename)
    if icon:
        return QIcon(icon)
    else:
        return QIcon()


def sort_versions(versions=(), reverse=False, sep=u'.'):
    """Sort a list of version number strings.

    This function ensures that the package sorting based on number name is
    performed correctly when including alpha, dev rc1 etc...
    """
    if versions == []:
        return []

    digits = u'0123456789'

    def toint(x):
        try:
            n = int(x)
        except Exception:
            n = x
        return n

    versions = list(versions)
    new_versions, alpha, sizes = [], set(), set()

    for item in versions:
        it = item.split(sep)
        temp = []
        for i in it:
            x = toint(i)
            if not isinstance(x, int):
                x = u(x)
                middle = x.lstrip(digits).rstrip(digits)
                tail = toint(x.lstrip(digits).replace(middle, u''))
                head = toint(x.rstrip(digits).replace(middle, u''))
                middle = toint(middle)
                res = [head, middle, tail]
                while u'' in res:
                    res.remove(u'')
                for r in res:
                    if is_unicode(r):
                        alpha.add(r)
            else:
                res = [x]
            temp += res
        sizes.add(len(temp))
        new_versions.append(temp)

    # replace letters found by a negative number
    replace_dic = {}
    alpha = sorted(alpha, reverse=True)
    if len(alpha):
        replace_dic = dict(zip(alpha, list(range(-1, -(len(alpha) + 1), -1))))

    # Complete with zeros based on longest item and replace alphas with number
    nmax = max(sizes)
    for i, new_version in enumerate(new_versions):
        item = []
        for z in new_version:
            if z in replace_dic:
                item.append(replace_dic[z])
            else:
                item.append(z)

        nzeros = nmax - len(item)
        item += [0] * nzeros
        item += [versions[i]]
        new_versions[i] = item

    new_versions = sorted(new_versions, reverse=reverse)
    return [n[-1] for n in new_versions]
