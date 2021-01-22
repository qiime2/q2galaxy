import sys
import textwrap
import tempfile

import qiime2
import qiime2.util
import qiime2.sdk as sdk

from q2galaxy.core.builtins import builtin_map
from q2galaxy.core.util import get_mystery_stew

GALAXY_TRIMMED_STRING_LEN = 255
MISC_INFO_WIDTH = 38


def _get_plugin(plugin_id):
    if plugin_id == 'mystery_stew':
        return get_mystery_stew()
    else:
        pm = sdk.PluginManager()
        return pm.get_plugin(id=plugin_id)


def _error_handler(header=''):
    def _decorator(function):
        def wrapped(*args, _stdio=(None, None), **kwargs):
            try:
                out, err = _stdio
                with qiime2.util.redirected_stdio(stdout=out, stderr=err):
                    return function(*args, **kwargs)
            except Exception as e:
                lines = (header + str(e)).split('\n')  # respect newlines
                error_lines = []
                for line in lines:
                    error_lines.extend(textwrap.wrap(line, MISC_INFO_WIDTH))
                # Fill the TrimmedString(255) with empty characters. This will
                # be stripped in the UI, but will prevent other parts of stdio
                # from being sent by the API
                error_lines.append(" " * GALAXY_TRIMMED_STRING_LEN)
                # trailing sad face (prevent stderr from showing up
                # immediately after, doubling the error message)
                error_lines.append(":(")
                misc_info = '\n'.join(error_lines)

                print(misc_info, file=sys.stdout)
                print(misc_info, file=sys.stderr)
                _print_stdio(_stdio)

                raise  # finish with traceback and thus exit

        return wrapped
    return _decorator


def _print_stdio(stdio):
    out, err = stdio
    out.seek(0)
    err.seek(0)
    for line in out:  # loop, just in case it's very big (like MAFFT)
        print(line.decode('utf8'), file=sys.stdout, end='')

    for line in err:
        print(line.decode('utf8'), file=sys.stderr, end='')


@_error_handler(header="Unexpected error finding the action in q2galaxy: ")
def _get_action(plugin_id, action_id):
    plugin = _get_plugin(plugin_id)
    action = plugin.actions[action_id]

    return action


@_error_handler(header="Unexpected error loading arguments in q2galaxy: ")
def _convert_arguments(signature, inputs):
    processed_inputs = {}

    all_inputs_params = {}
    all_inputs_params.update(signature.parameters)
    all_inputs_params.update(signature.inputs)
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
                elif k in signature.inputs:
                    new_list = [sdk.Artifact.load(v) for v in inputs[k]]
                else:
                    new_list = inputs[k]

                processed_inputs[k] = new_list
            elif type_.name == 'Set':
                if qiime2.sdk.util.is_metadata_type(type_):
                    new_set = \
                        set(_convert_metadata(type_, v) for v in inputs[k])
                elif k in signature.inputs:
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
        elif k in signature.inputs:
            processed_inputs[k] = sdk.Artifact.load(v)
        else:
            processed_inputs[k] = v

    return processed_inputs


@_error_handler(header="This plugin encountered an error:\n")
def _execute_action(action, action_kwargs):
    for param, arg in action_kwargs.items():
        pretty_arg = repr(arg)
        if isinstance(arg, qiime2.sdk.Result):
            pretty_arg = arg.uuid
        line = f"{param}: {pretty_arg}"
        print(line, file=sys.stdout, end=('\n\n' if len(line) > MISC_INFO_WIDTH
                                          else '\n'))
    print(" " * GALAXY_TRIMMED_STRING_LEN)  # see _error_handler for rational

    return action(**action_kwargs)


@_error_handler(header="Unexpected error saving results in q2galaxy: ")
def _save_results(results):
    for name, result in zip(results._fields, results):
        location = result.save(name)
        print(f"Saved {result.type} to: {location}", file=sys.stdout)


def action_runner(plugin_id, action_id, inputs):
    out = tempfile.NamedTemporaryFile(prefix='q2galaxy-stdout-', suffix='.log')
    err = tempfile.NamedTemporaryFile(prefix='q2galaxy-stderr-', suffix='.log')
    # Each helper below is decorated to accept stdout and stderr, the goal is
    # to catch issues and promote the error message to the start of stdout and
    # stderr so that Galaxy's misc_info block will be the most relevant info.
    # Otherwise, you tend to end up with a traceback or the start of stdout
    # for noisy actions. To preserve stdout and stderr, we do want to log them
    # and then emit them at the end after writing out the relevant error first
    with out as out, err as err:
        stdio = (out, err)
        action = _get_action(plugin_id, action_id,
                             _stdio=stdio)
        action_kwargs = _convert_arguments(action.signature, inputs,
                                           _stdio=stdio)
        results = _execute_action(action, action_kwargs,
                                  _stdio=stdio)
        _save_results(results,
                      _stdio=stdio)

        # Everything has gone well so far, print the final contents
        _print_stdio(stdio)


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
