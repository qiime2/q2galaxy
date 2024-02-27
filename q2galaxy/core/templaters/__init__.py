# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import types

from q2galaxy.core.templaters.action import make_tool
from q2galaxy.core.templaters.common import make_tool_id
from q2galaxy.core.templaters.import_data import make_builtin_import
from q2galaxy.core.templaters.import_fastq_data import \
    make_builtin_import_fastq
from q2galaxy.core.templaters.export_data import make_builtin_export
# from q2galaxy.core.templaters.qza_to_tabular import make_builtin_to_tabular

from q2galaxy.core.drivers.builtins import IMPORT_FASTQ

BUILTINS = {
    make_tool_id('tools', 'import'): make_builtin_import,
    make_tool_id('tools', 'export'): make_builtin_export,
    # make_tool_id('tools', 'qza_to_tabular'): make_builtin_to_tabular,
}

if IMPORT_FASTQ:
    BUILTINS[make_tool_id('tools', 'import_fastq')] = make_builtin_import_fastq

BUILTIN_MAKERS = types.MappingProxyType(BUILTINS)


__all__ = ['make_tool', 'make_tool_id', 'BUILTIN_MAKERS']
