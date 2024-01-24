# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from textwrap import dedent

import qiime2.plugin.model as model
import qiime2.sdk as sdk
from qiime2.sdk.plugin_manager import GetFormatFilters

from q2galaxy.core.util import (XMLNode, galaxy_esc, pretty_fmt_name,
                                galaxy_ui_var, rst_header)
from q2galaxy.core.templaters.common import (make_builtin_version,
                                             make_tool_name_from_id,
                                             make_requirements,
                                             make_citations,
                                             make_formats_help)


def make_builtin_import(meta, tool_id):
    pm = sdk.PluginManager()
    inputs = XMLNode('inputs')

    # Not a galaxy_ui_var() because this will be taken by name from the
    # Cheetah searchList  (see `def _inline_code` below)
    conditional = XMLNode('conditional', name='import_root')
    inputs.append(conditional)

    type_ = XMLNode('param', name='type', type='select',
                    label=('Type of data to import:'))
    type_.append(XMLNode('option', 'Select a QIIME 2 type to import.',
                         value='None'))
    conditional.append(type_)

    when = XMLNode('when', value="None")
    conditional.append(when)

    default_formats = _get_default_formats(pm)
    plugins = set()
    known_formats = set()
    for record in sorted(pm.get_semantic_types().values(),
                         key=lambda x: str(x.semantic_type)):
        plugins.add(record.plugin)

        type_option = XMLNode('option', str(record.semantic_type),
                              value=galaxy_esc(str(record.semantic_type)))
        type_.append(type_option)

        when = XMLNode('when', value=galaxy_esc(str(record.semantic_type)))

        fmt_conditional = XMLNode(
            'conditional', name=galaxy_ui_var(tag='cond', name='format'))
        select = XMLNode('param', type='select', name='format',
                         label="QIIME 2 file format to import from:")
        fmt_conditional.append(select)

        when.append(fmt_conditional)

        default_format = default_formats[record.semantic_type]
        seen_formats = set()
        for fmt_rec in sorted(
                pm.get_formats(filter=GetFormatFilters.IMPORTABLE,
                               semantic_type=record.semantic_type).values(),
                key=lambda x: x.format.__name__):
            if issubclass(fmt_rec.format,
                          model.SingleFileDirectoryFormatBase):
                # These are really just noise for the galaxy UI
                # an implicit transformation from the backing file format
                # is simpler and removes the redundancy
                fmt = fmt_rec.format.file.format
                plugin = fmt_rec.plugin
            else:
                fmt = fmt_rec.format
                plugin = fmt_rec.plugin

            if fmt not in seen_formats:
                plugins.add(plugin)
                known_formats.add(fmt)
                seen_formats.add(fmt)

                option = XMLNode('option', pretty_fmt_name(fmt),
                                 value=galaxy_esc(fmt.__name__),
                                 selected=str(fmt == default_format).lower())
                select.append(option)

                fmt_when = XMLNode('when',
                                   value=galaxy_esc(fmt.__name__))
                fmt_conditional.append(fmt_when)

                _add_format_ui(fmt_when, fmt)

        conditional.append(when)

    outputs = XMLNode('outputs')
    outputs.append(XMLNode('data', name='imported_data', format='qza',
                           from_work_dir='imported_data.qza'))

    tool = XMLNode('tool', id=tool_id, name=make_tool_name_from_id(tool_id),
                   version=make_builtin_version(plugins))

    tool.append(inputs)
    tool.append(outputs)
    tool.append(
        XMLNode('command', "q2galaxy run tools import '$inputs'",
                detect_errors="exit_code"))
    tool.append(_make_config())
    tool.append(XMLNode('description', 'Import data into a QIIME 2 artifact'))
    tool.append(make_citations())
    tool.append(make_requirements(meta, *[p.project_name for p in plugins]))
    tool.append(_make_help(known_formats))
    return tool


def _make_config():
    configfiles = XMLNode("configfiles")
    configfiles.append(XMLNode("inputs", name="inputs",
                               data_style="staging_path_and_source_path"))
    return configfiles


def _add_format_ui(root, format):
    if issubclass(format, model.DirectoryFormat):
        for field in format._fields:
            file_attr = getattr(format, field)

            if isinstance(file_attr, model.FileCollection):
                _add_collection_ui(root, file_attr)
            else:
                section = XMLNode(
                    "section", name=f'import_{file_attr.name}',
                    expanded='true', title=f'Import {file_attr.name}')
                _add_data_ui(section, file_attr)
                root.append(section)
    else:
        section = XMLNode("section", name='import', expanded='true',
                          title='Import')
        section.append(XMLNode('param', type='hidden', name='name',
                               value=galaxy_esc(None)))
        section.append(XMLNode('param', type='data', name='data',
                               format='data',
                               help=_format_help_text(format)))
        root.append(section)


def _add_collection_ui(root, file_attr):
    section = XMLNode("section", name=f'import_{file_attr.name}',
                      expanded='true', title=f'Import {file_attr.name}')
    conditional = XMLNode("conditional",
                          name=galaxy_ui_var(tag='cond', name=file_attr.name))
    select = XMLNode("param", type='select', label='Select a mechanism',
                     name=galaxy_ui_var(tag='select', name='picker'))
    select.append(XMLNode("option", "Use collection to import",
                          value='collection', selected='true'))
    select.append(XMLNode("option", "Associate individual files",
                          value='individual'))
    conditional.append(select)

    when_collection = XMLNode("when", value='collection')
    when_collection.append(
        XMLNode('param', type='data_collection', name='elements',
                help=_format_help_text(file_attr.format)
                + ' Elements must match regex:'
                  f' {_regex_xml_escape(file_attr.pathspec)}'))
    add_ext_cond = XMLNode("conditional",
                           name=galaxy_ui_var(tag='cond', name='add_ext'))
    ext_select = XMLNode("param", type='select', label='Append an extension?',
                         help='This is needed if your element identifiers lack'
                              ' one.',
                         name=galaxy_ui_var(tag='select', name='ext_pick'))
    ext_select.append(XMLNode("option", "No, use element identifiers as is",
                              value="no"))
    ext_select.append(XMLNode("option", "Yes, append an extension",
                              value="yes"))
    add_ext_cond.append(ext_select)

    ext_when = XMLNode("when", value="yes")
    ext_when.append(XMLNode("param", type='text', name='ext',
                            label="Extension to append (e.g. '.fastq.gz')"))
    add_ext_cond.append(ext_when)
    add_ext_cond.append(XMLNode("when", value="no"))
    when_collection.append(add_ext_cond)

    when_individual = XMLNode("when", value='individual')
    repeat = XMLNode("repeat", name='elements', min='1', title='Add Elements')
    _add_data_ui(repeat, file_attr)
    when_individual.append(repeat)

    conditional.append(when_collection)
    conditional.append(when_individual)

    section.append(conditional)
    root.append(section)


def _format_help_text(format):
    return (f'This data should be formatted as a {format.__name__}.'
            ' See the documentation below for more information.')


def _make_help(formats):
    help_ = rst_header('QIIME 2: tools import', 1)
    help_ += "Import data as a QIIME 2 artifact\n"
    help_ += rst_header('Instructions', 2)
    help_ += _instructions
    help_ += make_formats_help(formats)

    return XMLNode('help', help_)


def _guess_regex(pathspec):
    return r'\.' in pathspec or r'.*' in pathspec or r'.+' in pathspec


def _regex_xml_escape(regex):
    # Galaxy appears to double escape this by turning it into an HTML comment
    # instead of &gt; or friends. So use a Unicode hack to make it seem about
    # right.
    regex = regex.replace("<", "‹")
    regex = regex.replace(">", "›")
    return regex


def _add_data_ui(root, file_attr):
    name = XMLNode('param', type='text', name='name')
    if _guess_regex(file_attr.pathspec):
        name.set('help', 'Filename to import the data as. Must match'
                 f' regex: {_regex_xml_escape(file_attr.pathspec)}')
        name.append(XMLNode('validator', file_attr.pathspec, type='regex',
                            message='This filename doesn\'t match the regex.'))
    else:
        name.set('help', 'Filename to import the data as. You shouldn\'t need'
                 ' to change this unless something is wrong.')
        name.set('value', file_attr.pathspec)

    root.append(name)
    root.append(XMLNode('param', type='data', name='data', format='data',
                        help=_format_help_text(file_attr.format)))


def _get_default_formats(pm):
    default_formats = {}
    for rec in pm.type_formats:
        fmt = rec.format
        if issubclass(fmt, model.SingleFileDirectoryFormatBase):
            fmt = fmt.file.format
        for semantic_type in rec.type_expression:
            default_formats[semantic_type] = fmt

    return default_formats


_instructions = """
 1. Select the type you wish to import. If you are uncertain, consider what
    your next action would be and identify what type it requires.

 2. Identify which format will best suite the data you have available. Many
    types will have only a single format available. There is some documentation
    available below on the different formats, however there may not be
    very much documentation available for your format.

 3. For each part of the format, you will need to associate some data.

    a. If it is a simple format, you may just select the history dataset.
    b. If it is a more complex format, you will need to provide either a
       filename and history dataset, or a collection.
    c. For collections, they can be constructed via matching a regex against
       the names of the items in that collection. (You may need to append an
       extension if your collection's element IDs lack one.) Or you can
       provide individual history datasets with a filename as in the simpler
       cases.
"""
