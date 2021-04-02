# q2galaxy

[![](https://github.com/qiime2/q2galaxy/workflows/ci/badge.svg)](https://github.com/qiime2/q2galaxy/actions/workflows/ci.yml)

An interface for generating Galaxy tool descriptions automatically from
QIIME 2 actions.

## Known Limitations

#### Docker
  - Tools are not pre-installed, so the first job will take an inordinate amount of time as the environment is constructed.a

#### Tool Environments
  - All tools share the same environment to reduce the burden of installing one for each plugin. This is likely to change in the future.

#### TypeMap
  - Constraints for inputs are not yet implemented
  - TypeMaps are treated as naive Unions

#### Semantic Properties
  - The generated tools will not accept artifacts which have been annotated with semantic properties

#### Metadata
  - Using artifacts as metadata is not yet supported
  - When providing metadata columns, it is possible to provide the ID column which will result in an error
  - Metadata columns are not yet typed 

## Usage

Coming soon!

## Setup

Coming soon!
