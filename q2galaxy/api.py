import os

import qiime2.sdk as _sdk

import q2galaxy.core.templating as _templating
import q2galaxy.core.environment as _environment


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
    meta = _environment.find_conda_meta()

    for action in plugin.actions.values():
        filename = _templating.get_tool_id(action) + '.xml'
        path = os.path.join(directory, filename)
        exists = os.path.exists(path)
        tool = _templating.make_tool(meta, plugin, action)
        _templating.write_tool(tool, path)
        if not exists:
            yield {'status': 'created', 'path': path}
        else:
            yield {'status': 'updated', 'path': path}


def template_all_iter(directory):
    pm = _sdk.PluginManager()
    for plugin in pm.plugins.values():
        yield from template_plugin_iter(plugin, directory)


def template_plugin(plugin, directory):
    for _ in template_plugin_iter(directory, plugin):
        pass


def template_all(directory):
    for _ in template_all_iter(directory):
        pass
