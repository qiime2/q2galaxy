# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import sys

import qiime2
import qiime2.sdk as sdk

from q2galaxy.core.util import get_mystery_stew
from q2galaxy.core.drivers.stdio import (
    error_handler, stdio_files, GALAXY_TRIMMED_STRING_LEN)


def action_runner(plugin_id, action_id, inputs):
    # Each helper below is decorated to accept stdout and stderr, the goal is
    # to catch issues and promote the error message to the start of stdout and
    # stderr so that Galaxy's misc_info block will be the most relevant info.
    # Otherwise, you tend to end up with a traceback or the start of stdout
    # for noisy actions. To preserve stdout and stderr, we do want to log them
    # and then emit them at the end after writing out the relevant error first
    with stdio_files() as stdio:
        action = _get_action(plugin_id, action_id,
                             _stdio=stdio)
        action_kwargs = _convert_arguments(action.signature, inputs,
                                           _stdio=stdio)
        results = _execute_action(action, action_kwargs,
                                  _stdio=stdio)
        _save_results(results,
                      _stdio=stdio)


def get_version(plugin_id):
    plugin = _get_plugin(plugin_id)
    return plugin.version


def _get_plugin(plugin_id):
    if plugin_id == 'mystery_stew':
        return get_mystery_stew()
    else:
        pm = sdk.PluginManager()
        return pm.get_plugin(id=plugin_id)


@error_handler(header="Unexpected error finding the action in q2galaxy: ")
def _get_action(plugin_id, action_id):
    plugin = _get_plugin(plugin_id)
    action = plugin.actions[action_id]

    return action


@error_handler(header="Unexpected error loading arguments in q2galaxy: ")
def _convert_arguments(signature, inputs):
    processed_inputs = {}

    all_inputs_params = {}
    all_inputs_params.update(signature.parameters)
    all_inputs_params.update(signature.inputs)
    for k, v in inputs.items():
        type_ = all_inputs_params[k].qiime_type

        if v is None:
            processed_inputs[k] = None

        elif qiime2.sdk.util.is_collection_type(type_):
            if k in signature.inputs:
                processed_inputs[k] = [sdk.Artifact.load(x) for x in v]
            elif v == []:
                if signature.parameters[k].has_default():
                    processed_inputs[k] = signature.parameters[k].default
                else:
                    raise NotImplementedError("Empty list given, but no"
                                              " default can be used")
            else:
                processed_inputs[k] = v

            if type_.name == 'Set' and processed_inputs[k] is not None:
                processed_inputs[k] = set(processed_inputs[k])

        elif qiime2.sdk.util.is_metadata_type(type_):
            processed_inputs[k] = _convert_metadata(type_, inputs[k], k)

        elif k in signature.inputs:
            processed_inputs[k] = sdk.Artifact.load(v)

        else:
            processed_inputs[k] = v

    return processed_inputs


@error_handler(header="This plugin encountered an error:\n")
def _execute_action(action, action_kwargs):
    for param, arg in action_kwargs.items():
        pretty_arg = repr(arg)
        if isinstance(arg, qiime2.sdk.Result):
            pretty_arg = str(arg.uuid)
        elif isinstance(arg, qiime2.Metadata):
            pretty_arg = "<Metadata>"
        elif isinstance(arg, list) or isinstance(arg, set):
            if len(arg) > 0 and isinstance(list(arg)[0], qiime2.sdk.Result):
                pretty_arg = ',\n'.join(str(a.uuid) for a in arg)
            else:
                pretty_arg = ', '.join(repr(a) for a in arg)
        line = f'｢{param}: {pretty_arg}｣'
        print(line, file=sys.stdout, flush=True)
    # see _error_handler for rational
    print(" " * GALAXY_TRIMMED_STRING_LEN, file=sys.stdout, flush=True)

    return action(**action_kwargs)


@error_handler(header="Unexpected error saving results in q2galaxy: ")
def _save_results(results):
    for name, result in zip(results._fields, results):
        location = result.save(name)
        print(f"Saved {result.type} to: {location}", file=sys.stdout)


def _convert_metadata(input_, value, param):
    if not value:
        return None

    if input_.name == 'MetadataColumn':
        if value['type'] == 'none':
            return None
        value = [value]

    mds = []
    for entry in value:
        if entry['type'] == 'tsv':
            try:
                md = qiime2.Metadata.load(entry['source'])
            except Exception as e:
                raise ValueError(
                    "There was an issue with loading the file provided to %r"
                    " as metadata:" % param) from e
        else:
            art = qiime2.Artifact.load(entry['source'])
            try:
                md = art.view(qiime2.Metadata)
            except Exception as e:
                raise ValueError(
                    "There was an issue with viewing the artifact provided to "
                    "%r as QIIME 2 Metadata:" % param) from e

        mds.append(md)

    if len(mds) > 1:
        return mds[0].merge(*mds[1:])
    else:
        metadata = mds[0]

    if input_.name == 'MetadataColumn':
        try:
            if value[0]['type'] == 'qza':
                column = value[0]['column']
            else:
                # Galaxy writes data_columns as lists in the JSON for reasons
                # I assume.
                column = value[0]['column'][0]
                # galaxy is 1-indexed and includes the ID column, so subtract 2
                column = list(metadata.columns.keys())[int(column) - 2]
            metadata_column = metadata.get_column(column)
        except Exception:
            raise ValueError("There was an issue with retrieving column %r "
                             "from %r." % (column, param))

        if metadata_column not in input_:
            raise ValueError("Metadata column is of type %r, but expected %r."
                             % (metadata_column, input_.fields[0]))

        return metadata_column

    else:
        return metadata
