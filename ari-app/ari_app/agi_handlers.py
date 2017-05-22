from panoramisk import fast_agi
import logging.config
import asyncio
import aiopg
from psycopg2.extras import Json
from pprint import pprint, pformat
from ari_app.AGIHelper import *
import json
import time

MAX_SCRIPT_ITER = 100

logger = logging.getLogger(__name__)



# ----------------------------------------------------------------------------------------------------------------------
async def _proc_hangup(agi:AsyncAGIHelper):
    result = {}
    result["dialstatus"] = "UNKNOWN"
    result["duration"] = 0
    result["bill_duration"] = 0
    result["wait_duration"] = 0
    try:
        result["dialstatus"] = await agi.getVariable('DIALSTATUS')
        result["duration"] = int(await agi.getVariable("CDR(duration)"))
        result["bill_duration"] = int(await agi.getVariable("CDR(billsec)"))
        result["wait_duration"] = result["duration"] - result["bill_duration"]
    except Exception:
        logger.exception("can`t  get variables")

    return result

# ----------------------------------------------------------------------------------------------------------------------
async def script_proc(request):
    log = []
    agi_helper = AsyncAGIHelper(request)
    logger.debug('AGI variables: ' + pformat(request.headers))
    task_id = await agi_helper.getVariable("TASK_ID")
    db_proc = await request.app['db'].dbproc()

    #script = await db_proc.get_script(task_id)
    service_task,err = await db_proc.get_task(task_id)
    script = service_task["formatted_script"]
    keys,err = await db_proc.get_service_keys(service_task["service"])
    task_sounds = await db_proc.get_task_sounds(task_id)

    try:
        script_iter = 1
        task_indx = 0
        while task_indx < len(script):
            task = script[task_indx]
            log_entry = {}
            action_result = ""
            step = task["step"]
            action = task["action"]
            params = {}
            err = None
            if "params" in task:
                params = task["params"]
            try:
                logger.debug("action: " + action + "\nparams:" +json.dumps(params))
                if action == "hangup":
                    action_result = await agi_helper.hangup()
                elif action == "say":
                    action_result = await agi_helper.say(msg=params["msg"], voice=params["voice"], emotion=params["emotion"],
                                                         lang=params["lang"], key=keys["speechkit"])
                elif "get_dtmf" in action:
                    # if step in task_sounds:
                    #     digits=[]
                    #     if "actions" in task["params"]:
                    #         for item in task["params"]["actions"]:
                    #             digits.append(item["value"])
                    #     logger.debug("Task digits: " + pprint.pformat(digits))
                    #     action_result, err = await agi_helper.getDMTF(task_sounds[step],digits)
                    #     if err is not None:
                    #         action_result = err
                    # else:
                    #     logger.debug("Can`t get sound file for task: {task}, step:{step}".format(task=task_id,step=step))
                    #     action_result = "can`t get sound file"
                    action_result = "not implemented"
                elif action == "recognize":
                    action_result, err = await  agi_helper.recognize(topic=params["topic"], classifier=params["classifier"],
                                                                     lang=params["lang"], key=keys["speechkit"], nlu_conf=request.app['nlu_conf'])
                    if err is None and params["classifier"] != "":
                        if action_result["classifier_res"] in params["actions"]:
                            next_step = int(params["actions"][action_result["classifier_res"]])
                            if next_step <= len(script):
                                task_indx = next_step-2
                            else:
                                task_indx = len(script)
                    elif err is not None:
                        if "err" in params["actions"]:
                            next_step = int(params["actions"]["err"])
                            if next_step < len(script):
                                task_indx = next_step-2
                            else:
                                task_indx = len(script)
                elif action == "say_and_recognize":
                    action_result, err = await  agi_helper.say_and_recognize(msg=params["msg"], voice=params["voice"], emotion=params["emotion"],
                                                                     topic=params["topic"], classifier=params["classifier"],
                                                                     lang=params["lang"],key=keys["speechkit"],nlu_conf=request.app['nlu_conf'])

                    if err is None and params["classifier"] != "":
                        if action_result["classifier_res"] in params["actions"]:
                            next_step = int(params["actions"][action_result["classifier_res"]])
                            if next_step <= len(script):
                                task_indx = next_step-2
                            else:
                                task_indx = len(script)
                    elif err is not None:
                        if "err" in params["actions"]:
                            next_step = int(params["actions"]["err"])
                            if next_step < len(script):
                                task_indx = next_step-2
                            else:
                                task_indx = len(script)
            except Exception:
                logger.exception("error execute script")
            finally:
                log_entry["step"] = step
                log_entry["result"] = action_result
                log_entry["error"] = err
                log.append(log_entry)
            task_indx += 1
            script_iter += 1
            if script_iter > MAX_SCRIPT_ITER:
                break
        await agi_helper.hangup()
    except Exception:
        logger.exception("Unknown error")

    while True:
        try:
            db_proc = await request.app['db'].dbproc()
            await db_proc.write_script_log(task_id,log)
            await db_proc.write_record_name(task_id,"task_{}_{}_{}.ogg".
                                            format(task_id,service_task["service"],service_task["service_task_id"]))
            break
        except Exception:
            logger.exception("can`t write script log")
        asyncio.sleep(1)

# ----------------------------------------------------------------------------------------------------------------------
async def originate_hangup(request):
    try:
        agi_helper = AsyncAGIHelper(request)
        logger.debug('AGI variables:\n' + pformat(request.headers))
        call_log = await _proc_hangup(agi_helper)

        task_id = await agi_helper.getVariable("TASK_ID")
        while True:
            db_proc = await request.app['db'].dbproc()
            err1 = await db_proc.write_call_log(task_id,call_log)
            err2 = await db_proc.set_task_status(task_id,"completed")
            if err1 is None and err2 is None:
                break
            asyncio.sleep(1)

    except Exception:
        logger.exception("can`t write call log")


# ----------------------------------------------------------------------------------------------------------------------
async def check(request):
    """
    used for checking connection between asterisk and agi server
    :param request:
    :return:
    """
    try:
        dbproc = await request.app['db'].dbproc()
        if dbproc:
            res = await dbproc.check_connection()
            if res:
                agi_helper = AsyncAGIHelper(request)
                logger.debug('AGI variables:\n' + pformat(request.headers))
                #await agi_helper.set_variable("CHECK_TIME",time.time())
                await agi_helper.execute("DATABASE PUT CHECKER CHECK_TIME {0}".format(time.time()))
    except Exception:
        logger.exception("can`t make check")



