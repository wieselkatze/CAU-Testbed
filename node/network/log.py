import json
import logging
import os

from kafka import KafkaProducer

from configuration import constants


class LogRetrievalMessage:
    def __init__(self, experiment_id: str, host_name: str, target_path: str, node_id: str):
        self.experimentId = experiment_id
        self.hostName = host_name
        self.userName = os.getlogin()
        self.targetPath = target_path
        self.nodeId = node_id

def resolve_local_log_path(working_directory: str, experiment_id: str):
    return os.path.join(working_directory, experiment_id, "logs", "*")

class LogTransfer:
    def __init__(self, host_name: str, node_id: str, working_directory: str, kafka_bootstrap: str):
        self.host_name = host_name
        self.node_id = node_id
        self.working_directory = working_directory
        self.retrieval_msg_producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap,
            value_serializer=lambda x: json.dumps(x, default=lambda o: o.__dict__).encode("utf-8")
        )

    def initiate_log_retrieval(self, experiment_id: str):
        local_log_path = resolve_local_log_path(self.working_directory, experiment_id)

        logging.info("Initiating log retrieval")

        self.retrieval_msg_producer.send(
            constants.LOG_RETRIEVAL_TOPIC,
            LogRetrievalMessage(
                experiment_id,
                self.host_name,
                local_log_path,
                self.node_id
            )
        )

    def create_logging_directory(self, experiment_id: str):
        os.makedirs(os.path.join(self.working_directory, experiment_id, "logs"), exist_ok=True)


transfer_handler = None  # To be populated by main program
