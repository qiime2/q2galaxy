import qiime2.sdk as sdk

def action_runner(plugin_id, action_id, inputs):
    pm = sdk.PluginManager()
    plugin = pm.plugins[plugin_id.replace('-', '_')]
    action = plugin.actions[action_id]

    inputs = {k: sdk.Artifact.load(v) for k, v in inputs.items()}

    results = action(**inputs)

    for name, result in zip(result._fields, result):
        result.save(name)

def get_version(plugin_id):
    pm = sdk.PluginManager()
    plugin = pm.plugins[plugin_id.replace('-', '_')]
    return plugin.version
