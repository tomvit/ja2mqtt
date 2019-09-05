# Jablon

Jablon is a collection of software tools that build on top of Jablotron 100+ via JA-121T serial interface. 
The tools allow a third-party application to interact with Jablotron 100 by a standard RESTful interface. 

In order to use the tools, you first need to initialise your environment by running `bin/venv-create.sh` script. This will create the python
virtual environment and install all required packages. After that, you need to run `source bin/env.sh` which activates 
the virtual environment and creates various environment variables and settings.    

## JA-121T Emulator

When Jablotron 100 is not available for testing or development purposes, JA-121T emulator can be used to emulate the 
communication with the system. The emulator implements JA-121T protocol as described in the [JA-121T Bus RS-485 Interface](https://jablotron.com.hk/image/data/pdf/manuel/JA-121T.pdf).

In order to test the emulator, you can use `tcp2serial.py` that redirects a communication from a TCP connection to the emulator and back. You can run it by `tcp2emulator` command and then connect to it via `telnet localhost 8081`    
  

