# Configuration

To set up ja2mqtt, you'll need to provide two configuration files: the main configuration and the ja2mqtt definition file. The main configuration includes essential system properties, the serial interface configuration, your Jablotron topology, and simulator configuration. Meanwhile, the definition file determines how the JA-121T protocol is converted to MQTT events and vice versa.

This guide will walk you through the process of setting up both configurations.

## Files

Both configuration files are written in YAML format, and ja2mqtt internally validates them using JSON schema. The main configuration file refers to the ja2mqtt definition file, and both files can have any name. You can use the `--config` option of the ja2mqtt CLI to specify which configuration file you want to use.

To illustrate, if your main configuration file is located in the config directory, you can use it as follows. Please note that the ja2mqtt definition file can be located in any directory and is referred to from the main configuration.

```bash
$ ja2mqtt run -c config/config.yaml
```

In this example, `config.yaml` is the name of the main configuration file, and it is located in the `config` directory. The `--config` option specifies that we want to use this file as the main configuration.

```{toctree}
:hidden:

main
ja2mqtt
```

## Python expressions

Configuration files for ja2mqtt may include Python expressions that are evaluated by the program when reading the file. These expressions can use a provided scope that includes various contextual data or functions that are available for use in Python. The resulting value of the expression is then assigned to the property where the expression is used.

The Python expression is prefixed with `!py` followed by a valid Python expression. The following YAML example illustrates this:

```yaml
foo:
  bar: !py random(10)
```

In this example, when the `bar` property is read, its value will be a random number between `0` and `10`. The `random` function must exist in the scope where the expression is evaluated. Please refer to the specific configuration documentation to see how Python expressions can be used.