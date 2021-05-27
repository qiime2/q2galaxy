# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import qiime2.plugin.model as model
import qiime2.sdk as sdk
from qiime2.sdk.plugin_manager import GetFormatFilters

from q2galaxy.core.util import (XMLNode, galaxy_esc, pretty_fmt_name,
                                galaxy_ui_var)
from q2galaxy.core.templaters.common import (make_builtin_version,
                                             make_tool_name_from_id)


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

        for fmt_rec in sorted(
                pm.get_formats(filter=GetFormatFilters.IMPORTABLE,
                               semantic_type=record.semantic_type).values(),
                key=lambda x: x.format.__name__):
            plugins.add(fmt_rec.plugin)
            known_formats.add(fmt_rec.format)

            if issubclass(fmt_rec.format,
                          model.SingleFileDirectoryFormatBase):
                # These are really just noise for the galaxy UI
                # an implicit transformation from the backing file format
                # is simpler and removes the redundancy
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
    outputs.append(XMLNode('data', name='imported_data', format='qza',
                           from_work_dir='imported_data.qza'))

    tool = XMLNode('tool', id=tool_id, name=make_tool_name_from_id(tool_id),
                   version=make_builtin_version(plugins))

    tool.append(inputs)
    tool.append(outputs)
    tool.append(
        XMLNode('command', "q2galaxy run tools import '$inputs'"))
    tool.append(_make_config())
    tool.append(XMLNode('description', 'Import data into a QIIME 2 Artifact'))
    tool.append(XMLNode('help', ''))
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
                section = XMLNode("section", name=f'import_{file_attr.name}',
                                  expanded='true')
                section.append(XMLNode('param', type='text', name='name',
                                       help='Filename to import as',
                                       value=file_attr.pathspec))
                section.append(XMLNode('param', type='data', name='data',
                                       help=file_attr.format.__name__))
                root.append(section)
    else:
        section = XMLNode("section", name='import', expanded='true')
        section.append(XMLNode('param', type='hidden', name='name',
                               value=galaxy_esc(None)))
        section.append(XMLNode('param', type='data', name='data',
                               help=format_record.format.__name__))
        root.append(section)


def _add_collection_ui(root, file_attr):
    section = XMLNode("section", name=f'import_{file_attr.name}',
                      expanded='true')
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
    when_collection.append(XMLNode('param', type='data_collection',
                                   name='elements',
                                   help=file_attr.format.__name__))
    add_ext_cond = XMLNode("conditional",
                           name=galaxy_ui_var(tag='cond', name='add_ext'))
    ext_select = XMLNode("param", type='select', label='Append an extension?',
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
    repeat = XMLNode("repeat", name='elements', min='1')
    repeat.append(XMLNode('param', type='text', name='name',
                          help='Filename to import as',
                          value=file_attr.pathspec))
    repeat.append(XMLNode('param', type='data', name='data',
                          help=file_attr.format.__name__))
    when_individual.append(repeat)

    conditional.append(when_collection)
    conditional.append(when_individual)

    section.append(conditional)
    root.append(section)


# ! IMPORTANT !
# This function is never called, but its source code is stolen for a
# PSP body to be templated by Cheetah. This is written here to permit basic
# syntax highlighting and linting (hence the `self` and `write` arguments for
# the PSP). Everything inside `_inline_code` will be embedded.
def _inline_code(self, write):
    # This is an exercise in cheating the Cheetah
    import json

    def expand_collection(collection):
        # All of this work is just to extract the
        # element identifier AND the path
        return [dict(name=d.element_identifier, data=stringify(d))
                for d in collection]

    def stringify(obj):
        if type(obj) is dict:
            new = {}
            for key, value in obj.items():
                if (key.startswith('__') and key.endswith('__')
                        and not key.startswith('__q2galaxy__')):
                    continue
                new[str(key)] = stringify(value)

            return new
        elif type(obj) is list:
            return [stringify(x) for x in obj]
        elif type(obj.__str__) is not type(object().__str__):  # noqa
            # There is an associated __str__ which will be used for
            # "normal" templating, it looks like a strange check because
            # it really is, we're testing for method-wrapper as a sign
            # of non-implementation
            return str(obj)
        elif obj.is_collection:
            return expand_collection(obj)
        else:
            raise NotImplementedError("Unrecognized situation in q2galaxy")

    dataset = self.getVar('import_root')
    inputs = stringify(dataset)
    write(json.dumps(inputs))


def _make_cheetah_config():
    import inspect
    from textwrap import dedent
    template_psp_lines = inspect.getsource(_inline_code).split('\n')[1:-1]
    template_body = dedent('\n'.join(template_psp_lines))
    return f'''<%
{template_body}
    %>'''
