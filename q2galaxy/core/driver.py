import qiime2
import qiime2.sdk as sdk

from q2galaxy.core.builtins import builtin_map
from q2galaxy.core.util import get_mystery_stew


def _get_plugin(plugin_id):
    if plugin_id == 'mystery_stew':
        return get_mystery_stew()
    else:
        pm = sdk.PluginManager()
        return pm.get_plugin(id=plugin_id)


def action_runner(plugin_id, action_id, inputs):
    plugin = _get_plugin(plugin_id)
    action = plugin.actions[action_id]

    processed_inputs = {}

    all_inputs_params = {}
    all_inputs_params.update(action.signature.parameters)
    all_inputs_params.update(action.signature.inputs)
    for k, v in inputs.items():
        try:
            type_ = all_inputs_params[k].qiime_type
        # If we had a metadata column arg then the extra arg generated to
        # accept the column specifier won't be in the signature and should be
        # skipped
        except KeyError as e:
            if '_Column' in str(e):
                continue
            else:
                raise(e)

        if v is None or v == 'None':
            processed_inputs[k] = None
        elif qiime2.sdk.util.is_collection_type(type_):
            inputs[k] = inputs[k].split(',')

            if type_.name == 'List':
                if qiime2.sdk.util.is_metadata_type(type_):
                    new_list = [_convert_metadata(type_, v) for v in inputs[k]]
                elif k in action.signature.inputs:
                    new_list = [sdk.Artifact.load(v) for v in inputs[k]]
                else:
                    new_list = inputs[k]

                processed_inputs[k] = new_list
            elif type_.name == 'Set':
                if qiime2.sdk.util.is_metadata_type(type_):
                    new_set = \
                        set(_convert_metadata(type_, v) for v in inputs[k])
                elif k in action.signature.inputs:
                    new_set = set(sdk.Artifact.load(v) for v in inputs[k])
                else:
                    new_set = set(inputs[k])

                processed_inputs[k] = new_set
        elif qiime2.sdk.util.is_metadata_type(type_):
            if type_.name == 'MetadataColumn':
                value = (inputs[k], inputs[f'{k}_Column'])
            else:
                value = inputs[k]

            processed_inputs[k] = _convert_metadata(type_, value)
        elif k in action.signature.inputs:
            processed_inputs[k] = sdk.Artifact.load(v)
        else:
            processed_inputs[k] = v

    results = action(**processed_inputs)

    for name, result in zip(results._fields, results):
        result.save(name)


def builtin_runner(action_id, inputs):
    action = builtin_map[action_id]
    result = action(**inputs)

    if action_id == 'import_data':
        result.save('imported')


def get_version(plugin_id):
    plugin = _get_plugin(plugin_id)
    return plugin.version


def _convert_metadata(input_, value):
    if input_.name == 'MetadataColumn':
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

    if input_.name != 'MetadataColumn':
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
