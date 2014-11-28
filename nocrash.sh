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
justreverted=0
while :
do
   if [ "$count" -eq "0" ] && [ "$justreverted" -eq "0" ]
   then
    python ws.py first_start
   elif [ "$count" -eq "0" ] && [ "$justreverted" -eq "1" ]
   then
    python ws.py first_start reverted_mode
   else
    python ws.py
   fi

   if [ "$?" -eq "3" ]
   then
    git checkout master
    git pull
    count=0
   else
    count=$((count+1))
   fi

   if [ "$?" -eq "4" ]
   then
    crashcount=$((crashcount+1))
    if [ "$crashcount" -eq "3" ]
    then
     git checkout HEAD~1
     count=0
     justreverted=1
     crashcount=0
    else
     crashcount=$((crashcount+1))
    fi
   fi
done
