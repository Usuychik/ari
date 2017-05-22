#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'visarev'

from panoramisk import fast_agi
from panoramisk.utils import *
import logging
import pprint
import asyncio
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
import aiohttp

logger = logging.getLogger(__name__)

class AGIException(Exception):
    pass

class AGIError(AGIException):
    pass

class AGIUnknownError(AGIError):
    pass

class AGIAppError(AGIError):
    pass

# there are several different types of hangups we can detect
# they all are derrived from AGIHangup

class AGIHangup(AGIAppError):
    pass


class AGISIGHUPHangup(AGIHangup):
    pass


class AGISIGPIPEHangup(AGIHangup):
    pass


class AGIResultHangup(AGIHangup):
    pass


class AGIDBError(AGIAppError):
    pass


class AGIUsageError(AGIError):
    pass


class AGIInvalidCommand(AGIError):
    pass

# ----------------------------------------------------------------------------------------------------------------------
class AsyncAGIHelper:
    def __init__(self,request):
        self.request = request

    async def execute(self, command, *args):
        #self.test_hangup()
        try:
            res = await self.request.send_command(command)
            logger.debug("command: " + command + "; agi response: "+ pprint.pformat(res))
            if "status_code" not in res:
                logger.error("command: " + command + "; Error app exec: " + pprint.pformat(res))
                if res["error"] == "AGIAppError":
                    raise AGIAppError
                msg = res["msg"]
                result = {'result': ('1', msg)}
                return result, msg
            code = res["status_code"]
            msg ="Ok"
            if code == 200:
                if "error" in res:
                    logger.error("Error app exec: "+pprint.pformat(res))
                    if res["error"] == "AGIResultHangup":
                        raise AGIResultHangup
                    if res["error"] == "AGIAppError":
                        raise AGIAppError
            if code == 510:
                raise AGIInvalidCommand(res["msg"])
            if code == 520:
                raise AGIUsageError(res["msg"])
            if code == 503:
                msg = "Service unavailable"
                logger.warning("Service unavailable")
            if res["status_code"] == 200 and int(res['result'][0]) == -1:
                msg = "Error executing application, or hangup"
                logger.warning(msg+": "+pprint.pformat(res))
                #raise AGIAppError("Error executing application, or hangup")

            return res, msg
        except IOError as e:
            if e.errno == 32:
                # Broken Pipe * let us go
                raise AGISIGPIPEHangup("Received SIGPIPE")
            else:
                raise

    async def getVariable(self, name):
        try:
            result, msg = await self.execute("GET VARIABLE " + name)
        except AGIResultHangup:
            result = {'result': ('1', 'hangup')}
        res, value = result['result']
        return value

    async def set_variable(self,variable,value):
        try:
            result, msg = await self.execute("SET VARIABLE {var} {val}".format(var=variable,val=value))
        except Exception:
            logger.exception("can`t set  variable")

    async def say(self,msg,voice="oksana",speed="1.0",emotion="neutral",lang="ru-Ru",key=None):
        """
        access speechkit using MRCP and speak msg to channel
        :param msg:
        :param voice:
        :param speed:
        :param emotion:
        :param lang:
        :param key: speachkit key
        :return:
        """

        if not key:
            return "No speechkit key for service"
        for i in range(1,5):
            try:
                res, msg = await self.execute(
                    "EXEC MRCPSynth \"<speak version='1.0' xml:lang='{lang}' xmlns='http://www.w3.org/2001/10/synthesis' key='{key}' "
                    "voice='{voice}' speed='{speed}' emotion='{emotion}'><p><s>{msg}</s></p></speak>\"".format(
                        lang=lang, key=key, voice=voice, emotion=emotion, msg=msg, speed=speed))
                if "Service unavailable" not in msg:
                    break
            except AGIAppError:
                asyncio.sleep(0.2)
        return msg

    async def __http_classify(self,msg,classifier,host,port,key):
        """
        access NLU classificator using HTTP
        :param msg:
        :param classifier:
        :param host:
        :param port:
        :param key: speechkit key
        :return:
        """
        res = ""
        err = None
        try:
            async with aiohttp.ClientSession() as session:
                uri='http://{host}:{port}/classifiers/{classifier}/classify?uuid={key}&utterance={msg}'.format(
                    host=host,port=port,classifier=classifier,key=key,msg=msg
                )
                async with session.get(uri) as resp:
                    if int(resp.status) == 200:
                        res = await resp.text()
                        res = res.rstrip("\n")
                    else:
                        err  = "can`t access classificator"
        except:
            err = "can`t access classificator"
            logger.exception("can`t access classificator")
        return res, err

    async def recognize(self, topic="general", lang="ru-Ru", classifier="", nlu_conf={}, key=None):
        """
         access speechkit using MRCP and listen to channel
        :param topic:
        :param lang:
        :param classifier:
        :param nlu_conf:
        :param key: speechkit key
        :return:
        """
        err = None
        result = {"classifier_res" : "",
                  "recog_res" : "",
                  "confidence":""
                 }

        if not key:
            err="No speechkit key for service"
            return result, err

        # check if classifier exist in config and not empty
        if classifier != "" and classifier in nlu_conf.sections():
            if nlu_conf[classifier]["type"] == "http":
                for i in range(1, 2):
                    try:
                        res, msg = await self.execute(
                            "EXEC MRCPRecog \"<yandex topic='{topic}' lang='{lang}' nluHand='classify_{classifier}' key='{key}'\",t=2000&b=1&ct=0.6".format(
                                topic=topic, lang=lang, classifier=classifier,key=key
                            )
                        )
                        if "Service unavailable" not in msg:
                            break
                    except AGIAppError:
                        asyncio.sleep(0.2)
                recogstatus = await self.getVariable("RECOGSTATUS")
                logger.debug("RECOGSTATUS: " + str(recogstatus))
                if "OK" in recogstatus:
                    recog_data = await self.getVariable("RECOG_RESULT")
                    logger.debug("RECOG_RESULT: " + str(recog_data))
                    try:
                        if "xml" in recog_data:
                            root = ElementTree.fromstring(recog_data)
                            root = root.find("interpretation")
                            result["confidence"] = root.get("confidence")
                            result["recog_res"] = root.find("input").text
                            class_res, err = await self.__http_classify(result["recog_res"],classifier,nlu_conf[classifier]["host"],
                                                                  nlu_conf[classifier]["port"],nlu_conf[classifier]["key"])
                            result["classifier_res"] = class_res
                    except ParseError:
                        logger.exception("cant parse RECOG_RESULT")
                        err = "cant get recognition result"
                else:
                    err = "cant get recognition result"
        else:
            for i in range(1, 2):
                try:
                    res, msg = await self.execute(
                        "EXEC MRCPRecog \"<yandex topic='{topic}' lang='{lang}' nluHand='classify_{classifier}' key='{key}'\",t=2000&b=1&ct=0.6".format(
                                topic=topic, lang=lang, classifier=classifier,key=key
                            )
                    )
                    if "Service unavailable" not in msg:
                        break
                except AGIAppError:
                    asyncio.sleep(0.2)
            recogstatus = await self.getVariable("RECOGSTATUS")
            logger.debug("RECOGSTATUS: " + str(recogstatus))
            if "OK" in recogstatus:
                recog_data = await self.getVariable("RECOG_RESULT")
                logger.debug("RECOG_RESULT: " + str(recog_data))
                try:
                    if "xml" in recog_data:
                        root = ElementTree.fromstring(recog_data)
                        root = root.find("interpretation")
                        result["confidence"] = root.get("confidence")
                        result["recog_res"] = root.find("input").text
                except ParseError:
                    logger.exception("cant parse RECOG_RESULT")
                    err = "cant get recognition result"
            else:
                err = "cant get recognition result"
        return result, err

    async def say_and_recognize(self, msg, voice="oksana", speed="1.0", emotion="neutral", topic="general", lang="ru-Ru", classifier="", nlu_conf={}, key=None):
        err = None
        result = {"classifier_res": "",
                  "recog_res": "",
                  "confidence": ""
                  }

        if not key:
            err = "No speechkit key for service"
            return result, err

        # check if classifier exist in config and not empty
        if classifier != "" and classifier in nlu_conf.sections():
            if nlu_conf[classifier]["type"] == "http":
                for i in range(1, 5):
                    try:
                        res, msg = await self.execute(
                            "EXEC SynthAndRecog \"<speak version='1.0' xml:lang='{lang}' xmlns='http://www.w3.org/2001/10/synthesis' key='{key}' "
                    "voice='{voice}' speed='{speed}' emotion='{emotion}'><p><s>{msg}</s></p></speak>\","
                            "\"<yandex topic='{topic}' lang='{lang}' nluHand='classify_{classifier}' key='{key}'\",t=2000&b=1&ct=0.6&sl=0.2".format(
                                voice=voice, emotion=emotion, msg=msg, speed=speed, topic=topic, lang=lang, classifier=classifier, key=key
                            )
                        )
                        if "Service unavailable" not in msg:
                            break
                    except AGIAppError:
                        asyncio.sleep(0.2)
                recogstatus = await self.getVariable("RECOG_STATUS")
                logger.debug("RECOG_STATUS: " + str(recogstatus))
                if "OK" in recogstatus:
                    recog_data = await self.getVariable("RECOG_RESULT")
                    logger.debug("RECOG_RESULT: " + str(recog_data))
                    try:
                        if "xml" in recog_data:
                            root = ElementTree.fromstring(recog_data)
                            root = root.find("interpretation")
                            result["confidence"] = root.get("confidence")
                            result["recog_res"] = root.find("input").text
                            class_res, err = await self.__http_classify(result["recog_res"], classifier,
                                                                        nlu_conf[classifier]["host"],
                                                                        nlu_conf[classifier]["port"],
                                                                        nlu_conf[classifier]["key"])
                            logger.debug("NLU result: " + class_res)
                            result["classifier_res"] = class_res
                    except ParseError:
                        logger.exception("cant parse RECOG_RESULT")
                        err = "cant get recognition result"
                else:
                    err = "cant get recognition result"
        else:
            for i in range(1, 5):
                try:
                    res, msg = await self.execute(
                        "EXEC MRCPRecog \"<speak version='1.0' xml:lang='{lang}' xmlns='http://www.w3.org/2001/10/synthesis' key='{key}' "
                    "voice='{voice}' speed='{speed}' emotion='{emotion}'><p><s>{msg}</s></p></speak>\","
                        "\"<yandex topic='{topic}' lang='{lang}' nluHand='classify_{classifier}' key='{key}'\",t=2000&b=1&ct=0.6&sl=0.2".format(
                            voice=voice, emotion=emotion, msg=msg, speed=speed, topic=topic, lang=lang, classifier=classifier, key=key
                        )
                    )
                    if "Service unavailable" not in msg:
                        break
                except AGIAppError:
                    asyncio.sleep(0.2)
            recogstatus = await self.getVariable("RECOG_STATUS")
            logger.debug("RECOG_STATUS: " + str(recogstatus))
            if "OK" in recogstatus:
                recog_data = await self.getVariable("RECOG_RESULT")
                logger.debug("RECOG_RESULT: " + str(recog_data))
                try:
                    if "xml" in recog_data:
                        root = ElementTree.fromstring(recog_data)
                        root = root.find("interpretation")
                        result["confidence"] = root.get("confidence")
                        result["recog_res"] = root.find("input").text
                except ParseError:
                    logger.exception("cant parse RECOG_RESULT")
                    err = "cant get recognition result"
            else:
                err = "cant get recognition result"
        return result, err

    async def answer(self):
        await self.execute("ANSWER")


    async def hangup(self):
        #hangup call
        await self.execute("HANGUP")

    async def getDMTF(self,sound,digits:list):
        # if not key:
        #     return "No speechkit key for service"
        # res,msg = await self.execute(
        #     "EXEC MRCPSynth \"<speak version='1.0' xml:lang='{lang}' xmlns='http://www.w3.org/2001/10/synthesis' "
        #     "key='{key}' voice='{voice}' speed='{speed}' emotion='{emotion}'><p><s>{msg}</s></p></speak>\",i=1234567890".format(
        #         lang=lang, key=key, voice=voice, emotion=emotion, msg=msg, speed=speed))
        max_dig = 1
        err = None
        res = ""
        for dig in digits:
            if len(dig) > max_dig:
                max_dig = len(dig)
        for i in range(1,5):
            try:
                res, msg = await self.execute("EXEC READ DTMF_DIGITS,{sound},{maxdigits}".format(sound=sound,maxdigits=max_dig))
                res = await self.getVariable("DTMF_DIGITS")
                if len(digits) == 0:
                    if str(res).strip() != "":
                        return res,err
                elif res in digits:
                    result = res
                    return result, err
            except AGIResultHangup:
                logger.exception("Can`t read dtmf digits")
                return res, err
            except Exception:
                logger.exception("Can`t read dtmf digits")
        err = "Reach max limit invalid input"
        return res,err

