import xml.etree.ElementTree as xml
import xml.dom.minidom as dom

import qiime2.sdk as sdk
from qiime2.core.type.grammar import UnionExp
from qiime2.core.type.meta import TypeVarExp

import q2galaxy

INPUT_FILE = 'inputs.json'
OUTPUT_FILE = 'outputs.json'

qiime_type_to_param_type = {
    'Int': 'integer',
    'Str': 'text',
    'Bool': 'boolean',
    'Float': 'float',
    'Metadata': 'data',
    'MetadataColumn': 'data',
}


def XMLNode(name_, _text=None, **attrs):
    e = xml.Element(name_, attrs)
    if _text is not None:
        e.text = _text
    return e


def make_tool(conda_meta, plugin, action):
    signature = action.signature

    inputs = XMLNode('inputs')
    for name, spec in signature.inputs.items():
        param = make_input_param(name, spec)
        inputs.append(param)
    for name, spec in signature.parameters.items():
        params = make_parameter_param(name, spec)
        inputs.extend(params)

    outputs = XMLNode('outputs')
    for name, spec in signature.outputs.items():
        output = make_output(name, spec)
        outputs.append(output)

    tool = XMLNode('tool', id=get_tool_id(action),
                   name=make_tool_name(plugin, action),
                   version=plugin.version,
                   profile='18.09')
    tool.append(XMLNode('description', action.name))
    tool.append(make_command(plugin, action))
    tool.append(make_version_command(plugin))
    tool.append(make_config())
    tool.append(inputs)
    tool.append(outputs)
    tool.append(XMLNode('help', action.description))
    tool.append(make_requirements(conda_meta, plugin.project_name))
    return tool


def make_input_param(name, spec):
    optional_attrs = {}
    if 'List' in spec.qiime_type.name or 'Set' in spec.qiime_type.name:
        optional_attrs['multiple'] = 'true'

    param = XMLNode('param', type='data', format='qza', name=name,
                    **optional_attrs)
    options = XMLNode(
        'options', options_filter_attribute='metadata.semantic_type')
    param.append(options)

    if spec.has_description():
        param.set('help', spec.description)
    if spec.has_default() and spec.default is None:
        param.set('optional', 'true')

    for t in spec.qiime_type:
        options.append(XMLNode('filter', type='add_value', value=repr(t)))

    return param


def make_parameter_param(name, spec):
    if isinstance(spec.qiime_type, TypeVarExp):
        qiime_types = list(spec.qiime_type.members)
    else:
        qiime_types = [spec.qiime_type]

    for qiime_type in qiime_types:
        if isinstance(qiime_type, UnionExp):
            qiime_types.remove(qiime_type)
            qiime_types.extend(qiime_type.unpack_union())

    params = []
    for qiime_type in qiime_types:
        XML_attrs = {}
        option_tags = []

        if sdk.util.is_collection_type(qiime_type):
            XML_attrs['multiple'] = 'true'
            # None of them seem to have more than one field, but it would be
            # nice if this were more robust
            qiime_type = qiime_type.fields[0]

        if qiime_type.predicate is not None:
            if qiime_type.predicate.name == 'Choices':
                choices = qiime_type.predicate.to_ast()['choices']
                XML_attrs['type'] = 'select'

                for choice in choices:
                    default = choice == spec.default
                    option_tags.append(XMLNode('option', value=str(choice),
                                               selected=str(default)))

            elif qiime_type.predicate.name == 'Range':
                range_ = qiime_type.predicate.to_ast()['range']
                XML_attrs['type'] = qiime_type_to_param_type[qiime_type.name]

                if range_[0] is not None:
                    XML_attrs['min'] = str(range_[0])

                if range_[1] is not None:
                    XML_attrs['max'] = str(range_[1])
        else:
            XML_attrs['type'] = qiime_type_to_param_type[qiime_type.name]

        # Any galaxy parameter that doesn't have a default value must be
        # optional. These parameters being "optional" isn't displayed to the
        # user in galaxy in any way, and the qiime method SHOULD behave as
        # expected if they are left blank.
        if qiime_type.name == 'Bool':
            XML_attrs['checked'] = str(spec.default)
        elif (qiime_type.name != 'Str' and spec.default == 'auto') \
                or str(spec.default) == 'NOVALUE' \
                or str(spec.default) == 'None':
            XML_attrs['optional'] = 'true'
        else:
            XML_attrs['value'] = str(spec.default)

        if str(spec.description) != 'NOVALUE' and \
                str(spec.description) != "None":
            XML_attrs['label'] = str(f'{name}: {spec.description}')

        param = XMLNode('param', name=name, **XML_attrs)
        for option in option_tags:
            param.append(option)

        params.append(param)

        if qiime_type.name == 'MetadataColumn':
            params.append(XMLNode('param', name=f'{name}_Column', type='text',
                                  optional='true', label='Specify which '
                                  'column from the metadata to use'))

    return params


def make_output(name, spec):
    if sdk.util.is_visualization_type(spec.qiime_type):
        ext = 'qzv'
    else:
        ext = 'qza'
    file_name = '.'.join([name, ext])
    return XMLNode('data', format=ext, name=name, from_work_dir=file_name)


def get_tool_id(action):
    return action.get_import_path().replace('.', '_')


def make_tool_name(plugin, action):
    return plugin.name + ' ' + action.id.replace('_', '-')


def make_command(plugin, action):
    return XMLNode(
        'command', f"q2galaxy run {plugin.id} {action.id} '$inputs'")


def make_version_command(plugin):
    return XMLNode('version_command', f'q2galaxy version {plugin.id}')


def make_config():
    configfiles = XMLNode('configfiles')
    configfiles.append(XMLNode('inputs', name='inputs', data_style='paths'))
    return configfiles


def make_citations(citations):
    # TODO: split our BibTeX up into single entries
    pass


def make_requirements(conda_meta, project_name):
    requirements = XMLNode('requirements')
    for dep, version in conda_meta.iter_deps(project_name, include_self=True):
        r = XMLNode('requirement', dep, type='package', version=version)
        requirements.append(r)

    requirements.append(XMLNode('requirement', 'q2galaxy',
                                type='package', version=q2galaxy.__version__))
    return requirements


def write_tool(tool, filepath):
    xmlstr = dom.parseString(xml.tostring(tool)).toprettyxml(indent="   ")
    with open(filepath, 'w') as fh:
        fh.write(xmlstr)


def template_builtins():
    template_import_data()
    template_export_data()


def template_import_data():
    pm = sdk.PluginManager()
    inputs = XMLNode('inputs')

    # TODO: I think we talked about not using that importable_types thing in
    # new places while talking about the import wizard, but is there a better
    # way to do this?
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

    tool = XMLNode('tool', id='import_data', name='import_data')
    tool.append(inputs)
    tool.append(output)
    tool.append(
        XMLNode('command', "q2galaxy run builtin import_data '$inputs'"))
    tool.append(make_config())
    tool.append(XMLNode('description', 'Import data to Qiime2 artifacts'))
    tool.append(XMLNode('help', 'This method allows for the importing of '
                        'external data into Qiime2 artifacts.'))

    write_tool(tool, '/home/anthony/src/galaxy/tools/qiime2/import_data.xml')


def template_export_data():
    inputs = XMLNode('inputs')

    inputs.append(XMLNode('param', name='input_path', type='text',
                          label='input_path: The path to the artifact you '
                          'want to export'))
    inputs.append(XMLNode('param', name='output_path', type='text',
                          label='output_path: Path to save exported data to'))
    # TODO: This probably needs to involve selecting from preset choices
    inputs.append(XMLNode('param', name='output_format', type='text',
                          optional='true',
                          label='output_format: The format you want to export '
                          'the data as, if in doubt leave blank'))

    tool = XMLNode('tool', id='export_data', name='export_data')
    tool.append(inputs)
    tool.append(
        XMLNode('command', "q2galaxy run builtin export_data '$inputs'"))
    tool.append(make_config())
    tool.append(XMLNode('description', 'Export data from Qiime2 artifacts'))
    tool.append(XMLNode('help', 'This method allows for the exporting of data '
                        'contained in Qiime2 artifacts to external '
                        'directories'))

    write_tool(tool, '/home/anthony/src/galaxy/tools/qiime2/export_data.xml')
