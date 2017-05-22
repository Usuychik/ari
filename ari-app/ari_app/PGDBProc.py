# -*- coding: utf-8 -*-
__author__ = 'visarev'

from psycopg2.extras import Json
import aiopg
import json
import psycopg2
import logging
from ari_app.DBProc import DBProc
from pprint import pprint
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------------------------------------------
class PGDBProc(DBProc):
    def __init__(self,engine):
        self.__engine = engine
        super().__init__()

    async def write_call_log(self,task_id,log:json):
        err = None
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = await cur.mogrify("UPDATE tasks  SET call_log = %s WHERE id= %s",(Json(log),task_id))
                    await cur.execute(sql)
        except psycopg2.Error as e:
            err = True
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = True
            logger.exception("task => {} -> unknown exception".format(task_id))
        return err

    async def set_task_status(self,task_id,status:str):
        err = None
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = await cur.mogrify("UPDATE tasks  SET status = %s WHERE id= %s",(status,task_id))
                    await cur.execute(sql)
        except psycopg2.Error as e:
            err = True
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = True
            logger.exception("task => {} -> unknown exception".format(task_id))
        return err

    async def write_script_log(self,task_id,log:json):
        err = None
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = await cur.mogrify("UPDATE tasks  SET script_log = %s WHERE id= %s", (Json(log), task_id))
                    await cur.execute(sql)
        except psycopg2.Error as e:
            err = True
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = True
            logger.exception("task => {} -> unknown exception".format(task_id))
        return err

    async def get_script(self,task_id):
        res = {}
        err = None
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "SELECT formated_script from tasks WHERE id={task_id}".format(task_id=task_id)
                    await cur.execute(sql)
                    res = (await cur.fetchone())[0]
        except psycopg2.Error as e:
            err = "can`t connect to db"
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = "can`t connect to db"
            logger.exception("task => {} -> unknown exception".format(task_id))
        return res, err

    async def write_record_name(self,task_id,filename):
        err = None
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = await cur.mogrify("UPDATE tasks  SET record_name = %s WHERE id= %s", (filename, task_id))
                    await cur.execute(sql)
        except psycopg2.Error as e:
            err = True
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = True
            logger.exception("task => {} -> unknown exception".format(task_id))
        return err

    async def save_task(self, host: str, service_task_id: str, service: str,phone: str,script: json,
                        formatted_script: json,log_uri: str,record_uri: str):
        err = None
        id = None
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "INSERT INTO tasks (service_task_id, service, phone, script, formated_script, log_uri, record_uri) "\
                        "VALUES ('{}', '{}', '{}', {}, {}, '{}', '{}') RETURNING id".format(
                        service_task_id, service, phone, Json(script), Json(formatted_script), log_uri, record_uri)
                    await cur.execute(sql)
                    id = (await cur.fetchone())[0]
        except psycopg2.Error as e:
            err = "can`t connect to db"
            logger.exception("can`t connect to db: " + str(e.pgerror))
        except:
            err = "can`t connect to db"
            logger.exception("unknown exception")
        return id, err

    async def get_task(self,task_id):
        err = None
        task = {}
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "SELECT * from tasks where id = {id}".format(id=task_id)
                    await cur.execute(sql)
                    res = await cur.fetchone()
                    task["service_task_id"] = str(res[1]).strip("\n").strip()
                    task["service"] = str(res[2]).strip("\n").strip()
                    task["phone"] = res[3]
                    task["script"] = res[4]
                    task["formatted_script"] = res[5]
        except psycopg2.Error as e:
            err = "can`t connect to db"
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = "can`t connect to db"
            logger.exception("task => {} -> unknown exception".format(task_id))
        return task, err

    async def get_log(self,service:str,service_task_id:str):
        err = None
        log = {}
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = await cur.mogrify(
                        "SELECT * FROM tasks WHERE service = %s AND service_task_id = %s ORDER BY task_date DESC LIMIT 1",
                        (service,service_task_id))
                    await cur.execute(sql)
                    result = await cur.fetchone()
                    if result is None or len(result) < 2:
                        log["task_id"] = service_task_id
                        log["status"] = "not_found"
                    else:
                        log["task_id"] = service_task_id
                        log["call_log"] = result[9]
                        log["script_log"] = result[10]
                        log["status"] = result[11]
                        log["record_name"] = result[12]
        except psycopg2.Error as e:
            err = "can`t connect to db"
            logger.exception("can`t connect to db: " + str(e.pgerror))
        except:
            err = "can`t connect to db"
            logger.exception("unknown exception")
        return log, err

    async def get_service_keys(self,service:str):
        keys = {}
        err = None
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "SELECT * FROM keys WHERE service=(SELECT id FROM services WHERE name='{servicename}')"\
                            .format(servicename=service)
                    await cur.execute(sql)
                    result = await cur.fetchone()
                    if result:
                        keys["speechkit"] = result[1]
        except psycopg2.Error as e:
            err = "can`t connect to db"
            logger.exception("can`t connect to db: " + str(e.pgerror))
        except:
            err = "unknown exception"
            logger.exception("unknown exception")
        return keys, err

    async def get_task_sounds(self,task_id):
        sounds = {}
        err = None
        try:
            async with self.__engine.acquire() as conn:
                async  with conn.cursor() as cur:
                    sql = "SELECT * FROM sounds WHERE task = {task}".format(task=task_id)
                    await cur.execute(sql)
                    for record in cur:
                        #sounds["step"] = record[1]
                        #sounds["filename"] = record[2]
                        sounds[record[1]] = record[2]
        except psycopg2.Error as e:
            err = "can`t connect to db"
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = "unknown exception"
            logger.exception("task => {} -> unknown exception".format(task_id))
        return sounds, err

    async def set_task_sound(self,task_id,step,filename):
        err = None
        try:
             async with self.__engine.acquire() as conn:
                 async  with conn.cursor() as cur:
                     sql = await cur.mogrify(
                         "INSERT INTO sounds (task,step,file_name) VALUES (%s, %s, %s)",
                         (task_id, step, filename))
                     #sql = "INSERT INTO sounds (task,step,file_name) VALUES ({}, {}, {})".format(task_id,step,filename)
                     await cur.execute(sql)
        except psycopg2.Error as e:
            err = "can`t connect to db"
            logger.exception("task => {} -> can`t connect to db: ".format(task_id) + str(e.pgerror))
        except:
            err = "unknown exception"
            logger.exception("task => {} -> unknown exception".format(task_id))
        return err

    async def check_connection(self):
        res = False
        sql = "SELECT id FROM services LIMIT 1"
        try:
            async with self.__engine.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql,timeout=1)
                    if (await cur.fetchone())[0]:
                        res = True
        except Exception:
            logger.exception("Can`t execute SQL query" )
            res = False
        return res
