import qiime2.sdk
import qiime2.plugin


def import_data(type, input_path, input_format):
    # raise ValueError(f'\n{type}\n{input_path}\n{input_format}\n')
    if input_format == '':
        input_format = None

    try:
        artifact = qiime2.sdk.Artifact.import_data(type, input_path,
                                                   view_type=input_format)
    except qiime2.plugin.ValidationError as e:
        raise ValueError(
            f'There was a problem importing {input_path}: ') from e
    except Exception as e:
        raise ValueError('An unexpected error has occurred:') from e

    if input_format is None:
        input_format = artifact.format.__name__

    return artifact


# def export_data(input_path, output_path, output_format):
#     import qiime2.util
#     import qiime2.sdk
#     import distutils
#     from q2cli.core.config import CONFIG
#     result = qiime2.sdk.Result.load(input_path)
#     if output_format is None:
#         if isinstance(result, qiime2.sdk.Artifact):
#             output_format = result.format.__name__
#         else:
#             output_format = 'Visualization'
#         result.export_data(output_path)
#     else:
#         if isinstance(result, qiime2.sdk.Visualization):
#             error = '--output-format cannot be used with visualizations'
#             click.echo(CONFIG.cfg_style('error', error), err=True)
#             click.get_current_context().exit(1)
#         else:
#             source = result.view(qiime2.sdk.parse_format(output_format))
#             if os.path.isfile(str(source)):
#                 if os.path.isfile(output_path):
#                     os.remove(output_path)
#                 elif os.path.dirname(output_path) == '':
#                     # This allows the user to pass a filename as a path if they
#                     # want their output in the current working directory
#                     output_path = os.path.join('.', output_path)
#                 if os.path.dirname(output_path) != '':
#                     # create directory (recursively) if it doesn't exist yet
#                     os.makedirs(os.path.dirname(output_path), exist_ok=True)
#                 qiime2.util.duplicate(str(source), output_path)
#             else:
#                 distutils.dir_util.copy_tree(str(source), output_path)

#     output_type = 'file' if os.path.isfile(output_path) else 'directory'
#     success = 'Exported %s as %s to %s %s' % (input_path, output_format,
#                                               output_type, output_path)
#     click.echo(CONFIG.cfg_style('success', success))


builtin_map = {
    'import_data': import_data
}
