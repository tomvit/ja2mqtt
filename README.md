# $ ja2mqtt

ja2mqtt is a bridge that connects a Jablotron control unit, extended with the [JA-121T RS-485 bus interface](https://www.jablotron.com/en/produkt/rs-485-bus-interface-426/), to an MQTT broker.

ja2mqtt reads input from the JA-121T serial interface, converts it into MQTT events, and publishes them to the MQTT broker using defined MQTT topics. It utilizes a ja2mqtt definition file that outlines the implementation of the JA-121T protocol. Additionally, ja2mqtt defines MQTT events that can be converted into input for the JA-121T serial interface, such as changing the state of a section to ARMED or READY. Each MQTT request may contain a correlation ID that is copied to the corresponding generated MQTT event.

If you do not have access to a JA-121T interface for testing, ja2mqtt offers a simulator that can simulate the interaction with the JA-121T interface. This allows you to test and verify the functionality of ja2mqtt even without the physical JA-121T interface available.

## Features

* Define Jablotron topology in the YAML configuration file, including sections with their codes, names, and peripherals' positions and names.
* Implement declarative rules in the ja2mqtt.yaml configuration file to support the serial JA-121T protocol.
* Read events from Jablotron, such as section arming and disarming, peripheral state changes, and convert them to MQTT events.
* Use MQTT events to query section and peripheral states and correlate request and response MQTT events.
* Implement automated recovery from serial interface connection failures or MQTT broker connection failures.
* JA-121T simulator that simulates section state changes, peripheral state changes and heartbeat messages.

## Testing using Docker

To test ja2mqtt with the JA-121T simulator, you can utilize the ja2mqtt Docker image that comes with pre-configured settings. The simulator provides a straightforward Jablotron topology with two sections: "House" with code "1" and an initial state of "ARMED", and "Garage" with code "2" and an initial state of "READY". This topology can be used to simulate changing the state or retrieving the status of the sections. The simulator also mimics Jablotron heartbeat messages by generating "OK" messages every 10 seconds.

To test ja2mqtt with the simulator, follow the steps below.

1. Run the `docker-compose.yaml` provided in the [docker](https://github.com/tomvit/ja2mqtt/tree/master/docker) directory.

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

## Getting Started

To use ja2mqtt, you will need:

* Jablotron alarms with the control unit and the JA-121T serial interface connected to a serial port on your computer. The device uses RS485 interface, which can be connected to your computer using a [USB to RS485 adapter](https://www.aliexpress.com/w/wholesale-ch340-usb-rs485.html).

* A running instance of an MQTT broker. [Mosquitto](https://mosquitto.org/) is the recommended MQTT broker, but others should also work without issues. You can run the MQTT broker on the same machine as ja2mqtt, on a separate machine, or use an existing instance of MQTT broker if you have one.

* Install ja2mqtt on a computer with access to the serial port where JA-121T is connected.

   ```
   $ pip install ja2mqtt
   ```

* Download the sample configuration file and ja2mqtt definition file from the [config directory](https://github.com/tomvit/ja2mqtt/tree/master/config) of the ja2mqtt GitHub repository. In the sample configuration file, you only need to define your Jablotron topology, such as section names and their numbers.

## Usage

ja2mqtt is a CLI that provides the following commands. You can use the `--help` option to get more information on command usage.

* `run` - the main command that reads/writes data from/to the serial interface and sends/receives MQTT events.
* `pub` - publishes MQTT events and waits for the response. It uses the correlation ID to relate the event request with the event response.
* `config main` - shows the main configuration in JSON.
* `config ja2mqtt` - shows the ja2mqtt definition file after Jinja2 templating is processed.
* `config env` - shows the environment variables used by ja2mqtt. You can define the variables in your system to set defaults for ja2mqtt options.
* `config topics` - shows publishing and subscribing topics. You can subscribe to publishing topics from your client or send subscribing topics to control the operation of your Jablotron control unit.
