# $ ja2mqtt

[![PyPI](https://img.shields.io/pypi/v/ja2mqtt?label=PyPI)](https://pypi.org/project/ja2mqtt/)
[![Docker Image Version (tag latest semver)](https://img.shields.io/docker/v/tomvit/ja2mqtt/latest?label=Docker)](https://hub.docker.com/r/tomvit/ja2mqtt/tags)

<!-- start elevator-pitch -->

ja2mqtt is a bridge that connects a Jablotron control unit, extended with the [JA-121T RS-485 bus interface](https://www.jablotron.com/en/produkt/rs-485-bus-interface-426/), to an MQTT broker.

<p align="center">
  <img src="https://docs.google.com/drawings/export/svg?id=1GINAM_3vBMGUWAl9Av3RNUfqQ2NBDTurdChcjQiTuOw" />
</p>

ja2mqtt reads input from the JA-121T serial interface, converts it into MQTT events, and publishes them to the MQTT broker using defined MQTT topics. It utilizes a ja2mqtt definition file that outlines the implementation of the JA-121T protocol. Additionally, ja2mqtt defines MQTT events that can be converted into input for the JA-121T serial interface, such as changing the state of a section to ARMED or READY.

<!-- end elevator-pitch -->

If you do not have access to a JA-121T interface for testing, ja2mqtt offers a simulator that can simulate the interaction with the JA-121T interface. This allows you to test and verify the functionality of ja2mqtt even without the physical JA-121T interface available.

Read the [ja2mqtt documentation](https://ja2mqtt.vitvar.com) for details on how to [configure](https://ja2mqtt.vitvar.com/configuration/), [install](https://ja2mqtt.vitvar.com/installation.html) and [use](https://ja2mqtt.vitvar.com/usage.html) ja2mqtt.  

## Features

<!-- start features -->

* **Jablotron topology** definition in the YAML configuration file, including sections and their codes, names, and peripherals' positions, types, and names.
* **Jablotron events published as MQTT events**, such as section arming and disarming or peripheral state changes.
* MQTT topics that clients can use to **control sections** and **retrieve section and peripheral states**.
* **Declarative rules** that define how JA-121T serial bus protocol is implemented.
* **Automated recovery** of serial interface and MQTT broker connection failures.
* **JA-121T simulator** to simulate section state changes, peripheral state changes, and heartbeat messages.

<!-- end features -->

## Quickstart

<!-- start quickstart -->

ja2mqtt requires JA-121T bus interface, however, you can test it using the simulator if you do not have one. The Docker image comes with a sample configuration that uses the simulator. ja2mqtt also requires a running instance of [MQTT broker](https://mqtt.org/). The below steps use the [Eclipse Mosquitto MQTT broker](https://mosquitto.org/) with a sample configuration. For complete installation instructions, please refer to the [installation guide](https://ja2mqtt.vitvar.com/installation.html).

1. In your working directory, create a sub-directory `mqtt-config` and add the [`mosquitto.conf`](https://github.com/tomvit/ja2mqtt/tree/master/docker/mqtt-config/mosquitto.conf) into it.

1. Add a [`docker-compose.yaml`](https://github.com/tomvit/ja2mqtt/tree/master/docker/docker-compose.yaml) with the following content.

   ```yaml
   version: '3.0'
   services:
     ja2mqtt:
       container_name: ja2mqtt
       image: tomvit/ja2mqtt:latest
       depends_on:
         - mqtt-broker
     mqtt-broker:
       container_name: mqtt-broker
       volumes:
         - ./mqtt-config/mosquitto.conf:/mosquitto/config/mosquitto.conf
       image: eclipse-mosquitto:latest
   ```

1. Run the `docker-compose.yaml`.

   ```
   $ docker-compose up -d
   ```

2. Inspect the logs of ja2mqtt by running the following command:

   ```
   $ docker logs ja2mqtt
   ```

3. The simulator provides a straightforward Jablotron topology with two sections: `House` with code `1` and an initial state of `ARMED`, and `Garage` with code `2` and an initial state of `READY`. This topology can be used to simulate changing the state or retrieving the status of the sections. The simulator also mimics peripheral state changes and Jablotron heartbeat messages by generating "OK" messages every 10 seconds.

   You can use the below example to publish the MQTT event to retrieve the state of sections:

   ```
   $ docker exec -it ja2mqtt pub -t ja2mqtt/section/get -d pin=1234
   <-- send: ja2mqtt/section/get: {"pin": "1234", "corrid": "ca8438b82f16"}
   --> recv: ja2mqtt/section/house: {"corrid": "ca8438b82f16", "section_code": 1, "section_name": "house", "state": "ARMED"}
   --> recv: ja2mqtt/section/garage: {"corrid": "ca8438b82f16", "section_code": 2, "section_name": "garage", "state": "READY"}   
   ```

   Please refer to the [usage guide](https://ja2mqtt.vitvar.com/usage.html) for more details on how to use ja2mqtt to query and control Jablotron sections and perihperals.


4. Check the log entries in the ja2mqtt log to see the events were generated.

<!-- end quickstart -->
