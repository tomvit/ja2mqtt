# Usage

ja2mqtt is a CLI tool that provides various commands. The command examples in this section use the configuration in `config/config.yaml` relative to your working directory. Replace `config/config.yaml` with the path to your configuration file.

## Common options

You can use the following options that are applicable to all commands:

* `-d`, `--debug`: Display debug information. This will also display the stack trace when an error occurs.
* `--no-ansi`: By default, ja2mqtt uses ANSI colors to display warnings in yellow and errors in red. You can turn off the coloring using this option.
* `--version`: Display the version of ja2mqtt.

## Logging

When you run a ja2mqtt command, logs are created in the `logs` directory by default (you can change the location of the logs in the [main configuration](configuration/main)). The logs are automatically rotated on daily basis and logs older than 30 days are automatically deleted. Some commands also display additional information on the console, and the `run` command displays the log on the console as well as storing it in the log file.

You can increase the verbosity of the logs by using the `--debug` option.

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

    The command validates both the main configuration and protocol definition configurations against their respective JSON schemas. These schemas use custom types that are prefixed with `__` to perform specific validation. The valid values for these types are as follows:

    * `__version` - A string representing a valid schema version.
    * `__python_expr_or_int` - A Python expression or integer.
    * `__python_expr_or_str` - A Python expression or string.
    * `__python_expr_or_str_or_number`  - A Python expression or string or integer or float.

## Run command

ja2mqtt run command is the main command the performs the function of the bridge between Jablotron control unit and MQTT broker. You can use it as follows:

```{code-block} bash
:class: copy-button
ja2mqtt run -c config/config.yaml
```

The logs will be automtically displayed on the console as well as will be stored in the log files.

The command first reads the configurations, establishes connections with serial interface and MQTT broker by subscribing to defined topics. It then starts workers that read data from serial interface and MQTT events and performs operations to send events to MQTT or write data to serial interface. The below snippet shows the initial logs after the command is started with debug on.

```
2023-05-05 22:30:32,245 [run-loop] [I] ja2mqtt, Jablotron JA-121 Serial MQTT bridge, version 1.0.4
2023-05-05 22:30:32,369 [bridge  ] [I] The ja2mqtt definition file is /opt/ja2mqtt/config/ja2mqtt.yaml
2023-05-05 22:30:32,369 [bridge  ] [I] There are 19 serial2mqtt and 14 mqtt2serial topics.
2023-05-05 22:30:32,369 [bridge  ] [D] The serial2mqtt topics are: ja2mqtt/heartbeat (disabled), ja2mqtt/section/house, ja2mqtt/section/garage, ...
2023-05-05 22:30:32,369 [bridge  ] [D] The mqtt2serial topics are: ja2mqtt/section/get, ja2mqtt/prfstate/get, ja2mqtt/section/house/set, ja2mqtt/section/house/setp, ...
2023-05-05 22:30:32,370 [serial  ] [I] The serial connection configured, the port is /dev/ttyUSB0
2023-05-05 22:30:32,370 [mqtt    ] [I] The MQTT client configured for costello.
2023-05-05 22:30:32,370 [mqtt    ] [D] The MQTT object is <class 'ja2mqtt.components.mqtt.MQTT'>: name=mqtt, address=costello, port=1883, keepalive=60, reconnect_after=30, loop_timeout=1, connected=False.
2023-05-05 22:30:32,371 [serial  ] [I] Opening serial port /dev/ttyUSB0
2023-05-05 22:30:32,372 [serial  ] [D] The serial object created: Serial<id=0x7f361df6d470, open=False>(port='/dev/ttyUSB0', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1, xonxoff=False, rtscts=False, dsrdtr=False)
2023-05-05 22:30:32,375 [bridge  ] [I] Running bridge worker, reading events from the serial buffer.
2023-05-05 22:30:32,376 [mqtt    ] [I] Connected to the MQTT broker at costello:1883
2023-05-05 22:30:32,377 [mqtt    ] [I] Subscribing to ja2mqtt/section/get
2023-05-05 22:30:32,377 [mqtt    ] [I] Subscribing to ja2mqtt/prfstate/get
2023-05-05 22:30:32,377 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/set
2023-05-05 22:30:32,377 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/setp
2023-05-05 22:30:32,378 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/unset
2023-05-05 22:30:32,378 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/get
2023-05-05 22:30:32,378 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/set
2023-05-05 22:30:32,378 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/setp
2023-05-05 22:30:32,378 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/unset
2023-05-05 22:30:32,379 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/get
2023-05-05 22:30:32,379 [mqtt    ] [I] Subscribing to ja2mqtt/section/cellar/set
2023-05-05 22:30:32,379 [mqtt    ] [I] Subscribing to ja2mqtt/section/cellar/setp
2023-05-05 22:30:32,379 [mqtt    ] [I] Subscribing to ja2mqtt/section/cellar/unset
2023-05-05 22:30:32,380 [mqtt    ] [I] Subscribing to ja2mqtt/section/cellar/get
```


## Query commands

ja2mqtt offers a command that allows you to send events to the MQTT broker to control or query Jablotron via ja2mqtt.

You can use the `pub` command to publish data to an MQTT topic. For example, to retrieve all section states, use the topic `ja2mqtt/section/get` as shown below. You also need to specify input data for the event to be generated using the `-d` option, where the data is in the form `key=value`. In this case, you need to provide the `PIN` for Jablotron to process the command. The input data for the event is defined in the [protocol definition](configuration/ja2mqtt).

```
ja2mqtt pub -c config/config.yaml -t ja2mqtt/section/get -d pin=1234
<-- send: ja2mqtt/section/get: {"pin": "1234", "corrid": "eb4333c5ef21"}
--> recv: ja2mqtt/section/house: {"corrid": "eb4333c5ef21", "section_code": 1, "section_name": "house", "state": "READY"}
--> recv: ja2mqtt/section/garage: {"corrid": "eb4333c5ef21", "section_code": 2, "section_name": "garage", "state": "ARMED"}
--> recv: ja2mqtt/section/cellar: {"corrid": "eb4333c5ef21", "section_code": 3, "section_name": "cellar", "state": "ARMED"}
```

To view a list of topics that can be used, run the `ja2mqtt config topics` command. These topics can be found under the "subscribing topics" section.
