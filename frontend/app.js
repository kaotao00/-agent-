const requestInput = document.getElementById("requestInput");
const resultOutput = document.getElementById("resultOutput");
const resultTabs = document.getElementById("resultTabs");
const statusText = document.getElementById("statusText");
const backendBadge = document.getElementById("backendBadge");
const loadDemoBtn = document.getElementById("loadDemoBtn");
const generateBtn = document.getElementById("generateBtn");
const searchBtn = document.getElementById("searchBtn");
const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const categoryInput = document.getElementById("categoryInput");
const regionInput = document.getElementById("regionInput");
const projectTypeInput = document.getElementById("projectTypeInput");
const tagsInput = document.getElementById("tagsInput");

let currentResult = null;

const tabLabels = {
  overview: "总览",
  technical: "技术方案",
  budget: "预算报价",
  business: "商务资质",
  compliance: "合规校验",
  memory: "共享记忆",
  logs: "执行日志",
};

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

function setStatus(text) {
  statusText.textContent = text;
}

function renderTabs(sectionNames) {
  resultTabs.innerHTML = "";
  const tabs = ["overview", ...sectionNames, "memory", "logs"];
  tabs.forEach((name, index) => {
    const button = document.createElement("button");
    button.className = `tab-button ${index === 0 ? "active" : ""}`;
    button.textContent = tabLabels[name] || name;
    button.addEventListener("click", () => showTab(name, button));
    resultTabs.appendChild(button);
  });
}

function showTab(name, clickedButton) {
  [...resultTabs.children].forEach((tab) => tab.classList.remove("active"));
  clickedButton.classList.add("active");
  if (!currentResult) {
    resultOutput.textContent = "暂无结果";
    return;
  }
  if (name === "overview") {
    resultOutput.textContent = pretty({
      项目名称: currentResult.project_name,
      检索后端: currentResult.retrieval_backend,
      执行计划: currentResult.execution_plan,
    });
    return;
  }
  if (name === "memory") {
    resultOutput.textContent = pretty(currentResult.shared_memory);
    return;
  }
  if (name === "logs") {
    resultOutput.textContent = pretty(currentResult.agent_logs);
    return;
  }
  resultOutput.textContent = pretty(currentResult.sections[name]);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function loadDemoRequest() {
  setStatus("正在载入示例请求...");
  const data = await fetchJson("/api/demo-request");
  requestInput.value = pretty(data);
  setStatus("示例请求已载入");
}

async function loadHealth() {
  const data = await fetchJson("/api/health");
  backendBadge.textContent = `检索模式：${data.retrieval_backend}`;
}

async function generateTender() {
  try {
    setStatus("正在生成标书...");
    const payload = JSON.parse(requestInput.value);
    currentResult = await fetchJson("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderTabs(Object.keys(currentResult.sections));
    resultOutput.textContent = pretty(currentResult);
    setStatus("标书生成完成");
  } catch (error) {
    setStatus("标书生成失败");
    resultOutput.textContent = String(error);
  }
}

async function searchKnowledge() {
  try {
    setStatus("正在执行知识检索...");
    const payload = JSON.parse(requestInput.value);
    const query = encodeURIComponent(`${payload.project_type} ${payload.region} 招标文件 施工 预算 资质 合规`);
    const data = await fetchJson(`/api/search?query=${query}`);
    currentResult = null;
    resultTabs.innerHTML = "";
    resultOutput.textContent = pretty(data);
    setStatus("知识检索完成");
  } catch (error) {
    setStatus("知识检索失败");
    resultOutput.textContent = String(error);
  }
}

async function uploadDocument() {
  try {
    if (!fileInput.files.length) {
      throw new Error("请先选择要导入的文件");
    }
    setStatus("正在导入知识文件...");
    const form = new FormData();
    form.append("file", fileInput.files[0]);
    form.append("category", categoryInput.value);
    form.append("region", regionInput.value.trim() || "通用");
    form.append("project_type", projectTypeInput.value.trim() || "general");
    form.append("tags", tagsInput.value.trim() || "导入文档,RAG");
    const data = await fetchJson("/api/ingest-document", {
      method: "POST",
      body: form,
    });
    currentResult = null;
    resultTabs.innerHTML = "";
    resultOutput.textContent = pretty(data);
    await loadHealth();
    setStatus("知识文件导入完成");
  } catch (error) {
    setStatus("知识文件导入失败");
    resultOutput.textContent = String(error);
  }
}

loadDemoBtn.addEventListener("click", loadDemoRequest);
generateBtn.addEventListener("click", generateTender);
searchBtn.addEventListener("click", searchKnowledge);
uploadBtn.addEventListener("click", uploadDocument);

loadHealth();
loadDemoRequest();
