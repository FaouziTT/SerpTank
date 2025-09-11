"""
Log aggregation configuration for centralized log management.

This module provides configurations for sending logs to various
log aggregation services like ELK stack, CloudWatch, or Datadog.
"""
import os
import logging
from typing import Optional, Dict, Any
from logging.handlers import SysLogHandler

from app.core.config import settings


class LogAggregationHandlers:
    """Factory for creating log aggregation handlers."""
    
    @staticmethod
    def create_cloudwatch_handler():
        """Create AWS CloudWatch Logs handler."""
        try:
            import watchtower
            
            handler = watchtower.CloudWatchLogHandler(
                log_group=f"/aws/voltex/{settings.ENVIRONMENT}",
                stream_name=f"{settings.HOSTNAME}-{os.getpid()}",
                use_queues=True,
                create_log_group=True
            )
            return handler
        except ImportError:
            logging.warning("watchtower not installed, CloudWatch logging disabled")
            return None
    
    @staticmethod
    def create_elasticsearch_handler():
        """Create Elasticsearch handler for ELK stack."""
        try:
            from cmreslogging.handlers import CMRESHandler
            
            handler = CMRESHandler(
                hosts=[{'host': settings.ELASTICSEARCH_HOST, 'port': settings.ELASTICSEARCH_PORT}],
                auth_type=CMRESHandler.AuthType.NO_AUTH,
                es_index_name=f"voltex-{settings.ENVIRONMENT}",
                es_doc_type='log',
                es_additional_fields={
                    'environment': settings.ENVIRONMENT,
                    'service': 'voltex-backend'
                }
            )
            return handler
        except ImportError:
            logging.warning("CMRESHandler not installed, Elasticsearch logging disabled")
            return None
    
    @staticmethod
    def create_datadog_handler():
        """Create Datadog logs handler."""
        try:
            # Datadog uses standard logging with JSON format
            # The Datadog agent will pick up the logs
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s", '
                '"environment": "' + settings.ENVIRONMENT + '", '
                '"service": "voltex-backend"}'
            ))
            return handler
        except Exception as e:
            logging.warning(f"Failed to create Datadog handler: {e}")
            return None
    
    @staticmethod
    def create_syslog_handler(
        address: tuple = ('localhost', 514),
        facility: int = SysLogHandler.LOG_LOCAL0
    ):
        """Create Syslog handler for traditional log aggregation."""
        try:
            handler = SysLogHandler(address=address, facility=facility)
            handler.setFormatter(logging.Formatter(
                '%(name)s[%(process)d]: %(levelname)s - %(message)s'
            ))
            return handler
        except Exception as e:
            logging.warning(f"Failed to create Syslog handler: {e}")
            return None


class LogAggregationConfig:
    """Configuration for log aggregation."""
    
    def __init__(self):
        self.handlers = []
        self.configure_handlers()
    
    def configure_handlers(self):
        """Configure log aggregation handlers based on settings."""
        
        # CloudWatch
        if getattr(settings, 'ENABLE_CLOUDWATCH_LOGS', False):
            handler = LogAggregationHandlers.create_cloudwatch_handler()
            if handler:
                self.handlers.append(handler)
        
        # Elasticsearch/ELK
        if getattr(settings, 'ENABLE_ELASTICSEARCH_LOGS', False):
            handler = LogAggregationHandlers.create_elasticsearch_handler()
            if handler:
                self.handlers.append(handler)
        
        # Datadog
        if getattr(settings, 'ENABLE_DATADOG_LOGS', False):
            handler = LogAggregationHandlers.create_datadog_handler()
            if handler:
                self.handlers.append(handler)
        
        # Syslog
        if getattr(settings, 'ENABLE_SYSLOG', False):
            syslog_host = getattr(settings, 'SYSLOG_HOST', 'localhost')
            syslog_port = getattr(settings, 'SYSLOG_PORT', 514)
            handler = LogAggregationHandlers.create_syslog_handler(
                address=(syslog_host, syslog_port)
            )
            if handler:
                self.handlers.append(handler)
    
    def apply_to_logger(self, logger: logging.Logger):
        """Apply aggregation handlers to a logger."""
        for handler in self.handlers:
            logger.addHandler(handler)
    
    def apply_to_root_logger(self):
        """Apply aggregation handlers to the root logger."""
        root_logger = logging.getLogger()
        for handler in self.handlers:
            root_logger.addHandler(handler)


# Log shipping configuration for different environments
LOG_SHIPPING_CONFIGS = {
    "development": {
        "console": True,
        "file": True,
        "elasticsearch": False,
        "cloudwatch": False,
        "datadog": False,
        "syslog": False
    },
    "staging": {
        "console": True,
        "file": True,
        "elasticsearch": True,
        "cloudwatch": False,
        "datadog": False,
        "syslog": True
    },
    "production": {
        "console": False,
        "file": True,
        "elasticsearch": True,
        "cloudwatch": True,
        "datadog": True,
        "syslog": True
    }
}


def setup_log_aggregation():
    """Set up log aggregation based on environment."""
    config = LogAggregationConfig()
    config.apply_to_root_logger()
    
    logger = logging.getLogger(__name__)
    logger.info(
        f"Log aggregation configured for {settings.ENVIRONMENT} environment",
        extra={
            'extra_fields': {
                'log_config': {
                    'handlers_count': len(config.handlers),
                    'environment': settings.ENVIRONMENT
                }
            }
        }
    )