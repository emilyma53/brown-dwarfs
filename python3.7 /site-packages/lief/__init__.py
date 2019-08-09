#!/usr/bin/env python

import sys
import _pylief
from _pylief import *

__version__ = _pylief.__version__

if 1:
    sys.modules.setdefault("lief.PE", _pylief.PE)

if 1:
    sys.modules.setdefault("lief.ELF", _pylief.ELF)

    sys.modules.setdefault("lief.ELF.ELF32", _pylief.ELF.ELF32)
    sys.modules.setdefault("lief.ELF.ELF64", _pylief.ELF.ELF64)

if 1:
    sys.modules.setdefault("lief.MachO", _pylief.MachO)

if 1:
    sys.modules.setdefault("lief.OAT",  _pylief.OAT)

if 1:
    sys.modules.setdefault("lief.DEX",  _pylief.DEX)

if 1:
    sys.modules.setdefault("lief.VDEX",  _pylief.VDEX)

if 1:
    sys.modules.setdefault("lief.ART",  _pylief.ART)

sys.modules.setdefault("lief.Android",  _pylief.Android)

