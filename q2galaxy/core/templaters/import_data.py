import qiime2.plugin.model as model
import qiime2.sdk as sdk
from qiime2.sdk.plugin_manager import GetFormatFilters

from q2galaxy.core.util import XMLNode, galaxy_esc, pretty_fmt_name
from q2galaxy.core.templaters.common import (make_builtin_version,
                                             make_tool_name_from_id)


def make_builtin_import(meta, tool_id):
    pm = sdk.PluginManager()
    inputs = XMLNode('inputs')

    conditional = XMLNode('conditional', name='import_data')
    inputs.append(conditional)

    type_ = XMLNode('param', name='type', type='select',
                    label=('Type of data to import:'))
    type_.append(XMLNode('option', 'Select a QIIME 2 type to import.',
                         value='None'))
    conditional.append(type_)

    when = XMLNode('when', value="None")
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
        fmt_conditional = XMLNode('conditional', name='import_ui')
        select = XMLNode('param', type='select', name='input_format',
                         label="QIIME 2 file format to import from:")
        fmt_conditional.append(select)
        when.append(fmt_conditional)

        for fmt_rec in sorted(
                pm.get_formats(filter=GetFormatFilters.IMPORTABLE,
                               semantic_type=record.semantic_type).values(),
                key=lambda x: x.format.__name__):
            plugins.add(fmt_rec.plugin)
            known_formats.add(fmt_rec.format)

            if issubclass(fmt_rec.format,
                          model.SingleFileDirectoryFormatBase):
                continue

            option = XMLNode('option', pretty_fmt_name(fmt_rec.format),
                             value=galaxy_esc(fmt_rec.format.__name__))
            select.append(option)

            fmt_when = XMLNode('when',
                               value=galaxy_esc(fmt_rec.format.__name__))
            fmt_conditional.append(fmt_when)

            _add_format_ui(fmt_when, fmt_rec)

        conditional.append(when)

    outputs = XMLNode('outputs')
    outputs.append(XMLNode('data', name='imported_qza', type='qza'))

    tool = XMLNode('tool', id=tool_id, name=make_tool_name_from_id(tool_id),
                   version=make_builtin_version(plugins))

    tool.append(inputs)
    tool.append(outputs)
    tool.append(
        XMLNode('command', "q2galaxy run builtin import_data '$inputs'"))
    tool.append(_make_config())
    tool.append(XMLNode('description', 'Import data to Qiime2 artifacts'))
    tool.append(XMLNode('help', 'This method allows for the importing of '
                        'external data into Qiime2 artifacts.'))
    return tool


def _make_config():
    configfiles = XMLNode("configfiles")
    configfiles.append(XMLNode("configfile", _make_cheetah_config(),
                               name="inputs"))
    return configfiles


def _add_format_ui(root, format_record):
    if issubclass(format_record.format, model.DirectoryFormat):
        for field in format_record.format._fields:
            file_attr = getattr(format_record.format, field)

            if isinstance(file_attr, model.FileCollection):
                _add_collection_ui(root, file_attr)
            else:
                root.append(XMLNode('param', type='data', name=file_attr.name,
                                    help=file_attr.format.__name__))
    else:
        root.append(XMLNode('param', type='data', name='source',
                            help=format_record.format.__name__))


def _add_collection_ui(root, file_attr):
    conditional = XMLNode("conditional", name=file_attr.name)
    select = XMLNode("param", type='select', name='picker')
    select.append(XMLNode("option", "Use collection to import",
                          value='collection', selected='true'))
    select.append(XMLNode("option", "Associate individual files",
                          value='individual'))
    conditional.append(select)

    when_collection = XMLNode("when", value='collection')
    when_collection.append(XMLNode('param', type='data_collection',
                                   name=file_attr.name,
                                   help=file_attr.format.__name__))

    when_individual = XMLNode("when", value='individual')
    repeat = XMLNode("repeat", name=file_attr.name)
    repeat.append(XMLNode('param', type='text', name=file_attr.name,
                          help=file_attr.format.__name__, default='TODO'))
    repeat.append(XMLNode('param', type='data', name=file_attr.name+'data',
                          help=file_attr.format.__name__))
    when_individual.append(repeat)

    conditional.append(when_collection)
    conditional.append(when_individual)

    root.append(conditional)


def _make_cheetah_config():
    return """
#import json


$import_data.import_ui.input_format

    """
