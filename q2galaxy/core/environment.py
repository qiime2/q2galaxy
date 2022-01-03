# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os
import json
import pkg_resources


class CondaMeta:
    def __init__(self, prefix):
        self.prefix = prefix
        self.meta = os.path.join(self.prefix, 'conda-meta')
        self._cache = {}

        self.meta_lookup = {}
        for filename in os.listdir(self.meta):
            if filename.endswith('.json'):
                name = filename.rsplit('-', 2)[0]
                self.meta_lookup[name] = os.path.join(self.meta, filename)

        self.backup = {d.project_name: d.version
                       for d in pkg_resources.working_set}

    def __getitem__(self, package):
        if package not in self._cache:
            with open(self.meta_lookup[package]) as fh:
                self._cache[package] = json.load(fh)

        return self._cache[package]

    def iter_primary_deps(self, package):
        if package not in self.meta_lookup:
            return
        yield from (dep.split(' ')[0] for dep in self[package]['depends']
                    # Ignore conda "virtual packages"
                    # https://conda.io/projects/conda/en/latest
                    # /user-guide/tasks/manage-virtual.html
                    if not dep.startswith('__'))

    def iter_deps(self, *packages, include_self=True, _seen=None):
        if _seen is None:
            _seen = set()

        if include_self:
            for package in packages:
                yield package, self.get_version(package)

        for package in packages:
            for dependency in self.iter_primary_deps(package):
                if dependency in _seen:
                    continue
                else:
                    _seen.add(dependency)
                    yield from self.iter_deps(dependency, _seen=_seen)

    def get_version(self, package):
        if package not in self.meta_lookup:
            return self.backup[package]
        return self[package]['version']


def get_conda_prefix():
    conda_prefix = os.getenv('CONDA_PREFIX')
    if conda_prefix is None:
        raise RuntimeError("Not in a conda environment.")

    return conda_prefix


_CURRENT_META = None


def find_conda_meta():
    global _CURRENT_META
    if _CURRENT_META is None:
        prefix = get_conda_prefix()
        _CURRENT_META = CondaMeta(prefix)
    return _CURRENT_META
