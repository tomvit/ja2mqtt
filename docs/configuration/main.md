# Main configuration

The main configuration defines the serial interface where JA-121T serial bus is connected to, MQTT broker connection details, your Jablotron topology and an optional simulator.

The configuration file includes a version property that defines the version of the configuration file. ja2mqtt uses this property to check if the version is supported. The current supported version is `1.0`.

```yaml nohighlight
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

You can provide a username and password for the client to authenticate with the MQTT broker. If you don't provide them, the client will not be authenticated, and the broker must have `allow_anonymous` set to `True`. For more information, refer to the [Mosquitto configuration](https://mosquitto.org/man/mosquitto-conf-5.html).

The `protocol` property determines the communication protocol used by the client to interact with the broker. The default value is `MQTTv311`, and `MQTTv31` is also supported. However, the `MQTTv5` protocol version is currently not supported. The `transport` property can be used to specify the underlying transport protocol, which can be `tcp` (default) or `websockets`. Additionally, the `clean_session` property can be set to ensure that session data is cleared after the connection is closed.

The `keepalive` property (default is 60 seconds) defines the maximum time interval between two messages for the MQTT broker to keep track of clients that are still connected. This enables the broker to know when to send the Last Will and Testament (LWT) message for the client. You can refer to the [MQTT keepalive](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349238) for further details.

```yaml
mqtt-broker:
  address: 192.168.10.20
  port: 1883
  username: user1
  password: password1
  protocol: MQTTv311
  transport: tcp
  clean_session: False
  keepalive: 60
  reconnect_after: 30
  loop_timeout: 1
```  

## Serial interface

You must specify the configuration of the serial interface where JA-121T is connected. The required property is port, and you can also define other serial interface properties such as `baudrate`, `bytesize`, `parity`, etc. However, it is essential to note that JA-121T requires the serial interface to use specific settings that you should not alter. Changing these settings may result in communication issues with JA-121T.

You can set the `use_simulator` property to `True` (default is `False`) to use the serial interface simulator instead of the actual JA-121T device connected to the serial interface. You can use the simulator if you do not have access to Jablotron, do not have a JA-121T serial interface, or want to test how ja2mqtt works.

The `minimum_write_delay` property sets a minimum delay in seconds between two write operations to the serial interface. By default, the value is set to 1 second. This delay is important to ensure that Jablotron can process requests sequentially.

```yaml
serial:
  use_simulator: False
  minimum_write_delay: 1
  port: /dev/ttyUSB0
  baudrate: 9600
  bytesize: 8
  parity: N
  stopbits: 1
  rtscts: False
  xonxoff: False
```

## Topology

Jablotron topology consists of three lists: one for sections, one for peripherals and one for alarms. Each section has a unique name and code, while each peripheral and alarm has a name, type, and position. For instance, a section may represent an entire house or a specific area within a house, like a garage or a cellar. Jablotron offers a range of sensor types that can be set up as peripherals, including motion sensors, magnets, and keyboards, among others. This allows users to create a tailored security system that fits their specific needs.

```{caution}
You can use arbitrary names for sections, peripherals, and alarms as well as peripherals and alarm types, however, you need to use section codes and peripherals and alarms positions according to your Jablotron configuration.
```

The below example shows a topology with two sections, two peripherals and two alarms.

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
  alarm:
    - name: house/siren  
      type: siren 
      pos: 1
    - name: house/smoke 
      type: smoke 
      pos: 2
```

Ja2mqtt utilizes the Jablotron topology to define MQTT events that can be published when there are state changes or events that ja2mqtt subscribes to for clients to control Jablotron sections or retrieve the states of the sections, peripherals and alarms. See [protocol definition](ja2mqtt.md) for more details.

## Simulator

The simulator is a component of ja2mqtt that replicates the JA-121T protocol in a way that resembles the JA-121T serial bus interface. Its primary purpose is to enable testing of ja2mqtt's functionality without requiring a JA-121T serial bus interface or a Jablotron system. The simulator is utilised only when the `use_simulator` property is set to `True` in the definition of the [serial interface](#serial-interface).

The `pin` property specifies a PIN that must be entered to modify the state of the sections. The `sections` property is a list of sections that the simulator will use, each with a code and an initial state of `ARMED`, `READY`, or `OFF`. Note that the section codes must exist in the topology.

The `response_delay` property defines the time in seconds that the simulator waits after receiving a request message before sending the response. It is used when recording a new section state, for example, after the user changes its state.

The `peripherals` property is a comma-separated list of peripheral positions for which states will be generated during simulation. This information is used when generating `PRFSTATE` events, either as a response to a `PRFSTATE` request or using the time interval rule defined in `rules` sub-property.

```yaml
simulator:
  pin: 1234
  sections:
    - code: 1
      state: "ARMED"
    - code: 2
      state: "READY"
  response_delay: 0.5
  peripherals: 1,2,3
```

The `rules` property specifies rules for simulating various events based on their time occurrence. It has two sub-properties: `time_next`, which defines the time interval in seconds at which the event should occur, and `write`, which defines the data to be written to the simulated serial interface. Both sub-properties can have a value (either a string or an integer) or a {ref}`Python expression <configuration/index:python expressions>`.

For instance, consider the following YAML definition, where the first rule generates a heartbeat event every 10 seconds, and the second rule generates a random `prfstate` event once every 10-20 seconds. The `prf_random_states` function is used with a probability of `0.8` to simulate the `ON` state of any of the three peripherals, with peripheral positions `1`, `2`, and `3`. Note that the three peripheral positions should exist in the topology.

```yaml
rules:
- time_next: 10
  write: OK
- time_next: !py random(10,20)
  write: !py prf_random_states(on_prob=0.8)
```

There are following Python functions that can be used in simulator rules:

* `random(a,b)` - returns a random number between `a` and `b`
* `prf_random_states(on_prob)` - returns encoded `PRFSTATE` string that represents peripherals' states. The `on_prob` parameter defines a probability for `ON` state of the peripheral. Note that the `PRFSTATE` will include all peripherals defined in `peripherals` property of the simulator.
