# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os
import itertools
from qiime2.sdk.util import (interrogate_collection_type, is_semantic_type,
                             is_union, is_metadata_type,
                             is_metadata_column_type)
from qiime2.plugin import Choices
from qiime2.core.type.signature import ParameterSpec
from qiime2 import ResultCollection

from q2galaxy.core.util import XMLNode, galaxy_esc, galaxy_ui_var


def signature_to_galaxy(signature, arguments=None, data_dir=None):
    for name, spec in itertools.chain(signature.inputs.items(),
                                      signature.parameters.items()):
        if arguments is None:
            arg = None
        elif name not in arguments:
            continue
        else:
            arg = arguments[name]
        yield identify_arg_case(name, spec, arg, data_dir=data_dir)


def is_union_anywhere(qiime_type):
    return is_union(qiime_type) or (
        qiime_type.predicate is not None and is_union(qiime_type.predicate))


def identify_arg_case(name, spec, arg, data_dir=None):
    style = interrogate_collection_type(spec.qiime_type)

    if is_semantic_type(spec.qiime_type):
        return InputCase(name, spec, arg, data_dir=data_dir,
                         multiple=style.style is not None,)

    if style.style is None:  # not a collection
        if is_union_anywhere(spec.qiime_type):
            return PrimitiveUnionCase(name, spec, arg)
        elif is_metadata_type(spec.qiime_type):
            if is_metadata_column_type(spec.qiime_type):
                return ColumnTabularCase(name, spec, arg)
            else:
                return MetadataTabularCase(name, spec, arg)
        elif spec.qiime_type.name == 'Bool':
            return BoolCase(name, spec, arg)
        elif spec.qiime_type.name == 'Str':
            return StrCase(name, spec, arg)
        else:
            return NumericCase(name, spec, arg)

    elif style.style == 'simple':  # single type collection
        return SimpleCollectionCase(name, spec, arg)
    elif style.style == 'monomorphic':  # multiple types, but monomorphic
        return NotImplementedCase(name, spec, arg)
    elif style.style == 'composite':  # multiple types, but polymorphic
        return SimpleCollectionCase(name, spec, arg)
    elif style.style == 'complex':  # oof
        return NotImplementedCase(name, spec, arg)

    raise NotImplementedError


class ParamCase:
    def __init__(self, name, spec, arg=None):
        self.name = name
        self.spec = spec
        self.arg = arg

    def get_rst_arg(self):
        return self.arg

    def is_advanced(self):
        return self.spec.has_default()

    def inputs_xml(self):
        raise NotImplementedError(self.__class__)

    def tests_xml(self):
        raise NotImplementedError(self.__class__)

    def rst_instructions(self):
        if self.spec.has_default() and self.spec.default == self.arg:
            return (f'Leave *"{self.name}"* as its default value of'
                    f' ``{self.get_rst_arg()}``')
        return f'Set *"{self.name}"* to ``{self.get_rst_arg()}``'

    def add_help(self, xml):
        if self.spec.has_default():
            default = self.spec.default
            if default is None:
                help_ = '[optional]'
            else:
                if type(default) is bool:
                    default = 'Yes' if default else 'No'
                else:
                    default = repr(default)
                help_ = f'[default: {default}]'
        else:
            help_ = '[required]'
        if self.spec.has_description():
            help_ = f'{help_}  {self.spec.description}'

        xml.set('help', help_)

    def add_default(self, xml):
        if self.spec.has_default():
            if self.spec.default is None:
                xml.set('optional', 'true')
            else:
                xml.set('value', str(self.spec.default))

    def add_label(self, xml):
        xml.set('label', f'{self.name}: {str(self.spec.qiime_type)}')


class NotImplementedCase(ParamCase):
    def inputs_xml(self):
        param = XMLNode('param', name=self.name, type='text',
                        value='NOT YET IMPLEMENTED')
        param.append(XMLNode('validator', 'False', type='expression',
                             message='NOT YET IMPLEMENTED'))
        return param

    def tests_xml(self):
        return XMLNode("param", name=self.name, value=str(self.arg))


class MetadataTabularCase(ParamCase):
    def inputs_xml(self):
        root = XMLNode('repeat', name=self.name,
                       title=f'{self.name}: {str(self.spec.qiime_type)}')
        self.add_help(root)
        if not self.spec.has_default():
            root.set('min', '1')

        conditional = XMLNode('conditional',
                              name=galaxy_ui_var(tag='conditional',
                                                 name=self.name))

        select = XMLNode('param', type='select',
                         name='type',
                         label=f'{self.name}: {str(self.spec.qiime_type)}')
        select.append(XMLNode('option', 'Metadata from TSV',
                              value='tsv', selected='true'))
        select.append(XMLNode('option', 'Metadata from Artifact',
                              value='qza'))

        conditional.append(select)

        when_tsv = XMLNode('when', value='tsv')
        tsv = XMLNode('param', type='data', format='tabular,qiime2.tabular',
                      name='source', label='Metadata Source')
        when_tsv.append(tsv)
        conditional.append(when_tsv)

        when_artifact = XMLNode('when', value='qza')
        artifact = XMLNode('param', type='data', format='qza',
                           name='source', label='Metadata Source')
        when_artifact.append(artifact)
        conditional.append(when_artifact)

        root.append(conditional)
        return root

    def tests_xml(self):
        if self.arg is None:
            return
        arg = self.arg
        if type(self.arg) is not list:
            arg = [self.arg]

        merged = []
        for type_, source in arg:
            repeat = XMLNode('repeat', name=self.name)
            cond = XMLNode('conditional',
                           name=galaxy_ui_var(tag='conditional',
                                              name=self.name))
            cond.append(XMLNode('param', name='type', value=type_))
            if type_ == 'tsv':
                type_ = 'qiime2.tabular'
            cond.append(XMLNode('param', name='source', value=source,
                                ftype=type_))
            repeat.append(cond)
            merged.append(repeat)
        return merged

    def rst_instructions(self):
        if self.arg is None:
            return f'Leave *"{self.name}"* unchanged (do not insert an entry).'

        md_args = self.arg
        if type(self.arg) is not list:
            md_args = [self.arg]

        sub = []
        first_md = not self.spec.has_default()
        for md_arg in md_args:
            inner_sub = []
            if first_md:
                first_md = False
                sub.append(('Perform the following steps.', inner_sub))
            else:
                sub.append((f'Press the ``+ Insert {self.name}`` button to set'
                            f' up the next steps.', inner_sub))
            type_, source = md_arg
            if type_ == 'tsv':
                inner_sub.append('Leave as ``Metadata from TSV``')
            else:
                inner_sub.append('Change to ``Metadata from Artifact``')
            inner_sub.append(f'Set *"Metadata Source"* to ``{source}``')

        return (f'For *"{self.name}"*:', sub)


class ColumnTabularCase(ParamCase):
    def inputs_xml(self):
        conditional = XMLNode('conditional', name=self.name)

        select = XMLNode('param', type='select',
                         name='type',
                         label=f'{self.name}: {str(self.spec.qiime_type)}')
        conditional.append(select)

        from_tsv = XMLNode('option', 'Metadata from TSV', value='tsv')
        if self.spec.has_default():
            select.append(XMLNode('option', 'None (default)', value='none',
                                  selected='true'))
            conditional.append(XMLNode('when', value='none'))
        else:
            from_tsv.set('selected', 'true')

        select.append(from_tsv)
        select.append(XMLNode('option', 'Metadata from Artifact',
                              value='qza'))

        when_tsv = XMLNode('when', value='tsv')
        tsv1 = XMLNode('param', type='data', format='tabular,qiime2.tabular',
                       name='source', label='Metadata Source')
        tsv2 = XMLNode('param', type='data_column', use_header_names='true',
                       data_ref='source', name='column', label='Column Name')
        tsv2.append(XMLNode('validator', 'value != "1"', type='expression',
                            message='The first column cannot be selected ('
                                    'they are IDs).'))
        when_tsv.append(tsv1)
        when_tsv.append(tsv2)
        conditional.append(when_tsv)

        when_artifact = XMLNode('when', value='qza')
        art1 = XMLNode('param', type='data', format='qza',
                       name='source', label='Metadata Source')
        art2 = XMLNode('param', type='text', name='column',
                       label='Column Name')
        art2.append(XMLNode('validator', type='empty_field'))
        when_artifact.append(art1)
        when_artifact.append(art2)
        conditional.append(when_artifact)
        self.add_help(select)

        return conditional

    def tests_xml(self):
        if self.arg is None:
            return
        type_, source, column = self.arg
        cond = XMLNode('conditional', name=self.name)
        cond.append(XMLNode('param', name='type', value=type_))
        if type_ == 'tsv':
            type_ = 'qiime2.tabular'
        cond.append(XMLNode('param', name='source', value=source, ftype=type_))
        cond.append(XMLNode('param', name='column', value=column))
        return cond

    def rst_instructions(self):
        if self.arg is None:
            return super().rst_instructions()

        sub = []
        type_, source, col = self.arg
        if type_ == 'tsv':
            sub.append('Leave as ``Metadata from TSV``')
        else:
            sub.append('Change to ``Metadata from Artifact``')

        sub.append(f'Set *"Metadata Source"* to ``{source}``')
        sub.append(f'Set *"Column Name"* to ``{col}``')

        return (f'For *"{self.name}"*:', sub)


class InputCase(ParamCase):
    def __init__(self, name, spec, arg=None, data_dir=None, multiple=False):
        super().__init__(name, spec, arg)
        self.data_dir = data_dir
        self.multiple = multiple

        self.qiime_type = spec.qiime_type
        if multiple:
            self.qiime_type = spec.qiime_type.fields[0]

    def get_rst_arg(self):
        if self.arg is None:
            return "'Nothing selected'"
        return f"#: {self.arg}"

    def inputs_xml(self):
        param = XMLNode('param', type='data', name=self.name)
        self.add_help(param)
        self.add_default(param)
        self.add_label(param)

        if self.spec.qiime_type.name == 'Collection':
            param.set('type', 'data_collection')
            param.set('collection_type', 'list')
        else:
            param.set('format', 'qza')
            if self.multiple:
                param.set('multiple', 'true')

            options = XMLNode('options',
                            options_filter_attribute='metadata.semantic_type')
            for t in self.qiime_type:
                options.append(XMLNode('filter', type='add_value',
                                        value=repr(t)))
            param.append(options)

        if not self.multiple:
            param.append(self._make_validator())

        return param

    def _make_validator(self):
        _validator_set = repr(list(sorted(set(map(str, self.qiime_type)))))
        validator = XMLNode(
            'validator',
            'hasattr(value.metadata, "semantic_type")'
            f' and value.metadata.semantic_type in {_validator_set}',
            type='expression', message='Incompatible type')
        return validator

    def tests_xml(self):
        if self.arg is None:
            return

        if self.spec.qiime_type.name == 'List' \
                or self.spec.qiime_type == 'Set':
            arg = ','.join(map(str, self.arg))
        elif self.spec.qiime_type.name == 'Collection':
            collection = ResultCollection.load(
                os.path.join(self.data_dir, self.arg))

            param_tag = XMLNode('param', name=self.name)
            collection_tag = XMLNode('collection', type='list')
            param_tag.append(collection_tag)

            for element in collection.keys():
                path = os.path.join(str(self.arg), element + '.qza')
                element_tag = XMLNode('element', name=element,
                                      value=path, type='qza')
                collection_tag.append(element_tag)

            return param_tag
        else:
            arg = str(self.arg)
        return XMLNode('param', name=self.name, value=arg, ftype='qza')

    def rst_instructions(self):
        if not self.multiple or self.spec.qiime_type.name == 'Collection':
            return super().rst_instructions()
        if self.arg is None:
            return 'Leave *"{self.name}"* without any selections.'

        sub = []
        for arg in self.arg:
            sub.append(f'``#: {arg}``')

        return (f'For *"{self.name}"*, use ctrl-(or command)-click to select'
                f' the following inputs:', sub)


class NumericCase(ParamCase):
    _qiime_type_to_param_type = {
        'Int': 'integer',
        'Float': 'float',
    }

    def get_rst_arg(self):
        if self.arg is None:
            return "<blank>"
        return self.arg

    def add_type(self, xml):
        xml.set('type',
                self._qiime_type_to_param_type[self.spec.qiime_type.name])

    def add_range(self, xml, predicate, step):
        min_, max_ = predicate.to_ast()['range']
        if min_ is not None:
            if not predicate.template.inclusive_start:
                min_ += step
            xml.set('min', str(min_))
        if max_ is not None:
            if not predicate.template.inclusive_end:
                max_ -= step
            xml.set('max', str(max_))

    def inputs_xml(self):
        param = XMLNode('param', name=self.name)
        self.add_type(param)
        self.add_help(param)
        self.add_default(param)
        self.add_label(param)

        if not self.spec.has_default():
            # trick galaxy
            param.set('value', '')

        predicate = self.spec.qiime_type.predicate
        if predicate is not None:
            if predicate.name == 'Range':
                if self.spec.qiime_type.name == 'Float':
                    self.add_range(param, predicate, 0.000001)
                else:
                    self.add_range(param, predicate, 1)
            else:
                print(self.spec)
                raise NotImplementedError

        return param

    def tests_xml(self):
        arg = str(self.arg) if self.arg is not None else ''
        return XMLNode('param', name=self.name, value=arg)


class StrCase(ParamCase):
    def inputs_xml(self):
        predicate = self.spec.qiime_type.predicate
        if predicate is not None and predicate.name == 'Choices':
            param = make_select(self.name, self.spec,
                                predicate.template.choices)
        else:
            param = XMLNode('param', name=self.name, type='text')
            # sanitizer prevents default replacement with 'X' for some
            # punctuation characters. It appears that this sanitizing requires
            # an enumeration of valid characters, so supporting arbitrary
            # unicode will likely require a change to Galaxy itself.
            sanitizer = XMLNode('sanitizer')
            valid = XMLNode('valid', initial='string.printable')
            sanitizer.append(valid)
            param.append(sanitizer)

            if self.spec.has_default():
                if self.spec.default is None:
                    self.add_help(param)
                    self.add_label(param)
                    param = make_optional(param)
                    # Do not add help as <conditional> doesn't permit it
                else:
                    param.set('value', self.spec.default)
                    self.add_help(param)
            else:
                param.append(XMLNode(
                    # validator type='length' fails on empty input
                    'validator', 'value is not None and len(value) > 0',
                    type='expression',
                    message='Please verify this parameter.'))
                self.add_help(param)

        self.add_label(param)

        return param

    def tests_xml(self):
        # NOTE: the results from make_optional don't seem to need a conditional
        # to define the <select/> as keeping track of the type doesn't matter
        # (they are strings either way)
        return XMLNode('param', name=self.name, value=galaxy_esc(self.arg))


class BoolCase(ParamCase):
    def get_rst_arg(self):
        if self.arg is None:
            return 'None'
        if self.arg:
            return 'Yes'
        return 'No'

    def inputs_xml(self):
        predicate = self.spec.qiime_type.predicate
        if (self.spec.has_default() and type(self.spec.default) is bool
                and (predicate is None
                     or len(predicate.template.choices) == 2)):
            param = XMLNode('param', name=self.name, type='boolean',
                            # Not super necessary, but makes it consistent for
                            # testing and any dynamic references
                            truevalue=galaxy_esc(True),
                            falsevalue=galaxy_esc(False))
            if self.spec.default is True:
                param.set('checked', 'true')
        else:
            choices = [True, False]
            if predicate is not None:
                choices = predicate.template.choices
            param = make_select(self.name, self.spec, choices,
                                lambda x: 'Yes' if x else 'No')

        self.add_help(param)
        self.add_label(param)
        return param

    def tests_xml(self):
        arg = galaxy_esc(self.arg)
        return XMLNode('param', name=self.name, value=arg)


class PrimitiveUnionCase(ParamCase):
    def __init__(self, name, spec, arg=None):
        super().__init__(name, spec, arg)
        self.branches = {}

        def _sanitize(t):
            return galaxy_ui_var(value=galaxy_esc(str(t).replace('%', 'X')))

        for type_ in spec.qiime_type:
            if type_.predicate is not None and is_union(type_.predicate):
                for pred in type_.predicate.unpack_union():
                    new_type = type_.duplicate(predicate=pred)
                    self.branches[_sanitize(new_type)] = new_type
            elif (type_.predicate is not None
                  and type_.predicate.name == 'Choices'):
                for choice in type_.predicate.template.choices:
                    new_type = type_.duplicate(predicate=Choices(choice))
                    self.branches[galaxy_esc(choice)] = new_type
            elif type_.name == 'Bool':
                for choice in [True, False]:
                    new_type = type_.duplicate(predicate=Choices(choice))
                    self.branches[galaxy_esc(choice)] = new_type
            else:
                self.branches[_sanitize(type_)] = type_

        if self.spec.default is None:
            self.branches[galaxy_esc(None)] = {None}

    def _display_func(self, choice):
        if type(choice) is str:
            return f"{choice} (Str)"
        elif type(choice) is bool:
            val = 'Yes' if choice else 'No'
            return f"{val} (Bool)"
        else:
            raise NotImplementedError

    def inputs_xml(self):
        base_types = []
        for t in self.spec.qiime_type:
            if t.predicate is not None and is_union(t.predicate):
                for pred in t.predicate.unpack_union():
                    base_types.append(t.duplicate(predicate=pred))
            else:
                base_types.append(t)

        to_add = []

        for t in base_types:
            if ((t.name == "Str" and t.predicate is None)
                    or t.name == 'Float' or t.name == 'Int'):
                to_add.append(t)

        root = None
        if to_add:
            root = XMLNode('conditional', name=galaxy_ui_var(tag='conditional',
                                                             name=self.name))
            select = XMLNode('param', type='select',
                             name=galaxy_ui_var(tag='select'))
            root.append(select)
        else:
            select = XMLNode('param', type='select', name=self.name)

        choices = []
        for t in base_types:
            if t.predicate is not None and t.predicate.name == 'Choices':
                choices.extend(t.predicate.template.choices)
            elif t.name == 'Bool':
                choices.extend([True, False])

        display = None
        if not self.spec.has_default():
            display = 'Selection required'
        elif self.spec.default is None:
            display = 'None (Use default behavior)'

        if display is not None:
            value = galaxy_esc(None)
            select.append(XMLNode('option', display, value=value,
                                  selected='true'))
            if root is not None:
                when = XMLNode('when', value=value)
                hidden = XMLNode('param', type='hidden', name=self.name,
                                 value=value)
                when.append(hidden)
                root.append(when)

        used_choices = set()
        for choice in choices:
            value = galaxy_esc(choice)
            if value in used_choices:
                continue
            else:
                used_choices.add(value)
            option = XMLNode('option', self._display_func(choice), value=value)
            if self.spec.has_default() and self.spec.default == choice:
                option.set('selected', 'true')
            select.append(option)
            if root is not None:
                when = XMLNode('when', value=value)
                hidden = XMLNode('param', type='hidden', name=self.name,
                                 value=value)
                when.append(hidden)
                root.append(when)

        default = self.spec.default  # NOVALUE is fine
        for addition in to_add:
            value = galaxy_ui_var(value=galaxy_esc(
                # Galaxy will convert % to X internally and then complain
                # about a lack of matching cases, so we'll just do it now
                str(addition).replace('%', 'X')))
            option = XMLNode('option', f'Provide a value ({addition})',
                             value=value)
            select.append(option)
            when = XMLNode('when', value=value)

            dispatch = {
                'Float': NumericCase, 'Int': NumericCase, 'Str': StrCase}
            try:
                ParamCase = dispatch[addition.name]
            except KeyError:
                raise NotImplementedError

            if default in addition:
                spec_default = default
                option.set('selected', 'true')
            else:
                spec_default = self.spec.NOVALUE

            new_spec = self.spec.duplicate(qiime_type=addition,
                                           default=spec_default)
            sub_ui = ParamCase(self.name, new_spec).inputs_xml()
            when.append(sub_ui)
            root.append(when)

        self.add_help(select)
        self.add_label(select)

        if not self.spec.has_default():
            select.append(XMLNode(
                'validator', f'value != {repr(galaxy_esc(None))}',
                type='expression', message='Please verify this parameter.'))

        if root is None:
            return select
        else:
            return root

    def tests_xml(self):
        arg = str(self.arg)
        if type(self.arg) is str or type(self.arg) is bool or self.arg is None:
            arg = galaxy_esc(self.arg)
        param = XMLNode('param', name=self.name, value=arg)

        selected_branch = None
        for galaxy_name, type_ in self.branches.items():
            if self.arg in type_:
                selected_branch = galaxy_name
                break
        else:
            raise Exception("Argument %s is incompatible with %s" % (self.arg, self.branches.values()))

        conditional = XMLNode(
            'conditional',
            name=galaxy_ui_var(tag='conditional', name=self.name))

        select = XMLNode('param', name=galaxy_ui_var(name='select'),
                         value=selected_branch)
        conditional.append(select)
        conditional.append(param)
        return conditional


class SimpleCollectionCase(ParamCase):
    def __init__(self, name, spec, arg=None):
        super().__init__(name, spec, arg)

        # If we have a simple collection, we only have a single field
        self.inner_type = spec.qiime_type.fields[0]
        self.inner_spec = ParameterSpec(self.inner_type, spec.view_type)

    def inputs_xml(self):
        root = XMLNode('repeat', name=self.name,
                       title=f'{self.name}: {str(self.spec.qiime_type)}')
        self.add_help(root)

        if not self.spec.has_default():
            root.set('min', '1')

        to_repeat = identify_arg_case('element', self.inner_spec, self.arg)
        root.append(to_repeat.inputs_xml())

        return root

    def tests_xml(self):
        roots = []

        if self.arg is None:
            return None

        if isinstance(self.arg, dict):
            _arg = self.arg.values()
        else:
            _arg = self.arg

        for idx, arg in enumerate(_arg):
            root = XMLNode('repeat', name=self.name)
            to_repeat = identify_arg_case('element', self.inner_spec, arg)
            root.append(to_repeat.tests_xml())
            roots.append(root)

        return roots

    def rst_instructions(self):
        if self.arg is None:
            return super().rst_instructions()

        if len(self.arg) == 1:
            case = identify_arg_case('element', self.inner_spec,
                                     next(iter(self.arg)))
            return (f'For *"{self.name}"*:',
                    [case.rst_instructions(),
                     '(Do not insert additional values.)'])

        sub = []
        for arg in self.arg:
            case = identify_arg_case('element', self.inner_spec, arg)
            sub.append(f'Add *"element"* set to ``{case.get_rst_arg()}``')

        return (f'For *"{self.name}"*, use the ``+ {self.name}`` button to add'
                f' the corresponding values:', sub)


def make_optional(param):
    name = param.get('name')
    help_ = param.attrib.pop('help')
    label = param.attrib.pop('label')
    conditional = XMLNode('conditional', name=galaxy_ui_var(tag='conditional',
                                                            name=name))

    use_default = galaxy_ui_var(value='default')
    use_value = galaxy_ui_var(value='provide')
    picker = XMLNode('param', name=galaxy_ui_var(tag='select'),
                     type='select', help=help_, label=label)
    picker.append(XMLNode('option', 'None (Use default behavior)',
                          value=use_default, selected='true'))
    picker.append(XMLNode('option', 'Provide a value', value=use_value))
    conditional.append(picker)

    when = XMLNode('when', value=use_default)
    when.append(XMLNode('param', type='hidden', name=name,
                        value=galaxy_esc(None)))
    conditional.append(when)

    when = XMLNode('when', value=use_value)
    when.append(param)
    conditional.append(when)

    return conditional


def make_select(name, spec, choices, display_func=str):
    param = XMLNode('param', name=name, type='select')

    default = None
    if spec.has_default():
        if spec.default is None:
            param.append(XMLNode('option', 'None (Use default behavior)',
                                 value=galaxy_esc(None), selected='true'))
        else:
            default = spec.default
    elif len(choices) > 1:
        # A validator for this is added a few lines down (after options)
        # this is done to force the XML structure to look right
        param.append(XMLNode('option', 'Selection required',
                             value=galaxy_esc(None)))

    if len(choices) < 5:
        param.set('display', 'radio')

    for choice in choices:
        option = XMLNode('option', display_func(choice),
                         value=galaxy_esc(choice))
        if choice == default:
            option.set('selected', 'true')
        param.append(option)

    if not spec.has_default() and len(choices) > 1:
        param.append(XMLNode(
            'validator', f'value != {repr(galaxy_esc(None))}',
            type='expression', message='Please verify this parameter.'))

    return param
