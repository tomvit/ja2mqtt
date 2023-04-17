# $ ja2mqtt

ja2mqtt is a bridge that connects a Jablotron control unit, extended with the [JA-121T RS-485 bus interface](https://www.jablotron.com/en/produkt/rs-485-bus-interface-426/), to an MQTT broker.

ja2mqtt enables the use of MQTT events to control Jablotron events, allowing for seamless integration with MQTT-based IoT systems and platforms. With this bridge, Jablotron alarms can be integrated into a larger IoT ecosystem, alongside other devices that use industry-standard protocols like ZigBee or MQTT. For example, by using ja2mqtt in conjunction with ZigBee2MQTT, Jablotron alarms and ZigBee devices can be connected in a single network and integrated with other systems such as Alexa, Tahoma, or Google Assistant, providing a unified and interoperable smart home or industrial automation solution.

## Getting Started

To use ja2mqtt, you will need:

* Jablotron alarms with the control unit and the JA-121T serial interface connected to a serial port on your computer. The device uses RS485 interface, which can be connected to your computer using a [USB to RS485 adapter](https://www.aliexpress.com/w/wholesale-ch340-usb-rs485.html).

* A running instance of an MQTT broker. [Mosquitto](https://mosquitto.org/) is the recommended MQTT broker, but others should also work without issues. You can run the MQTT broker on the same machine as ja2mqtt, on a separate machine, or use an existing instance of MQTT broker if you have one.

* Install ja2mqtt on a computer with access to the serial port where JA-121T is connected.

* Download the sample configuration file and ja2mqtt definition file from the ja2mqtt GitHub repository. In the sample configuration file, you only need to define your Jablotron topology, such as section names and their numbers.

## Testing in Docker

In order to test ja2mqtt with default configuration that uses JA-121T simulator, do the following:

1. Run the `docker-compose.yaml` provided in the [docker](https://github.com/tomvit/ja2mqtt/tree/master/docker) directory.

   ```
   $ docker-compose up -d
   ```

2. Inspect logs of ja2mqtt by running the following command:

   ```
   $ docker logs ja2mqtt -f
   2023-04-17 21:58:05,894 [run-loop] [I] ja2mqtt, Jablotron JA-121 Serial MQTT bridge, version 2.0.0
   2023-04-17 21:58:05,894 [serial  ] [I] The simulation is enabled, events will be simulated. The serial interface is not used.
   2023-04-17 21:58:05,895 [serial  ] [D] The simulator object is <class 'ja2mqtt.components.simulator.Simulator'>: pin=1234, timeout=1, response_delay=0.5, sections=['STATE 1 ARMED', 'STATE 2 READY', 'STATE 3 False', 'STATE 4 False'], rules=[{'time': 10, 'write': 'OK'}]
   2023-04-17 21:58:05,895 [mqtt    ] [I] The MQTT client configured for mqtt-broker.
   2023-04-17 21:58:05,895 [mqtt    ] [D] The MQTT object is <class 'ja2mqtt.components.mqtt.MQTT'>: name=mqtt, address=mqtt-broker, port=1883, keepalive=60, reconnect_after=30, loop_timeout=1, connected=False.
   2023-04-17 21:58:05,903 [bridge  ] [I] The ja2mqtt definition file is /opt/ja2mqtt/config/ja2mqtt.yaml
   2023-04-17 21:58:05,903 [bridge  ] [I] There are 5 serial2mqtt and 9 mqtt2serial topics.
   2023-04-17 21:58:05,903 [bridge  ] [D] The serial2mqtt topics are: ja2mqtt/heartbeat, ja2mqtt/section/house, ja2mqtt/section/garage, ja2mqtt/error, ja2mqtt/response
   2023-04-17 21:58:05,903 [bridge  ] [D] The mqtt2serial topics are: ja2mqtt/section/get, ja2mqtt/section/house/set, ja2mqtt/section/house/setp, ja2mqtt/section/house/unset, ja2mqtt/section/house/get, ja2mqtt/section/garage/set, ja2mqtt/section/garage/setp, ja2mqtt/section/garage/unset, ja2mqtt/section/garage/get
   2023-04-17 21:58:05,906 [mqtt    ] [I] Connected to the MQTT broker at mqtt-broker:1883
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/get
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/set
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/setp
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/unset
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/house/get
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/set
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/setp
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/unset
   2023-04-17 21:58:05,906 [mqtt    ] [I] Subscribing to ja2mqtt/section/garage/get
   ```

3. Publish the mqtt event to retrieve a state of sections as follows:

   ```
   $ docker exec -it ja2mqtt pub -t ja2mqtt/section/get -d pin=1234
   ```

4. Check log entries in the ja2mqtt log:

   ```
   2023-04-17 21:59:45,696 [mqtt    ] [I] --> recv: ja2mqtt/section/get, payload={"pin": "1234"}
   2023-04-17 21:59:45,697 [bridge  ] [D] The event data parsed as JSON object: {'pin': '1234'}
   2023-04-17 21:59:45,697 [bridge  ] [D] The event data is valid according to the defined rules.
   2023-04-17 21:59:45,697 [serial  ] [D] Writing to serial: 1234 STATE
   2023-04-17 21:59:46,202 [serial  ] [D] Received data from serial: STATE 1 ARMED
   2023-04-17 21:59:46,203 [mqtt    ] [I] <-- send: ja2mqtt/section/house, data={"section_code": 1, "section_name": "house", "state": "ARMED"}
   2023-04-17 21:59:46,407 [serial  ] [D] Received data from serial: STATE 2 READY
   2023-04-17 21:59:46,408 [mqtt    ] [I] <-- send: ja2mqtt/section/garage, data={"section_code": 2, "section_name": "garage", "state": "READY"}
   2023-04-17 21:59:46,611 [serial  ] [D] Received data from serial: STATE 3 False
   2023-04-17 21:59:46,613 [bridge  ] [D] No rule found for the data: STATE 3 False
   2023-04-17 21:59:46,816 [serial  ] [D] Received data from serial: STATE 4 False
   2023-04-17 21:59:46,817 [bridge  ] [D] No rule found for the data: STATE 4 False
   ```
