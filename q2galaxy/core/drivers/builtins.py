import os
import distutils

import qiime2

from q2galaxy.core.drivers.stdio import error_handler, stdio_files


def builtin_runner(action_id, inputs):
    with stdio_files() as stdio:
        tool = _get_tool(action_id,
                         _stdio=stdio)
        tool(inputs, stdio=stdio)


@error_handler("Unexpected error finding tool: ")
def _get_tool(action_id):
    builtin_map = {
        'import': import_data,
        'export': export_data,
        'qza_to_tabular': qza_to_tabular
    }
    try:
        return builtin_map[action_id]
    except KeyError:
        raise ValueError(f"{action_id} does not exist.")


def import_data(inputs, stdio):
    raise NotImplementedError("TODO")
    # if input_format == 'None':
    #     input_format = None
    # artifact = qiime2.sdk.Artifact.import_data(type, input_path,
    #                                            view_type=input_format)
    # artifact.save('imported')


def export_data(inputs, stdio):
    output_format, result = _export_get_args(inputs,
                                             _stdio=stdio)
    output_format = _export_transform(result, output_format,
                                      _stdio=stdio)
    _export_save(output_format,
                 _stdio=stdio)


def qza_to_tabular(inputs, stdio):
    raise NotImplementedError("TODO")


@error_handler(header='Unexpected error collecting arguments: ')
def _export_get_args(inputs):
    input_ = inputs['input']
    output_format = inputs['fmt_finder']['output_format']

    if output_format == 'None':
        output_format = None
    else:
        output_format = qiime2.sdk.parse_format(output_format)

    result = qiime2.sdk.Result.load(input_)

    return output_format, result


@error_handler(header='Error converting format:\n')
def _export_transform(result, output_format):
    if output_format is None:
        result.export_data(os.getcwd())
        return None

    return result.view(output_format)


@error_handler(header='Unexpected error saving output: ')
def _export_save(format_obj):
    if format_obj is None:
        pass  # from default output_format in _export_transform (return None)
    elif format_obj.path.is_dir():
        distutils.dir_util.copy_tree(str(format_obj), os.getcwd())
    else:
        qiime2.util.duplicate(str(format_obj), format_obj.path.name)
