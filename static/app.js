// ── State ────────────────────────────────────────────
const state = {
  token: localStorage.getItem("token") || null,
  authMode: "login",
  sourceMode: "ai",
  difficulty: "easy",
  questionType: "multiple-choice",
  timerChoice: "None",
  docTimerChoice: "None",
  selectedFile: null,
  questions: [],
  answers: {},          // { index: answerRecord }
  currentIndex: 0,
  selectedOptions: [],  // for current question (multi-answer support)
  timerInterval: null,
  timeLeft: null,
  lastResult: null,
  charts: {},
}

const API = ""   // same origin

// ── Utilities ────────────────────────────────────────

function api(path, options = {}) {
  return fetch(API + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
      ...(options.headers || {}),
    },
  })
}

function showToast(msg) {
  let t = document.getElementById("toast")
  if (!t) {
    t = document.createElement("div")
    t.id = "toast"
    t.className = "toast"
    document.body.appendChild(t)
  }
  t.textContent = msg
  t.classList.add("show")
  setTimeout(() => t.classList.remove("show"), 2500)
}

function showError(id, msg) {
  const el = document.getElementById(id)
  if (!el) return
  el.textContent = msg
  el.classList.remove("hidden")
}

function clearError(id) {
  const el = document.getElementById(id)
  if (el) el.classList.add("hidden")
}

// ── Page switching ────────────────────────────────────

function switchPage(name) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"))
  const page = document.getElementById(`page-${name}`)
  if (page) page.classList.add("active")

  if (name === "history")   loadHistory()
  if (name === "analytics") loadAnalytics()
}

// ── Auth ─────────────────────────────────────────────

function authTab(mode) {
  state.authMode = mode
  document.querySelectorAll(".tab-row .tab").forEach((t, i) => {
    t.classList.toggle("active", (i === 0 && mode === "login") || (i === 1 && mode === "register"))
  })
  document.querySelector("#auth-form .btn-primary").textContent =
    mode === "login" ? "Login" : "Register"
  clearError("auth-error")
}

async function submitAuth() {
  const username = document.getElementById("auth-username").value.trim()
  const password = document.getElementById("auth-password").value.trim()
  clearError("auth-error")

  if (!username || !password) return showError("auth-error", "Please fill in both fields")

  const endpoint = state.authMode === "login" ? "/auth/login" : "/auth/register"
  const res = await api(endpoint, { method: "POST", body: JSON.stringify({ username, password }) })
  const data = await res.json()

  if (!res.ok) return showError("auth-error", data.detail || "Something went wrong")

  if (state.authMode === "register") {
    showToast("Account created! Please log in.")
    authTab("login")
    return
  }

  state.token = data.access_token
  localStorage.setItem("token", state.token)
  checkShareLink()
  switchPage("setup")
}

function logout() {
  state.token = null
  localStorage.removeItem("token")
  switchPage("auth")
}

// ── Setup helpers ─────────────────────────────────────

function setPill(btn, group) {
  btn.closest(".pill-group").querySelectorAll(".pill").forEach(p => p.classList.remove("active"))
  btn.classList.add("active")
  if (group === "difficulty") state.difficulty = btn.textContent.trim()
  if (group === "timer") state.timerChoice = btn.textContent.trim()
  if (group === "doc-timer") state.docTimerChoice = btn.textContent.trim()
}

function setType(btn, type) {
  document.querySelectorAll(".type-card").forEach(c => c.classList.remove("active"))
  btn.classList.add("active")
  state.questionType = type
}

function sourceTab(mode) {
  state.sourceMode = mode
  document.querySelectorAll(".source-tabs .tab").forEach((t, i) => {
    t.classList.toggle("active", (i === 0 && mode === "ai") || (i === 1 && mode === "doc"))
  })
  document.getElementById("source-ai").classList.toggle("hidden", mode !== "ai")
  document.getElementById("source-doc").classList.toggle("hidden", mode !== "doc")
}

function handleFileSelect(input) {
  state.selectedFile = input.files[0] || null
  const nameEl = document.getElementById("file-name")
  if (state.selectedFile) {
    nameEl.textContent = state.selectedFile.name
    nameEl.classList.remove("hidden")
  } else {
    nameEl.classList.add("hidden")
  }
}

function getTimeLimit() {
  const map = { "None": null, "10 min": 600, "20 min": 1200, "30 min": 1800 }
  return map[state.timerChoice] ?? null
}

// ── Start quiz (AI) ───────────────────────────────────

async function startAIQuiz() {
  const topic = document.getElementById("topic").value.trim()
  clearError("setup-error")
  if (!topic) return showError("setup-error", "Please enter a topic")

  const count = parseInt(document.getElementById("count").value)
  const body = {
    topic,
    difficulty: state.difficulty,
    count,
    type: state.questionType,
    time_limit: getTimeLimit(),
  }

  const btn = document.querySelector("#source-ai .btn-primary")
  btn.textContent = "Generating…"
  btn.disabled = true

  const res = await api("/quiz/generate", { method: "POST", body: JSON.stringify(body) })
  const data = await res.json()

  btn.textContent = "Generate Quiz →"
  btn.disabled = false

  if (!res.ok) return showError("setup-error", data.detail || "Failed to generate quiz")

  initQuiz(data, getTimeLimit())
}

// ── Start quiz (Document) ─────────────────────────────

async function startDocQuiz() {
  clearError("doc-error")
  if (!state.selectedFile) return showError("doc-error", "Please upload a file first")

  const formData = new FormData()
  formData.append("file", state.selectedFile)

  const btn = document.querySelector("#source-doc .btn-primary")
  btn.textContent = "Parsing…"
  btn.disabled = true

  const res = await fetch(API + "/quiz/from-document", {
    method: "POST",
    headers: { Authorization: `Bearer ${state.token}` },
    body: formData,
  })
  const data = await res.json()

  btn.textContent = "Start Quiz →"
  btn.disabled = false

  if (!res.ok) return showError("doc-error", data.detail || "Failed to parse document")

  const map = { "None": null, "10 min": 600, "20 min": 1200, "30 min": 1800 }
  const timeLimit = map[state.docTimerChoice] ?? null
  initQuiz(data, timeLimit)
}

// ── Quiz initialisation ───────────────────────────────

function shuffle(array) {
  const arr = [...array]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

function shuffleQuestions(questions) {
  return shuffle(questions).map(q => {
    // Only shuffle options for multiple-choice and true-false
    if (!q.options || q.type === "true-false") return q

    // Track which indices are correct before shuffling
    const indexed = q.options.map((opt, i) => ({
      opt,
      isCorrect: q.correct_answers.includes(i)
    }))

    const shuffled = shuffle(indexed)

    // Rebuild correct_answers indices based on new positions
    const newCorrectAnswers = shuffled
      .map((item, i) => item.isCorrect ? i : null)
      .filter(i => i !== null)

    return {
      ...q,
      options: shuffled.map(item => item.opt),
      correct_answers: newCorrectAnswers
    }
  })
}

function initQuiz(questions, timeLimit) {
  state.questions    = shuffleQuestions(questions)
  state.answers      = {}
  state.currentIndex = 0
  state.selectedOptions = []

  buildSidebar()
  renderQuestion(0)
  startTimer(timeLimit)
  switchPage("quiz")
}

// ── Sidebar ───────────────────────────────────────────

function buildSidebar() {
  const nav = document.getElementById("question-nav")
  nav.innerHTML = ""
  state.questions.forEach((_, i) => {
    const btn = document.createElement("button")
    btn.className = "nav-btn" + (i === 0 ? " current" : "")
    btn.textContent = i + 1
    btn.onclick = () => navigateTo(i)
    nav.appendChild(btn)
  })
}

function updateSidebar() {
  document.querySelectorAll(".nav-btn").forEach((btn, i) => {
    btn.className = "nav-btn"
    if (i === state.currentIndex) btn.classList.add("current")
    else if (state.answers[i] !== undefined) btn.classList.add("answered")
  })
}

// ── Navigation ────────────────────────────────────────

function navigateTo(index) {
  state.currentIndex = index
  state.selectedOptions = []
  renderQuestion(index)
  updateSidebar()
}

// ── Render question ───────────────────────────────────

function renderQuestion(index) {
  const q   = state.questions[index]
  const area = document.getElementById("question-area")
  const existing = state.answers[index]

  let html = `<span class="q-type-badge">${q.type}</span>`
  if (q.is_multi) html += `<span class="q-multi-badge">Select all correct</span>`
  html += `<p class="q-text">${q.question}</p>`

  if (q.type === "open-ended") {
    const saved = existing ? existing.userAnswer : ""
    html += `<textarea class="open-answer" id="open-input" placeholder="Type your answer here…">${saved}</textarea>`
    if (existing) {
      html += explanationHTML(q, existing)
      html += selfGradeHTML()
    } else {
      html += `<button class="btn-primary" onclick="submitOpenEnded()">Submit</button>`
    }
  } else {
    html += `<div class="options">`
    q.options.forEach((opt, i) => {
      let cls = "option"
      if (existing) {
        if (q.correct_answers.includes(i)) cls += " correct"
        else if (existing.selectedIndices.includes(i)) cls += " wrong"
      } else if (state.selectedOptions.includes(i)) {
        cls += " selected"
      }
      const letter = String.fromCharCode(65 + i)
      const disabled = existing ? "disabled" : ""
      html += `<button class="${cls}" ${disabled} onclick="toggleOption(${i})">
        <span class="opt-letter">${letter}</span>${opt}
      </button>`
    })
    html += `</div>`

    if (existing) {
      html += explanationHTML(q, existing)
      html += `<button class="btn-primary" onclick="nextQuestion()">Next →</button>`
    } else {
      html += `<button class="btn-primary" id="submit-btn"
        onclick="submitMC()" ${state.selectedOptions.length === 0 ? "disabled" : ""}>
        Submit
      </button>`
    }
  }

  area.innerHTML = html
}

function explanationHTML(q, record) {
  return `<div class="explanation">
    <p class="exp-label">Explanation</p>
    <p>${q.explanation}</p>
    ${record && !record.isCorrect && q.type !== "open-ended"
      ? `<p style="margin-top:8px"><span class="rl">Correct answer:</span> ${q.correct_answers.map(i => q.options[i]).join(", ")}</p>`
      : ""}
  </div>`
}

function selfGradeHTML() {
  return `<div class="self-grade">
    <p>Did you get it right?</p>
    <div class="grade-btns">
      <button class="btn-grade correct-btn" onclick="gradeOpen(true)">Yes ✓</button>
      <button class="btn-grade wrong-btn" onclick="gradeOpen(false)">No ✗</button>
    </div>
  </div>`
}

// ── Answer submission ─────────────────────────────────

function toggleOption(index) {
  const q = state.questions[state.currentIndex]
  if (q.is_multi) {
    // Checkboxes — toggle
    if (state.selectedOptions.includes(index)) {
      state.selectedOptions = state.selectedOptions.filter(i => i !== index)
    } else {
      state.selectedOptions.push(index)
    }
  } else {
    // Radio — single select
    state.selectedOptions = [index]
  }
  renderQuestion(state.currentIndex)
}

function submitMC() {
  const q = state.questions[state.currentIndex]
  const selected = [...state.selectedOptions].sort()
  const correct  = [...q.correct_answers].sort()
  const isCorrect = JSON.stringify(selected) === JSON.stringify(correct)

  const record = {
    question: q.question,
    type: q.type,
    userAnswer: selected.map(i => q.options[i]).join(", "),
    correctAnswer: correct.map(i => q.options[i]).join(", "),
    selectedIndices: selected,
    isCorrect,
    explanation: q.explanation,
  }

  state.answers[state.currentIndex] = record
  updateSidebar()
  renderQuestion(state.currentIndex)
}

function submitOpenEnded() {
  const text = document.getElementById("open-input").value.trim()
  if (!text) return
  const q = state.questions[state.currentIndex]
  state.answers[state.currentIndex] = {
    question: q.question,
    type: "open-ended",
    userAnswer: text,
    correctAnswer: q.sample_answer,
    selectedIndices: [],
    isCorrect: null,   // pending self-grade
    explanation: q.explanation,
  }
  renderQuestion(state.currentIndex)
}

function gradeOpen(isCorrect) {
  state.answers[state.currentIndex].isCorrect = isCorrect
  updateSidebar()
  renderQuestion(state.currentIndex)
}

function nextQuestion() {
  const next = state.currentIndex + 1
  if (next < state.questions.length) {
    navigateTo(next)
  }
  // Do nothing on last question — wait for End Exam button
}

function confirmFinish() {
  const total = state.questions.length
  const answered = Object.keys(state.answers).length
  const unanswered = total - answered

  if (unanswered > 0) {
    const go = confirm(`You have ${unanswered} unanswered question(s). End the exam anyway?`)
    if (!go) return
  } else {
    const go = confirm("Submit the exam?")
    if (!go) return
  }

  finishQuiz()
}

// ── Timer ─────────────────────────────────────────────

function startTimer(seconds) {
  stopTimer()
  const display = document.getElementById("timer-display")
  if (!seconds) { display.classList.add("hidden"); return }

  state.timeLeft = seconds
  display.classList.remove("hidden")
  updateTimerDisplay()

  state.timerInterval = setInterval(() => {
    state.timeLeft--
    updateTimerDisplay()
    if (state.timeLeft <= 60) display.classList.add("warning")
    if (state.timeLeft <= 0) {
      stopTimer()
      onTimeExpired()
    }
  }, 1000)
}

function stopTimer() {
  if (state.timerInterval) { clearInterval(state.timerInterval); state.timerInterval = null }
}

function updateTimerDisplay() {
  const m = Math.floor(state.timeLeft / 60).toString().padStart(2, "0")
  const s = (state.timeLeft % 60).toString().padStart(2, "0")
  document.getElementById("timer-display").textContent = `${m}:${s}`
}

function onTimeExpired() {
  // Auto-submit all unanswered questions as blank/wrong
  state.questions.forEach((q, i) => {
    if (state.answers[i] === undefined) {
      state.answers[i] = {
        question: q.question,
        type: q.type,
        userAnswer: "(no answer)",
        correctAnswer: q.correct_answers?.map(j => q.options[j]).join(", ") || q.sample_answer || "",
        selectedIndices: [],
        isCorrect: false,
        explanation: q.explanation,
      }
    }
  })
  showToast("Time's up!")
  setTimeout(finishQuiz, 1200)
}

// ── Finish & Results ──────────────────────────────────

async function finishQuiz() {
  stopTimer()
  const answers = Object.values(state.answers)
  const score   = answers.filter(a => a.isCorrect).length
  const total   = answers.length
  const percentage = Math.round((score / total) * 100)

  const result = {
    topic: document.getElementById("topic")?.value || "Document quiz",
    difficulty: state.difficulty,
    type: state.questionType,
    score, total, percentage,
    answers: answers.map(a => ({
      question: a.question,
      type: a.type,
      user_answer: a.userAnswer,
      correct_answer: a.correctAnswer,
      is_correct: a.isCorrect ?? false,
      explanation: a.explanation,
    }))
  }

  // Save to history
  const res = await api("/history/save", { method: "POST", body: JSON.stringify(result) })
  if (res.ok) state.lastResult = await res.json()

  showResults(result)
}

function showResults(result) {
  const grade =
    result.percentage >= 90 ? { label: "Excellent!",   color: "#22c55e" } :
    result.percentage >= 70 ? { label: "Good job!",    color: "#3b82f6" } :
    result.percentage >= 50 ? { label: "Keep going!",  color: "#f59e0b" } :
                              { label: "Need practice", color: "#ef4444" }

  document.getElementById("results-hero").innerHTML = `
    <p class="grade-label" style="color:${grade.color}">${grade.label}</p>
    <p class="score-big">${result.score}<span>/${result.total}</span></p>
    <p class="score-pct">${result.percentage}% correct</p>
    <p class="result-meta">${result.topic} · ${result.difficulty} · ${result.type}</p>
    <button class="btn-ghost" style="margin:12px auto 0;display:block" onclick="copyShareLink()">Share this quiz ↗</button>
  `

  const review = result.answers.map((a, i) => `
    <div class="review-item ${a.is_correct ? 'correct' : 'wrong'}">
      <div class="review-header">
        <span class="review-icon">${a.is_correct ? "✓" : "✗"}</span>
        <p class="review-question">${i + 1}. ${a.question}</p>
      </div>
      <div class="review-body">
        <p><span class="rl">Your answer:</span> ${a.user_answer}</p>
        ${!a.is_correct ? `<p><span class="rl">Correct:</span> ${a.correct_answer}</p>` : ""}
        <p>${a.explanation}</p>
      </div>
    </div>
  `).join("")

  document.getElementById("results-review").innerHTML = `<h2>Review</h2>${review}`
  switchPage("results")
}

// ── Retry wrong answers ───────────────────────────────

function retryWrongAnswers() {
  const total = state.questions.length

  // Collect wrong answers
  const wrongIndices = Object.entries(state.answers)
    .filter(([, a]) => !a.isCorrect)
    .map(([i]) => parseInt(i))

  // Collect unanswered questions
  const unansweredIndices = Array.from({ length: total }, (_, i) => i)
    .filter(i => state.answers[i] === undefined)

  // Merge and deduplicate, preserve original order
  const retryIndices = [...new Set([...wrongIndices, ...unansweredIndices])]
    .sort((a, b) => a - b)

  if (retryIndices.length === 0) {
    showToast("All questions answered correctly!")
    return
  }

  const retryQuestions = retryIndices.map(i => state.questions[i])
  showToast(`Retrying ${retryIndices.length} question(s)`)
  initQuiz(retryQuestions, null)
}

// ── Quit ──────────────────────────────────────────────

function confirmQuit() {
  if (confirm("Quit the quiz? Progress will be lost.")) {
    stopTimer()
    switchPage("setup")
  }
}

// ── History ───────────────────────────────────────────

async function loadHistory() {
  const res = await api("/history/")
  const records = res.ok ? await res.json() : []
  const list = document.getElementById("history-list")

  if (!records.length) {
    list.innerHTML = `<p class="empty-state">No quizzes yet. Go take one!</p>`
    return
  }

  list.innerHTML = records.map(r => `
    <div class="history-card">
      <div class="history-summary" onclick="toggleHistory('${r.id}')">
        <div class="hs-left">
          <p class="hs-topic">${r.topic}</p>
          <p class="hs-meta">${r.difficulty} · ${r.type} · ${r.date.slice(0,10)}</p>
        </div>
        <div class="hs-right">
          <span class="hs-score" style="color:${r.percentage>=70?'#22c55e':r.percentage>=50?'#f59e0b':'#ef4444'}">${r.percentage}%</span>
          <span class="hs-expand" id="exp-${r.id}">▼</span>
        </div>
      </div>
      <div id="detail-${r.id}" class="history-detail hidden">
        <p class="hd-score">${r.score}/${r.total} correct</p>
        ${r.answers.map(a => `
          <div class="hd-answer ${a.is_correct ? 'correct' : 'wrong'}">
            <span>${a.is_correct ? "✓" : "✗"}</span>
            <span>${a.question}</span>
          </div>
        `).join("")}
        <div class="export-btns">
          <a href="/history/${r.id}/export/pdf" download>Download PDF</a>
          <a href="/history/${r.id}/export/docx" download>Download DOCX</a>
        </div>
        <button class="btn-ghost danger" style="margin-top:10px" onclick="deleteRecord('${r.id}')">Delete</button>
      </div>
    </div>
  `).join("")
}

function toggleHistory(id) {
  const detail = document.getElementById(`detail-${id}`)
  const icon   = document.getElementById(`exp-${id}`)
  const open   = !detail.classList.contains("hidden")
  detail.classList.toggle("hidden", open)
  icon.textContent = open ? "▼" : "▲"
}

async function deleteRecord(id) {
  if (!confirm("Delete this record?")) return
  const res = await api(`/history/${id}`, { method: "DELETE" })
  if (res.ok) loadHistory()
}

async function clearAllHistory() {
  if (!confirm("Clear all history?")) return
  await api("/history/", { method: "DELETE" })
  loadHistory()
}

// ── Analytics ─────────────────────────────────────────

async function loadAnalytics() {
  const [sumRes, scoresRes, topicsRes, weakRes] = await Promise.all([
    api("/analytics/summary"),
    api("/analytics/scores"),
    api("/analytics/topics"),
    api("/analytics/weak-topics"),
  ])

  const summary = await sumRes.json()
  const scores  = await scoresRes.json()
  const topics  = await topicsRes.json()
  const weak    = await weakRes.json()

  // Summary cards
  document.getElementById("analytics-summary").innerHTML = `
    <div class="metric"><p class="mlabel">Total quizzes</p><p class="mval">${summary.total}</p></div>
    <div class="metric"><p class="mlabel">Avg score</p><p class="mval">${summary.avg_score}%</p></div>
    <div class="metric"><p class="mlabel">Best topic</p><p class="mval" style="font-size:14px">${summary.best_topic || "—"}</p></div>
    <div class="metric"><p class="mlabel">Worst topic</p><p class="mval" style="font-size:14px">${summary.worst_topic || "—"}</p></div>
  `

  // Destroy old charts before redrawing
  if (state.charts.scores) state.charts.scores.destroy()
  if (state.charts.topics) state.charts.topics.destroy()

  // Line chart — scores over time
  state.charts.scores = new Chart(document.getElementById("chart-scores"), {
    type: "line",
    data: {
      labels: scores.map(s => s.date),
      datasets: [{ label: "Score %", data: scores.map(s => s.percentage),
        borderColor: "#2563eb", backgroundColor: "rgba(37,99,235,0.08)",
        tension: 0.3, fill: true, pointRadius: 4 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 100, ticks: { callback: v => v + "%" } } }
    }
  })

  // Bar chart — topics
  state.charts.topics = new Chart(document.getElementById("chart-topics"), {
    type: "bar",
    data: {
      labels: topics.map(t => t.topic),
      datasets: [{ label: "Avg %", data: topics.map(t => t.avg_score),
        backgroundColor: "#2563eb", borderRadius: 6 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 100, ticks: { callback: v => v + "%" } },
        x: { ticks: { autoSkip: false, maxRotation: 30 } } }
    }
  })

  // Weak topics
  const weakSection = document.getElementById("weak-topics-section")
  if (weak.length) {
    weakSection.innerHTML = `
      <p class="chart-label">Topics needing improvement</p>
      <div class="weak-topics">
        ${weak.map(t => `<span class="weak-tag">${t.topic} (${t.avg_score}%)</span>`).join("")}
      </div>`
  } else {
    weakSection.innerHTML = `<p style="font-size:13px;color:var(--muted)">No weak topics — great work!</p>`
  }
}

// ── Share ─────────────────────────────────────────────

async function copyShareLink() {
  const topic = document.getElementById("topic")?.value || ""
  const config = {
    topic,
    difficulty: state.difficulty,
    count: parseInt(document.getElementById("count")?.value || 5),
    type: state.questionType,
    time_limit: getTimeLimit(),
  }
  const token = btoa(JSON.stringify(config))
  const url   = `${location.origin}?quiz=${token}`
  await navigator.clipboard.writeText(url)
  showToast("Share link copied!")
}

function checkShareLink() {
  const params = new URLSearchParams(location.search)
  const token  = params.get("quiz")
  if (!token) return
  try {
    const config = JSON.parse(atob(token))
    if (config.topic) document.getElementById("topic").value = config.topic
    if (config.difficulty) state.difficulty = config.difficulty
    if (config.type) state.questionType = config.type
    showToast(`Loaded shared quiz: "${config.topic}"`)
  } catch {}
}

// ── Boot ──────────────────────────────────────────────

if (state.token) {
  checkShareLink()
  switchPage("setup")
} else {
  switchPage("auth")
}