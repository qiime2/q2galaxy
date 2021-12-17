# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os

import qiime2.sdk as _sdk

import q2galaxy.core.util as _util
import q2galaxy.core.templaters as _templaters
import q2galaxy.core.environment as _environment
import q2galaxy.core.usage as _usage
from q2galaxy.api.usage import GalaxyRSTInstructionsUsage


__all__ = ['template_action_iter', 'template_plugin_iter',
           'template_builtins_iter', 'template_all_iter', 'template_action',
           'template_plugin', 'template_builtins', 'template_all',
           'GalaxyRSTInstructionsUsage']


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
    suite_name = f'suite_qiime2_{plugin.id.replace("_", "-")}'
    suite_dir = os.path.join(directory, suite_name, '')

    if plugin.actions:
        yield from _template_dir_iter(suite_dir)
    for action in plugin.actions.values():
        yield from template_action_iter(plugin, action, suite_dir)


def template_builtins_iter(directory):
    meta = _environment.find_conda_meta()

    suite_name = 'suite_qiime2_tools'
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
