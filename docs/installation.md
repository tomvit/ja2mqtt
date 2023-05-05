# Installation

To use ja2mqtt, you will need:

* Jablotron alarms with the control unit and the JA-121T serial interface connected to a serial port on your computer. The device uses RS485 interface, which can be connected to your computer using a [USB to RS485 adapter](https://www.aliexpress.com/w/wholesale-ch340-usb-rs485.html).

* A running instance of an MQTT broker. [Mosquitto](https://mosquitto.org/) is the recommended MQTT broker, but others should also work without issues. You can run the MQTT broker on the same machine as ja2mqtt, on a separate machine, or use an existing instance of MQTT broker if you have one.

There are two ways to install and run ja2mqtt. You can install it as a Python package in your Python environment using PyPI, or you can use a Docker image. An image is always provided for the current version. This guide assumes that you have a sub-directory created in your working directory.

```{code-block} bash
:class: copy-button
mkdir config
```

## Run Mosquitto

If you haven't set up an MQTT broker yet, follow these steps to start the Mosquitto MQTT broker in Docker. Alternatively, you can download Mosquitto binary and follow the installation process [here](https://mosquitto.org/download/).

1. Download a [sample Mosquitto configuration file](https://github.com/tomvit/ja2mqtt/blob/master/docker/mqtt-config/mosquitto.conf) from the ja2mqtt repository and save it as `config/mosquitto.yaml`. Note that this configuration file allows Mosquitto to accept connections from any client and does not enable authentication, meaning any client can access the broker:

   ```{code-block} bash
   :class: copy-button
   wget \
      https://raw.githubusercontent.com/tomvit/ja2mqtt/master/docker/mqtt-config/mosquitto.conf \
      -O config/mosquitto.yaml
   ```

2. Start Mosquitto using Docker. The below command will start Mosquitto using `docker run`. If you want to use `docker-compose` or you want to run ja2mqtt togetehr with Mosquitto in Docker, follow steps in the [Docker](#docker) section

    ```{code-block} bash
    :class: copy-button
    docker run \
      -d \
      --name mosquitto-mqtt \
      -p 1833:1833 \
      -v $(pwd)/config/mosquitto.yaml:/mosquitto/config/mosquitto.yaml \
      eclipse-mosquitto:latest
    ```

    Mosquitto MQTT will start listening on `tcp/1833` on the machine where it was started. You will need to configure ja2mqtt to connect to it later.

## Add configuration files

1. Download the sample configuration file from ja2mqtt repository as well as ja2mqtt definition file.

```{code-block} bash
:class: copy-button
wget \
  https://raw.githubusercontent.com/tomvit/ja2mqtt/master/config/sample-config.yaml \
  -O config/config.yaml && \
wget \
  https://raw.githubusercontent.com/tomvit/ja2mqtt/master/config/ja2mqtt.yaml \
  -O config/ja2mqtt.yaml
```

2. To configure ja2mqtt, you need to edit the `config.yaml` file by setting the address of your MQTT broker in `mqtt-broker.address` and adding your Jablotron topology in `topology`. You can find the details of the ja2mqtt configuration in the [Configuration](configuration/index) section. Note that you do not need to modify the `ja2mqtt.yaml` protocol definition file unless you want to customize the implementation of the JA-121T protocol. If you do need to modify it, you can find the configuration details in the [Protocol definition](configuration/ja2mqtt) section.

## Install and check configuration

1. To install ja2mqtt from the Python package index, run the following command. This will install the latest version of the package:

    ```{code-block} bash
    :class: copy-button
    pip install ja2mqtt
    ```

2. Verify that the main configuration is correct. The following command will display `config.yaml` in JSON as ja2mqtt reads it:

    ```{code-block} bash
    :class: copy-button
    ja2mqtt config main -c config/config.yaml
    ```

3. Verify that the ja2mqtt protocol definition is correct. The following command will display `ja2mqtt.yaml` in JSON after the Jinja2 templates are processed:

    ```{code-block} bash
    :class: copy-button
    ja2mqtt config ja2mqtt -c config/config.yaml
    ```


## Docker

To use ja2mqtt Docker image with your configuration, you can follow these steps. The instructions below use `docker-compose` to run both ja2mqtt and Mosquitto MQTT broker. If you already have a MQTT broker running elsewhere, you can skip the `mqtt-broker` service.

1. In your working directory, create a folder to store ja2mqtt logs.

    ```{code-block} bash
    :class: copy-button
    mkdir logs
    ```

2. Create the `docker-compose.yaml` file with the following content. The ja2mqtt container needs to have access to a serial port where your JA-121T is connected to. The code below assumes that the serial port is `/dev/ttyUSB0`. If it is connected to a different port, you need to adjust this configuration.

   ```{code-block} yaml
   :class: copy-button
   version: '3.0'
   services:
     ja2mqtt:
       container_name: ja2mqtt
       image: tomvit/ja2mqtt:latest
       volumes:
         - ./config/config.yaml:/opt/ja2mqtt/config/config.yaml
         - ./config/ja2mqtt.yaml:/opt/ja2mqtt/config/ja2mqtt.yaml
         - ./logs:/opt/ja2mqtt/logs
       devices:
         - /dev/ttyUSB0:/dev/ttyUSB0
     mqtt-broker:
       container_name: mqtt-broker
       volumes:
         - ./config/mosquitto.conf:/mosquitto/config/mosquitto.conf
       image: eclipse-mosquitto:latest
   ```

2. Run the docker-compose file as follows:

    ```{code-block} yaml
    :class: copy-button
    docker-compose up -d
    ```
