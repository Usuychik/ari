# -*- coding: utf-8 -*-
__author__ = 'visarev'
from enum import Enum
import asyncio
import aiopg
import aiomysql
from ari_app.PGDBProc import PGDBProc
#from ari_app.MYSQLDBProc import MYSQLDBProc
import logging

logger = logging.getLogger(__name__)


def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


# ----------------------------------------------------------------------------------------------------------------------
class DBType(Enum):
    pgsql = 1
    mysql = 2


# ----------------------------------------------------------------------------------------------------------------------
class DBAPIConnector():
    def __init__(self,dbtype:DBType,loop):
        self.__loop = loop
        self.__engine = None
        self.__pool = None
        self.__dsn = {}
        self.__testcur = None
        self.__dbtype = dbtype
        self.__check_delay = 1
        self.__checker = None
        self.__connected = False
        self.__dbproc = None

    async def connect(self,host:str,port:int,user:str,passwd:str,dbname:str):
        self.__dsn={
            "host":host,
            "port":port,
            "user":user,
            "passwd":passwd,
            "dbname":dbname
        }
        await self.__connect()

    async def __connect(self):
        try:
            if self.__dbtype == DBType.pgsql:
                dsn = 'dbname={dbname} user={user} password={passwd} host={host} port={port}'.format(
                    dbname=self.__dsn["dbname"],user=self.__dsn["user"],passwd=self.__dsn["passwd"],
                    host=self.__dsn["host"],port=self.__dsn["port"])
                self.__engine = await aiopg.create_pool(dsn,maxsize=6,loop=self.__loop)
                self.__dbproc = PGDBProc(self.__engine)
            # elif self.__dbtype == DBType.mysql:
            #     self.__engine = await aiomysql.create_pool(db=self.__dsn["dbname"], user=self.__dsn["user"],
            #                                                password=self.__dsn["passwd"], host=self.__dsn["host"],
            #                                                port=self.__dsn["port"], maxsize=6, loop=self.__loop,autocommit=True)
            #     self.__dbproc = MYSQLDBProc(self.__engine)
            self.__connected = await self.__dbproc.check_connection()
            if self.__connected:
                logger.info("DB connected")
            self.__checker = self.__loop.call_later(self.__check_delay,
                                                    lambda: asyncio.ensure_future(self.connection_checker()))
        except:
            logger.exception("can`t connect to DB")
            self.__connected = False
            self.__engine = None

    @property
    def engine(self):
        return self.__engine

    @property
    def connected(self):
        return self.__connected

    @property
    def dbproc(self):
        """
        :return: implementation of dbproc according dbtype.
        """
        return self.__dbproc

    async def close(self):
        if self.__checker is not None:
            self.__checker.cancel()
            self.__checker = None
        self.__engine.close()
        await self.__engine.wait_closed()
        self.__engine = None

    async def connection_checker(self):
        self.__connected = await self.__dbproc.check_connection()
        if self.__connected:
            self.__checker = self.__loop.call_later(self.__check_delay,
                                                    lambda: asyncio.ensure_future(self.connection_checker()))
        else:
            logger.error("DB connection lost")
            try:
                self.__engine.close()
                await self.__engine.wait_closed()
            except:
                logger.exception("can`t close db connection")
            self.__engine = None
            await self.__connect()


# ----------------------------------------------------------------------------------------------------------------------
@singleton
class DBConnector():
    async def connect(self,dbtype:DBType,host:str,port:int,user:str,passwd:str,dbname:str,loop):
        self.__loop = loop
        self.__dbtype = dbtype
        self.__db = DBAPIConnector(dbtype=dbtype,loop=self.__loop)
        await self.__db.connect(host=host,port=port,user=user,passwd=passwd,dbname=dbname)
        if not self.__db.connected:
            raise Exception

    async def close(self):
        await self.__db.close()

    async def dbproc(self):
        """
        task_indx: current task index for tasks tables

        :return: xDBProc object
        """
        if self.__dbtype == DBType.pgsql:
            return PGDBProc(self.__db.engine)
        # if self.__dbtype == DBType.mysql:
        #     return MYSQLDBProc(self.__db.engine)






