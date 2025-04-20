import re
import autopep8
import logging
from .api import query_anythingllm
from .utils import check_ram_usage

logger = logging.getLogger(__name__)

def clean_code_output(text, language):
    """Clean LLM output to extract raw code, removing markdown and invalid content."""
    code = re.sub(r'```(?:python|julia|html|javascript)?\n([\s\S]*?)\n```', r'\1', text, flags=re.MULTILINE)
    code = re.sub(r'```[\s\S]*', '', code)
    code = code.strip()
    lines = code.splitlines()
    code_lines = []
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith(('# ', '##', '###', '*', '-')) or line.lower().startswith(('example', 'note', 'output', 'certainly', 'below', 'here')):
            continue
        stripped_line = line.lstrip()
        if not stripped_line:
            continue
        code_lines.append(line)
    return '\n'.join(code_lines).strip()

def format_python_code(code):
    """Format Python code using autopep8 to fix indentation and style issues."""
    try:
        formatted_code = autopep8.fix_code(code, options={'aggressive': 2})
        return formatted_code.strip()
    except Exception as e:
        logger.error("Failed to format Python code with autopep8: %s", e)
        return code

def generate_code(prompt, api_base, workspace, api_key, mode, language, model=None, workspace_config=None, chat_model=None, agent_model=None):
    """Generate code using AnythingLLM with fallback, and format Python code with autopep8."""
    try:
        if model and not check_ram_usage():
            logger.warning("Skipping model-specific operations due to high RAM usage.")
            model = None
        text, model_used = query_anythingllm(prompt, api_base, workspace, api_key, mode, model, workspace_config, chat_model, agent_model)
        cleaned_text = clean_code_output(text, language)
        if language == "python":
            cleaned_text = format_python_code(cleaned_text)
        return cleaned_text, model_used
    except Exception as e:
        logger.error("Failed to generate code: %s", e)
        raise