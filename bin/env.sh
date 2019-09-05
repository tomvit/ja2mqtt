# jablon env file

# this script directory
export JABLON_HOME=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )

# path to jablon python modules
export PYTHONPATH=$JABLON_HOME/libs

alias tcp2emulator='$JABLON_HOME/libs/tcp2serial.py -P 8081 /dev/emulator'

# activate the environment
source $JABLON_HOME/bin/venv/bin/activate
