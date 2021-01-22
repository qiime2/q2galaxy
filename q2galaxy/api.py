import os

import qiime2.sdk as _sdk

import q2galaxy.core.templating as _templating
import q2galaxy.core.environment as _environment
import q2galaxy.core.usage as _usage


def action_to_galaxy_xml(action):
    meta = _environment.find_conda_meta()
    plugin = _sdk.PluginManager().get_plugin(id=action.id)

    return _templating.make_tool(meta, plugin, action)


def plugin_to_galaxy_xml(plugin):
    action_wrappers = {}
    meta = _environment.find_conda_meta()
    for action in plugin.actions.values():
        key = (plugin.id, action.id)
        action_wrappers[key] = _templating.make_tool(meta, plugin, action)

    return action_wrappers


def template_plugin_iter(plugin, directory):
    suite_name = f'suite_qiime2_{plugin.id}'
    tool_dir = os.path.join(directory, suite_name, '')
    if not os.path.exists(tool_dir):
        os.mkdir(tool_dir)
        yield {'status': 'created', 'type': 'directory', 'path': tool_dir}

    for action in plugin.actions.values():
        yield from template_tool_iter(plugin, action, tool_dir)


def template_tool_iter(plugin, action, directory):
    meta = _environment.find_conda_meta()

    filename = _templating.get_tool_id(plugin, action) + '.xml'
    path = os.path.join(directory, filename)
    is_existing = os.path.exists(path)

    test_dir = os.path.join(directory, 'test-data', '')
    if not os.path.exists(test_dir):
        os.mkdir(test_dir)
        yield {'status': 'created', 'type': 'directory', 'path': test_dir}

    tool = _templating.make_tool(meta, plugin, action)
    _templating.write_tool(tool, path)
    yield from _usage.collect_test_data(action, test_dir)

    if not is_existing:
        yield {'status': 'created', 'type': 'file', 'path': path}
    else:
        yield {'status': 'updated', 'type': 'file', 'path': path}


def template_all_iter(directory):
    pm = _sdk.PluginManager()
    for plugin in pm.plugins.values():
        yield from template_plugin_iter(plugin, directory)


def template_plugin(plugin, directory):
    for _ in template_plugin_iter(plugin, directory):
        pass


def template_tool(plugin, action, directory):
    for _ in template_tool_iter(plugin, action, directory):
        pass


def template_all(directory):
    for _ in template_all_iter(directory):
        pass
