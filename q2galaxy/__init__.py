# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from q2galaxy.api import (template_action, template_plugin, template_builtins,
                          template_all)


__version__ = '0.0.1'  # TODO: use versioneer
__all__ = ['template_action', 'template_plugin', 'template_builtins',
           'template_all']

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
