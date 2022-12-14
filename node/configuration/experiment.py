import datetime
from enum import Enum
from typing import List, Dict


class ModuleType(Enum):
    NRF52 = "NRF52"
    ZOUL = "ZOUL"
    SKY = "SKY"


class InvocationMethod(Enum):
    START = "START"
    STOP = "STOP"
    CANCEL = "CANCEL"


class ExperimentModule:
    def __init__(self, id: ModuleType, firmware: str, serial_dump: bool, serial_forward: bool, gpio_tracer: bool):
        self.id = id
        self.firmware = firmware
        self.serial_dump = serial_dump
        self.gpio_tracer = gpio_tracer
        self.serial_forward = serial_forward

    @staticmethod
    def from_json(json_dict: Dict):
        return ExperimentModule(
            id=ModuleType(json_dict["id"]),
            firmware=json_dict["firmware"],
            serial_dump=json_dict["serialDump"],
            serial_forward=json_dict["serialForward"],
            gpio_tracer=json_dict["gpioTracer"]
        )

    def __repr__(self):
        return f"ExperimentModule(id={self.id}, firmware={self.firmware})"


class ExperimentNode:
    def __init__(self, id: str, modules: List[ExperimentModule]):
        self.id = id
        self.modules = modules

    @staticmethod
    def from_json(json_dict: Dict):
        module_list_json = json_dict["modules"]
        module_list = []

        for module_json in module_list_json:
            module_list.append(ExperimentModule.from_json(module_json))

        return ExperimentNode(
            json_dict["id"],
            module_list
        )

    def __repr__(self):
        return f"ExperimentNode(id={self.id}, modules=[{self.modules}])"


class Experiment:
    def __init__(self,
                 name: str,
                 experimentId: str,
                 start: datetime.datetime,
                 end: datetime.datetime,
                 nodes: List[ExperimentNode],
                 action: InvocationMethod
                 ):
        self.action = action
        self.name = name
        self.experiment_id = experimentId
        self.start = start
        self.end = end
        self.nodes = nodes

    @staticmethod
    def from_json(json_dict: Dict):
        nodes_list_json = json_dict["nodes"]
        nodes_list = []

        for node_json in nodes_list_json:
            nodes_list.append(ExperimentNode.from_json(node_json))

        return Experiment(
            json_dict["name"],
            json_dict["experimentId"],
            datetime.datetime(*json_dict["start"]),
            datetime.datetime(*json_dict["end"]),
            nodes_list,
            InvocationMethod(json_dict["action"])
        )
