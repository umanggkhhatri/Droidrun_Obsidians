// Global state
const state = {
  description: "",
  mediaSourceInstructions: "",
  links: "",
  platforms: ["threads"],
  eventSource: null,
};

// DOM Elements
const descriptionInput = document.getElementById("descriptionInput");
const charCount = document.getElementById("charCount");
const mediaSourceInput = document.getElementById("mediaSourceInput");
const linksInput = document.getElementById("linksInput");
const postBtn = document.getElementById("postBtn");
const clearBtn = document.getElementById("clearBtn");
const resultsSection = document.getElementById("resultsSection");
const resultsList = document.getElementById("resultsList");

// Terminal Elements
const terminalLog = document.getElementById("terminalLog");
const clearLogBtn = document.getElementById("clearLogBtn");
const statusIndicator = document.getElementById("statusIndicator");
const progressInline = document.getElementById("progressInline");
const progressFillInline = document.getElementById("progressFillInline");
const progressTextInline = document.getElementById("progressTextInline");

// Event Listeners
descriptionInput.addEventListener("input", handleDescriptionChange);
mediaSourceInput.addEventListener("input", handleMediaSourceChange);
linksInput.addEventListener("input", handleLinksChange);
postBtn.addEventListener("click", handlePost);
clearBtn.addEventListener("click", handleClear);
clearLogBtn.addEventListener("click", clearTerminalLog);

function handleDescriptionChange(e) {
  state.description = e.target.value;
  charCount.textContent = state.description.length;
}

function handleMediaSourceChange(e) {
  state.mediaSourceInstructions = e.target.value;
}

function handleLinksChange(e) {
  state.links = e.target.value;
}

function handleClear() {
  state.description = "";
  state.mediaSourceInstructions = "";
  state.links = "";
  descriptionInput.value = "";
  mediaSourceInput.value = "";
  linksInput.value = "";
  charCount.textContent = "0";
  resultsSection.classList.add("hidden");
}

async function handlePost() {
  // Validation
  if (
    !state.description.trim() &&
    !state.mediaSourceInstructions.trim() &&
    !state.links.trim()
  ) {
    alert(
      "Please write a description, add media source instructions, or add links",
    );
    return;
  }

  const selectedPlatforms = getSelectedPlatforms();
  if (selectedPlatforms.length === 0) {
    alert("Please select at least one platform");
    return;
  }

  // Clear previous logs and show running state
  clearTerminalLog();
  setRunningState(true);
  appendToTerminalLog("🚀 Starting post workflow...", "step");

  // Connect to progress stream BEFORE making the request
  connectProgressStream();

  try {
    const formData = new FormData();
    formData.append("text", state.description);
    formData.append("media_source_instructions", state.mediaSourceInstructions);
    formData.append("links", state.links);
    formData.append("platforms", JSON.stringify(selectedPlatforms));

    appendToTerminalLog("📤 Sending request to server...", "info");

    const response = await fetch("/api/post", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (data.success) {
      appendToTerminalLog("✅ Post completed successfully!", "success");
      displayResults(data.results);
      handleClear();
    } else {
      appendToTerminalLog("❌ Error: " + data.message, "error");
      alert("Error: " + data.message);
    }
  } catch (error) {
    console.error("Error:", error);
    appendToTerminalLog("💥 Error: " + error.message, "error");
    alert("Error posting content: " + error.message);
  } finally {
    setRunningState(false);
    if (state.eventSource) {
      state.eventSource.close();
    }
  }
}

function getSelectedPlatforms() {
  const checkboxes = document.querySelectorAll(
    'input[name="platform"]:checked',
  );
  return Array.from(checkboxes).map((cb) => cb.value);
}

function connectProgressStream() {
  if (state.eventSource) {
    state.eventSource.close();
  }

  state.eventSource = new EventSource("/api/progress");

  state.eventSource.onmessage = function (event) {
    try {
      const data = JSON.parse(event.data);

      // Skip heartbeat
      if (data.type === "heartbeat") {
        return;
      }

      // Handle log-only messages
      if (data.type === "log") {
        appendToTerminalLog(data.log, data.logType || "info");
        return;
      }

      // Handle progress updates
      if (data.percentage !== undefined) {
        updateProgressBar(data.percentage);
      }

      // Add log if present
      if (data.log) {
        appendToTerminalLog(data.log, data.logType || "info");
      }

      // Add message as log
      if (data.message && !data.log) {
        appendToTerminalLog(data.message, "step");
      }

      // Add details as log
      if (data.details) {
        appendToTerminalLog("  → " + data.details, "info");
      }
    } catch (e) {
      console.error("Error parsing progress:", e);
    }
  };

  state.eventSource.onerror = function () {
    console.error("Progress stream disconnected");
  };
}

function setRunningState(running) {
  postBtn.disabled = running;

  if (running) {
    statusIndicator.textContent = "● Running";
    statusIndicator.classList.add("running");
    progressInline.classList.remove("hidden");
    progressFillInline.style.width = "0%";
    progressTextInline.textContent = "0%";
  } else {
    statusIndicator.textContent = "● Idle";
    statusIndicator.classList.remove("running");
    progressInline.classList.add("hidden");
  }
}

function updateProgressBar(percentage) {
  progressFillInline.style.width = `${percentage}%`;
  progressTextInline.textContent = `${percentage}%`;
}

function appendToTerminalLog(message, type = "info") {
  const timestamp = new Date().toLocaleTimeString();
  const logEntry = document.createElement("div");
  logEntry.className = `log-${type}`;
  logEntry.textContent = `[${timestamp}] ${message}`;
  terminalLog.appendChild(logEntry);
  terminalLog.scrollTop = terminalLog.scrollHeight;
}

function clearTerminalLog() {
  terminalLog.innerHTML =
    '<div class="log-info">[Ready] Waiting for task...</div>';
}

function displayResults(results) {
  resultsSection.classList.remove("hidden");
  resultsList.innerHTML = "";

  results.forEach((result) => {
    const resultItem = document.createElement("div");
    resultItem.className = `result-item ${result.success ? "success" : "error"}`;

    const icon = result.success ? "✓" : "✕";
    const platformName =
      result.platform.charAt(0).toUpperCase() + result.platform.slice(1);
    const message = result.reason || result.error || "Unknown error";

    resultItem.innerHTML = `
      <div class="result-icon">${icon}</div>
      <div class="result-content">
        <div class="result-platform">${platformName}</div>
        <div class="result-message">${message}</div>
      </div>
    `;

    resultsList.appendChild(resultItem);
  });

  resultsSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  const checkboxes = document.querySelectorAll('input[name="platform"]');
  checkboxes.forEach((cb) => {
    cb.addEventListener("change", () => {
      state.platforms = getSelectedPlatforms();
    });
  });
});
