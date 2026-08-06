# ----------------------------------------------------------------------------
# Copyright (c) 2018-2026, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os
import tempfile
import unittest

import lxml.etree as xml
import yaml

from q2galaxy.api.distribution import _environment_for, _write_yaml_iter
from q2galaxy.core.environment import ContainerSpec, find_environment
from q2galaxy.core.templaters.common import make_requirements


class ContainerRenderingTests(unittest.TestCase):
    def test_container_requirement_replaces_conda_requirements(self):
        reference = 'quay.io/qiime2/q2galaxy-runtime@sha256:1234'
        requirements = make_requirements(
            ContainerSpec(reference), 'q2-feature-table')

        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].tag, 'container')
        self.assertEqual(requirements[0].get('type'), 'docker')
        self.assertEqual(requirements[0].text, reference)
        self.assertNotIn(b'<requirement ', xml.tostring(requirements))

    def test_container_and_metapackage_are_mutually_exclusive(self):
        with self.assertRaisesRegex(ValueError, 'Only one'):
            find_environment(
                metapackage='qiime2-amplicon@2026.7',
                container='quay.io/qiime2/amplicon:2026.7')

    def test_explicit_container_overrides_legacy_distro_image(self):
        distro = {
            'default_docker_image': 'quay.io/qiime2/amplicon',
            'default_version': '2026.7',
        }
        expected = 'quay.io/qiime2/runtime@sha256:1234'
        self.assertEqual(
            _environment_for(distro, expected), (None, expected))

    def test_legacy_distro_image_schema_remains_supported(self):
        distro = {
            'default_docker_image': 'quay.io/qiime2/amplicon',
            'default_version': '2026.7',
        }
        self.assertEqual(
            _environment_for(distro, None),
            (None, 'quay.io/qiime2/amplicon:2026.7'))

    def test_toolshed_yaml_preserves_field_order_and_list_indentation(self):
        data = {'owner': 'q2d2', 'categories': ['One', 'Two']}
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, '.shed.yml')
            statuses = list(_write_yaml_iter(data, path))
            with open(path) as fh:
                rendered = fh.read()

        self.assertEqual(statuses[0]['status'], 'created')
        self.assertTrue(rendered.startswith('owner: q2d2\ncategories:\n'))
        self.assertIn('  - One\n  - Two\n', rendered)
        self.assertEqual(yaml.safe_load(rendered), data)

if __name__ == '__main__':
    unittest.main()
