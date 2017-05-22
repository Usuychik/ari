# -*- coding: utf-8 -*-
__author__ = 'visarev'

from abc import *
import json


class DBProc(ABC):
    @abstractmethod
    async def write_call_log(self,task_id,log:json):
        """
        
        :param task_id: 
        :param log: 
        :return: err if method failed 
        """
        pass

    @abstractmethod
    async def set_task_status(self, task_id, status: str):
        """
        
        :param task_id: 
        :param status: 
        :return: err if method failed 
        """
        pass

    @abstractmethod
    async def write_script_log(self, task_id, log: json):
        """
        
        :param task_id: 
        :param log: 
        :return: err if method failed
        """
        pass

    @abstractmethod
    async def get_script(self, task_id):
        """
        return formated_script from task
        :param task_id: 
        :return: script, err
        """
        pass

    @abstractmethod
    async def write_record_name(self, task_id, filename):
        """
        saves record filename for task, return err message if failed
        :param task_id: 
        :param filename: 
        :return: err
        """
        pass

    @abstractmethod
    async def save_task(self, host: str, service_task_id: str, service: str, phone: str, script: json, formated_script: json,
                        log_uri: str, record_uri: str):
        """
        saves task and return task id and error message if method failed
        :param host: source host ip
        :param service_task_id: task id from request
        :param service: service name from request
        :param phone: phone to dial
        :param script: script from request
        :param formated_script: script from web_helpers.preformat_script() 
        :param log_uri: 
        :param record_uri: 
        :return: id, err
        """
        pass

    @abstractmethod
    async def get_task(self, task_id):
        """
        return task dict with format:
        {
        "service_task_id": string
        "service": string
        "phone": string
        "script": json
        "formated_script": json
        
        }
        :param task_id: task_id from save_task()
        :return: task, err
        """
        pass

    @abstractmethod
    async def get_log(self, service: str, service_task_id: str):
        """
        return log for task and service according schema:
        https://wiki.yandex-team.ru/noc/Office/dialapi/docs/#jsonschemalog
        :param service: service_name
        :param service_task_id: task_id from remote service
        :return: log, err
        """
        pass

    @abstractmethod
    async def get_service_keys(self, service: str):
        """
        return all keys for service
        :param service: service name
        :return: {"keyname":"key"}, err
        """
        pass

    @abstractmethod
    async def get_task_sounds(self, task_id):
        """
        return all sounds filenames for current task and error message if method failed
        :param task_id: 
        :return: {"step":"filename"}, err
        """
        pass

    @abstractmethod
    async def set_task_sound(self, task_id, step, filename):
        """
        writes filename for current task and step
        :param task_id: task_id from save_task()
        :param step: current task step
        :param filename: 
        :return: err message if method failed 
        """
        pass

    @abstractmethod
    async def check_connection(self):
        """
        check if connection to DB ok
        :return: True if connection ok, else False
        """
        pass