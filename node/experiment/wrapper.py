import logging
import os.path
import sched
import threading
import time
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from pathlib import Path
from typing import List, Callable

from configuration import nodeConfiguration, experiment
from configuration.experiment import ModuleType, Experiment
from experiment.gpiotracer import GPIOTracer
from experiment.modules.module import ExperimentModule
from experiment.modules.nrf52 import NRF52ExperimentModule
from experiment.modules.sky import SkyExperimentModule
from experiment.modules.zoul import ZoulExperimentModule
from network import firmware, log


# Create a shared GPIO tracer object
gpio_tracer = GPIOTracer()


class ModuleWrapper:
    """
    Wraps an experiment module an provides a way to check if
    prepare, start or stop have been called already.

    Uses a lock to prevent race conditions on starts and stops of experiments
    """

    def __init__(self, module: ExperimentModule):
        self.__lock = threading.Lock()
        self.wrapped_module = module
        self.has_prepared = False
        self.has_started = False
        self.has_stopped = False

    def prepare(self):
        self.has_prepared = True
        self.wrapped_module.prepare()

    def start(self):
        with self.__lock:
            self.has_started = True

            if not self.has_stopped:  # Prevent stray schedulers from starting even if it was cancelled
                self.wrapped_module.start()

    def stop(self):
        with self.__lock:
            self.has_stopped = True

            if self.has_started:  # Only flash null firmware when module was actually started
                self.wrapped_module.stop()


def module_factory(experiment_id: str, module: experiment.ExperimentModule, logger: logging.Logger):
    if module.serial_dump:
        log_path_prefix = nodeConfiguration.configuration.workingDirectory.joinpath(experiment_id, "logs")
    else:
        log_path_prefix = Path("/tmp", "testbed", experiment_id)
        os.makedirs(log_path_prefix, exist_ok=True)

    kwargs = {
        "firmware": firmware.resolve_local_fw_path(
            nodeConfiguration.configuration.workingDirectory, experiment_id
        ).joinpath(module.firmware),
        "logger": logger,
        "serial_dump": module.serial_dump,
        "serial_forward": module.serial_forward,
        "gpio_tracer": module.gpio_tracer
    }

    if module.id == ModuleType.ZOUL:
        module_inst = ZoulExperimentModule(**kwargs, log_path=log_path_prefix.joinpath("zoul.log"))
    elif module.id == ModuleType.SKY:
        module_inst = SkyExperimentModule(**kwargs, log_path=log_path_prefix.joinpath("sky.log"))
    elif module.id == ModuleType.NRF52:
        module_inst = NRF52ExperimentModule(**kwargs, log_path=log_path_prefix.joinpath("nrf52.log"))
    else:
        raise RuntimeError("Module type " + str(module.id) + " not defined")

    return ModuleWrapper(module_inst)


def is_gpio_trace_enabled(modules: list[ExperimentModule]) -> bool:
    return True in (module.gpio_tracer for module in modules)


class ExperimentWrapper:
    def __init__(self, node_id: str, descriptor: Experiment, on_finish_callback: Callable):
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.node_id = node_id
        self.descriptor = descriptor
        self.wrapped_modules: List[ModuleWrapper] = []
        self.event_list = []
        self.on_finish_callback = on_finish_callback
        self.logger = logging.getLogger(f'experiment{descriptor.experiment_id}')

        log.transfer_handler.create_logging_directory(self.descriptor.experiment_id)

        file_handler = logging.FileHandler(
            filename=os.path.join(nodeConfiguration.configuration.workingDirectory, descriptor.experiment_id, "logs", "node.log"),
            mode='w'
        )

        formatter = logging.Formatter(
            fmt=f'%(asctime)s.%(msecs)03d [%(levelname)s] [{nodeConfiguration.configuration.id}] [Experiment {descriptor.experiment_id}] %(message)s',
            datefmt='%H:%M:%S'
        )

        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)

    def get_descriptor_modules(self) -> List[experiment.ExperimentModule]:
        for node in self.descriptor.nodes:
            if node.id == self.node_id:
                return node.modules

        return []

    def initiate_firmware_retrieval(self):
        self.logger.info("Initiating firmware retrieval")

        modules = self.get_descriptor_modules()

        for module in modules:
            nodeConfiguration.firmware_retriever.retrieve_firmware(self.descriptor.experiment_id, module.firmware)

    def wait_for_firmware(self, target_time: DateTime):
        self.logger.info("Waiting for firmware")

        modules = self.get_descriptor_modules()

        for module in modules:
            firmware_file_path = os.path.join(
                firmware.resolve_local_fw_path(nodeConfiguration.configuration.workingDirectory,
                                               self.descriptor.experiment_id),
                module.firmware
            )

            while not os.path.exists(firmware_file_path):
                time.sleep(1)

                if DateTime.now() >= target_time:
                    raise RuntimeError("Failed to retrieve firmware in time!")

            # Perhaps improve this with a message back from the server
            # If this size check isn't used, this will terminate immediately as soon as the file is created,
            # but the firmware isn't transferred yet
            firmware_file_size = -1
            while firmware_file_size < (firmware_file_size := os.path.getsize(firmware_file_path)):
                time.sleep(0.05)

            print(f"Got firmware '{module.firmware}'")
            self.logger.info(f"Got firmware '{module.firmware}'")

        self.logger.info("All firmware received")

    def __early_stop(self, retrieve_logs: bool):
        for event in reversed(self.event_list):
            try:
                self.scheduler.cancel(event)
            except ValueError:  # This could have been executed already
                pass

        self.event_list.clear()

        for module in self.wrapped_modules:
            self.scheduler.enter(0, 0, module.stop)

        self.scheduler.enter(0, 1, gpio_tracer.stop)
        self.scheduler.enter(0, 2, lambda: map(self.logger.removeHandler, self.logger.handlers))

        if retrieve_logs:
            self.scheduler.enter(0, 2, lambda: log.transfer_handler.initiate_log_retrieval(self.descriptor.experiment_id))

        self.scheduler.run()
        self.on_finish_callback()

    def initiate_log_retrieval(self):
        self.logger.info("Initiating log retrieval")
        map(self.logger.removeHandler, self.logger.handlers)
        del self.logger.manager.loggerDict[self.logger.name]
        log.transfer_handler.initiate_log_retrieval(self.descriptor.experiment_id)

    def cancel(self):
        self.logger.info("Cancelling experiment.")
        self.__early_stop(False)

    def stop(self):
        self.logger.info("Stopping experiment.")
        self.__early_stop(True)

    def schedule(self, *args, **kwargs):
        self.event_list.append(self.scheduler.enter(*args, **kwargs))

    def schedule_abs(self, *args, **kwargs):
        self.event_list.append(self.scheduler.enterabs(*args, **kwargs))

    def run(self):
        self.initiate_firmware_retrieval()

        max_firmware_wait_time = max(
            self.descriptor.start - TimeDelta(seconds=30),
            DateTime.now() + TimeDelta(seconds=30)
        )

        self.schedule(0, 0, lambda: self.wait_for_firmware(max_firmware_wait_time))

        modules = self.get_descriptor_modules()
        for module in modules:
            wrapped_module = module_factory(self.descriptor.experiment_id, module, self.logger)

            self.schedule(0, 1, wrapped_module.prepare)
            self.schedule_abs(max(self.descriptor.start, DateTime.now()).timestamp(), 2, wrapped_module.start)
            self.schedule_abs(max(self.descriptor.end, DateTime.now()).timestamp(), 5, wrapped_module.stop)

            self.wrapped_modules.append(wrapped_module)

        if is_gpio_trace_enabled(modules):
            self.schedule_gpio_tracing()

        end = max(self.descriptor.end, DateTime.now()).timestamp()
        self.schedule_abs(end, 6, self.initiate_log_retrieval)

        self.scheduler.run()
        self.on_finish_callback()

    def schedule_gpio_tracing(self):
        self.schedule_abs(
            max(self.descriptor.start, DateTime.now()).timestamp(),
            3,
            lambda: gpio_tracer.start(int(self.descriptor.experiment_id), self.logger)
        )
        self.schedule_abs(
            max(self.descriptor.end, DateTime.now()).timestamp(),
            4,
            gpio_tracer.stop
        )
