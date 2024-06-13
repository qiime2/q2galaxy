# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from qiime2.sdk import PluginManager

from q2galaxy.core.util import XMLNode
from q2galaxy.core.templaters.common import (make_builtin_version,
                                             make_tool_name_from_id,
                                             make_requirements,
                                             make_citations,
                                             make_xrefs)


def make_builtin_import_fastq(meta, tool_id):
    pm = PluginManager()

    plugins = set()
    for record in sorted(pm.get_semantic_types().values(),
                         key=lambda x: str(x.semantic_type)):
        plugins.add(record.plugin)

    tool = XMLNode('tool', id=tool_id, name=make_tool_name_from_id(tool_id),
                   version=make_builtin_version(plugins))
    tool.append(_make_input())
    tool.append(_make_output())
    tool.append(
        XMLNode('command', "q2galaxy run tools import-fastq '$inputs'"))
    tool.append(XMLNode('description',
                        'Import fastq data into a QIIME 2 artifact'))
    tool.append(_make_config())
    tool.append(make_citations())
    tool.append(make_requirements(meta, *[p.project_name for p in plugins]))
    tool.append(make_xrefs())
    return tool


def _make_config():
    configfiles = XMLNode('configfiles')
    configfiles.append(XMLNode(
        'inputs', name='inputs', data_style='staging_path_and_source_path'))
    return configfiles


def _make_input():
    inputs = XMLNode('inputs')
    inputs.append(XMLNode(
        'param', name='import', type='data_collection',
        collection_type='list, list:paired'))
    return inputs


def _make_output():
    outputs = XMLNode('outputs')
    outputs.append(XMLNode(
        'data', name='imported-data', format='qza',
        from_work_dir='imported_data.qza'))
    return outputs
