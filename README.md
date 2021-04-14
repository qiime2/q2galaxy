# q2galaxy

[![](https://github.com/qiime2/q2galaxy/workflows/ci/badge.svg)](https://github.com/qiime2/q2galaxy/actions/workflows/ci.yml)

An interface for generating Galaxy tool descriptions automatically from
QIIME 2 actions.

## Table of Contents
* [Known Limitations](#known-limitations)
* [Usage](#usage)
* [Galaxy Quickstart](#galaxy-quickstart)
  * [Docker](#docker-1)
  * [Planemo](#planemo)


# Known Limitations
This interface is currently in alpha, as such there are a few known problems and likely many other currently unknown issues.
If you come across something you do not see listed, please create an issue!

### Docker
  - Tools are not pre-installed, so the first job will take an inordinate amount of time as the environment is constructed.

### Tool Environments
  - All tools share the same environment to reduce the burden of installing one for each plugin. This is likely to change in the future.

### TypeMap
  - Constraints for inputs are not yet implemented
  - TypeMaps are treated as naive Unions

### Semantic Properties
  - The generated tools will not accept artifacts which have been annotated with semantic properties

### Metadata
  - Using artifacts as metadata is not yet supported
  - When providing metadata columns, it is possible to provide the ID column which will result in an error
  - Metadata columns are not yet typed


# Usage

There are three subcommands to `q2galaxy`:
 - `run`
 - `version`
 - `template`

`run` and `version` are internal details and are what the Galaxy tool XML files will call (this means that q2galaxy needs to be installed as part of the tool definition, but this is handled automatically for you).

What you will be most interested in will be the `template` subcommand, which provides four additional subcommands:
- `template`
  - `all`
  - `builtins`
  - `plugin`
  - `tests`

Each of these will take a directory to place the generated tools into. So if you wanted to create all of the tools available in your QIIME 2 environment (including builtins) you might run:

```
q2galaxy template all <some directory>
```

If you wanted to template only a single plugin, for example `qiime feature-table`, you can run:
```
q2galaxy template plugin feature_table <some directory>
```
(note that the plugin is provided as the ID form with underscores rather than dashes)


Once this is done, you can use the generated tool suites in a **modified Galaxy installation**. See below for additional details.

# Galaxy Quickstart
As this is an alpha interface, some of the changes to add Galaxy datatypes are not yet finalized, which means that for the moment, you will need to use this fork and branch of Galaxy:

- https://github.com/ebolyen/galaxy/tree/qiime2

In the future this will not be necessary.

To skip most of the setup involved in a Galaxy deployment, there are two simple ways to test drive this interface, `docker` and `planemo`.

## Docker
Docker is the more robust option at the moment for running q2galaxy. To learn more about how to use Docker, see this documentation:
 - https://docs.docker.com/desktop/
 - https://docs.docker.com/get-started/

Once you have Docker installed, you will want to pull the image from https://quay.io/repository/qiime2/q2galaxy.
On the command line this might look like:
```
docker pull quay.io/qiime2/q2galaxy
```

Once you have the image downloaded, the next step is to run the container. Our container is based on:
- https://github.com/bgruening/docker-galaxy-stable

and the instructions in that [README](https://github.com/bgruening/docker-galaxy-stable/blob/master/README.md#usage--toc) will generally apply (just remember to change the container name).
To persist any data, make sure you mount the `/export` directory as described in those instructions.

### Building the image yourself
This can be skipped if you are not interested in customizing the image.
If you are interested, see the [readme here](docker/README.md).

## Planemo
This is more useful for those building plugin tool definitions who want to take a quick look at the results.

In your QIIME 2 environment, run:
```
pip install planemo
```

Then you will want to template the tools you are interested in (see [Usage](#usage) above).
Then you can run this command (in your QIIME 2 environment)
```
planemo test --install_galaxy \
  --galaxy_branch qiime2 \
  --galaxy_source https://github.com/ebolyen/galaxy.git \
  --no_conda_auto_install \
  --no_conda_auto_init \
  <directory of tools here>

```
This command will skip installation of any tools as they are assumed to already be available in your environment. To disable that, you can omit the `--no_conda` flags from the above command.

## DIY Everything
For the very bravest, there are really only a few unusual parts to setting up the Galaxy instance. The first is to use the QIIME 2 specific fork and branch described above, and the next is to ensure that you have the correct configuration for conda and a tool config file so that your generated tools are accessible. For hints on this, see our [Dockerfile](docker/Dockerfile), and [tool_conf.xml](docker/qiime2_tool_conf.xml) and adapt as necessary.