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

The following configuration shows the system property definitions with initial values.

```yaml
system:
  correlation_id: 'corrid'
  correlation_timeout: 1.5
  prfstate_bits: 24
```

## Jinja templates

The Jablotron topology may have multiple sections and peripherals that could have different rules but share the same parameters. To address this, ja2mqtt definition file utilizes Jinja2 templates and Jablotron topology data to define parametrized publishing and subscribing topic rules.

For instance, the following code shows how MQTT topics for all sections can be defined:

```jinja
{% for s in topology.section %}
- name: ja2mqtt/section/{{ s.name }}
  rules:
  - read: !py pattern('STATE {{ s.code }} (READY|ARMED_PART|ARMED|SERVICE|BLOCKED|OFF)')
    write:
      section_code: {{ s.code }}
      section_name: {{ s.name }}
      state: !py data.match.group(1)
{% endfor %}
```

This code uses a `for` loop to iterate through all sections in the topology and generates MQTT topics based on the specified rules.

## MQTT topics

ja2mqtt publishes events on a number of topics and subscribes to topics to receive requests to query or control Jablotron system. Any topic starts with `ja2mqtt` and is followed by a type and an optional sub-type or a location. The topic names are automatically generated based on ja2mqtt topic definition and Jablotron topology.

```{hint}
You can use the command `ja2mqtt config topics -c config.yaml` to retrieve the publishing and subscribing topics that your configuration defines.
```

### Publishing topics

ja2mqtt utilizes MQTT topics to publish state changes for both sections and peripherals. The topics include general-purpose topics such as `ja2mqtt/heartbeat`, `ja2mqtt/error`, and `ja2mqtt/response`, as well as specific topics for section and peripheral state changes. The publishing topics are defined in the `serial2mqtt` property, which apart from the topic name it also defines a set of rules that determine the data to be read from the serial interface and written to MQTT.

#### Sections

The section topics follow the format `ja2mqtt/section/{name}`, where `{name}` refers to the section name. As an example of a topic and a rule for the `house` section, suppose we have the following configuration that specifies a topic for publishing section state changes under the name `ja2mqtt/section/house`:

```yaml
- name: ja2mqtt/section/house
  rules:
  - read: !py pattern('STATE 1 (READY|ARMED_PART|ARMED|SERVICE|BLOCKED|OFF)')
    write:
      section_code: 1
      section_name: house
      state: !py data.match.group(1)
```

In this configuration, the `read` property of the rule matches the data in the serial interface using the given regular expression, which defines the possible section 1 state changes as `READY`, `ARMED_PART`, `ARMED`, `SERVICE`, `BLOCKED`, or `OFF`. Once the `read` condition is satisfied, the data is written to MQTT under the topic with the name `ja2mqtt/section/house`. The data fields that are written include the section code (set to 1), the section name (set to "house"), and the section state (set to the matched group from the regular expression).

In the `write` property, you can define arbitrary sub-properties as data to be sent to MQTT. When specifying values for the data, you can use any arbitrary values or a {ref}`Python expression <configuration/index:python expressions>`. The scope to evaluate the expression includes the `data` variable that contains the data read from the serial interface. If you use the `pattern` function in the `read` property of the rule, you can access captured groups using the [`match` object](https://docs.python.org/3/library/re.html#match-objects).

In the example, for the following serial interface data,

 ```
 STATE 1 ARMED
 ```

the topic with name `ja2mqtt/section/house` will be published with the following data:

 ```json
 {
   "section_code": 1,
   "section_name": "house",
   "state": "ARMED"
 }
 ```

#### Peripherals

The ja2mqtt definition file specifies the topics for publishing changes in peripheral states. The peripheral topics follow the format `ja2mqtt/{type}/{location}`, where `{type}` refers to the type of peripheral (e.g. motion, siren, magnet, smoke) and `{location}` refers to the location of the peripheral device (e.g. `garage`, `house/groundfloor/office`, etc.). The types and locations are taken from the Jablotron topology in the main configuration file and can be defined by the user.

Although the rules for these topics are similar to the ones for MQTT topics, ja2mqtt uses different functions to decode the peripheral states that JA-121T transmits through the serial interface as `PRFSTATE {number}`. Here, `{number}` is an octal number that encodes the peripheral states. ja2mqtt includes decoding and encoding functions for this `PRFSTATE` octal number based on the [JA-121T serial protocol](https://github.com/tomvit/ja2mqtt/tree/master/etc/JA-121T.pdf).

This topic definition provides an example of a rule for reading `PRFSTATE` and creating event data with four properties: `name`, `type`, `pos`, and `state`. The `read` property of the rule uses a Python expression with the `prf_state_change` function to detect changes in the state of a peripheral on position `3`. If a change is detected, the `write` property specifies the data to be generated for the event, including the name of the peripheral, its type, position, and state. Since the rule is only applicable to a single peripheral state change topic and the `PRFSTATE` octal number may indicate state changes for multiple peripherals, the `process_next_rule` property is included to allow for the processing of the next topic rule and the generation of events for other peripheral state changes.

Here's the example YAML configuration:

```yaml
- name: ja2mqtt/motion/garage
  rules:
  - read: !py prf_state_change(3)
    write:
      name: garage
      type: motion
      pos: 1
      state: !py data.state
    process_next_rule: True
```
### Subscribing topics

ja2mqtt subscribes to a number of topics to receive requests that a client can use to control Jablotron system.