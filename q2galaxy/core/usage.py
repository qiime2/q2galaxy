import os

from qiime2.sdk.usage import DiagnosticUsage

from q2galaxy.core.util import XMLNode


def collect_test_data(action, test_dir):
    for example in action.examples.values():
        use = TestDataUsage(write_dir=test_dir)
        example(use)
        for r in use.recorder:
            if r['source'] == 'init_data':
                path = os.path.join(test_dir, r['ref'])
                yield {'status': 'created', 'type': 'file', 'path': path}


class TestDataUsage(DiagnosticUsage):
    def __init__(self, write_dir=None):
        super().__init__()
        self.write_dir = write_dir

    def _init_helper(self, ref, factory, ext):
        basename = '.'.join([ref, ext])
        if self.write_dir is not None:
            path = os.path.join(self.write_dir, basename)
            factory().save(path)

        return basename

    def _init_data_(self, ref, factory):
        super()._init_data_(ref, factory)
        return self._init_helper(ref, factory, 'qza')

    def _init_metadata_(self, ref, factory):
        super()._init_metadata_(ref, factory)
        return self._init_helper(ref, factory, 'qza')


class TemplateTestUsage(TestDataUsage):
    def __init__(self):
        super().__init__()
        self.xml = XMLNode('test')
        self._output_lookup = {}

    def _make_params(self, action, input_opts):
        _, sig = action.get_action()
        for param, argument in input_opts.items():
            extras = {}
            if param in sig.inputs:
                extras = dict(ftype='qza')
            param_xml = XMLNode('param', name=param, value=str(argument),
                                **extras)
            self.xml.append(param_xml)

    def _make_outputs(self, output_opts):
        for output_name, output in output_opts.items():
            output_xml = XMLNode('output', name=output_name, ftype='qza')
            self._output_lookup[output] = output_xml
            self.xml.append(output_xml)

    def _action_(self, action, input_opts: dict, output_opts: dict):
        self._make_params(action, input_opts)
        self._make_outputs(output_opts)

        return super()._action_(action, input_opts, output_opts)

    def _assert_has_line_matching_(self, ref, label, path, expression):
        output = self._output_lookup[ref]

        contents = XMLNode('assert_contents')
        archive = XMLNode('has_archive_member', path=f'.*/data/{path}')
        archive.append(XMLNode('has_line_matching', expression=expression))
        contents.append(archive)
        output.append(contents)
