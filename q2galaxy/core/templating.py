import xml.etree.ElementTree as xml
import xml.dom.minidom as dom

import qiime2.sdk as sdk

import q2galaxy

INPUT_FILE = 'inputs.json'
OUTPUT_FILE = 'outputs.json'


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
        param = make_parameter_param(name, spec)
        # TODO: inputs.append(param)

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
    param = XMLNode('param', type='data', format='qza', name=name)
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
    # TODO: implement this
    pass


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
