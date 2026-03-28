import { useState } from "react";
import axios from "axios";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import "./App.css";

const API_URL = "https://autoqallms-api.onrender.com";

const MODELS = [
  { id: "claude", label: "Claude" },
  { id: "gpt4", label: "GPT-4" },
  { id: "grok", label: "Grok" },
];

const FRAMEWORKS = [
  { id: "selenium_python", label: "Selenium Python" },
  { id: "playwright_js", label: "Playwright JavaScript" },
  { id: "selenium_java", label: "Selenium Java" },
];

const FRAMEWORK_LABELS = {
  selenium_python: "Selenium Python",
  playwright_js: "Playwright JS",
  selenium_java: "Selenium Java",
};

export default function App() {
  const [url, setUrl] = useState("");
  const [model, setModel] = useState("claude");
  const [framework, setFramework] = useState("selenium_python");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [runOutput, setRunOutput] = useState(null);

  const handleGenerate = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setRunOutput(null);

    try {
      const response = await axios.post(`${API_URL}/generate`, {
        url: url.trim(),
        model,
        framework,
      });

      if (response.data.success) {
        setResult(response.data);
      } else {
        setError(response.data.error || "Generation failed.");
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        "Could not connect to backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(result.script);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    let ext = "py";
    if (framework === "playwright_js") ext = "js";
    if (framework === "selenium_java") ext = "java";
    const filename = `autoqallms_test.${ext}`;
    const blob = new Blob([result.script], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
  };

  const handleRunInfo = () => {
    let cmd = "python autoqallms_test.py";
    if (framework === "playwright_js") cmd = "node autoqallms_test.js";
    if (framework === "selenium_java") cmd = "javac autoqallms_test.java && java AutoQATest";

    setRunOutput(
      "To run this script locally on your machine:\n\n" +
      "1. Click Download to save the script\n" +
      "2. Open your terminal\n" +
      `3. Run: ${cmd}\n\n` +
      "Note: Chrome browser must be installed on your machine."
    );
  };

  let language = "python";
  if (framework === "playwright_js") language = "javascript";
  if (framework === "selenium_java") language = "java";

  const formatRunOutput = (output) => {
    return output.split("\n").map((line, i) => {
      let cls = "info-line";
      if (line.includes("Passed")) cls = "pass-line";
      else if (line.includes("Failed") || line.includes("Error")) cls = "fail-line";
      return <div key={i} className={cls}>{line}</div>;
    });
  };

  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <h1>AutoQALLMs</h1>
        <p>Generate automated test scripts from any URL using AI</p>
      </div>

      {/* Input Form */}
      <div className="form-card">
        <div className="form-group">
          <label>Website URL</label>
          <input
            className="url-input"
            type="text"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          />
        </div>

        <div className="form-group">
          <label>AI Model</label>
          <div className="options-row">
            {MODELS.map((m) => (
              <button
                key={m.id}
                className={`option-btn ${model === m.id ? "selected" : ""}`}
                onClick={() => setModel(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Framework</label>
          <div className="options-row">
            {FRAMEWORKS.map((f) => (
              <button
                key={f.id}
                className={`option-btn ${framework === f.id ? "selected" : ""}`}
                onClick={() => setFramework(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <button
          className="generate-btn"
          onClick={handleGenerate}
          disabled={loading || !url.trim()}
        >
          {loading ? "Generating..." : "Generate Test Script"}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Analysing page and generating tests...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="error-card">
          Error: {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <>
          {/* Stats */}
          <div className="stats-bar">
            <div className="stat">
              <span className="stat-label">Model</span>
              <span className="stat-value">
                {result.model_used?.toUpperCase()}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Framework</span>
              <span className="stat-value">
                {FRAMEWORK_LABELS[result.framework] || result.framework}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Elements Found</span>
              <span className="stat-value">{result.elements_found}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Generation Time</span>
              <span className="stat-value">{result.generation_time}s</span>
            </div>
          </div>

          {/* Script Output */}
          <div className="output-card">
            <div className="output-header">
              <span className="output-title">Generated Test Script</span>
              <div className="action-buttons">
                <button
                  className={`action-btn ${copied ? "copy-success" : ""}`}
                  onClick={handleCopy}
                >
                  {copied ? "Copied!" : "Copy"}
                </button>
                <button className="action-btn" onClick={handleDownload}>
                  Download
                </button>
                <button
                  className="action-btn run-btn"
                  onClick={handleRunInfo}
                >
                  How to Run
                </button>
              </div>
            </div>

            <div className="code-block">
              <SyntaxHighlighter
                language={language}
                style={vscDarkPlus}
                customStyle={{ margin: 0, borderRadius: 0 }}
                showLineNumbers
              >
                {result.script}
              </SyntaxHighlighter>
            </div>

            {/* Run Output */}
            {runOutput && (
              <div className="run-results">
                <h3>How to Run</h3>
                <div className="run-output">
                  {formatRunOutput(runOutput)}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}