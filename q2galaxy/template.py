import os
import xml.etree.ElementTree as xml
import xml.dom.minidom as dom

import bs4

import qiime2.sdk as sdk

INPUT_FILE = 'inputs.json'
OUTPUT_FILE = 'outputs.json'


def XMLNode(name_, **attrs):
    return xml.Element(name_, attrs)

def _hack_requirements():
    requirements = XMLNode('requirements')
    requirement = XMLNode('requirement', type='package', version='2018.6.0')
    requirement.text = 'qiime2'
    requirements.append(requirement)
    return requirements

def get_tool_id(action):
    return action.get_import_path().replace('.', '_')


def template_all(directory):
    pm = sdk.PluginManager()
    for name, plugin in pm.plugins.items():
        for action in plugin.actions.keys():
            write_tool(directory, name.replace('-', '_'), action)


def write_tool(directory, plugin_id, action_id):
    pm = sdk.PluginManager()
    plugin = pm.plugins[plugin_id.replace('_', '-')]
    action = plugin.actions[action_id]

    filename = os.path.join(directory, get_tool_id(action) + '.xml')

    tool = make_tool(plugin_id, action, plugin.version)

    with open(filename, 'w') as fh:
        xmlstr = dom.parseString(xml.tostring(tool)).toprettyxml(indent="   ")
        fh.write(xmlstr)


def make_config():
    configfiles = XMLNode('configfiles')
    configfiles.append(XMLNode('inputs', name='inputs', data_style='paths'))
    return configfiles



def make_tool(plugin_id, action, version):
    tool = XMLNode('tool', id=get_tool_id(action),
                   name=make_tool_name(plugin_id, action.id),
                   version=version)

    inputs = XMLNode('inputs')
    outputs = XMLNode('outputs')

    description = XMLNode('description')
    description.text = action.name
    help_ = XMLNode('help')
    help_.text = action.description

    command = make_command(plugin_id, action.id)
    version_command = make_version_command(plugin_id)

    _hack = _hack_requirements()
    tool.append(_hack)

    tool.append(description)
    tool.append(command)
    tool.append(version_command)
    tool.append(make_config())
    tool.append(inputs)
    tool.append(outputs)
    tool.append(help_)

    signature = action.signature

    for name, spec in signature.inputs.items():
        param = make_input_param(name, spec)
        inputs.append(param)

    for name, spec in signature.parameters.items():
        #param = make_parameter_param(name, spec)
        #inputs.append(param)
        pass

    for name, spec in signature.outputs.items():
        output = make_output(name, spec)
        outputs.append(output)


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
    pass


def make_output(name, spec):
    if spec.qiime_type.name == 'Visualization':
        format_ = 'qzv'
    else:
        format_ = 'qza'

    output = XMLNode('data', format=format_, name=name, from_work_dir='.'.join([name, format_]))

    return output


def make_command(plugin_id, action_id):
    command = XMLNode('command')
    command.text = ("q2galaxy run {plugin_id} {action_id} '$inputs'"
                    ).format(plugin_id=plugin_id,
                                             action_id=action_id,
                                             INPUT_FILE=INPUT_FILE)
    return command


def make_version_command(plugin_id):
    version_command = XMLNode('version_command')
    version_command.text = 'q2galaxy version %s' % plugin_id
    return version_command


def make_citations(citations):
    # TODO: split our BibTeX up into single entries
    pass


def make_tool_name(plugin_id, action_id):
    return plugin_id.replace('_', '-') + ' ' + action_id.replace('_', '-')
