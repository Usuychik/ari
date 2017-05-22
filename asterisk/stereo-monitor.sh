#!/bin/sh


E_BADARGS=65

BASENAME=`echo $4 | sed -e "s/ //g"`

R_NAME=$1
T_NAME=$2

if [ ! -f $R_NAME ]
then
        logger -s "File $R_NAME doesn't exist" 2>> /var/log/monitor.log;
fi

if [ ! -f $T_NAME ]
then
        logger -s "File $T_NAME doesn't exist" 2>> /var/log/monitor.log;
fi

logger -s "R_NAME: $R_NAME" 2>> /var/log/monitor.log;
logger -s "T_NAME: $T_NAME" 2>> /var/log/monitor.log;
logger -s "BASNEAME: $BASENAME" 2>> /var/log/monitor.log;

OUT_NAME="/var/spool/asterisk/monitor/$BASENAME.ogg"

#/usr/bin/oggenc -Q $NAME
# (/usr/bin/oggenc -Q $NAME 2>&1) >> /var/log/monitor.log
(/usr/bin/sox -M -c1 $R_NAME -c1 $T_NAME $OUT_NAME  2>&1) >> /var/log/monitor.log

rm $R_NAME
rm $T_NAME

