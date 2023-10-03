# q2galaxy

[![](https://github.com/qiime2/q2galaxy/workflows/ci-dev/badge.svg)](https://github.com/qiime2/q2galaxy/actions/workflows/ci-dev.yml)

An interface for generating Galaxy tool descriptions automatically from
QIIME 2 actions.

## Table of Contents
* [Very Quick Start](#the-very-quick-start)
* [Known Limitations](#known-limitations)
* [Usage](#usage)
* [Galaxy Quickstart](#galaxy-quickstart)
  * [Docker](#docker-1)
  * [Planemo](#planemo)


# The Very Quick Start
This is not necessarily the best way to run q2galaxy, but it is the quickest way to take a peek at this interface.

**Before starting, please be aware that your history will not persist between sessions, so you must download any results you wish to keep track of.** To avoid this, use the [Docker instructions](#docker-1) instead.

First, activate your QIIME 2 environment, it will have q2galaxy already installed.
Then, install Planemo:
```
pip install planemo
```

Then create a directory to store data in for q2galaxy
```
export Q2GALAXY_DATA=$HOME/q2galaxy_data
mkdir -p $Q2GALAXY_DATA
```
Next, template out the tools in your environment:
```
q2galaxy template all $Q2GALAXY_DATA
```

Finally run planemo (this will take a while as it must build Galaxy from source, [using Docker](#docker-1) will avoid this):
```
planemo serve --install_galaxy \
  --galaxy_branch qiime2 \
  --galaxy_source https://github.com/ebolyen/galaxy.git \
  --no_conda_auto_install \
  --no_conda_auto_init \
  --no_cleanup \
  --file_path $Q2GALAXY_DATA \
  $Q2GALAXY_DATA
```

Once that has finished, navigate to [http://localhost:9090](http://localhost:9090)

## **!~ IMPORTANT ~!**
When using planemo, there is not a convenient way to persist the database which means you will lose information in your History. The above command will store the datasets in `$Q2GALAXY_DATA`, however these are not conveniently named (they will end with `.dat`) and you may need to use `qiime tools peek` to figure out what they used to be.

To avoid losing History state, consider using `Docker` instead.

# Known Limitations
This interface is currently in alpha, as such there are a few known problems and likely many other currently unknown issues.
If you come across something you do not see listed, please create an issue!

### Viewing QZV files
  - To use the `view at qiime2view` links, your Galaxy instance must be running over HTTPS with appropriate CORS headers set. Configuring those settings can be straight-forward if you are already familiar with these terms in a production environment but it is beyond the scope of these instructions.

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

Usually you will start the server on `http://localhost:8080`, but this can be changed via the `-p` parameter.

Example:
```
docker run -d -p 8080:80 -p 8021:21 -p 8022:22 -v $HOME/q2galaxy_data/:/export/ quay.io/qiime2/q2galaxy
```

### Building the image yourself
This can be skipped if you are not interested in customizing the image.
If you are interested, see the [readme here](docker/README.md).

## Planemo
This is more useful for those building plugin tool definitions who want to take a quick look at the results. Persisting history state does not appear to be possible.

In your QIIME 2 environment, run:
```
pip install planemo
```

Then you will want to template the tools you are interested in (see [Usage](#usage) above).
Then you can run this command (in your QIIME 2 environment)
```
planemo serve --install_galaxy \
  --galaxy_branch qiime2 \
  --galaxy_source https://github.com/ebolyen/galaxy.git \
  --no_conda_auto_install \
  --no_conda_auto_init \
  --database_type sqlite \
  --no_cleanup \
  --file_path <directory to store data> \
  <directory of tools here>

```
This command will skip installation of any tools as they are assumed to already be available in your environment. To disable that, you can omit the `--no_conda` flags from the above command.

Note: this command can take quite some time as it will build the Galaxy UI from source. This will involve creating a lot of node modules via webpack which may appear intimidating.

Once that is finished, the server will be running on: `http://localhost:9090`

## DIY Everything
For the very bravest, there are really only a few unusual parts to setting up the Galaxy instance. The first is to use the QIIME 2 specific fork and branch described above, and the next is to ensure that you have the correct configuration for conda and a tool config file so that your generated tools are accessible. For hints on this, see our [Dockerfile](docker/Dockerfile), and [tool_conf.xml](docker/qiime2_tool_conf.xml) and adapt as necessary.