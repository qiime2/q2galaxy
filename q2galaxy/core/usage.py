# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os

import qiime2
from qiime2.sdk.usage import DiagnosticUsage

from q2galaxy.core.util import XMLNode
from q2galaxy.core.templaters.helpers import signature_to_galaxy


def collect_test_data(action, test_dir):
    for example in action.examples.values():
        use = TestDataUsage(write_dir=test_dir)
        example(use)
        yield from use._created_files


class TestDataUsage(DiagnosticUsage):
    def __init__(self, write_dir=None):
        super().__init__()
        self.write_dir = write_dir
        self._created_files = []
        self._factories = {}

    def _init_helper(self, ref, factory, ext):
        basename = '.'.join([ref, ext])
        self._factories[ref] = factory
        if self.write_dir is not None:
            path = os.path.join(self.write_dir, basename)
            if not os.path.exists(path):
                self._created_files.append(
                    {'status': 'created', 'type': 'file', 'path': path})

            factory().save(path)

        return basename

    def _init_data_(self, ref, factory):
        return self._init_helper(ref, factory, 'qza')

    def _init_metadata_(self, ref, factory):
        return self._init_helper(ref, factory, 'tsv')


class TemplateTestUsage(TestDataUsage):
    def __init__(self):
        super().__init__()
        self.xml = XMLNode('test')
        self._output_lookup = {}

    def _make_params(self, action, input_opts):
        _, sig = action.get_action()

        for case in signature_to_galaxy(sig, input_opts):
            test_xml = case.tests_xml()
            if test_xml is None:
                continue
            if type(test_xml) is not list:
                test_xml = [test_xml]
            for xml in test_xml:
                self.xml.append(xml)

    def _make_outputs(self, output_opts):
        for output_name, output in output_opts.items():
            output_xml = XMLNode('output', name=output_name, ftype='qza')
            self._output_lookup[output] = output_xml
            self.xml.append(output_xml)

    def _action_(self, action, input_opts: dict, output_opts: dict):
        self._make_params(action, input_opts)
        self._make_outputs(output_opts)

        return super()._action_(action, input_opts, output_opts)

    def _get_metadata_column_(self, column_name, record):
        if record.result is None:
            return None
        md = self._factories[record.ref]()
        column = str(list(md.columns.keys()).index(column_name) + 2)
        return (record.result, column)

    def _assert_has_line_matching_(self, ref, label, path, expression):
        output = self._output_lookup[ref]

        contents = output.find('assert_contents')
        if contents is None:
            contents = XMLNode('assert_contents')
            output.append(contents)

        path = f'.*/data/{path}'
        archive = contents.find(f'has_archive_member[@path="{path}"]')
        if archive is None:
            archive = XMLNode('has_archive_member', path=path)
            contents.append(archive)

        archive.append(XMLNode('has_line_matching', expression=expression))
