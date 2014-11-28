#!/bin/bash
read -p "Username: " u
export ChatExchangeU=$u
export CEU="h"
stty -echo
read -p "Password: " p
export ChatExchangeP=$p
stty echo
count=0
crashcount=0
while :
do
   if [ "$count" -eq "0" ]
   then
    python ws.py first_start
   else
    python ws.py
   fi

   ecode=$?

   if [ "$ecode" -eq "3" ]
   then
    git checkout master
    git pull
    count=0
   elif [ "$ecode" -eq "4" ]
   then
    count=$((count+1))
    if [ "$crashcount" -eq "2" ]
    then
     git checkout HEAD~1
     count=0
     crashcount=0
    else
     crashcount=$((crashcount+1))
    fi
   else
    count=$((count+1))
   fi

done