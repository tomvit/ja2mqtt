#!/bin/bash
# parent directory
pdir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )
pwd=${pwd}
cd ${pdir}

# Check if setup.py file exists
if [ ! -f "setup.py" ]; then
  echo "Error: setup.py file not found!"
  exit 1
fi

# remove the current egg-info
rm -fr ja2mqtt.egg-info

# Run setup.py to extract dependencies
echo "Running setup.py to extract dependencies..."
python setup.py egg_info >/dev/null || exit 1

# Extract dependencies from egg-info/requires.txt
echo "Extracting dependencies from egg-info/requires.txt..."
grep -v "#" ja2mqtt.egg-info/requires.txt | awk '{print $1}' > bin/requirements.txt || exit 1

echo "requirements.txt file has been created successfully!"

cd $pwd
