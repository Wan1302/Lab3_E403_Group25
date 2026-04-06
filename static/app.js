const questionInput = document.getElementById("question-input");
const runButton = document.getElementById("run-button");
const statusLine = document.getElementById("status-line");

const providerValue = document.getElementById("provider-value");
const toolsetValue = document.getElementById("toolset-value");
const deltaTokenV1Value = document.getElementById("delta-token-v1-value");
const deltaTokenV2Value = document.getElementById("delta-token-v2-value");
const deltaLatencyV1Value = document.getElementById("delta-latency-v1-value");
const deltaLatencyV2Value = document.getElementById("delta-latency-v2-value");

const panelMap = {
  chatbot: {
    answer: document.getElementById("chatbot-answer"),
    promptTokens: document.getElementById("chatbot-prompt-tokens"),
    completionTokens: document.getElementById("chatbot-completion-tokens"),
    totalTokens: document.getElementById("chatbot-total-tokens"),
    latency: document.getElementById("chatbot-latency"),
    details: document.getElementById("chatbot-details"),
  },
  react_v1: {
    answer: document.getElementById("react-answer"),
    promptTokens: document.getElementById("react-prompt-tokens"),
    completionTokens: document.getElementById("react-completion-tokens"),
    totalTokens: document.getElementById("react-total-tokens"),
    latency: document.getElementById("react-latency"),
    steps: document.getElementById("react-steps"),
    toolCalls: document.getElementById("react-tool-calls"),
    details: document.getElementById("react-details"),
  },
  langgraph_v2: {
    answer: document.getElementById("v2-answer"),
    promptTokens: document.getElementById("v2-prompt-tokens"),
    completionTokens: document.getElementById("v2-completion-tokens"),
    totalTokens: document.getElementById("v2-total-tokens"),
    latency: document.getElementById("v2-latency"),
    steps: document.getElementById("v2-steps"),
    toolCalls: document.getElementById("v2-tool-calls"),
    details: document.getElementById("v2-details"),
  },
};

function formatNumber(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat("vi-VN").format(value);
}

function formatLatency(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${formatNumber(value)} ms`;
}

function buildChatbotDetails(data) {
  return [
    `Mo hinh: ${data.details.model}`,
    `Provider: ${data.details.provider}`,
    `Do tre: ${formatLatency(data.details.latency_ms)}`,
    `Prompt tokens: ${formatNumber(data.details.usage.prompt_tokens || 0)}`,
    `Completion tokens: ${formatNumber(data.details.usage.completion_tokens || 0)}`,
    "",
    "Noi dung tra loi:",
    data.answer,
  ].join("\n");
}

function buildAgentDetails(data) {
  const history = (data.details.history || []).join("\n");
  const toolCalls = (data.details.tool_calls || [])
    .map((tool, index) => `${index + 1}. ${tool.tool_name}(${tool.args})\n   => ${tool.observation}`)
    .join("\n");

  return [
    `Mo hinh: ${data.details.model}`,
    `So buoc suy luan: ${formatNumber(data.details.steps || 0)}`,
    `So lan goi tool: ${formatNumber((data.details.tool_calls || []).length)}`,
    `Do tre cong don: ${formatLatency(data.details.latency_ms)}`,
    `Prompt tokens: ${formatNumber(data.details.usage.prompt_tokens || 0)}`,
    `Completion tokens: ${formatNumber(data.details.usage.completion_tokens || 0)}`,
    "",
    "Cac lan goi cong cu:",
    toolCalls || "Khong co",
    "",
    "Nhat ky suy luan:",
    history || "Khong co",
  ].join("\n");
}

function updateChatbot(data) {
  const panel = panelMap.chatbot;
  panel.answer.textContent = data.answer;
  panel.promptTokens.textContent = formatNumber(data.metrics.prompt_tokens);
  panel.completionTokens.textContent = formatNumber(data.metrics.completion_tokens);
  panel.totalTokens.textContent = formatNumber(data.metrics.total_tokens);
  panel.latency.textContent = formatLatency(data.metrics.latency_ms);
  panel.details.textContent = buildChatbotDetails(data);
}

function updateAgent(key, data) {
  const panel = panelMap[key];
  panel.answer.textContent = data.answer;
  panel.promptTokens.textContent = formatNumber(data.metrics.prompt_tokens);
  panel.completionTokens.textContent = formatNumber(data.metrics.completion_tokens);
  panel.totalTokens.textContent = formatNumber(data.metrics.total_tokens);
  panel.latency.textContent = formatLatency(data.metrics.latency_ms);
  panel.steps.textContent = formatNumber(data.details.steps || 0);
  panel.toolCalls.textContent = formatNumber((data.details.tool_calls || []).length);
  panel.details.textContent = buildAgentDetails(data);
}

function updatePanel(data) {
  providerValue.textContent = data.provider;
  toolsetValue.textContent = data.toolset;

  updateChatbot(data.chatbot);
  updateAgent("react_v1", data.react_v1);
  updateAgent("langgraph_v2", data.langgraph_v2);

  deltaTokenV1Value.textContent = `${formatNumber(data.react_v1.metrics.total_tokens - data.chatbot.metrics.total_tokens)} token`;
  deltaTokenV2Value.textContent = `${formatNumber(data.langgraph_v2.metrics.total_tokens - data.chatbot.metrics.total_tokens)} token`;
  deltaLatencyV1Value.textContent = formatLatency(data.react_v1.metrics.latency_ms - data.chatbot.metrics.latency_ms);
  deltaLatencyV2Value.textContent = formatLatency(data.langgraph_v2.metrics.latency_ms - data.react_v1.metrics.latency_ms);
}

async function runComparison() {
  const question = questionInput.value.trim();
  if (!question) {
    statusLine.textContent = "Vui long nhap cau hoi truoc khi chay.";
    return;
  }

  runButton.disabled = true;
  statusLine.textContent = "Dang goi mo hinh va so sanh 3 phien ban...";

  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Khong the xu ly yeu cau.");
    }

    updatePanel(data);
    statusLine.textContent = "Da chay xong. Ban co the doi cau hoi de tiep tuc so sanh.";
  } catch (error) {
    statusLine.textContent = `Co loi xay ra: ${error.message}`;
  } finally {
    runButton.disabled = false;
  }
}

runButton.addEventListener("click", runComparison);
questionInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    runComparison();
  }
});

document.querySelectorAll(".example-pill").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.prompt || "";
    questionInput.focus();
  });
});
