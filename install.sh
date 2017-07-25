#!/bin/sh

locationOfScript=$(dirname "$(readlink -e "$0")")

sed -i "s|INSTDIR=.*|INSTDIR=$locationOfScript|" fritzCallMon.sh
sed -i "s|INSTDIR=.*|INSTDIR=$locationOfScript|" fritzCallMon

cp fritzCallMon /etc/init.d/fritzCallMon
chmod +x /etc/init.d/fritzCallMon
chown root:root /etc/init.d/fritzCallMon
update-rc.d fritzCallMon defaults
