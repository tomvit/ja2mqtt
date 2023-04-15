# $ ja2mqtt

**this is a DRAFT version, not all commands below works**

ja2mqtt is a bridge that connects a Jablotron control unit, extended with the [JA-121T RS-485 bus interface](https://www.jablotron.com/en/produkt/rs-485-bus-interface-426/), with a MQTT broker.

ja2mqtt enables the use of MQTT events to control Jablotron events, allowing for seamless integration with MQTT-based IoT systems and platforms. With this bridge, Jablotron alarms can be integrated into a larger IoT ecosystem, alongside other devices that use industry-standard protocols like ZigBee or MQTT. For example, by using ja2mqtt in conjunction with ZigBee2MQTT, Jablotron alarms and ZigBee devices can be connected in a single network and integrated with other systems such as Alexa, Tahoma, or Google Assistant, providing a unified and interoperable smart home or industrial automation solution.

## Get started

If you want to use ja2mqtt, you need to have:

* Jablotron alarms with the control unit and the JA-121T serial interface connected to a serial port of your computer. The device uses RS485 interface that you can connect to your computer by using [USB to RS485 adapter](https://www.aliexpress.com/w/wholesale-ch340-usb-rs485.html).

* Running instance of a MQTT broker. [Mosquitto](https://mosquitto.org/) is the recommended MQTT broker but others should also work without issues. You can run the MQTT broker on the same machine as ja2mqtt, on a separate machine or use an axisting instance of MQTT broker if you have any.

* Install ja2mqtt on a computer with access to the serial port where JA-121T is connected.

  ```
  pip install ja2mqtt
  ```

* Download the sample configuration file and ja2mqtt definition file from ja2mqtt GitHub repository. In the sample configuration file you only need to define your Jablotron topology such as section names and their numbers.   
