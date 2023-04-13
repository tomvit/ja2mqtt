#!/bin/bash
bdir=$(realpath)
mdir=$( cd $bdir && cd ../.. && pwd)

if [ ! -f $bdir/env/bin/activate ]; then
  echo "ERROR: You must source the env.sh script from the ja2mqtt/bin directory and the Python virtual environment must exist!"
else 
  . $bdir/env/bin/activate 
  export PATH=$PATH:$mdir/ja2mqtt/bin
  export PYTHONPATH=$mdir/ja2mqtt
fi
