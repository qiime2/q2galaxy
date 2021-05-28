# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import qiime2.sdk as sdk
import qiime2.plugin.model as model
from qiime2.sdk.plugin_manager import GetFormatFilters

from q2galaxy.core.util import XMLNode, galaxy_esc, pretty_fmt_name, rst_header
from q2galaxy.core.templaters.common import (
    make_builtin_version, make_requirements, make_tool_name_from_id,
    make_config, make_citations, make_formats_help)


def make_builtin_export(meta, tool_id):
    pm = sdk.PluginManager()
    inputs = XMLNode('inputs')

    # This also works for qzvs even though the format just says qza so. . .
    qza_input = 'input'
    inputs.append(XMLNode('param', format="qza", name=qza_input, type='data',
                          label='input: The path to the artifact you '
                          'want to export'))

    type_peek = XMLNode('param', type='select', name='type_peek',
                        display='radio',
                        label="The type of your input qza is:")
    type_peek_opts = XMLNode('options')
    type_peek_filter = XMLNode('filter', type='data_meta', ref=qza_input,
                               key='semantic_type')
    type_peek_opts.append(type_peek_filter)
    type_peek.append(type_peek_opts)
    inputs.append(type_peek)

    fmt_peek = XMLNode('param', type='select', name='fmt_peek',
                       display='radio', label="The current QIIME 2 format is:")
    fmt_peek_opts = XMLNode('options')
    fmt_peek_filter = XMLNode('filter', type='data_meta', ref=qza_input,
                              key='format')
    fmt_peek_opts.append(fmt_peek_filter)
    fmt_peek.append(fmt_peek_opts)
    inputs.append(fmt_peek)

    conditional = XMLNode('conditional', name='fmt_finder')
    inputs.append(conditional)

    type_ = XMLNode('param', name='type', type='select',
                    label=('To change the format, select the type indicated'
                           ' above:'))
    type_.append(XMLNode('option', 'export as is (no conversion)',
                         value='None', selected='true'))
    conditional.append(type_)

    when = XMLNode('when', value="None")
    select = XMLNode('param', type='select', name='output_format',
                     label="QIIME 2 file format to convert to:")

    select.append(XMLNode('option', 'export as is (no conversion)',
                          value='None', selected='true'))
    when.append(select)
    conditional.append(when)

    plugins = set()
    known_formats = set()
    for record in sorted(pm.get_semantic_types().values(),
                         key=lambda x: str(x.semantic_type)):
        plugins.add(record.plugin)

        type_option = XMLNode('option', str(record.semantic_type),
                              value=galaxy_esc(str(record.semantic_type)))
        type_.append(type_option)

        when = XMLNode('when', value=galaxy_esc(str(record.semantic_type)))
        select = XMLNode('param', type='select', name='output_format',
                         label="QIIME 2 file format to convert to:")

        select.append(XMLNode('option', 'export as is (no conversion)',
                      value='None', selected='true'))

        for fmt_rec in sorted(
                pm.get_formats(filter=GetFormatFilters.EXPORTABLE,
                               semantic_type=record.semantic_type).values(),
                key=lambda x: x.format.__name__):
            plugins.add(fmt_rec.plugin)
            known_formats.add(fmt_rec.format)

            if not issubclass(fmt_rec.format,
                              model.SingleFileDirectoryFormatBase):
                option = XMLNode('option', pretty_fmt_name(fmt_rec.format),
                                 value=galaxy_esc(fmt_rec.format.__name__))
                select.append(option)

        when.append(select)
        conditional.append(when)

    outputs = XMLNode('outputs')

    # default collection:
    collection = XMLNode('collection', name='exported', type='list',
                         label='${tool.name} on ${on_string} as ${fmt_peek}')

    _filter_set = repr({galaxy_esc(x.__name__) for x in known_formats})
    collection.append(XMLNode('filter', "fmt_finder['output_format'] == 'None'"
                              f" and fmt_peek not in {_filter_set}"))
    collection.append(XMLNode('discover_datasets', visible='false',
                              pattern='__designation_and_ext__'))
    outputs.append(collection)

    for fmt in sorted(known_formats, key=lambda x: x.__name__):
        esc_fmt = galaxy_esc(fmt.__name__)
        filter_exp = (f"fmt_finder['output_format'] == '{esc_fmt}'"
                      " or (fmt_finder['output_format'] == 'None' and fmt_peek"
                      f" == '{esc_fmt}')")
        label = '${tool.name} on ${on_string} as ' + fmt.__name__
        if issubclass(fmt, model.DirectoryFormat):
            dyn_data = None
            for field in fmt._fields:  # file attrs of the dirfmt
                file_attr = getattr(fmt, field)
                pattern, has_ext = pathspec_to_galaxy_regex(file_attr.pathspec)
                extras = {}
                if not has_ext:
                    if issubclass(file_attr.format, model.TextFileFormat):
                        extras['ext'] = 'txt'
                    else:
                        extras['ext'] = 'data'

                if isinstance(file_attr, model.FileCollection):
                    col = XMLNode('collection', type='list',
                                  name='_'.join([esc_fmt, file_attr.name]),
                                  label=label + f' ({file_attr.name})')
                    col.append(XMLNode('filter', filter_exp))
                    col.append(XMLNode('discover_datasets', visible='false',
                                       pattern=pattern, **extras))
                    outputs.append(col)
                else:
                    if dyn_data is None:
                        # init a root for all of the discoverable datasets
                        dyn_data = XMLNode('data', name=esc_fmt, label=label)
                        dyn_data.append(XMLNode('filter', filter_exp))
                        # only the first one, will take over the history item
                        extras['assign_primary_output'] = 'true'

                    dyn_data.append(XMLNode('discover_datasets',
                                            visible='true', pattern=pattern,
                                            **extras))
            if dyn_data is not None:
                outputs.append(dyn_data)
        else:
            # as it is not a directory, we don't know much about the original
            # filename anymore, so we will let galaxy sort it out
            # .gz may be considered the format instead of fastq.gz, but users
            # can always re-sniff a history item for the format
            collection = XMLNode('data', name=esc_fmt, label=label)
            collection.append(XMLNode('filter', filter_exp))
            collection.append(XMLNode('discover_datasets', visible='true',
                                      assign_primary_output='true',
                                      pattern='__designation_and_ext__'))
            outputs.append(collection)

    tool = XMLNode('tool', id=tool_id, name=make_tool_name_from_id(tool_id),
                   version=make_builtin_version(plugins))
    tool.append(XMLNode('description', 'Export data from a QIIME 2 artifact'))
    tool.append(XMLNode('command', "q2galaxy run tools export '$inputs'"))
    tool.append(make_config())
    tool.append(inputs)
    tool.append(outputs)
    tool.append(make_citations())
    tool.append(make_requirements(meta, *[p.project_name for p in plugins]))
    tool.append(_make_help(known_formats))

    return tool


def pathspec_to_galaxy_regex(pathspec):
    if r'\.' in pathspec:
        delim = r'\.'  # It's a regex system! I know this!
    else:
        delim = '.'
    parts = pathspec.split(delim)

    if len(parts) == 1:
        return f'(?P<designation>{pathspec})', False

    if parts[-1] == 'gz' or parts[-1] == 'bz2':
        ext = delim.join(parts[-2:])
        rest = parts[:-2]
    else:
        ext = parts[-1]
        rest = parts[:-1]

    return f'(?P<designation>{delim.join(rest)})\\.(?P<ext>{ext})', True


def _make_help(formats):
    help_ = rst_header('QIIME 2: tools export', 1)
    help_ += "Export a QIIME 2 artifact to different formats\n"
    help_ += rst_header('Instructions', 2)
    help_ += _instructions
    help_ += make_formats_help(formats)

    return XMLNode('help', help_)


_instructions = """
TODO
"""
