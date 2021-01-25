#!/bin/bash

function jumpto
{
    label=$1
    cmd=$(sed -n "/$label/{:a;n;p;ba};" $0 | grep -v ':$')
    eval "$cmd"
    exit
}

git fetch
#MERGE
git merge
if [[ $? == 0 ]]; then
    echo 'restart fritzCallMon'
    systemctl restart fritzCallMon.service
else
    echo "git merge failed"
    echo -n "Do you wanna stash your changes (y/n)? "
    old_stty_cfg=$(stty -g)
    stty raw -echo
    answer=$( while ! head -c 1 | grep -i '[ny]' ;do true ;done )
    stty $old_stty_cfg
    if echo "$answer" | grep -iq "^y" ;then
        echo ''
        git stash
        jumpto MERGE
    fi
fi
