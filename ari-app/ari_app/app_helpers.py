# -*- coding: utf-8 -*-
__author__ = 'visarev'

from aiohttp import web
import configparser
import logging.config
from pprint import pprint
import re
import json
import asyncio
import urllib
from ari_app.DBConnector import DBConnector,DBType
import asterisk.manager
from asterisk.manager import  ManagerException
#from ari_app.web_handlers import *
import os

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------------------------------------------
def shutdown(loop):
    logging.info('received stop signal, cancelling tasks...')
    for task in asyncio.Task.all_tasks():
        task.cancel()
    logging.info('shutdown, exiting in a minute...')
    loop.close()

# ----------------------------------------------------------------------------------------------------------------------
async def init_db(config,loop):
    try:
        #conf = app['config']
        conf = config
        db = DBConnector()
        if "pgsql" in conf['db']['type']:
            dbtype=DBType.pgsql
        if "mysql" in conf['db']['type']:
            dbtype=DBType.mysql
        await db.connect(dbtype=dbtype,host=conf['db']['host'],port=int(conf['db']['port']),
                         user=conf['db']['user'],passwd=conf['db']['pass'],dbname=conf['db']['dbname'],loop=loop)
        #app['db'] = db
        return db
    except Exception:
        logger.exception("can`t connect to db")
        #shutdown(loop)
    return None

# ----------------------------------------------------------------------------------------------------------------------
async def check_db(db,loop):
    await asyncio.sleep(2)
    while True:
        try:
            if not await db.check_connection():
                logger.error("lost connection to DB")
                await db.reconnect()
        except:
            logger.exception("fatal exception.  Hangup app")
            shutdown(loop)
        await asyncio.sleep(1)

# ----------------------------------------------------------------------------------------------------------------------
async def close_db(db):
    await db.close()