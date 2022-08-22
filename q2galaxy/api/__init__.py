# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os

import lxml.etree as _xml

import qiime2.sdk as _sdk

import q2galaxy.core.util as _util
import q2galaxy.core.templaters as _templaters
import q2galaxy.core.environment as _environment
import q2galaxy.core.usage as _usage
from q2galaxy.api.usage import GalaxyRSTInstructionsUsage


__all__ = ['template_action_iter', 'template_plugin_iter',
           'template_builtins_iter', 'template_all_iter', 'template_action',
           'template_plugin', 'template_builtins', 'template_all',
           'GalaxyRSTInstructionsUsage', 'template_tool_conf']


_SUITE_PREFIX = 'suite_qiime2__'


def _template_dir_iter(directory):
    if not os.path.exists(directory):
        os.mkdir(directory)
        yield {'status': 'created', 'type': 'directory', 'path': directory}


def _template_tool_iter(tool, path):
    is_existing = os.path.exists(path)

    _util.write_tool(tool, path)

    if not is_existing:
        yield {'status': 'created', 'type': 'file', 'path': path}
    else:
        yield {'status': 'updated', 'type': 'file', 'path': path}


def template_action_iter(plugin, action, directory):
    meta = _environment.find_conda_meta()

    filename = _templaters.make_tool_id(plugin.id, action.id) + '.xml'
    filepath = os.path.join(directory, filename)
    test_dir = os.path.join(directory, 'test-data', '')

    tool = _templaters.make_tool(meta, plugin, action)

    yield from _template_tool_iter(tool, filepath)
    yield from _template_dir_iter(test_dir)
    yield from _usage.collect_test_data(action, test_dir)


def template_plugin_iter(plugin, directory):
    suite_name = _SUITE_PREFIX + plugin.id
    suite_dir = os.path.join(directory, suite_name, '')

    if plugin.actions:
        yield from _template_dir_iter(suite_dir)
    for action in plugin.actions.values():
        yield from template_action_iter(plugin, action, suite_dir)


def template_builtins_iter(directory):
    meta = _environment.find_conda_meta()

    suite_name = _SUITE_PREFIX + 'tools'
    suite_dir = os.path.join(directory, suite_name, '')
    yield from _template_dir_iter(suite_dir)

    for tool_id, tool_maker in _templaters.BUILTIN_MAKERS.items():
        path = os.path.join(suite_dir, tool_id + '.xml')
        tool = tool_maker(meta, tool_id)
        yield from _template_tool_iter(tool, path)


def template_all_iter(directory):
    pm = _sdk.PluginManager()
    for plugin in pm.plugins.values():
        yield from template_plugin_iter(plugin, directory)

    yield from template_builtins_iter(directory)


def template_action(plugin, action, directory):
    for _ in template_action_iter(plugin, action, directory):
        pass


def template_plugin(plugin, directory):
    for _ in template_plugin_iter(plugin, directory):
        pass


def template_builtins(directory):
    for _ in template_builtins_iter(directory):
        pass


def template_all(directory):
    for _ in template_all_iter(directory):
        pass


def template_tool_conf(directory, out_path):
    toolbox = _util.XMLNode('toolbox')

    section = _util.XMLNode('section', id='getext', name='Get Data')
    section.append(_util.XMLNode('tool', file='data_source/upload.xml'))
    toolbox.append(section)

    section = _util.XMLNode('section', id='qiime2__tools',
                            name='QIIME 2 Tools')

    suite_name = _SUITE_PREFIX + 'tools'
    suite_dir = os.path.join(directory, suite_name)
    for tool_id in _templaters.BUILTIN_MAKERS:
        path = os.path.join(suite_dir, tool_id + '.xml')
        section.append(_util.XMLNode('tool', file=path))

    toolbox.append(section)

    pm = _sdk.PluginManager()
    for plugin in sorted(pm.plugins.values(), key=lambda x: x.id):
        suite_name = _SUITE_PREFIX + plugin.id
        plugin_name = plugin.id.replace('_', '-')
        section = _util.XMLNode('section', id=suite_name,
                                name=f'QIIME 2 {plugin_name}')

        for action in sorted(plugin.actions.values(), key=lambda x: x.id):
            filename = _templaters.make_tool_id(plugin.id, action.id) + '.xml'
            path = os.path.join(directory, suite_name, filename)
            section.append(_util.XMLNode('tool', file=path))

        toolbox.append(section)

    with open(out_path, 'wb') as fh:
        _xml.indent(toolbox, ' ' * 4)
        fh.write(_xml.tostring(toolbox, pretty_print=True, encoding='utf-8',
                               xml_declaration=True))
