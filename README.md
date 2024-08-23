# STAP-Mock
Mock of an ARINC 834 STAP (Simple Text Avionic Protocol) server for development and testing purposes.

# Overview
The program implements most of the commands as defined in the ARINC 834 Supplement 8 specification (Aircraft Data Interface Function), as of July 21st, 2020. It even offers a basic data generator using examples as defined in ARINC 429 Part 1 Supplement 19 specification (Digital Information Transfer System: Functional Description, Electrical Interfaces, Label Assignments, and Word Formats), as of January 21st, 2019.

# Usage
```$ python stap-server.py [configuration-filepath]```

# Configuration
The optional configuration file shall be of a JSON-Object format, reflecting the structure of the ```GLOBAL_CONFIG``` variable. It consists of basic settings of the server, simulated equipment and simulated data. The external file's contents will be merged with the default settings, which means you only need to define the parameters that you wish to change.

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| host | 'localhost' | Address to listen on. |
| port | 50600 | Port number to listen on. | 
| nl_sequence | '\\r\\n' | New-line sequence to be used in responses of the server. |
| error_codes | True | Use error codes in error responses. |
| error_messages | True | Use error messages in error responses. Possible only if error codes are activated as well. |
| stap_version | '834.8' | STAP version number as returned in the status message. |
| max_input_buffer | 1024 | Maximal length of a request from the client before rejecting it. |
| max_transmitex_words | 1023 | Maximal amount of words to be transmitted at once in the bulk approach. |
| data_generator_interval | 5.0 | Interval (in seconds) between consecutive data generation loops. |
| data_generator_word_delay | 0.05 | Additional delay (in seconds) before each generated word. |
| equipment | see below | Simulated equipment. |
| sample_data | see below | Simulated data. |

# Simulated Equipment
The program simulates at least one of each channel types: ARINC 429 receiver, ARINC 429 transmitter, ARINC 717 receiver and discrete lines. They can be specified in a complex structure (see ```GLOBAL_CONFIG``` variable in the code). Default equipment is specified as follows:
| Channel ID | Equipment Type | Parameters |
|------------|----------------|------------|
| 0 | ARINC 429 Receiver | High speed. |
| 1 | ARINC 429 Receiver | Low speed. |
| 2 | ARINC 429 Receiver | Unknown speed. |
| 10 | ARINC 429 Transmitter | High speed, free (not reserved). |
| 11 | ARINC 429 Transmitter | Low speed, owned (reserved by the current client). |
| 12 | ARINC 429 Transmitter | High speed, locked (reserved by another client). |
| 20 | ARINC 717 Receiver | 1024 words per subframe. |
| 21 | ARINC 717 Receiver | 2048 words per subframe. |
| 30 | Discrete Input | n/a |
| 31 | Discrete Output | n/a |
| 32 | Discrete Output | Free (not reserved). |
| 33 | Discrete Output | Owned (reserved by the current client). |
| 34 | Discrete Output | Locked (reserved by another client). |

# Simulated Data
ARINC 429 words as provided in the examples of the ARINC 429 Part 1 specification (Table 6-25 for BCD and Table 6-27 for BNR) are generated as soon as subscribed to by the client, no matter what ARINC 429 receiver is used.
ARINC 717 words are generated as soon as subscribed by the client, no matter what ARINC 717 receiver, subframe or word no. are used. Always a fixed value of 0x0fff.
Discrete line updates are generated as soon as subscribed by the client, no matter what Discrete Input is used. Always a fixed high state (1).

The ARINC 429 words can be modified per configuration using the ```sample_data```section. The structure is a dictionary of labels as keys and data as values. When providing the data in a configuration file, the keys must be denoted as string representation of a decimal value (please note, normally labels are noted octally), the data must be denoted as integers in their decimal form (please note, normally data is noted hexadecimally).

# Error Codes
As error codes are not specified by the standard, they are specific to this specific implementation of the STAP protocol. Please treat them as a good example, but don't relay on their values when talking to other implementations.
A few cases are not clearly stated in the specification, therefore specific implementations may differ, when it comes to that. This statement is valid for reporting an error in case a client subscribes a parameter or removes a subscription that is already (or was not) subscribed. While it is a clear error in simple cases, it gets confusing when mixing it with the ```all``` keyword (for all labels, all subframes or all words). This implementation accepts any potential conflicts if the keyword ```all``` is used. It performs strict verfication in simple cases.

# Features and Limitations
- Only integer channel identifiers are supported.
- No generic parameters are supported.
- Exit by pressing "Enter". The process will freeze for as long as at least one client connection is active (known bug).
- Support for the CRC32 mode.
- Support for the backspace key.
- Hex values of the form 0xFFFF are accepted as well, although the standard does not define them.
- Requested frequencies of generated data are ignored - everything happens in one common simple loop.
