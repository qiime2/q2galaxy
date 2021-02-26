# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import q2galaxy
from q2galaxy.core.util import XMLNode
from q2galaxy.core.templaters.common import make_tool_name_from_id


def make_builtin_to_tabular(meta, tool_id):
    tool = XMLNode('tool', id=tool_id, name=make_tool_name_from_id(tool_id),
                   version=q2galaxy.__version__)
    return tool
