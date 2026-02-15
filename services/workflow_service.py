import logging

from client.aws_client import DynamoDBClient
from utils.logger import Logger


class WorkflowService:
    """Service for workflow management operations"""

    def __init__(self, dynamodb_client: DynamoDBClient) -> None:
        """
        Initialize WorkflowService with DynamoDB client dependency.

        Args:
            dynamodb_client: DynamoDB client for data access
        """
        self.logger = Logger.get_logger("workflow_service", logging.INFO)
        self.dynamodb_client = dynamodb_client
