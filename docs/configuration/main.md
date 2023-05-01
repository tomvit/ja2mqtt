# Main configuration

The main configuration defines the serial interface where JA-121T serial bus is connected to, MQTT broker connection details and your Jablotron topology.

The configuration file includes a version property that defines the version of the configuration file. ja2mqtt uses this property to check if the version is supported. The current supported version is `1.0`.

```yaml
version: 1.0
```

The `ja2mqtt` property specifies the location of the protocol definition file. The file location is relative to the location of the main configuration file, and it can be stored in the same directory as the main configuration file.

```yaml
ja2mqtt: ja2mqtt.yaml
```

The `logs` property specifies the directory where the ja2mqtt logs will be stored. The directory location is relative to the location of the main configuration file. You can store logs in a subdirectory of your ja2mqtt working directory.

```yaml
logs: ../logs
```


## MQTT broker

The MQTT broker is an external system that ja2mqtt uses to publish and subscribe to events. To use the MQTT broker, you need to specify the MQTT address and an optional TCP port (default is 1883). The address can be a domain name or an IP address.

The `keepalive` property (default is 60 seconds) defines the maximum time interval between two messages for the MQTT broker to keep track of clients that are still connected. This enables the broker to know when to send the Last Will and Testament (LWT) message for the client. You can refer to the [MQTT keepalive](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349238) for further details.

```yaml
mqtt-broker:
  address: 192.168.10.20
  port: 1883
  keepalive: 60
  reconnect_after: 30
  loop_timeout: 1
```  


## Serial interface

You must specify the configuration of the serial interface where JA-121T is connected. The required property is port, and you can also define other serial interface properties such as `baudrate`, `bytesize`, `parity`, etc. However, it is essential to note that JA-121T requires the serial interface to use specific settings that you should not alter. Changing these settings may result in communication issues with JA-121T.

You can set the `use_simulator` property to `True` (default is `False`) to use the serial interface simulator instead of the actual JA-121T device connected to the serial interface. You can use the simulator if you do not have access to Jablotron, do not have a JA-121T serial interface, or want to test how ja2mqtt works.


```yaml
serial:
  use_simulator: False
  port: /dev/ttyUSB0
  baudrate: 9600
  bytesize: 8
  parity: N
  stopbits: 1
  rtscts: False
  xonxoff: False
```

## Topology

Jablotron topology consists of two lists: one for sections and another for peripherals. Each section has a unique name and code, while each peripheral has a name, type, and position. For instance, a section may represent an entire house or a specific area within a house, like a garage or a cellar. Jablotron offers a range of sensor types that can be set up as peripherals, including motion sensors, sirens, smoke detectors, magnets, and keyboards, among others. This allows users to create a tailored security system that fits their specific needs.

```{caution}
You can use arbitrary names for sections and peripherals as well as peripherals types, however, you need to use section codes and peripherals positions according to your Jablotron configuration.
```

The below example shows a topology with two sections and two peripherals.

```yaml
topology:
  section:
    - name: house
      code: 1
    - name: garage
      code: 2
  peripheral:
    - name: house/hall
      type: motion
      pos: 1
    - name: house/smoke
      type: smoke
      pos: 2
```

Ja2mqtt utilizes the Jablotron topology to define MQTT events that can be published when there are state changes or events that ja2mqtt subscribes to for clients to control Jablotron sections or retrieve the states of the sections and peripherals. See [protocol definition](ja2mqtt.md) for more details.

## Simulator

The simulator is a component of ja2mqtt that replicates the JA-121T protocol in a way that resembles the JA-121T serial bus interface. Its primary purpose is to enable testing of ja2mqtt's functionality without requiring a JA-121T serial bus interface or a Jablotron system. The simulator is utilised only when the `use_simulator` property is set to `True` in the definition of the [serial interface](#serial-interface).
