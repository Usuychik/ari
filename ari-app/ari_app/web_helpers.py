# -*- coding: utf-8 -*-
__author__ = 'visarev'

import urllib
import aiohttp
import async_timeout
import re
import json
import logging
from jsonschema import validate, ValidationError
from copy import deepcopy
from pprint import pprint
import subprocess

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------------------------------------------
def is_valid_req(app,req:json):
    """
    check request and return False if request is not valid
    :param req:
    :return: bool
    """
    try:
        validate(req,app['schema'])
    except ValidationError:
        logger.warning("Wrong request")
        return False
    return True

# ----------------------------------------------------------------------------------------------------------------------
def preformat_script(script:json):
    """
    get script and add missimg params and update message for Yandex SpeechKit platform
    :param script:
    :return:
    """
    formated_script = deepcopy(script)
    for task in formated_script:
        action = task["action"]
        if "say" in action:
            params = task["params"]
            if not "lang" in params:
                task["params"]["lang"] = "ru-RU"
            if not "voice" in params:
                task["params"]["voice"] = "oksana"
            if not "emotion" in params:
                task["params"]["emotion"] = "neutral"
            msg = str(params["msg"])
            msg = msg.replace("'"," ")
            msg = msg.replace(","," - ")
            msg = msg.replace('"'," ")
            msg = msg.replace("\n","")
            task["params"]["msg"] = msg
        elif "dtmf" in action:
            params = task["params"]
            if not "lang" in params:
                task["params"]["lang"] = "ru-RU"
            if not "voice" in params:
                task["params"]["voice"] = "oksana"
            if not "emotion" in params:
                task["params"]["emotion"] = "neutral"
            params = task["params"]
            msg = str(params["msg"])
            msg = msg.replace("'", " ")
            msg = msg.replace(",", " - ")
            msg = msg.replace('"', " ")
            msg = msg.replace("\n", "")
            task["params"]["msg"] = msg
        elif "recognize" in action:
            params = task["params"]
            if not "lang" in params:
                task["params"]["lang"] = "ru-RU"
            if not "classifier" in params:
                task["params"]["classifier"] = ""
        elif "say_and_recognize" in action:
            params = task["params"]
            if not "lang" in params:
                task["params"]["lang"] = "ru-RU"
            if not "classifier" in params:
                task["params"]["classifier"] = ""
            if not "voice" in params:
                task["params"]["voice"] = "oksana"
            if not "emotion" in params:
                task["params"]["emotion"] = "neutral"
            msg = str(params["msg"])
            msg = msg.replace("'"," ")
            msg = msg.replace(","," - ")
            msg = msg.replace('"'," ")
            msg = msg.replace("\n","")
            task["params"]["msg"] = msg
    return formated_script

# ----------------------------------------------------------------------------------------------------------------------
async def msg_to_sound(msg,lang,voice,emotion,key,filename):
    """
    converts text to soundfile using Yandex SpeechKit
    :param msg:
    :param lang:
    :param voice:
    :param emotion:
    :param key:
    :param filename:
    :return:
    """
    err = None
    msg = urllib.parse.quote(msg)
    req = "https://tts.voicetech.yandex.net/generate?text={msg}&format=wav&lang={lang}&speaker={voice}&emotion={emotion}&" \
          "key={key}".format(msg=msg,lang=lang,voice=voice,key=key,emotion=emotion)
    try:
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.get(req) as resp:
                    with open(filename+"-tmp.wav", 'wb') as fd:
                        while True:
                            chunk = await resp.content.read(10)
                            if not chunk:
                                break
                            fd.write(chunk)
                    await resp.release()
        subprocess.call(["sox", filename+"-tmp.wav", "-r", "8000", "-c", "1", filename+".wav","--norm"])
        subprocess.call(["mv",filename+".wav","/usr/share/asterisk/sounds/"])
        return err
    except:
        logger.exception("Can`t convert msg: " + msg)
        err ="Can`t convert msg: " + msg
    return err

# ----------------------------------------------------------------------------------------------------------------------
async def preproc_script(app, task_id, service, formated_script):
    """
    make some helper tasks before call
    :param app:
    :param task_id:
    :param service:
    :param formated_script:
    :return:
    """
    err = None
    db_proc = await app['db'].dbproc()
    keys, err = await db_proc.get_service_keys(service)

    if err:
        return err

    for task in formated_script:
        if "get_dtmf" in task["action"]:
            if not "speechkit" in keys:
                db_proc.set_task_status(task_id,"failed")
                return "No SpeechKit key for service {0}".format(service)
            sounds_dir = app["config"]["general"]["sounds_dir"]
            filename = "task_{task_id}_{step}".format(task_id=task_id,step=task["step"])
            fullfilename = sounds_dir + "/"+ filename
            err = await msg_to_sound(task["params"]["msg"],task["params"]["lang"],task["params"]["voice"],
                               task["params"]["emotion"],keys["speechkit"],fullfilename)
            db_proc = await db_proc.set_task_sound(task_id,task["step"],filename)
        elif "say" or "recognize" or "say_and_recognize" in task["action"]:
            if not "speechkit" in keys:
                db_proc.set_task_status(task_id,"failed")
                return "No SpeechKit key for service {0}".format(service)

    return err
