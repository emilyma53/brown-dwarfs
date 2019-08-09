# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 Anaconda, Inc.
#
# May be copied and distributed freely only as part of an Anaconda or
# Miniconda installation.
# -----------------------------------------------------------------------------
"""
Transitional module providing compatibility functions between python 2 and 3.

This module should be fully compatible with:
    * Python >=v2.7
    * Python 3
"""

from __future__ import print_function

# Standard library imports
import operator
import os
import sys

PY2 = sys.version[0] == '2'
PY3 = sys.version[0] == '3'
PY33 = sys.version_info[0:2] >= (3, 3)

# =============================================================================
# Data types
# =============================================================================
if PY2:
    # Python 2
    TEXT_TYPES = (str, unicode)
    INT_TYPES = (int, long)
else:
    # Python 3
    TEXT_TYPES = (str, )
    INT_TYPES = (int, )
NUMERIC_TYPES = tuple(list(INT_TYPES) + [float, complex])

# =============================================================================
# Renamed/Reorganized modules
# =============================================================================
if PY2:
    # Python 2
    import __builtin__ as builtins
    import ConfigParser as configparser
    try:
        import _winreg as winreg
    except ImportError:
        pass
    from sys import maxint as maxsize
    try:
        import CStringIO as io
    except ImportError:
        import StringIO as io
    try:
        import cPickle as pickle
    except ImportError:
        import pickle
    from UserDict import DictMixin as MutableMapping
    import thread as _thread
    import repr as reprlib
    import urllib
    request = urllib
    parse = urllib
else:
    # Python 3
    import builtins  # flake8: noqa
    import configparser
    try:
        import winreg  # flake8: noqa
    except ImportError:
        pass
    from sys import maxsize
    import io  # flake8: noqa
    import pickle
    from collections import MutableMapping  # flake8: noqa
    import _thread
    import reprlib  # flake8: noqa
    from urllib import request, parse  # flake8: noqa


# =============================================================================
# Strings
# =============================================================================
def is_text_string(obj):
    """
    Return True if `obj` is a text string, False if it is anything else.

    Binary data (Python 3) or QString (Python 2, PyQt API #1).
    """
    if PY2:
        # Python 2
        return isinstance(obj, basestring)
    else:
        # Python 3
        return isinstance(obj, str)


def is_binary_string(obj):
    """Return True if obj is a binary string, False if it is anything else."""
    if PY2:
        # Python 2
        return isinstance(obj, str)
    else:
        # Python 3
        return isinstance(obj, bytes)


def is_string(obj):
    """
    Check if object is a string.

    Return True if `obj` is a text or binary Python string object False if it
    is anything else, like a QString (Python 2, PyQt API #1).
    """
    return is_text_string(obj) or is_binary_string(obj)


def is_unicode(obj):
    """Return True if `obj` is unicode."""
    if PY2:
        # Python 2
        return isinstance(obj, unicode)
    else:
        # Python 3
        return isinstance(obj, str)


def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string."""
    if PY2:
        # Python 2
        if encoding is None:
            return unicode(obj)
        else:
            return unicode(obj, encoding)
    else:
        # Python 3
        if encoding is None:
            return str(obj)
        elif isinstance(obj, str):
            # In case this function is not used properly, this could happen
            return obj
        else:
            return str(obj, encoding)


def to_binary_string(obj, encoding=None):
    """Convert `obj` to binary string (bytes in Python 3, str in Python 2)."""
    if PY2:
        # Python 2
        if encoding is None:
            return str(obj)
        else:
            return obj.encode(encoding)
    else:
        # Python 3
        return bytes(obj, 'utf-8' if encoding is None else encoding)


if PY2:
    # Python 2
    import codecs

    def u(obj):
        """Make unicode object."""
        return codecs.unicode_escape_decode(obj)[0]
else:
    # Python 3
    def u(obj):
        """Return string as it is."""
        return obj


# =============================================================================
# Function attributes
# =============================================================================
def get_func_code(func):
    """Return function code object."""
    if PY2:
        # Python 2
        return func.func_code
    else:
        # Python 3
        return func.__code__


def get_func_name(func):
    """Return function name."""
    if PY2:
        # Python 2
        return func.func_name
    else:
        # Python 3
        return func.__name__


def get_func_defaults(func):
    """Return function default argument values."""
    if PY2:
        # Python 2
        return func.func_defaults
    else:
        # Python 3
        return func.__defaults__


# =============================================================================
# Special method attributes
# =============================================================================
def get_meth_func(obj):
    """Return method function object."""
    if PY2:
        # Python 2
        return obj.im_func
    else:
        # Python 3
        return obj.__func__


def get_meth_class_inst(obj):
    """Return method class instance."""
    if PY2:
        # Python 2
        return obj.im_self
    else:
        # Python 3
        return obj.__self__


def get_meth_class(obj):
    """Return method class."""
    if PY2:
        # Python 2
        return obj.im_class
    else:
        # Python 3
        return obj.__self__.__class__


# =============================================================================
# Misc.
# =============================================================================
if PY2:
    # Python 2
    input = raw_input
    getcwd = os.getcwdu
    cmp = cmp
    import string
    str_lower = string.lower
    from itertools import izip_longest as zip_longest
else:
    # Python 3
    input = input
    getcwd = os.getcwd

    def cmp(a, b):
        """Return negative if a<b, zero if a==b, positive if a>b."""
        return (a > b) - (a < b)

    str_lower = str.lower
    from itertools import zip_longest  # flake8: noqa


def qbytearray_to_str(qba):
    """Convert QByteArray object to str in a way compatible with Python 2/3."""
    return str(bytes(qba.toHex().data()).decode())


# =============================================================================
# Dict funcs
# =============================================================================
if PY3:

    def iterkeys(d, **kw):
        """Return an iterator over the dictionary's keys."""
        return iter(d.keys(**kw))

    def itervalues(d, **kw):
        """Return an iterator over the dictionary's values."""
        return iter(d.values(**kw))

    def iteritems(d, **kw):
        """Return an iterator over the dictionary's items."""
        return iter(d.items(**kw))

    def iterlists(d, **kw):
        """Return an iterator over a multi dictionary."""
        return iter(d.lists(**kw))

    viewkeys = operator.methodcaller("keys")

    viewvalues = operator.methodcaller("values")

    viewitems = operator.methodcaller("items")
else:

    def iterkeys(d, **kw):
        """Return an iterator over the dictionary's keys."""
        return d.iterkeys(**kw)

    def itervalues(d, **kw):
        """Return an iterator over the dictionary's values."""
        return d.itervalues(**kw)

    def iteritems(d, **kw):
        """Return an iterator over the dictionary's items."""
        return d.iteritems(**kw)

    def iterlists(d, **kw):
        """Return an iterator over a multi dictionary."""
        return d.iterlists(**kw)

    viewkeys = operator.methodcaller("viewkeys")

    viewvalues = operator.methodcaller("viewvalues")

    viewitems = operator.methodcaller("viewitems")
