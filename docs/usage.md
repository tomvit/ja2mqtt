# Usage

ja2mqtt is a CLI tool that provides various commands. The command examples in this section use the configuration in `config/config.yaml` relative to your working directory. Replace `config/config.yaml` with the path to your configuration file.

## Common options

You can use the following options that are applicable to all commands:

* `-d`, `--debug`: Display debug information. This will also display the stack trace when an error occurs.
* `--no-ansi`: By default, ja2mqtt uses ANSI colors to display warnings in yellow and errors in red. You can turn off the coloring using this option.
* `--version`: Display the version of ja2mqtt.

## Logging

When you run a ja2mqtt command, logs are created in the `logs` directory by default (you can change the location of the logs in the [main configuration](configuration/main)). The logs are automatically rotated. Some commands also display additional information on the console, and the `run` command displays the log on the console as well as storing it in the log file.

You can increase the verbosity of the logs by using the `--debug` option.

```{note}
ja2mqtt does not perform any housekeeping of the logs. You will need to remove old logs manually or use your own script to manage them to ensure sufficient space on your storage.
```

## Configuration commands

Use configuration commands to explore configuration that ja2mqtt uses including main configuration, protocol definition, their validation and environment variables.

* **Display main configuration**

    ```{code-block} bash
    :class: copy-button
    ja2mqtt config main -c config/config.yaml
    ```

* **Display protocol definition** after Jinja2 templates are processed.

    ```{code-block} bash
    :class: copy-button
    ja2mqtt config ja2mqtt -c config/config.yaml
    ```

* **List MQTT topics** that ja2mqtt publishes and is subsribed to.

    ```{code-block} bash
    :class: copy-button
    ja2mqtt config topics -c config/config.yaml
    ```

* **List environment variables** that ja2mqtt uses as default values for some options.

    ```{code-block} bash
    :class: copy-button
    ja2mqtt config env
    ```

* **Validate configurations** and display validation errors.

    ```{code-block} bash
    :class: copy-button
    ja2mqtt config validate -c config/config.yaml
    ```


## Run command

TODO

## Query commands

TODO
