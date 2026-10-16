# ----------------------------------------------------------------------------
# Copyright (c) 2018-2026, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from q2galaxy import __main__ as cli


class RunResourceParametersTests(unittest.TestCase):
    def invoke_run(self, plugin, inputs):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open('inputs.json', 'w') as fh:
                json.dump(inputs, fh)
            return runner.invoke(cli.root, ['run', plugin, 'example',
                                            'inputs.json'])

    def test_resources_are_not_forwarded_to_runners(self):
        resources = [
            None,
            {'__job_resource__select': 'no'},
            {'__job_resource__select': 'yes', 'processors': 4, 'mem': 16},
        ]
        for plugin in ('demux', 'tools'):
            for resource in resources:
                with self.subTest(plugin=plugin, resource=resource):
                    inputs = {'sample_size': 100}
                    if resource is not None:
                        inputs['__job_resource'] = resource
                    with patch.object(cli, 'action_runner') as action, \
                            patch.object(cli, 'builtin_runner') as builtin:
                        result = self.invoke_run(plugin, inputs)
                    self.assertEqual(result.exit_code, 0, result.output)
                    if plugin == 'tools':
                        builtin.assert_called_once_with(
                            'example', {'sample_size': 100})
                        action.assert_not_called()
                    else:
                        action.assert_called_once_with(
                            'demux', 'example', {'sample_size': 100})
                        builtin.assert_not_called()

    def test_existing_gui_and_string_cleaning_is_preserved(self):
        inputs = {
            '__q2galaxy__GUI__': {'sample_size': 100},
            'where': '__sq__sample__sq__',
            '__job_resource': {'__job_resource__select': 'no'},
        }
        with patch.object(cli, 'action_runner') as action:
            result = self.invoke_run('demux', inputs)
        self.assertEqual(result.exit_code, 0, result.output)
        action.assert_called_once_with(
            'demux', 'example', {'sample_size': 100, 'where': "'sample'"})

    def test_unrelated_and_nested_arguments_are_preserved(self):
        # Do not silently accept malformed action arguments or remove values
        # inside user data while filtering Galaxy's top-level control group.
        inputs = {
            'unknown_parameter': 100,
            '__unrelated_key': 'unchanged',
            'nested': {'__job_resource': 'user data'},
            '__job_resource': {'__job_resource__select': 'yes'},
        }
        with patch.object(cli, 'action_runner') as action:
            result = self.invoke_run('demux', inputs)
        self.assertEqual(result.exit_code, 0, result.output)
        action.assert_called_once_with('demux', 'example', {
            'unknown_parameter': 100,
            '__unrelated_key': 'unchanged',
            'nested': {'__job_resource': 'user data'},
        })
