import sys
import os

# This makes sure Python can find your existing files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import json
import time
import re
import requests
import autopep8
from bs4 import BeautifulSoup

import openai
import anthropic

# Set API keys from .env
openai.api_key = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")


def fetch_and_parse(url: str) -> dict:
    """
    Fetches HTML from the URL and extracts all testable elements.
    Returns parsed data dictionary.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    parsed_data = {
        "title": soup.title.string.strip() if soup.title and soup.title.string else "No title found",
        "links": [a["href"] for a in soup.find_all("a", href=True)],
        "headings": {
            f"h{level}": [h.get_text(strip=True) for h in soup.find_all(f"h{level}")]
            for level in range(1, 7)
        },
        "images": [img["src"] for img in soup.find_all("img", src=True)],
        "forms": [
            {
                "action": form.get("action"),
                "method": form.get("method"),
                "id": form.get("id"),
                "name": form.get("name"),
            }
            for form in soup.find_all("form")
        ],
        "inputs": [
            {
                "type": inp.get("type"),
                "name": inp.get("name"),
                "id": inp.get("id"),
                "placeholder": inp.get("placeholder"),
            }
            for inp in soup.find_all("input")
        ],
        "buttons": [
            {
                "text": btn.get_text(strip=True),
                "type": btn.get("type"),
                "id": btn.get("id"),
                "name": btn.get("name"),
            }
            for btn in soup.find_all("button")
        ],
        "selects": [
            {
                "name": sel.get("name"),
                "id": sel.get("id"),
                "options": [opt.get_text(strip=True) for opt in sel.find_all("option")],
            }
            for sel in soup.find_all("select")
        ],
    }
    return parsed_data


def build_prompt(url: str, parsed_data: dict, framework: str) -> str:
    """
    Builds the correct prompt depending on which framework was selected.
    """
    base = (
        f"You are a strict code generator. Output ONLY executable code, "
        f"no explanations, no markdown fences.\n\n"
        f"URL: {url}\n\n"
        f"Parsed HTML Data:\n{json.dumps(parsed_data, indent=2)[:2000]}...\n\n"
        f"Instructions:\n"
        f"- Create 30 sequential test cases.\n"
        f"- Log each test as 'Test X Passed' or 'Test X Failed'.\n"
        f"- Include error handling for each test.\n"
        f"- Do NOT include markdown or explanatory text.\n"
    )

    if framework == "selenium_python":
        return base + (
            f"- Generate Selenium 4+ Python test code.\n"
            f"- Use only find_element(By.<LOCATOR>, value) syntax.\n"
            f"- Import By from selenium.webdriver.common.by.\n"
            f"- Open Chrome, maximise window.\n"
            f"- Add time.sleep() where needed.\n"
            f"- End with driver.quit().\n"
            f"- Output must be syntactically valid Python.\n"
        )
    elif framework == "playwright_js":
        return base + (
            f"- Generate Playwright JavaScript test code.\n"
            f"- Use @playwright/test syntax with test() and expect().\n"
            f"- Use async/await throughout.\n"
            f"- Use page.goto(), page.locator(), page.click(), page.fill().\n"
            f"- Each test must be independent.\n"
            f"- Output must be syntactically valid JavaScript.\n"
        )
    else:
        return base


def clean_code(code: str) -> str:
    """Removes markdown and LLM artifacts from generated code."""
    code = re.sub(r"^```[\w]*", "", code, flags=re.MULTILINE).strip()
    code = re.sub(r"```$", "", code, flags=re.MULTILINE).strip()
    code = re.sub(r"Here is.*?code.*?:", "", code, flags=re.DOTALL)
    code = re.sub(r"Please replace.*?\n", "", code)
    return code.strip()


def generate_with_gpt4(prompt: str) -> str:
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "You are a senior test automation engineer. Output only clean, executable code."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    return response.choices[0].message.content.strip()


def generate_with_claude(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        system="You are a senior test automation engineer. Output only clean, executable code.",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4000,
    )
    return response.content[0].text.strip()


def generate_with_grok(prompt: str) -> str:
    try:
        from xai_sdk import Client
        from xai_sdk.chat import user, system
        client = Client(api_key=XAI_API_KEY, timeout=5000)
        chat = client.chat.create(model="grok-code-fast-1")
        chat.append(system("You are a senior test automation engineer. Output only clean, executable code."))
        chat.append(user(prompt))
        response = chat.sample()
        return response.content.strip()
    except Exception as e:
        raise Exception(f"Grok error: {str(e)}")


def count_elements(parsed_data: dict) -> int:
    return (
        len(parsed_data.get("inputs", [])) +
        len(parsed_data.get("buttons", [])) +
        len(parsed_data.get("links", [])) +
        len(parsed_data.get("selects", [])) +
        len(parsed_data.get("forms", [])) +
        len(parsed_data.get("images", []))
    )


def generate_test_script(url: str, model: str, framework: str) -> dict:
    """
    Main function called by the API endpoint.
    Takes URL, model choice, and framework.
    Returns script and metadata.
    """
    start_time = time.time()

    # Step 1: Fetch and parse HTML
    parsed_data = fetch_and_parse(url)

    # Step 2: Build prompt for selected framework
    prompt = build_prompt(url, parsed_data, framework)

    # Step 3: Generate with selected model
    if model == "gpt4":
        raw_code = generate_with_gpt4(prompt)
    elif model == "claude":
        raw_code = generate_with_claude(prompt)
    elif model == "grok":
        raw_code = generate_with_grok(prompt)
    else:
        raise ValueError(f"Unknown model: {model}")

    # Step 4: Clean the output
    clean = clean_code(raw_code)

    generation_time = round(time.time() - start_time, 2)
    elements_found = count_elements(parsed_data)

    return {
        "script": clean,
        "generation_time": generation_time,
        "elements_found": elements_found,
        "framework": framework,
        "model_used": model
    }