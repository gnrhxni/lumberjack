#!/bin/bash

mydir=$(readlink -f "${0}" | sed -e 's#\(.*/\).*#\1#g')

init_scripts="lumberjack sluice"

echo "installing init defaults and init scripts"
for script in $init_scripts; do
    prog=$(which $script)
    sudo sed -ne '/establish defaults/, /done_defaults/ p' $mydir/$script \
	| sed -e 's#prog=.*#prog='$prog'#g' > /etc/sysconfig/$script
    sudo install -v $mydir/$script /etc/init.d/
done

