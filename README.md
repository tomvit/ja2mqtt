# $ ja2mqtt

<!-- start elevator-pitch -->

ja2mqtt is a bridge that connects a Jablotron control unit, extended with the [JA-121T RS-485 bus interface](https://www.jablotron.com/en/produkt/rs-485-bus-interface-426/), to an MQTT broker.

<p align="center">
  <img src="https://docs.google.com/drawings/export/svg?id=1GINAM_3vBMGUWAl9Av3RNUfqQ2NBDTurdChcjQiTuOw" />
</p>

ja2mqtt reads input from the JA-121T serial interface, converts it into MQTT events, and publishes them to the MQTT broker using defined MQTT topics. It utilizes a ja2mqtt definition file that outlines the implementation of the JA-121T protocol. Additionally, ja2mqtt defines MQTT events that can be converted into input for the JA-121T serial interface, such as changing the state of a section to ARMED or READY.

<!-- end elevator-pitch -->

If you do not have access to a JA-121T interface for testing, ja2mqtt offers a simulator that can simulate the interaction with the JA-121T interface. This allows you to test and verify the functionality of ja2mqtt even without the physical JA-121T interface available.

Read the [ja2mqqt documentation](https://ja2mqtt.vitvar.com) for more details.  

## Features

<!-- start features -->

* Jablotron topology definition in the YAML configuration file, including sections and their codes, names, and peripherals' positions, types, and names.
* Declarative rules that define how JA-121T serial bus protocol is implemented.
* Reading events from Jablotron, such as section arming and disarming, peripheral state changes, and converting them to MQTT events.
* MQTT topics that clients can use to retrieve section and peripheral states.
* Automated recovery of serial interface and MQTT broker connection failures.
* JA-121T simulator to simulate section state changes, peripheral state changes, and heartbeat messages.

<!-- end features -->

## Quickstart

<!-- start quickstart -->

ja2mqtt requires JA-121T bus interface, however, you can test it using the simulator if you do not have one. The Docker image comes with a sample configuration that uses the simulator. The simulator provides a straightforward Jablotron topology with two sections: `House` with code `1` and an initial state of `ARMED`, and `Garage` with code `2` and an initial state of `READY`. This topology can be used to simulate changing the state or retrieving the status of the sections. The simulator also mimics peripheral state changes and Jablotron heartbeat messages by generating "OK" messages every 10 seconds.

In addition, ja2mqtt requires a running instance of [MQTT broker](https://mqtt.org/). The below steps use the [Eclipse Mosquitto MQTT broker](https://mosquitto.org/) with a sample configuration. To test ja2mqtt, follow the steps below.

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

3. Publish the MQTT event to retrieve the state of sections as follows:

   ```
   $ docker exec -it ja2mqtt pub -t ja2mqtt/section/get -d pin=1234
   <-- send: ja2mqtt/section/get: {"pin": "1234", "corrid": "ca8438b82f16"}
   --> recv: ja2mqtt/section/house: {"corrid": "ca8438b82f16", "section_code": 1, "section_name": "house", "state": "ARMED"}
   --> recv: ja2mqtt/section/garage: {"corrid": "ca8438b82f16", "section_code": 2, "section_name": "garage", "state": "READY"}   
   ```

4. Check the log entries in the ja2mqtt log again to see if the events were generated.

<!-- end quickstart -->

## Requirements and installation

To use ja2mqtt, you will need:

* Jablotron alarms with the control unit and the JA-121T serial interface connected to a serial port on your computer. The device uses RS485 interface, which can be connected to your computer using a [USB to RS485 adapter](https://www.aliexpress.com/w/wholesale-ch340-usb-rs485.html).

* A running instance of an MQTT broker. [Mosquitto](https://mosquitto.org/) is the recommended MQTT broker, but others should also work without issues. You can run the MQTT broker on the same machine as ja2mqtt, on a separate machine, or use an existing instance of MQTT broker if you have one.

* Install ja2mqtt on a computer with access to the serial port where JA-121T is connected.

   ```
   $ pip install ja2mqtt
   ```

* Download the sample configuration file and ja2mqtt definition file from the [config directory](https://github.com/tomvit/ja2mqtt/tree/master/config) of the ja2mqtt GitHub repository. In the sample configuration file, you only need to define your Jablotron topology, such as section names and their numbers.

<!-- ## Usage

ja2mqtt is a CLI that provides the following commands. You can use the `--help` option to get more information on command usage.

* `run` - the main command that reads/writes data from/to the serial interface and sends/receives MQTT events.
* `pub` - publishes MQTT events and waits for the response. It uses the correlation ID to relate the event request with the event response.
* `config main` - shows the main configuration in JSON.
* `config ja2mqtt` - shows the ja2mqtt definition file after Jinja2 templating is processed.
* `config env` - shows the environment variables used by ja2mqtt. You can define the variables in your system to set defaults for ja2mqtt options.
* `config topics` - shows publishing and subscribing topics. You can subscribe to publishing topics from your client or send subscribing topics to control the operation of your Jablotron control unit. -->
