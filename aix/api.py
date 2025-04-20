import requests
import json
import logging

logger = logging.getLogger(__name__)

def check_api_availability(api_base, workspace, api_key):
    """Verify API endpoint and workspace accessibility."""
    try:
        response = requests.get(f"{api_base}/api/docs", timeout=5)
        response.raise_for_status()
        logger.info("API endpoint is accessible at %s/api/docs", api_base)

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"{api_base}/api/v1/workspaces", headers=headers)
        response.raise_for_status()
        workspaces = response.json().get("workspaces", [])
        workspace_slugs = [ws["slug"] for ws in workspaces]
        if workspace not in workspace_slugs:
            logger.error("Workspace '%s' not found. Available workspaces: %s", workspace, workspace_slugs)
            return False, None
        logger.info("Workspace '%s' is valid", workspace)

        for ws in workspaces:
            if ws["slug"] == workspace:
                chat_mode = ws.get("chatMode", "chat")
                agent_provider = ws.get("agentProvider")
                chat_model = ws.get("chatModel")
                agent_model = ws.get("agentModel")
                logger.info("Workspace '%s' supports chatMode: %s, agentProvider: %s", workspace, chat_mode, agent_provider)
                return True, {"chat_model": chat_model, "agent_model": agent_model, "agent_provider": agent_provider}
        return False, None
    except requests.exceptions.RequestException as e:
        logger.error("API or workspace not accessible at %s: %s", api_base, e)
        return False, None

def query_anythingllm(prompt, api_base, workspace, api_key, mode="chat", model=None, workspace_config=None, chat_model=None, agent_model=None):
    """Query AnythingLLM for a response and return text and model used."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": prompt,
            "mode": mode
        }
        # Use the specified model if provided, otherwise fallback to chat_model or agent_model based on mode
        if model:
            payload["model"] = model
        elif mode == "chat" and chat_model:
            payload["model"] = chat_model
        elif mode == "agent" and agent_model:
            payload["model"] = agent_model

        url = f"{api_base}/api/v1/workspace/{workspace}/chat"
        logger.info("Sending request to AnythingLLM at %s with mode '%s' and prompt: %s", url, mode, prompt[:50])
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        
        logger.debug("Full API response: %s", json.dumps(response_data, indent=2))
        
        if "error" in response_data and response_data["error"]:
            error_msg = response_data["error"]
            logger.error("API returned error: %s", error_msg)
            raise ValueError(f"API error: {error_msg}")
        if "textResponse" not in response_data or response_data["textResponse"] is None:
            logger.error("No valid 'textResponse' in response: %s", response_data)
            raise ValueError("No valid response from AnythingLLM")
        
        model_used = response_data.get("metrics", {}).get("model")
        if not model_used:
            model_used = response_data.get("chatModel")
        if not model_used and workspace_config:
            model_used = workspace_config.get("agent_model" if mode == "agent" else "chat_model")
        if not model_used:
            model_used = model or "unknown"
        logger.info("Response generated successfully")
        
        return response_data["textResponse"], model_used
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP error from AnythingLLM: %s, Response text: %s", e, response.text)
        raise
    except requests.exceptions.JSONDecodeError as e:
        logger.error("Failed to parse JSON response: %s, Response text: %s", e, response.text)
        raise
    except Exception as e:
        logger.error("Unexpected error querying AnythingLLM: %s", e)
        raise