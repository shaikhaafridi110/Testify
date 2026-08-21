/* ============================================================
   TESTIFY — Exam UI (timer, navigation, palette, submit)
   ============================================================ */

const EXAM_STATE = {
  questions: [],
  current: 0,
  answers: {},
  marked: {},
  timeLeft: 0,
  timerId: null,
  submitted: false,
};

/* ---------- Demo question bank ---------- */
function demoQuestions() {
  return [
    { id: 1, text: 'Which language is used to structure a webpage?', options: ['CSS', 'HTML', 'Python', 'SQL'], correct: 1, marks: 2 },
    { id: 2, text: 'Which data structure uses LIFO order?', options: ['Queue', 'Stack', 'Array', 'Linked List'], correct: 1, marks: 2 },
    { id: 3, text: 'What does SQL stand for?', options: ['Structured Query Language', 'Simple Query Logic', 'Standard Question Language', 'System Query Layer'], correct: 0, marks: 2 },
    { id: 4, text: 'Which protocol is used for secure web browsing?', options: ['FTP', 'HTTP', 'HTTPS', 'SMTP'], correct: 2, marks: 2 },
    { id: 5, text: 'A binary search tree requires the left subtree to contain values…', options: ['Greater than root', 'Less than root', 'Equal to root', 'Random'], correct: 1, marks: 3 },
    { id: 6, text: 'Which sorting algorithm has O(n log n) average complexity?', options: ['Bubble Sort', 'Selection Sort', 'Merge Sort', 'Insertion Sort'], correct: 2, marks: 2 },
    { id: 7, text: 'In DBMS, a primary key…', options: ['Can be NULL', 'Must be unique', 'Allows duplicates', 'Is optional'], correct: 1, marks: 2 },
    { id: 8, text: 'Which is NOT a JavaScript framework?', options: ['React', 'Vue', 'Django', 'Angular'], correct: 2, marks: 2 },
    { id: 9, text: 'Time complexity of accessing an array element by index is…', options: ['O(n)', 'O(log n)', 'O(1)', 'O(n²)'], correct: 2, marks: 1 },
    { id: 10, text: 'Which layer of OSI handles routing?', options: ['Data Link', 'Network', 'Transport', 'Session'], correct: 1, marks: 2 },
  ];
}

/* ---------- Timer ---------- */
function startTimer(seconds) {
  EXAM_STATE.timeLeft = seconds;
  const el = document.getElementById('exam-timer');
  if (!el) return;
  function tick() {
    if (EXAM_STATE.timeLeft <= 0) {
      clearInterval(EXAM_STATE.timerId);
      el.textContent = '00:00';
      autoSubmit();
      return;
    }
    EXAM_STATE.timeLeft--;
    const m = Math.floor(EXAM_STATE.timeLeft / 60);
    const s = EXAM_STATE.timeLeft % 60;
    el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    el.classList.remove('warning', 'danger');
    if (EXAM_STATE.timeLeft <= 60) el.classList.add('danger');
    else if (EXAM_STATE.timeLeft <= 180) el.classList.add('warning');
  }
  tick();
  EXAM_STATE.timerId = setInterval(tick, 1000);
}

/* ---------- Render question ---------- */
function renderQuestion() {
  const q = EXAM_STATE.questions[EXAM_STATE.current];
  if (!q) return;
  const main = document.getElementById('exam-main');
  if (!main) return;
  const answered = Object.keys(EXAM_STATE.answers).length;
  const total = EXAM_STATE.questions.length;
  const progress = Math.round((answered / total) * 100);

  main.innerHTML = `
    <div class="question-block fade-in-up">
      <div class="q-nav-top">
        <div class="q-counter"><span class="now">Question ${EXAM_STATE.current + 1}</span> of ${total}</div>
        <span class="badge badge-primary">${q.marks} mark${q.marks > 1 ? 's' : ''}</span>
      </div>
      <div class="progress mb-5"><div class="progress-bar" style="width:${progress}%"></div></div>
      <div class="q-text">${q.text}</div>
      <div class="options" id="options-list"></div>
      <div class="exam-actions">
        <button class="btn btn-secondary" id="prev-btn" ${EXAM_STATE.current === 0 ? 'disabled' : ''}>Previous</button>
        <div class="flex gap-3">
          <button class="btn btn-outline" id="mark-btn">${EXAM_STATE.marked[q.id] ? 'Unmark' : 'Mark for review'}</button>
          ${EXAM_STATE.current === total - 1
            ? '<button class="btn btn-accent" id="submit-btn">Submit Exam</button>'
            : '<button class="btn btn-primary" id="next-btn">Next</button>'}
        </div>
      </div>
    </div>`;

  const opts = main.querySelector('#options-list');
  q.options.forEach((opt, i) => {
    const div = document.createElement('div');
    div.className = 'option' + (EXAM_STATE.answers[q.id] === i ? ' selected' : '');
    div.innerHTML = `<div class="opt-letter">${String.fromCharCode(65 + i)}</div><div class="opt-text">${opt}</div>`;
    div.addEventListener('click', () => {
      EXAM_STATE.answers[q.id] = i;
      renderQuestion();
      renderPalette();
    });
    opts.appendChild(div);
  });

  main.querySelector('#prev-btn')?.addEventListener('click', () => {
    if (EXAM_STATE.current > 0) { EXAM_STATE.current--; renderQuestion(); renderPalette(); }
  });
  main.querySelector('#next-btn')?.addEventListener('click', () => {
    if (EXAM_STATE.current < EXAM_STATE.questions.length - 1) { EXAM_STATE.current++; renderQuestion(); renderPalette(); }
  });
  main.querySelector('#mark-btn')?.addEventListener('click', () => {
    if (EXAM_STATE.marked[q.id]) delete EXAM_STATE.marked[q.id];
    else EXAM_STATE.marked[q.id] = true;
    renderQuestion();
    renderPalette();
  });
  main.querySelector('#submit-btn')?.addEventListener('click', confirmSubmit);
}

/* ---------- Question palette ---------- */
function renderPalette() {
  const grid = document.getElementById('q-palette');
  if (!grid) return;
  grid.innerHTML = '';
  EXAM_STATE.questions.forEach((q, i) => {
    const cell = document.createElement('button');
    cell.className = 'q-cell';
    if (EXAM_STATE.answers[q.id] !== undefined) cell.classList.add('answered');
    if (EXAM_STATE.marked[q.id]) cell.classList.add('marked');
    if (i === EXAM_STATE.current) cell.classList.add('current');
    cell.textContent = i + 1;
    cell.addEventListener('click', () => { EXAM_STATE.current = i; renderQuestion(); renderPalette(); });
    grid.appendChild(cell);
  });
  const summary = document.getElementById('palette-summary');
  if (summary) {
    const answered = Object.keys(EXAM_STATE.answers).length;
    const marked = Object.keys(EXAM_STATE.marked).length;
    summary.textContent = `${answered} answered · ${marked} marked · ${EXAM_STATE.questions.length - answered} remaining`;
  }
}

/* ---------- Submit ---------- */
function confirmSubmit() {
  const answered = Object.keys(EXAM_STATE.answers).length;
  const total = EXAM_STATE.questions.length;
  confirmAction(
    `You have answered ${answered} of ${total} questions. ${answered < total ? 'Unanswered questions will be marked as skipped.' : ''} Submit your exam now?`,
    () => submitExam(),
    { title: 'Submit exam?', confirmText: 'Submit Now' }
  );
}

function submitExam() {
  if (EXAM_STATE.submitted) return;
  EXAM_STATE.submitted = true;
  clearInterval(EXAM_STATE.timerId);
  const btn = document.querySelector('#submit-btn');
  if (btn) { btn.classList.add('is-loading'); btn.textContent = 'Submitting…'; }
  setTimeout(() => {
    window.location.href = 'submission.html';
  }, 900);
}

function autoSubmit() {
  if (EXAM_STATE.submitted) return;
  toast('Time is up. Your exam is being submitted automatically.', { title: 'Time over', type: 'error' });
  submitExam();
}

/* ---------- Boot exam ---------- */
function initExam() {
  const shell = document.getElementById('exam-shell');
  if (!shell) return;
  EXAM_STATE.questions = demoQuestions();
  EXAM_STATE.current = 0;
  renderQuestion();
  renderPalette();
  startTimer(30 * 60);
}

document.addEventListener('DOMContentLoaded', initExam);
