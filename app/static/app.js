const uploadForm = document.querySelector("#upload-form");
const pdfInput = document.querySelector("#pdf-input");
const fileTitle = document.querySelector("#file-title");
const fileSubtitle = document.querySelector("#file-subtitle");
const uploadButton = document.querySelector("#upload-button");
const clearButton = document.querySelector("#clear-button");
const documentName = document.querySelector("#document-name");
const statusDot = document.querySelector("#status-dot");
const statusText = document.querySelector("#status-text");
const messages = document.querySelector("#messages");
const askForm = document.querySelector("#ask-form");
const questionInput = document.querySelector("#question-input");
const askButton = document.querySelector("#ask-button");
const headerCopy = document.querySelector("#header-copy");

let currentDocumentId = null;
let statusTimer = null;

pdfInput.addEventListener("change", () => {
  const file = pdfInput.files[0];
  if (!file) {
    fileTitle.textContent = "Choose a PDF";
    fileSubtitle.textContent = "Drop or browse up to your configured limit";
    return;
  }
  fileTitle.textContent = file.name;
  fileSubtitle.textContent = `${formatBytes(file.size)} selected`;
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = pdfInput.files[0];
  if (!file) {
    addMessage("system", "Choose a PDF first.");
    return;
  }

  setBusy(uploadButton, true, "Uploading");
  setAskEnabled(false);
  clearMessages();

  const body = new FormData();
  body.append("file", file);

  try {
    const response = await fetch("/documents/upload", {
      method: "POST",
      body,
    });
    const payload = await readJson(response);
    if (!response.ok) {
      throw new Error(payload.detail || "Upload failed");
    }

    currentDocumentId = payload.document_id;
    documentName.textContent = payload.filename;
    clearButton.disabled = false;
    headerCopy.textContent = "Indexing the PDF. Questions unlock as soon as retrieval is ready.";
    setStatus("processing", "Processing");
    addMessage("system", "PDF uploaded. Indexing is running in the background.");
    pollStatus();
  } catch (error) {
    addMessage("error", error.message);
    setStatus("failed", "Upload failed");
  } finally {
    setBusy(uploadButton, false, "Upload and Index");
  }
});

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || !currentDocumentId) {
    return;
  }

  addMessage("user", question);
  questionInput.value = "";
  setBusy(askButton, true, "Asking");
  setAskEnabled(false);

  try {
    const response = await fetch(`/documents/${currentDocumentId}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });
    const payload = await readJson(response);
    if (!response.ok) {
      throw new Error(payload.detail || "Question failed");
    }
    addAnswer(payload);
  } catch (error) {
    addMessage("error", error.message);
  } finally {
    setBusy(askButton, false, "Ask");
    setAskEnabled(true);
    questionInput.focus();
  }
});

clearButton.addEventListener("click", () => {
  currentDocumentId = null;
  stopPolling();
  documentName.textContent = "No document uploaded";
  clearButton.disabled = true;
  pdfInput.value = "";
  fileTitle.textContent = "Choose a PDF";
  fileSubtitle.textContent = "Drop or browse up to your configured limit";
  headerCopy.textContent = "Upload a document and ask grounded questions with page citations.";
  setStatus("idle", "Waiting");
  setAskEnabled(false);
  clearMessages();
});

function pollStatus() {
  stopPolling();
  fetchStatus();
  statusTimer = window.setInterval(fetchStatus, 1800);
}

async function fetchStatus() {
  if (!currentDocumentId) {
    return;
  }

  try {
    const response = await fetch(`/documents/${currentDocumentId}/status`);
    const payload = await readJson(response);
    if (!response.ok) {
      throw new Error(payload.detail || "Could not load document status");
    }

    documentName.textContent = payload.filename;
    setStatus(payload.status, titleCase(payload.status));

    if (payload.status === "ready") {
      stopPolling();
      setAskEnabled(true);
      headerCopy.textContent = "Ask questions and inspect the retrieved citations.";
      addMessage("system", "Indexing complete. You can ask questions now.");
      questionInput.focus();
    }

    if (payload.status === "failed") {
      stopPolling();
      setAskEnabled(false);
      addMessage("error", payload.error_message || "Document processing failed.");
    }
  } catch (error) {
    stopPolling();
    setStatus("failed", "Status unavailable");
    addMessage("error", error.message);
  }
}

function addAnswer(payload) {
  const wrapper = document.createElement("article");
  wrapper.className = "message assistant";

  const answer = document.createElement("div");
  answer.className = "answer-content";
  const answerText = payload.cached ? `${payload.answer}\n\n_Cached answer._` : payload.answer;
  answer.innerHTML = renderMarkdown(answerText);
  wrapper.append(answer);

  if (payload.citations?.length) {
    const citations = document.createElement("div");
    citations.className = "citations";

    payload.citations.slice(0, 4).forEach((citation) => {
      const item = document.createElement("div");
      item.className = "citation";

      const heading = document.createElement("strong");
      heading.textContent = `Page ${citation.page_number} · score ${citation.score.toFixed(3)}`;

      const snippet = document.createElement("span");
      snippet.textContent = citation.text;

      item.append(heading, snippet);
      citations.append(item);
    });

    wrapper.append(citations);
  }

  messages.append(wrapper);
  scrollMessages();
}

function addMessage(type, text) {
  const emptyState = messages.querySelector(".empty-state");
  if (emptyState) {
    emptyState.remove();
  }

  const message = document.createElement("article");
  message.className = `message ${type}`;
  const body = document.createElement("p");
  body.textContent = text;
  message.append(body);
  messages.append(message);
  scrollMessages();
}

function clearMessages() {
  messages.innerHTML = `
    <div class="empty-state">
      <h3>Ready when your document is.</h3>
      <p>Answers will appear here with retrieved source snippets and page numbers.</p>
    </div>
  `;
}

function setStatus(status, text) {
  statusDot.className = `status-dot ${status}`;
  statusText.textContent = text;
}

function setAskEnabled(enabled) {
  questionInput.disabled = !enabled;
  askButton.disabled = !enabled;
}

function setBusy(button, busy, text) {
  button.disabled = busy;
  button.textContent = text;
}

function stopPolling() {
  if (statusTimer) {
    window.clearInterval(statusTimer);
    statusTimer = null;
  }
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function scrollMessages() {
  messages.scrollTop = messages.scrollHeight;
}

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let listType = null;
  let inCodeBlock = false;
  let codeLines = [];

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
        inCodeBlock = false;
      } else {
        closeList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(rawLine);
      continue;
    }

    if (!line.trim()) {
      closeList();
      continue;
    }

    const heading = line.match(/^(#{2,4})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = Math.min(heading[1].length, 4);
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    if (unordered) {
      if (listType !== "ul") {
        closeList();
        html.push("<ul>");
        listType = "ul";
      }
      html.push(`<li>${renderInline(unordered[1])}</li>`);
      continue;
    }

    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (ordered) {
      if (listType !== "ol") {
        closeList();
        html.push("<ol>");
        listType = "ol";
      }
      html.push(`<li>${renderInline(ordered[1])}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${renderInline(line.trim())}</p>`);
  }

  if (inCodeBlock) {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  closeList();
  return html.join("");
}

function renderInline(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/_([^_]+)_/g, "<em>$1</em>");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
