# $ ja2mqtt

ja2mqtt is a bridge that connects a Jablotron control unit, extended with the [JA-121T RS-485 bus interface](https://www.jablotron.com/en/produkt/rs-485-bus-interface-426/), to an MQTT broker.

ja2mqtt enables the use of MQTT events to control Jablotron events, allowing for seamless integration with MQTT-based IoT systems and platforms. With this bridge, Jablotron alarms can be integrated into a larger IoT ecosystem, alongside other devices that use industry-standard protocols like ZigBee or MQTT. For example, by using ja2mqtt in conjunction with ZigBee2MQTT, Jablotron alarms and ZigBee devices can be connected in a single network and integrated with other systems such as Alexa, Tahoma, or Google Assistant, providing a unified and interoperable smart home or industrial automation solution.

## Getting Started

To use ja2mqtt, you will need:

* Jablotron alarms with the control unit and the JA-121T serial interface connected to a serial port on your computer. The device uses RS485 interface, which can be connected to your computer using a [USB to RS485 adapter](https://www.aliexpress.com/w/wholesale-ch340-usb-rs485.html).

* A running instance of an MQTT broker. [Mosquitto](https://mosquitto.org/) is the recommended MQTT broker, but others should also work without issues. You can run the MQTT broker on the same machine as ja2mqtt, on a separate machine, or use an existing instance of MQTT broker if you have one.

* Install ja2mqtt on a computer with access to the serial port where JA-121T is connected.

   ```
   $ pip install ja2mqtt
   ```

* Download the sample configuration file and ja2mqtt definition file from the [config directory](https://github.com/tomvit/ja2mqtt/tree/master/config) of the ja2mqtt GitHub repository. In the sample configuration file, you only need to define your Jablotron topology, such as section names and their numbers.

## Testing in Docker

In  order to test ja2mqtt with default configuration that uses JA-121T simulator, do the following:

1. Run the `docker-compose.yaml` provided in the [docker](https://github.com/tomvit/ja2mqtt/tree/master/docker) directory.

   ```
   $ docker-compose up -d
   ```

2. Inspect logs of ja2mqtt by running the following command:

   ```
   $ docker logs ja2mqtt -f
   ```

3. Publish the mqtt event to retrieve a state of sections as follows:

   ```
   $ docker exec -it ja2mqtt pub -t ja2mqtt/section/get -d pin=1234
   ```

4. Check log entries in the ja2mqtt log to see that the following entries are present:

   ```
   2023-04-17 21:59:46,203 [mqtt    ] [I] <-- send: ja2mqtt/section/house, data={"section_code": 1, "section_name": "house", "state": "ARMED"}
   2023-04-17 21:59:46,408 [mqtt    ] [I] <-- send: ja2mqtt/section/garage, data={"section_code": 2, "section_name": "garage", "state": "READY"}
   ```
