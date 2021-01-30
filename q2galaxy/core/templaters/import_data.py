import qiime2.sdk as sdk

from q2galaxy.core.util import XMLNode
from q2galaxy.core.templaters.common import (
    make_tool_name_from_id, make_config)


def make_builtin_import(meta, tool_id):
    pm = sdk.PluginManager()
    inputs = XMLNode('inputs')

    type_param = XMLNode('param', name='type', type='select',
                         label='type: The type of the data you want to import')
    for type_ in sorted(pm.importable_types, key=repr):
        type_param.append(XMLNode('option', value=type_))
    inputs.append(type_param)

    inputs.append(XMLNode('param', name='input_path', type='text',
                          label='input_path: The filepath to the data you '
                          'want to import'))
    format_param = (XMLNode('param', name='input_format', type='select',
                            optional='true',
                            label='input_format: The format you want to '
                            'import the data as, if in doubt leave blank'))
    for format_ in sorted(pm.importable_formats, key=repr):
        format_param.append(XMLNode('option', value=format_))
    inputs.append(format_param)

    output = XMLNode('outputs')
    output.append(XMLNode('data', format='qza', name='imported',
                          from_work_dir='imported.qza'))

    tool = XMLNode('tool', id=tool_id, name=make_tool_name_from_id(tool_id))

    tool.append(inputs)
    tool.append(output)
    tool.append(
        XMLNode('command', "q2galaxy run builtin import_data '$inputs'"))
    tool.append(make_config())
    tool.append(XMLNode('description', 'Import data to Qiime2 artifacts'))
    tool.append(XMLNode('help', 'This method allows for the importing of '
                        'external data into Qiime2 artifacts.'))
    return tool
