import qiime2.sdk as sdk
from qiime2.core.type.grammar import UnionExp
from qiime2.core.type.meta import TypeVarExp

from q2galaxy.core.usage import TemplateTestUsage
from q2galaxy.core.util import XMLNode, rst_header
from q2galaxy.core.templaters.common import (
    make_tool_id, make_tool_name, make_config, make_citations,
    make_requirements)

qiime_type_to_param_type = {
    'Int': 'integer',
    'Str': 'text',
    'Bool': 'boolean',
    'Float': 'float',
    'Metadata': 'data',
    'MetadataColumn': 'data',
}


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

    tool = XMLNode('tool', id=make_tool_id(plugin.id, action.id),
                   name=make_tool_name(plugin.name, action.id),
                   version=plugin.version,
                   profile='18.09')
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
    for example in action.examples.values():
        use = TemplateTestUsage()
        example(use)
        tests.append(use.xml)

    return tests


def make_input_param(name, spec):
    optional_attrs = {}
    if 'List' in spec.qiime_type.name or 'Set' in spec.qiime_type.name:
        optional_attrs['multiple'] = 'true'

    param = XMLNode('param', type='data', format='qza', name=name,
                    label=f'{name}: {str(spec.qiime_type)}',
                    **optional_attrs)
    options = XMLNode(
        'options', options_filter_attribute='metadata.semantic_type')
    param.append(options)

    _validator_set = repr(set(map(str, spec.qiime_type)))
    validator = XMLNode(
        'validator',
        'hasattr(value.metadata, "semantic_type")'
        f' and value.metadata.semantic_type in {_validator_set}',
        type='expression', message='Incompatible type')
    param.append(validator)

    if spec.has_description():
        param.set('help', spec.description)
    if spec.has_default() and spec.default is None:
        param.set('optional', 'true')

    for t in spec.qiime_type:
        if t.name == 'List' or t.name == 'Set':
            for t in t:
                t = t.fields[0]
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
                    default = (choice == spec.default)
                    option_tags.append(XMLNode('option', value=str(choice),
                                               selected=str(default)))

            elif qiime_type.predicate.name == 'Range':
                min_, max_ = qiime_type.predicate.to_ast()['range']
                XML_attrs['type'] = qiime_type_to_param_type[qiime_type.name]

                FLOAT_RESOLUTION = 0.000001
                if min_ is not None:
                    if not qiime_type.predicate.template.inclusive_start:
                        if qiime_type.name == 'Int':
                            min_ += 1
                        else:
                            min_ += FLOAT_RESOLUTION
                    XML_attrs['min'] = str(min_)

                if max_ is not None:
                    if not qiime_type.predicate.template.inclusive_end:
                        if qiime_type.name == 'Int':
                            max_ -= 1
                        else:
                            max_ -= FLOAT_RESOLUTION
                    XML_attrs['max'] = str(max_)
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

        XML_attrs['label'] = f'{name}: {str(spec.qiime_type)}'
        if spec.has_description():
            XML_attrs['help'] = spec.description

        param = XMLNode('param', name=name, **XML_attrs)
        for option in option_tags:
            param.append(option)

        params.append(param)

        if qiime_type.name == 'MetadataColumn':
            params.append(XMLNode('param', name=f'{name}_Column',
                                  type='data_column', data_ref=name,
                                  optional='true', label='Specify which '
                                  'column from the metadata to use'))

    return params


def make_filename(name, spec):
    if sdk.util.is_visualization_type(spec.qiime_type):
        ext = 'qzv'
    else:
        ext = 'qza'
    return '.'.join([name, ext]), ext


def make_output(name, spec):
    file_name, ext = make_filename(name, spec)
    XML_attrs = {}
    if ext == 'qza':
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
    help_ += "\n\n"
    help_ += "|  \n\n"
    return XMLNode('help', help_)


def make_command(plugin, action):
    return XMLNode(
        'command', f"q2galaxy run {plugin.id} {action.id} '$inputs'",
        detect_errors="aggressive")


def make_version_command(plugin):
    return XMLNode('version_command', f'q2galaxy version {plugin.id}')
