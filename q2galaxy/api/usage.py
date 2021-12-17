# ----------------------------------------------------------------------------
# Copyright (c) 2018-2021, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import textwrap


from q2galaxy.core.usage import GalaxyBaseUsage
from q2galaxy.core.templaters.helpers import signature_to_galaxy
from q2galaxy.core.templaters.common import (make_tool_name_from_id,
                                             make_tool_id)


def _list_to_lines(bullets, indent):
    marker = '- '
    if len(bullets) > 1:
        marker = '#. '

    indent_str = ' ' * indent
    child_indent = indent + len(marker)

    lines = []
    for bullet in bullets:
        if type(bullet) is str:
            entry, sub = bullet, []
        else:
            entry, sub = bullet

        lines.append(''.join((indent_str, marker, entry)))
        if sub:
            lines.append('')
            lines.extend(_list_to_lines(sub, indent=child_indent))

    lines.append('')

    return lines


class GalaxyRSTInstructionsUsage(GalaxyBaseUsage):
    def __init__(self):
        super().__init__()
        self.recorder = []

    def _add_instructions(self, rst):
        self.recorder.extend(textwrap.dedent(rst).split('\n'))

    def comment(self, text):
        self._add_instructions("| " + text)

    def action(self, action, inputs, outputs):
        results = super().action(action, inputs, outputs)

        tool_name = make_tool_name_from_id(make_tool_id(action.plugin_id,
                                                        action.action_id))

        sig = action.get_action().signature
        mapped = inputs.map_variables(lambda v: v.to_interface_name())

        standard_cases = []
        advanced_cases = []
        for case in signature_to_galaxy(sig, mapped):
            if case.is_advanced():
                advanced_cases.append(case)
            else:
                standard_cases.append(case)

        instructions = [case.rst_instructions() for case in standard_cases]
        if advanced_cases:
            instructions.append(
                ('Expand the ``additional options`` section',
                 [case.rst_instructions() for case in advanced_cases])
            )
        instructions.append('Press the ``Execute`` button.')

        lines = [f'Using the ``{tool_name}`` tool:']
        lines.extend(_list_to_lines(instructions, indent=1))

        use_og_name = all(getattr(results, n).name == n for n in sig.outputs)
        if not use_og_name:
            if len(sig.outputs) > 1:
                clause = 'for each new entry in your history'
            else:
                clause = 'for the new entry in your history'
            lines.append(f'Once completed, {clause}, use '
                         f'the ``Edit`` button to set the name as follows:')

            lines.append(' (Renaming is optional, but it will make any'
                         ' subsequent steps easier to complete.)')
            lines.append('')
            lines.append(' .. list-table::')
            lines.append('    :align: left')
            lines.append('    :header-rows: 1')
            lines.append('')
            lines.append('    * - History Name')
            lines.append('      - *"Name"* to set (be sure to press ``Save``)')

        for output_name, spec in sig.outputs.items():
            try:
                var = getattr(results, output_name)
            except AttributeError:
                continue
            ext = 'qzv' if spec.qiime_type.name == 'Visualization' else 'qza'
            history_name = f"{tool_name} [...] : {output_name}.{ext}"
            if use_og_name:
                var._q2galaxy_ref = history_name
            else:
                lines.append(f'    * - ``#: {history_name}``')
                lines.append(f'      - ``{var.to_interface_name()}``')

        lines.append('')
        self._add_instructions('\n'.join(lines))

        return results

    def render(self, flush=False):
        records = self.recorder
        if flush:
            self.recorder = []
        return records
