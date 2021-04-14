# Building your own image

To start, run the `prepare.sh` script in this directory by passing it an environment file you wish to template.

```
cd q2galaxy/docker/
./prepare.sh some_environment_file.yml
```

This will install an environment in the root of the project and use that to template out your tools.
At the end of this process, the script will echo a `docker build` command. Adapt this as desired (usually just the image name) and run it.

You should now have a working container.