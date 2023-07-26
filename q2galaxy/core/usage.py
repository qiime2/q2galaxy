# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os
import re

from qiime2.sdk.usage import Usage, UsageVariable
from qiime2.core.type.util import is_collection_type

from q2galaxy.core.util import XMLNode
from q2galaxy.core.templaters.helpers import signature_to_galaxy


def collect_test_data(action, test_dir):
    for idx, example in enumerate(action.examples.values()):
        use = GalaxyTestUsage(example_path=(action, idx), write_dir=test_dir)
        example(use)
        yield from use.created_files


class GalaxyBaseUsageVariable(UsageVariable):
    def to_interface_name(self, skip_ref=False):
        ext_map = {'artifact': 'qza',
                   'result_collection': '/',
                   'visualization': 'qzv',
                   'metadata': 'tsv',
                   'column': '',
                   'format': ''}

        if not skip_ref and hasattr(self, '_q2galaxy_ref'):
            return self._q2galaxy_ref

        ext = ext_map[self.var_type]
        if ext:
            return '.'.join([self.name.replace('_', '-'), ext])
        return self.name


class GalaxyBaseUsage(Usage):
    """Manage representation of metadata, etc, used by case handlers"""
    _USE_TSV_INDEX = False

    def usage_variable(self, name, factory, var_type):
        return GalaxyBaseUsageVariable(name, factory, var_type, self)

    def init_metadata(self, name, factory):
        var = super().init_metadata(name, factory)

        var._q2galaxy_ref = ('tsv', var.to_interface_name())

        return var

    def get_metadata_column(self, name, column_name, variable):
        var = super().get_metadata_column(name, column_name, variable)

        if type(variable._q2galaxy_ref) is list:
            raise NotImplementedError(
                "q2galaxy does not support merging before taking a column")
        if self._USE_TSV_INDEX and variable._q2galaxy_ref[0] == 'tsv':
            md = variable.execute()
            # 1-based index, 1st col is IDs, 2nd col is the first data column
            column_name = str(list(md.columns.keys()).index(column_name) + 2)

        var._q2galaxy_ref = (*variable._q2galaxy_ref, column_name)

        return var

    def view_as_metadata(self, name, variable):
        var = super().view_as_metadata(name, variable)

        var._q2galaxy_ref = ('qza', variable.to_interface_name())

        return var

    def merge_metadata(self, name, *variables):
        var = super().merge_metadata(name, *variables)

        var._q2galaxy_ref = [v.to_interface_name() for v in variables]

        return var


class GalaxyTestUsageVariable(GalaxyBaseUsageVariable):
    def __init__(self, name, factory, var_type, usage, prefix):
        super().__init__(name, factory, var_type, usage)
        self.prefix = prefix

    def write_file(self, write_dir):
        basename = self.to_interface_name(skip_ref=True)
        path = os.path.join(write_dir, basename)

        if not os.path.exists(path):
            status = {'status': 'created', 'type': 'file', 'path': path}
        else:
            status = {'status': 'updated', 'type': 'file', 'path': path}

        self.factory().save(path)
        return status

    def to_interface_name(self, skip_ref=False):
        name = super().to_interface_name(skip_ref=skip_ref)
        if type(name) is str:
            return '.'.join([self.prefix, name])
        return name

    def assert_output_type(self, semantic_type, key=None):
        semantic_type = re.escape(str(semantic_type))
        path = 'metadata.yaml'

        if key is not None:
            key = str(key)

        if self.var_type == 'result_collection' and key:
            self._key_helper(path, expression='type: EchoOutput', key=key)
            return

        self._galaxy_has_line_matching(path=path,
                                       expression=f'type: {semantic_type}')

    def assert_has_line_matching(self, path, expression, key=None):
        path = f'data\\/{path}'

        if key is not None:
            key = str(key)

        if self.var_type == 'result_collection' and key:
            self._key_helper(path, expression, key)
            return

        self._galaxy_has_line_matching(path=path,
                                       expression=expression)

    def _key_helper(self, path, expression, key):
        output = self.use.output_lookup[self.name]
        element = XMLNode('element', name=str(key), ftype="qza")
        output.append(element)

        contents = XMLNode('assert_contents')
        element.append(contents)

        path = (r'[0-9a-f]{8}-[0-9a-f]{4}-[4][0-9a-f]{3}-[89ab][0-9a-f]'
                r'{3}-[0-9a-f]{12}\/') + path
        archive = contents.find(f'has_archive_member[@path="{path}"]')
        if archive is None:
            archive = XMLNode('has_archive_member', path=path)
            contents.append(archive)

        archive.append(XMLNode('has_line_matching', expression=expression))

    def _galaxy_has_line_matching(self, path, expression):
        output = self.use.output_lookup[self.name]

        contents = output.find('assert_contents')
        if contents is None:
            contents = XMLNode('assert_contents')
            output.append(contents)

        path = (r'[0-9a-f]{8}-[0-9a-f]{4}-[4][0-9a-f]{3}-[89ab][0-9a-f]'
                r'{3}-[0-9a-f]{12}\/') + path
        archive = contents.find(f'has_archive_member[@path="{path}"]')
        if archive is None:
            archive = XMLNode('has_archive_member', path=path)
            contents.append(archive)

        archive.append(XMLNode('has_line_matching', expression=expression))


class GalaxyTestUsage(GalaxyBaseUsage):
    _USE_TSV_INDEX = True

    def __init__(self, example_path, write_dir=None):
        super().__init__()
        self.prefix = f'{example_path[0].id}.test{example_path[1]}'
        self.xml = XMLNode('test')
        self.output_lookup = {}
        self.write_dir = write_dir
        self.created_files = []

    def usage_variable(self, name, factory, var_type):
        return GalaxyTestUsageVariable(name, factory, var_type, self,
                                       self.prefix)

    def init_artifact(self, name, factory):
        var = super().init_artifact(name, factory)

        if self.write_dir is not None:
            status = var.write_file(self.write_dir)
            self.created_files.append(status)

        return var

    # TODO: might need to loop through each item in the collection, we'll see
    def init_result_collection(self, name, factory):
        var = super().init_result_collection(name, factory)

        if self.write_dir is not None:
            status = var.write_file(self.write_dir)
            self.created_files.append(status)

        return var

    def init_metadata(self, name, factory):
        var = super().init_metadata(name, factory)

        if self.write_dir is not None:
            status = var.write_file(self.write_dir)
            self.created_files.append(status)

        return var

    def action(self, action, inputs, outputs):
        vars_ = super().action(action, inputs, outputs)

        sig = action.get_action().signature
        mapped = inputs.map_variables(lambda v: v.to_interface_name())
        for case in signature_to_galaxy(sig, mapped):
            test_xml = case.tests_xml()
            if test_xml is None:
                continue
            if type(test_xml) is not list:
                test_xml = [test_xml]
            for xml in test_xml:
                self.xml.append(xml)

        for idx, (output_name, output) in enumerate(sig.outputs.items()):
            if is_collection_type(output.qiime_type):
                xml_out = XMLNode('output_collection',
                                  name=output_name,
                                  type='list')

                # for i in range(2):
                #     element = XMLNode('element', name=str(i), ftype='qza')
                #     _assert = XMLNode('assert_contents')
                #     matching = XMLNode('has_text_matching',
                #                        expression=f"{idx}: {i}")

                #     _assert.append(matching)
                #     element.append(_assert)
                #     xml_out.append(element)
            else:
                xml_out = XMLNode('output', name=output_name, ftype='qza')

            self.output_lookup[output_name] = xml_out
            self.xml.append(xml_out)

        return vars_
