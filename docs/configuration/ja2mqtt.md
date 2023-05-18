# Protocol definition

The JA-121T protocol definition provides a definition of generic system properties, as well as two groups of MQTT topics. The first group consists of a list of topics where ja2mqtt publishes state changes as they occur in Jablotron. The second group consists of a list of topics that ja2mqtt subscribes to, which clients can use to query section and peripheral states. The protocol definition is a YAML configuration file that uses [Jinja2 template](https://jinja.palletsprojects.com/en/3.1.x/) with data from the [Jablotron topology](configuration/main:topology) provided in the main configuration file.

```{note}
The protocol definition is provided in `ja2mqtt.yaml` and you normally do not need to modify this file unless you want to change the way how JA121 protocol is implemented by ja2mqtt.
```

The definition file should include a `version` property that defines the schema version of the file. ja2mqtt validates the file against the schema of the specified version, and the valid version is `1.0`.

```yaml
version: 1.0
```

## System properties

The system properties provide a definition for the correlation ID, correlation timeout, and the number of bits in peripheral states.

The correlation ID is the field name in incoming requests (received via a topic that ja2mqtt is subscribed to) that ja2mqtt copies to the outgoing response (sent via a topic that ja2mqtt publishes). The correlation timeout is the maximum time in seconds that ja2mqtt uses to relate incoming and outgoing events and to which the correlation ID applies. When correlation ID is not present, ja2mqtt will not correlate any data.

The property `prfstate_bits` defines a number of bits in `PRFSTATE` object. This value depends on a number of peripherals that your Jablotron system uses.

The `topic_prefix` property defines a prefix for both publishing and subscribing topics. By default, the prefix is `ja2mqtt`. However, it may be useful to change the prefix when you have multiple ja2mqtt instances using a single MQTT broker, and you want to segregate events from both instances.

The following configuration shows the system property definitions with initial values.

```yaml
system:
  correlation_id: 'corrid'
  correlation_timeout: 1.5
  prfstate_bits: 24
  topic_prefix: 'ja2mqtt'
```

## Jinja templates

The Jablotron topology may have multiple sections, peripherals and alarms that could have different rules but share the same parameters. To address this, ja2mqtt definition file utilizes Jinja2 templates and Jablotron topology data to define parametrized publishing and subscribing topic rules.

For instance, the following code shows how MQTT topics for all sections can be defined:

```jinja
{% for s in topology.section %}
- name: ja2mqtt/section/{{ s.name }}
  rules:
  - read: !py section_state('STATE ({{ s.code }}) (READY|ARMED_PART|ARMED|SERVICE|BLOCKED|OFF)',1,2)
    write:
      section_code: {{ s.code }}
      section_name: {{ s.name }}
      state: !py data.state
      count: !py data.count
{% endfor %}
```

This code uses a `for` loop to iterate through all sections in the topology and generates MQTT topics based on the specified rules.

## MQTT topics

ja2mqtt publishes events on a number of topics and subscribes to topics to receive requests to query or control Jablotron system. Any topic starts with a topic prefix (`ja2mqtt` by default) and is followed by a type and an optional sub-type or a location. The topic names are automatically generated based on ja2mqtt topic definition and Jablotron topology.

```{hint}
You can use the command `ja2mqtt config topics -c config.yaml` to retrieve the publishing and subscribing topics that your configuration defines.
```

### Publishing topics

ja2mqtt utilizes MQTT topics to publish state changes for both sections and peripherals. The topics include general-purpose topics such as `ja2mqtt/heartbeat`, `ja2mqtt/error`, and `ja2mqtt/response`, as well as specific topics for section and peripheral state changes. The publishing topics are defined in the `serial2mqtt` property, which apart from the topic name it also defines a set of rules that determine the data to be read from the serial interface and written to MQTT.

#### Sections

The section topics follow the format `{prefix}/section/{name}`, where `{prefix}` is the topic prefix defined in `system` properties and `{name}` refers to the section name. As an example of a topic and a rule for the `house` section, suppose we have the following configuration that specifies a topic for publishing section state changes under the name `ja2mqtt/section/house`:

```yaml
- name: section/house
  rules:
  - read: !py section_state('STATE (1) (READY|ARMED_PART|ARMED|SERVICE|BLOCKED|OFF)',1,2)
    write:
      section_code: 1
      section_name: house
      state: !py data.state
      updated: !py data.updated
      count: !py data.count
```

In this configuration, the `read` property of the rule utilizes the built-in function `section_state` to match the data from the serial interface using the provided regular expression. The parameters `1` and `2` represent the capture groups for the state code and state name respectively. The regular expression defines the possible state changes for section 1 as `READY`, `ARMED_PART`, `ARMED`, `SERVICE`, `BLOCKED`, or `OFF`. The function `section_state` is an internal function that monitors the state changes for a section and updates the timestamp for the last change. Once the `read` condition is satisfied, the data is written to MQTT under the topic named `ja2mqtt/section/house`. The written data includes the section code (set to 1), the section name (set to "house"), the section state (derived from the `state` property of the `data` variable, which is defined by the `section_state` function and corresponds to the matched group from the regular expression), the timestamp of the most recent section state update, and the number of section state changes indicated by the `count` property.

In the `write` property, you can define arbitrary sub-properties as data to be sent to MQTT. When specifying values for the data, you can use any arbitrary values or a {ref}`Python expression <configuration/index:python expressions>`. The scope to evaluate the expression includes the `data` variable that contains the data read from the serial interface. If you use a built-in function in the `read` property of the rule, you can access various properties of the result of the function such as the [`match` object](https://docs.python.org/3/library/re.html#match-objects) that can be used for `pattern` and `section_state` functions.

In the example, for the following serial interface data,

 ```
 STATE 1 ARMED
 ```

the topic with name `ja2mqtt/section/house` will be published with the following data:

 ```json
 {
   "section_code": 1,
   "section_name": "house",
   "state": "ARMED",
   "updated": 1683727085.619606,
   "count": 123
 }
 ```

#### Peripherals and Alarms

The ja2mqtt definition file specifies the topics for publishing changes in peripheral and alarm states. The topics for peripherals follow the format `ja2mqtt/{type}/{location}`, while the alarm topics follow the format `ja2mqtt/alarm/{type}/{location}`. In these formats, `{type}` refers to the type of peripheral or alarm (e.g., motion, siren, magnet, smoke), and `{location}` refers to the location of the device (e.g., `garage`, `house/groundfloor/office`). The types and locations are extracted from the Jablotron topology in the main configuration file and can be customized by the user.

While the rules for these topics are similar to MQTT topics, ja2mqtt employs different functions to decode the peripheral states transmitted by the JA-121T device via the serial interface as `PRFSTATE {number}`. Here, `{number}` represents a hexadecimal number that encodes the peripheral states. ja2mqtt includes decoding and encoding functions for this `PRFSTATE` number, based on the [JA-121T serial protocol](https://github.com/tomvit/ja2mqtt/tree/master/etc/JA-121T.pdf). Conversely, the alarm states are read as numeric values from the serial interface.

The following example showcases a topic rule that reads the `PRFSTATE` message from the serial interface and generates event data with five properties: `name`, `type`, `pos`, `state`, and `updated`. The `read` property of the rule utilizes a Python expression with the `prf_state` function, which employs an internal peripheral state object to check for changes in the state of the peripheral at position `3` (e.g., transitioning from ON to OFF or vice versa). If a change is detected, the `write` property specifies the data to be generated for the event, including the name, type, position, state, and updated time of the peripheral. As this rule is specific to a single peripheral state change topic, and the `PRFSTATE` number may indicate state changes for multiple peripherals, the `process_next_rule` property is included to allow for the processing of the next topic rule and the generation of events for other peripheral state changes.

Below is an example YAML configuration for a peripheral of type `motion`:

```yaml
- name: motion/garage
  rules:
  - read: !py prf_state(3)
    write:
      name: garage
      type: motion
      pos: 1
      state: !py data.state
      updated: !py data.updated
      count: !py data.count
    process_next_rule: True
```

### Subscribing topics

Ja2mqtt subscribes to multiple topics to receive requests that clients can use to query or control the Jablotron system. The topic rules are defined such that the `read` property specifies the format of the event data, while the `write` property defines the string that ja2mqtt writes to the serial interface.

#### Sections

Topics for sections are in a form `{prefix}/section/{name}/{verb}` where `{prefix}` is a topic prefix, `{name}` is the section name, and `{verb}` represents a type of operation to perform, i.e. `get`, `set`, `unset`, and `setp` to retrieve a section state, arm or disarm a section or partially arm a section.

In addition, there is a topic with the name `ja2mqtt/section/get` that can be used to retrieve the state of all sections. The following example presents a rule for this topic with a `read` property that defines incoming event data with a `pin` property. The `pattern` function specifies a regular expression that the `pin` property value must match. If the value does not match, the request will not be processed, and an error will be logged. The `write` property defines a string to be written to the serial interface. The `format` function formats the string with the `pin` parameter taken from the event data. The `request_ttl` property defines a TTL (time-to-live) for the corresponding responses that will be generated as a result of the operation. A TTL value of `99` indicates that up to 99 responses will be correlated with this request. This is necessary because the JA-121T command `STATE` results in several `STATE` serial interface events generated by Jablotron, for which ja2mqtt creates publishing events. The correlation of such messages is still limited by the `correlation_timeout` system property.

```yaml
- name: section/get
  rules:
    - read:
        pin: !py pattern("^[0-9]{4}$")
      write: !py format("{pin} STATE",pin=data.pin)
      request_ttl: 99
```

#### Peripherals

To retrieve the state of peripherals, the following rule uses the `write_prf_state` function that generates the string `PRFSTATE`, which is then written to the serial interface. The function makes sure that subsequent peripheral state events will be published under the corresponding MQTT topics, regardless of the change in the peripheral state.

```yaml
- name: prfstate/get
  rules:
    - write: !py write_prf_state()
      request_ttl: 128
```

#### All states

The ja2mqtt protocol definition includes a `all/get` topic that allows retrieval of states for both sections and peripherals. The following YAML code displays the rules for this topic, which are constructed from rules of the `section/get` and `prfstate/get` topics.

```yaml
- name: all/get
  rules:
    - write: !py write_prf_state()
      request_ttl: 128
    - read:
        pin: !py pattern("^[0-9]{4}$")
      write: !py format("{pin} STATE",pin=data.pin)
      request_ttl: 99
```
