# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os
import sys
import tempfile
import distutils

import qiime2
import qiime2.sdk
import qiime2.util

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
    type_, format_, files_to_move = _import_get_args(inputs,
                                                     _stdio=stdio)
    artifact = _import_name_data(type_, format_, files_to_move,
                                 _stdio=stdio)
    _import_save(artifact,
                 _stdio=stdio)


@error_handler(header='Unexpected error collecting arguments: ')
def _import_get_args(inputs):
    type_ = qiime2.sdk.parse_type(inputs.pop('type'))
    format_ = qiime2.sdk.parse_format(inputs.pop('format'))
    print(f'｢type: {type_}｣', file=sys.stdout)
    print(f'｢format: {format_.__name__}｣', file=sys.stdout)

    files_to_move = []
    for key, value in inputs.items():
        if not key.startswith('import'):
            raise ValueError(f"Unknown instruction in JSON: {key}")
        elif key == 'import':
            # leave name as is, it's a FileFormat not a Directory Attr
            files_to_move.append((value['data'], value['data']))
        else:
            _, attr_name = key.split("_")
            if 'elements' in value:
                ext = value.get('ext', '')
                files_to_move.extend([
                    (v['data'], v['name'] + ext) for v in value['elements']])
            else:
                files_to_move.append((value['data'], value['name']))

    return type_, format_, files_to_move


@error_handler(header='Unexpected error importing data: ')
def _import_name_data(type_, format_, files_to_move):
    if len(files_to_move) == 1:
        path = files_to_move[0][1]
        return qiime2.Artifact.import_data(type_, path, view_type=format_)

    with tempfile.TemporaryDirectory(prefix='q2galaxy-import',
                                     dir=os.getcwd()) as dir_:
        for src, dst in files_to_move:
            qiime2.util.duplicate(src, os.path.join(dir_, dst))
        return qiime2.Artifact.import_data(type_, dir_, view_type=format_)


@error_handler(header='Unexpected error saving QZA: ')
def _import_save(artifact):
    artifact.save('imported_data')


def export_data(inputs, stdio):
    output_format, result = _export_get_args(inputs,
                                             _stdio=stdio)
    output_format = _export_transform(result, output_format,
                                      _stdio=stdio)
    _export_save(output_format,
                 _stdio=stdio)


@error_handler(header='Unexpected error collecting arguments: ')
def _export_get_args(inputs):
    input_ = inputs['input']
    output_format = inputs['fmt_finder']['output_format']

    if output_format == 'None':
        output_format = None
    else:
        output_format = qiime2.sdk.parse_format(output_format)

    # TODO: Result.load will die if the format is unknown, there may be a
    # better way to handle unkown /data/ directories
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


def qza_to_tabular(inputs, stdio):
    raise NotImplementedError("TODO")
