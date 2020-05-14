import os

import qiime2.sdk as sdk


def action_runner(plugin_id, action_id, inputs):
    pm = sdk.PluginManager()
    plugin = pm.get_plugin(id=plugin_id)
    action = plugin.actions[action_id]

    # This is sloppy and should probably be handled higher up by passing inputs
    # and params to this function as seperate entities in the first place
    params = {}
    to_remove = []
    for name, input_ in inputs.items():
        if not os.path.exists(str(input_)):
            params[name] = input_
            to_remove.append(name)

    for name in to_remove:
        inputs.pop(name)

    inputs = {k: sdk.Artifact.load(v) for k, v in inputs.items()
              if v is not None}

    results = action(**inputs, **params)

    for name, result in zip(results._fields, results):
        result.save(name)


def get_version(plugin_id):
    pm = sdk.PluginManager()
    plugin = pm.get_plugin(id=plugin_id)
    return plugin.version
