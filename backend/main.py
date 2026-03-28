from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from backend.models import GenerateRequest, GenerateResponse
from backend.engine import generate_test_script
from fastapi.responses import JSONResponse
import subprocess
import tempfile
import os
app = FastAPI(
    title="AutoQALLMs API",
    description="Generate test scripts from any URL using LLMs",
    version="1.0.0"
)

# This allows your React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "AutoQALLMs API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Main endpoint. Receives URL + model + framework.
    Returns generated test script.
    """
    # Basic validation
    if not request.url.startswith("http"):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://"
        )

    if request.model not in ["gpt4", "claude", "grok"]:
        raise HTTPException(
            status_code=400,
            detail="Model must be gpt4, claude, or grok"
        )

    if request.framework not in ["selenium_python", "playwright_js"]:
        raise HTTPException(
            status_code=400,
            detail="Framework must be selenium_python or playwright_js"
        )

    try:
        result = generate_test_script(
            url=request.url,
            model=request.model,
            framework=request.framework
        )
        return GenerateResponse(
            success=True,
            script=result["script"],
            generation_time=result["generation_time"],
            elements_found=result["elements_found"],
            framework=result["framework"],
            model_used=result["model_used"]
        )
    except Exception as e:
        return GenerateResponse(
            success=False,
            error=str(e)
        )
    

class RunRequest(BaseModel):
    script: str
    framework: str

@app.post("/run")
async def run_script(request: RunRequest):
    """
    Saves the script to a temp file and executes it.
    Returns the console output.
    """
    try:
        # Choose file extension based on framework
        ext = ".js" if request.framework == "playwright_js" else ".py"

        # Write script to a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=ext,
            delete=False
        ) as tmp:
            tmp.write(request.script)
            tmp_path = tmp.name

        # Run the script and capture output
        if request.framework == "playwright_js":
            cmd = ["node", tmp_path]
        else:
            cmd = ["python", tmp_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr[:1000]

        # Clean up temp file
        os.unlink(tmp_path)

        return {"success": True, "output": output}

    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Run timed out after 120 seconds."}
    except Exception as e:
        return {"success": False, "output": f"Run error: {str(e)}"}