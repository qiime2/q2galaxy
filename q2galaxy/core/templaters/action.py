# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import qiime2.sdk as sdk

import q2galaxy
from q2galaxy.api.usage import GalaxyRSTInstructionsUsage
from q2galaxy.core.usage import GalaxyTestUsage
from q2galaxy.core.util import XMLNode, galaxy_ui_var, rst_header
from q2galaxy.core.templaters.common import (
    make_tool_id, make_tool_name, make_config, make_citations,
    make_requirements)
from q2galaxy.core.templaters.helpers import signature_to_galaxy


def make_tool(conda_meta, plugin, action):
    signature = action.signature

    inputs = XMLNode('inputs')
    advanced = []
    for case in signature_to_galaxy(signature):
        xml = case.inputs_xml()
        if case.is_advanced():
            if type(xml) is list:
                advanced.extend(xml)
            else:
                advanced.append(xml)
        else:
            if type(xml) is list:
                inputs.extend(xml)
            else:
                inputs.append(xml)

    if advanced:
        section = XMLNode('section', name=galaxy_ui_var(tag='section',
                                                        name='extra_opts'),
                          title='Click here for additional options')
        section.extend(advanced)
        inputs.append(section)

    outputs = XMLNode('outputs')
    for name, spec in signature.outputs.items():
        output = make_output(name, spec)
        outputs.append(output)

    # Drop local identifier if it exists, it will be in a different local
    # identifier (multiple + is not allowed in pep440)
    if '+' in plugin.version:
        # swap some things around
        plugin_version, local = plugin.version.split('+')
        local += '-'
    else:
        plugin_version = plugin.version
        local = ''

    q2galaxy_version = q2galaxy.__version__.replace('+', '.')
    tool = XMLNode(
        'tool', id=make_tool_id(plugin.id, action.id),
        name=make_tool_name(plugin.id, action.id),
        version=f'{plugin_version}+{local}q2galaxy.{q2galaxy_version}')
    tool.append(XMLNode('description', action.name))
    tool.append(make_command(plugin, action))
    tool.append(make_version_command(plugin))
    tool.append(make_config())
    tool.append(inputs)
    tool.append(outputs)
    tool.append(make_tests(action))
    tool.append(make_help(plugin, action))
    tool.append(make_citations(plugin, action))
    tool.append(make_requirements(conda_meta, plugin.project_name))
    return tool


def make_tests(action):
    tests = XMLNode('tests')
    for idx, example in enumerate(action.examples.values()):
        use = GalaxyTestUsage(example_path=(action, idx))
        example(use)
        tests.append(use.xml)

    return tests


def make_filename(name, spec):
    if sdk.util.is_visualization_type(spec.qiime_type):
        ext = 'qzv'
    else:
        ext = 'qza'
    return '.'.join([name, ext]), ext


# TODO: this probably needs to change to do stuff with collections
def make_output(name, spec):
    file_name, ext = make_filename(name, spec)
    XML_attrs = {}
    if ext == 'qza' or ext == 'qzv':
        XML_attrs['label'] = '${tool.id} on ${on_string}: ' + file_name
    return XMLNode('data', format=ext, name=name, from_work_dir=file_name,
                   **XML_attrs)


def make_help(plugin, action):
    help_ = rst_header(' '.join(['QIIME 2:', plugin.name,
                                 action.id.replace('_', '-')]), 1)
    help_ += action.name + '\n'
    help_ += "\n"
    help_ += rst_header('Outputs:', 2)
    for name, spec in action.signature.outputs.items():
        description = '<no description>'
        if spec.has_description():
            description = spec.description
        help_ += f":{make_filename(name, spec)[0]}: {description}\n"
    help_ += "\n"
    help_ += "|  \n"
    help_ += rst_header("Description:", 2)
    help_ += action.description
    help_ += "\n"
    if action.examples:
        help_ += rst_header("Examples:", 2)
        for example_name, example in action.examples.items():
            use = GalaxyRSTInstructionsUsage()
            example(use)

            help_ += rst_header(example_name, 3)
            help_ += '\n'.join(use.render())

    help_ += "\n\n"
    help_ += "|  \n\n"
    return XMLNode('help', help_)


def make_command(plugin, action):
    return XMLNode(
        'command', f"q2galaxy run {plugin.id} {action.id} '$inputs'",
        detect_errors="aggressive")


def make_version_command(plugin):
    return XMLNode('version_command', f'q2galaxy version {plugin.id}')
