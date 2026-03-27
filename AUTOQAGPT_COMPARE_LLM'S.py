import os
import re
import json
import time
import requests
import autopep8
from logger import build_record, save_record
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import anthropic
import openai
from xai_sdk import Client
from xai_sdk.chat import user, system
from anthropic import Anthropic


# Load Environment Variables

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")



# Fetch HTML content

def fetch_html(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


# Parse HTML and extract elements

def parse_html(soup):
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


# Generate code using GPT-4

def generate_with_gpt4(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Senior Selenium Automation Tester with 10+ years of experience "
                        "in Python and QA automation. Your job is to generate latest,perfect, executable "
                        "Python Selenium test scripts — no markdown, no explanations, only clean code."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1800,
        )

        code_output = response.choices[0].message.content.strip()

        # Remove markdown fences if any
        code_output = re.sub(r"^```(?:python)?", "", code_output, flags=re.MULTILINE).strip()
        code_output = re.sub(r"```$", "", code_output, flags=re.MULTILINE).strip()

        match = re.search(r"(?m)^(from\s+\S+\s+import\s+\S+|import\s+\S+)", code_output)
        if match:
            code_output = code_output[match.start():]

        # Keep all lines up to and including driver.quit()
        match_end = re.search(r"driver\.quit\(\)", code_output)
        if match_end:
            code_output = code_output[: match_end.end()]

        return code_output.strip()

    except Exception as e:
        print(f"Error generating Selenium code: {e}")
        return None

# Generate code using Claude 4.5

def generate_with_claude(prompt):
    try:
        client = Anthropic(api_key=ANTHROPIC_KEY)

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            system="You are a senior Selenium QA engineer who writes clean, optimized Selenium test scripts.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=4000,
        )


        return response.content[0].text.strip()

    except Exception as e:
        print(f"Claude Error: {e}")
        return None





# Generate code using Grok Fast (xAI)



def generate_with_grok(prompt):
    try:
        client = Client(
        api_key=XAI_API_KEY,
        timeout=5000)



        chat = client.chat.create(model="grok-code-fast-1")
        chat.append(system("You are a senior Selenium QA engineer who writes clean, optimized Selenium test scripts."))
        chat.append(user(prompt))


        response = chat.sample()

        # Return clean code text
        return response.content.strip()
    except Exception as e:
        print(f"Grok Error: {e}")
        return None





# Main code generation handler

def generate_selenium_code(url, parsed_data, model_choice="gpt4"):
    """
        Sends structured HTML data to the LLM and requests clean, executable Python Selenium code only.
        The model is explicitly instructed to output raw Python code with no extra text or Markdown.
        """
    prompt = (
        f"-You are a **strict code generator**. Your output must contain ONLY executable Python code, "
        f"-with no explanations, comments, or markdown fences.\n\n"
        f"-Generate Selenium Python test code for the following parsed HTML data.\n\n"
        f"-URL: {url}\n\n"
        f"-Parsed Data:\n{json.dumps(parsed_data, indent=2)[:2000]}...\n\n"
        f"-Instructions:\n"
        f"-Add test for javascript based webelements also"
        f"-Automate each test case using Selenium 4+ syntax.\n"
        f"-**Use only 'find_element(By.<LOCATOR>, value)' and 'find_elements(By.<LOCATOR>, value)'** — never use deprecated 'find_element_by_*' or 'find_elements_by_*' methods.\n"
        f"-Import 'By' from 'selenium.webdriver.common.by' at the top of the code.\n"
        f"- Open the page using ChromeDriver (not headless) and maximize the window.\n"
        f"- Add time.sleep() where ever needed"
        f"- Create 30 sequential test cases that interact with the elements (titles, headings, images, links, forms, inputs, buttons, and selects).\n"
        f"- Each test should include realistic user actions (typing, clicking, submitting, selecting options) with time.sleep() between actions.\n"
        f"- Log each test as 'Test X Passed/Failed' directly in the console.\n"
        f"- Include 'driver.quit()' at the end of the script.\n"
        f"- Do NOT include markdown (```) or any descriptive text before or after the code.\n"
        f"- The entire output must be syntactically valid Python — ready to run as-is.\n"

    )

    if model_choice == "gpt4":
        return generate_with_gpt4(prompt)
    elif model_choice == "claude":
        return generate_with_claude(prompt)
    elif model_choice == "grok":
        return generate_with_grok(prompt)
    else:
        raise ValueError("Invalid model choice. Use 'gpt4', 'claude', or 'grok'.")


# Code cleanup and formatting

def clean_selenium_code(code):
    unwanted_patterns = [
        r"```python", r"```",
        r"Here is.*?code.*?:", r"Please replace.*?\n",
    ]
    for pattern in unwanted_patterns:
        code = re.sub(pattern, "", code, flags=re.DOTALL)
    return code

def remove_lines_after_quit(code):
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if "driver.quit()" in line:
            return "\n".join(lines[: i + 1])
    return code

def format_selenium_code(code):
    return autopep8.fix_code(code)


# Chrome setup and execution

def setup_chrome():
    options = Options()
    driver = webdriver.Chrome(options=options)
    return driver

def execute_selenium_code(selenium_code):
    cleaned = clean_selenium_code(selenium_code)
    formatted = format_selenium_code(cleaned)
    final = remove_lines_after_quit(formatted)

    with open("generated_test.py", "w") as f:
        f.write(final)
    print("\n Selenium Test Script Saved as generated_test.py")

    print("\n Running Selenium Tests...\n")

    # Capture the output of the test run so we can count passes and fails
    import subprocess
    result = subprocess.run(
        ["python", "generated_test.py"],
        capture_output=True,
        text=True
    )

    # Print the output to console so you still see it as before
    print(result.stdout)
    if result.stderr:
        print("[STDERR]", result.stderr[:500])

    # Count how many tests passed and failed from the console output
    passed = result.stdout.count("Passed")
    failed = result.stdout.count("Failed")

    return passed, failed



# MAIN ENTRY POINT

def main():
    url = input("Enter the URL to parse and test: ").strip()
    model_choice = input("Select model (gpt4 / claude / grok): ").strip().lower()

    print("\n Fetching and Parsing HTML...")
    soup = fetch_html(url)
    parsed_data = parse_html(soup)
    print(json.dumps(parsed_data, indent=2))

    print(f"\n Generating Selenium Code using {model_choice.upper()}...")
    start_time = time.time()
    selenium_code = generate_selenium_code(url, parsed_data, model_choice)
    duration = time.time() - start_time
    print(f"\n Generation Time: {duration:.2f} seconds")

    if selenium_code:
        print("\n--- Generated Code (preview) ---\n")
        print(selenium_code[:800], "...\n")

        # Start timing the execution
        exec_start = time.time()
        tests_passed, tests_failed = execute_selenium_code(selenium_code)
        exec_duration = time.time() - exec_start

        # Build and save the training record
        record = build_record(
            url=url,
            model_used=model_choice,
            parsed_data=parsed_data,
            generation_time=duration,
            execution_time=exec_duration,
            tests_passed=tests_passed,
            tests_failed=tests_failed
        )
        save_record(record)

    else:
        print(" Failed to generate Selenium code.")

if __name__ == "__main__":
    main()
