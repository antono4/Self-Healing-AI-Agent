"""OpenHands Cloud Integration for Self-Healing Agent.

This module provides integration with OpenHands Cloud API to:
- Start new conversations for self-healing tasks
- Monitor conversation status
- Report results back to GitHub
"""

import os
import time
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class OpenHandsConfig:
    """Configuration for OpenHands Cloud integration."""

    api_key: str = ""
    base_url: str = "https://app.all-hands.dev"
    repository: str = ""
    branch: str = "master"
    title_prefix: str = "[Self-Healing]"


class OpenHandsClient:
    """Client for OpenHands Cloud API."""

    def __init__(self, config: OpenHandsConfig | None = None):
        self.config = config or OpenHandsConfig()
        self.logger = logger.bind(component="OpenHandsClient")
        
        # Get API key from environment if not provided
        if not self.config.api_key:
            self.config.api_key = os.environ.get("OPENHANDS_CLOUD_API_KEY", "")
        
        if not self.config.api_key:
            self.logger.warning("OPENHANDS_CLOUD_API_KEY not set")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def start_conversation(
        self,
        message: str,
        title: str | None = None,
    ) -> dict[str, Any] | None:
        """Start a new OpenHands Cloud conversation.
        
        Args:
            message: Initial message/instruction for the agent
            title: Optional title for the conversation
            
        Returns:
            Conversation info dict with id, status, etc.
        """
        import requests

        if not self.config.api_key:
            self.logger.error("API key not configured")
            return None

        url = f"{self.config.base_url}/api/v1/app-conversations"

        payload: dict[str, Any] = {
            "initial_message": {
                "content": [{"type": "text", "text": message}]
            },
        }

        if self.config.repository:
            payload["selected_repository"] = self.config.repository

        if self.config.branch:
            payload["selected_branch"] = self.config.branch

        if title:
            payload["title"] = title

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info("Conversation started", conversation_id=data.get("app_conversation_id"))

            return data

        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to start conversation", error=str(e))
            return None

    def poll_conversation(
        self,
        conversation_id: str,
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> dict[str, Any] | None:
        """Poll conversation status until completed.
        
        Args:
            conversation_id: The conversation ID to poll
            max_wait: Maximum seconds to wait
            poll_interval: Seconds between polls
            
        Returns:
            Final conversation state
        """
        import requests

        if not self.config.api_key:
            return None

        url = f"{self.config.base_url}/api/v1/app-conversations?ids={conversation_id}"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30,
                )
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [])
                
                if items:
                    conversation = items[0]
                    status = conversation.get("execution_status", "")
                    
                    self.logger.info(
                        "Polling conversation",
                        conversation_id=conversation_id,
                        status=status,
                    )
                    
                    if status in ("completed", "failed", "stopped"):
                        return conversation
                
                time.sleep(poll_interval)

            except requests.exceptions.RequestException as e:
                self.logger.error("Polling failed", error=str(e))
                time.sleep(poll_interval)

        self.logger.warning("Max wait exceeded", conversation_id=conversation_id)
        return None

    def get_conversation_events(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent events from a conversation.
        
        Args:
            conversation_id: The conversation ID
            limit: Maximum number of events
            
        Returns:
            List of events
        """
        import requests

        if not self.config.api_key:
            return []

        url = (
            f"{self.config.base_url}/api/v1/conversation/{conversation_id}"
            f"/events/search?limit={limit}&sort_order=TIMESTAMP_DESC"
        )

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            return data.get("items", [])

        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to get events", error=str(e))
            return []

    def run_self_healing_task(
        self,
        task_description: str,
        wait_for_completion: bool = True,
    ) -> dict[str, Any]:
        """Run a self-healing task on OpenHands Cloud.
        
        Args:
            task_description: Description of the self-healing task
            wait_for_completion: Whether to wait for completion
            
        Returns:
            Dict with conversation info and status
        """
        title = f"{self.config.title_prefix} {task_description[:50]}..."

        # Start conversation
        conversation = self.start_conversation(
            message=task_description,
            title=title,
        )

        if not conversation:
            return {
                "success": False,
                "error": "Failed to start conversation",
            }

        result = {
            "success": True,
            "conversation_id": conversation.get("app_conversation_id"),
            "conversation_url": f"{self.config.base_url}/conversations/{conversation.get('app_conversation_id')}",
            "status": conversation.get("execution_status"),
        }

        # Poll for completion if requested
        if wait_for_completion:
            conversation_id = conversation.get("app_conversation_id")
            if conversation_id:
                final_state = self.poll_conversation(conversation_id)
                if final_state:
                    result["status"] = final_state.get("execution_status")
                    result["events"] = self.get_conversation_events(conversation_id)

        return result

    def list_recent_conversations(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent conversations.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of conversation records
        """
        import requests

        if not self.config.api_key:
            return []

        url = f"{self.config.base_url}/api/v1/app-conversations/search?limit={limit}"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            return data.get("items", [])

        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to list conversations", error=str(e))
            return []
