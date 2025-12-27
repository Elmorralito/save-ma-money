"""
Package metadata for papita_txnsplugins.

This module provides access to metadata information about the papita_txnsplugins
package extracted from Poetry configuration. It exposes version, author information,
and other package metadata that can be used by the package itself and other dependent
modules.

Attributes:
    __configs__ (dict): Dictionary containing all Poetry configuration values.
    __authors__ (dict): Dictionary containing author information from Poetry config.
    __version__ (str): Package version string, with any 'v' prefix removed.
"""

from papita_txnsmodel.__meta__ import get_poetry_configs

__configs__ = get_poetry_configs(module_path=__file__)

__authors__ = __configs__.get("authors", {})

__version__ = __configs__.get("version", "0.0.1").replace("v", "")
