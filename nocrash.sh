#!/bin/bash
read -p "Username: " u
export ChatExchangeU=$u
export CEU="h"
stty -echo
read -p "Password: " p
export ChatExchangeP=$p
stty echo
count=0
while :
do
   if [ "$count" -eq "0" ]
   then
    python ws.py first_start
   else
    python ws.py
   fi

   if [ "$?" -eq "3" ]
   then
     echo "exit code 3"
   fi

   count=$((count+1))
done
