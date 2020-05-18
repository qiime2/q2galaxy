import os

import qiime2
from qiime2.plugin import Metadata, MetadataColumn
import qiime2.sdk as sdk


def action_runner(plugin_id, action_id, inputs):
    pm = sdk.PluginManager()
    plugin = pm.get_plugin(id=plugin_id)
    action = plugin.actions[action_id]

    # TODO: This is sloppy and should probably be handled higher up by passing
    # inputs and params to this function as seperate entities in the first
    # place
    params = {}
    to_remove = []
    for name, input_ in inputs.items():
        if not os.path.exists(str(input_)):
            params[name] = input_
            to_remove.append(name)

    for name in to_remove:
        inputs.pop(name)

    metadata_inputs = {}
    to_remove = []
    all_inputs_params = {}
    all_inputs_params.update(action.signature.parameters)
    all_inputs_params.update(action.signature.inputs)
    for key, value in inputs.items():
        type_ = all_inputs_params[key].qiime_type
        if type_ == Metadata or type_ == MetadataColumn:
            metadata_inputs[key] = _convert_metadata(type_, inputs[key])
            to_remove.append(key)

    for name in to_remove:
        inputs.pop(name)

    inputs = {k: sdk.Artifact.load(v) for k, v in inputs.items()
              if v is not None}

    inputs.update(metadata_inputs)

    results = action(**inputs, **params)

    for name, result in zip(results._fields, results):
        result.save(name)


def get_version(plugin_id):
    pm = sdk.PluginManager()
    plugin = pm.get_plugin(id=plugin_id)
    return plugin.version


def _convert_metadata(input_, value):
    if input_ == 'MetadataColumn':
        value, column = value
    fp = value

    try:
        artifact = qiime2.Artifact.load(fp)
    except Exception:
        try:
            metadata = qiime2.Metadata.load(fp)
        except Exception as e:
            raise ValueError("There was an issue with loading the file %s as "
                             "metadata:" % fp) from e
    else:
        try:
            metadata = artifact.view(qiime2.Metadata)
        except Exception as e:
            raise ValueError("There was an issue with viewing the artifact "
                             "%s as QIIME 2 Metadata:" % fp) from e

    if input_ != 'MetadataColumn':
        return metadata
    else:
        try:
            metadata_column = metadata.get_column(column)
        except Exception:
            raise ValueError("There was an issue with retrieving column %r "
                             "from the metadata." % column)

        if metadata_column not in input_:
            raise ValueError("Metadata column is of type %r, but expected %r."
                             % (metadata_column, input_.fields[0]))

        return metadata_column
