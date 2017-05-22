# -*- coding: utf-8 -*-
__author__ = 'visarev'

from aiohttp import web
import logging

from asterisk.manager import  ManagerException
from ari_app.web_helpers import *
from urllib.parse import urlencode
import urllib

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------------------------------------------
async def ari_handle(request):
    try:
        app = request.app
        manager = app['ami']
        response = await manager.send_action({'Action': 'Command',
                                              'Command': 'sip show channels'
                                              })
        active_calls = int(re.search('(\d+) active SIP dial',str(response)).group(1))
        if active_calls is None:
            return web.Response(text="Can`t connect PBX", status=500)
        logger.info("active calls = {0}".format(active_calls))
        if active_calls > int(app['config']['general']['max_calls']):
            return web.Response(text="Too many active calls",status=422)
        req = await request.json()
        if not is_valid_req(app,req):
            return web.HTTPBadRequest()

        task = {}

        task["log_uri"] = ""
        task["record_uri"] = ""
        task["host"] = request.headers.get('X-Real-IP')
        try:
            task["service"] = req["service"]
            task["script"] = req["script"]
            task["formatted_script"] = preformat_script(task["script"])
            task["service_task_id"] = req["task_id"]
            task["phone"] = req["phone"]
            if "log_uri" in req:
                task["log_uri"] = req["log_uri"]
            if "record_uri" in req:
                task["record_uri"] = req["record_uri"]
            await app["task_queue"].put(task)
        except Exception:
            logger.exception("can`t parse values")
            return web.HTTPInternalServerError(text="Can`t parse values")
    except Exception:
        logger.exception("unknown error")
        return web.HTTPInternalServerError(text="Unknown error")

    return web.Response(text="Task was submitted for processing",status=202)

# ----------------------------------------------------------------------------------------------------------------------
async def status(request):
    app = request.app
    if app["ari_status"]["error"] == "":
        return web.HTTPOk(text="ok")
    else:
        return web.HTTPInternalServerError(text=app["ari_status"]["error"])
