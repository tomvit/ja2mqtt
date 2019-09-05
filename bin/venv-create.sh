scriptDir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
pwd=$(pwd)
cd $scriptDir

#python3 -m venv venv 
virtualenv venv
source ./venv/bin/activate
pip install -r requirements.txt

cd $pwd
