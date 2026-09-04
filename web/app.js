/**
 * ==============================================================================
 * DEMON MUSIC TERMINAL — FRONTEND INTERACTION ENGINE
 * ==============================================================================
 */

// Initial Seed Data matching Demon Music Terminal screenshot
const DEFAULT_TRACKS = [
  { id: 1, title: "NEFFEX - Grateful", artist: "NEFFEX", duration: "3:28", durSec: 208, thumb: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&auto=format&fit=crop&q=80", genre: "Trap / Hip Hop", isPlaying: true },
  { id: 2, title: "Courtesy Call", artist: "Thousand Foot Krutch", duration: "3:57", durSec: 237, thumb: "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=100&auto=format&fit=crop&q=80", genre: "Rock" },
  { id: 3, title: "Fairy Tail Main Theme", artist: "Yasuharu Takanashi", duration: "2:52", durSec: 172, thumb: "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=100&auto=format&fit=crop&q=80", genre: "Anime OST" },
  { id: 4, title: "Bones", artist: "Imagine Dragons", duration: "2:45", durSec: 165, thumb: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=100&auto=format&fit=crop&q=80", genre: "Alternative" },
  { id: 5, title: "Legend Never Die", artist: "Against The Current", duration: "3:55", durSec: 235, thumb: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=100&auto=format&fit=crop&q=80", genre: "Gaming / Pop" },
  { id: 6, title: "From The Start", artist: "Good Kid", duration: "2:53", durSec: 173, thumb: "https://images.unsplash.com/photo-1498038432885-c6f3f1b912ee?w=100&auto=format&fit=crop&q=80", genre: "Indie Rock" },
  { id: 7, title: "On & On", artist: "Cartoon, Daniel Levi", duration: "3:27", durSec: 207, thumb: "https://images.unsplash.com/photo-1487180144351-b8472da7d491?w=100&auto=format&fit=crop&q=80", genre: "Electronic" },
];

let state = {
  currentTrack: DEFAULT_TRACKS[0],
  queue: [...DEFAULT_TRACKS.slice(0)],
  isPlaying: true,
  positionSec: 84, // 1:24
  durationSec: 208, // 3:28
  volume: 80,
  loop: true,
  djMode: true,
  theme: "dark",
  connectedGuild: "DEMON'S REALM",
  activeTab: "top"
};

// DOM ELEMENTS
const heroArt = document.getElementById("hero-art");
const heroTitle = document.getElementById("hero-title");
const heroArtist = document.getElementById("hero-artist");
const heroGenre = document.getElementById("hero-genre");
const currentTimeEl = document.getElementById("current-time");
const totalTimeEl = document.getElementById("total-time");
const scrubFill = document.getElementById("scrub-fill");
const heroPlayBtn = document.getElementById("hero-play");
const dockPlayBtn = document.getElementById("dock-play");
const heroVolume = document.getElementById("hero-volume");
const rightVolumeSlider = document.getElementById("right-volume-slider");
const volumeValDisplay = document.getElementById("volume-val-display");
const dockTitle = document.getElementById("dock-title");
const dockArtist = document.getElementById("dock-artist");
const dockThumb = document.getElementById("dock-thumb");
const dockTimeStr = document.getElementById("dock-time-str");
const rightQueueList = document.getElementById("right-queue-list");
const tracksTableBody = document.getElementById("tracks-table-body");
const globalSearch = document.getElementById("global-search");
const themeBtn = document.getElementById("theme-btn");
const themeIcon = document.getElementById("theme-icon");

// FORMAT SECONDS -> MM:SS
function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// RENDER QUEUE
function renderQueue() {
  if (!rightQueueList) return;
  rightQueueList.innerHTML = "";

  state.queue.forEach((item, index) => {
    const isCurr = state.currentTrack && state.currentTrack.title === item.title;
    const el = document.createElement("div");
    el.className = "queue-item";
    el.innerHTML = `
      <img src="${item.thumb}" class="queue-item-thumb" alt="Thumb">
      <div class="queue-item-info">
        <div class="queue-item-title">${item.title}</div>
        <div class="queue-item-artist">${item.artist}</div>
      </div>
      <div class="queue-item-right">
        ${isCurr ? `
          <div class="eq-bars" style="height: 12px;">
            <div class="eq-bar"></div>
            <div class="eq-bar"></div>
            <div class="eq-bar"></div>
          </div>
        ` : ''}
        <span style="font-size: 11px; color: var(--text-muted);">${item.duration}</span>
        <span class="drag-handle">⋮⋮</span>
      </div>
    `;
    el.addEventListener("click", () => playTrack(item));
    rightQueueList.appendChild(el);
  });
}

// RENDER TRACK TABLE
function renderTrackTable() {
  if (!tracksTableBody) return;
  tracksTableBody.innerHTML = "";

  state.queue.forEach((item) => {
    const isCurr = state.currentTrack && state.currentTrack.title === item.title;
    const row = document.createElement("div");
    row.className = `track-row ${isCurr ? 'playing' : ''}`;
    row.innerHTML = `
      <img src="${item.thumb}" class="track-thumb" alt="Thumb">
      <div class="track-meta">
        <div class="track-name">${item.title}</div>
        <div class="track-sub">${item.genre || 'Electronic'}</div>
      </div>
      <div class="track-artist">${item.artist}</div>
      <div style="display: flex; align-items: center; gap: 8px;">
        ${isCurr ? `
          <div class="eq-bars" style="height: 12px;">
            <div class="eq-bar"></div>
            <div class="eq-bar"></div>
            <div class="eq-bar"></div>
          </div>
        ` : ''}
        <span class="track-dur">${item.duration}</span>
      </div>
      <button class="add-queue-btn" title="Add to Queue">+</button>
    `;

    row.querySelector(".add-queue-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      queueSong(item.title);
    });

    row.addEventListener("click", () => playTrack(item));
    tracksTableBody.appendChild(row);
  });
}

// UPDATE UI DISPLAY
function updatePlayerUI() {
  if (!state.currentTrack) return;

  const t = state.currentTrack;
  if (heroTitle) heroTitle.innerText = t.title;
  if (heroArtist) heroArtist.innerText = t.artist;
  if (heroGenre) heroGenre.innerText = t.genre || "Trap / Hip Hop";
  if (heroArt) heroArt.src = t.thumb;

  if (dockTitle) dockTitle.innerText = t.title;
  if (dockArtist) dockArtist.innerText = t.artist;
  if (dockThumb) dockThumb.src = t.thumb;

  const curStr = formatTime(state.positionSec);
  const totStr = formatTime(state.durationSec);

  if (currentTimeEl) currentTimeEl.innerText = curStr;
  if (totalTimeEl) totalTimeEl.innerText = totStr;
  if (dockTimeStr) dockTimeStr.innerText = `${curStr} / ${totStr}`;

  const pct = Math.min((state.positionSec / (state.durationSec || 1)) * 100, 100);
  if (scrubFill) scrubFill.style.width = `${pct}%`;

  const playIcon = state.isPlaying ? "⏸️" : "▶️";
  if (heroPlayBtn) heroPlayBtn.innerText = playIcon;
  if (dockPlayBtn) dockPlayBtn.innerText = playIcon;

  renderQueue();
  renderTrackTable();
}

// PLAY SPECIFIC TRACK
function playTrack(track) {
  state.currentTrack = track;
  state.durationSec = track.durSec || 210;
  state.positionSec = 0;
  state.isPlaying = true;
  updatePlayerUI();
  fetch('/api/play', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: `${track.title} ${track.artist}` })
  }).catch(() => {});
}

// QUEUE A SONG
function queueSong(query) {
  fetch('/api/play', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: query })
  }).then(() => {
    alert(`Added "${query}" to the Discord queue!`);
  }).catch(() => {
    alert(`Added "${query}" to queue.`);
  });
}

// TOGGLE PLAY/PAUSE
function togglePlayPause() {
  state.isPlaying = !state.isPlaying;
  updatePlayerUI();
  fetch('/api/pause', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paused: !state.isPlaying })
  }).catch(() => {});
}

// SKIP TRACK
function skipTrack() {
  if (state.queue.length > 1) {
    state.queue.shift();
    playTrack(state.queue[0]);
  }
  fetch('/api/skip', { method: 'POST' }).catch(() => {});
}

// PREVIOUS TRACK
function prevTrack() {
  state.positionSec = 0;
  updatePlayerUI();
  fetch('/api/previous', { method: 'POST' }).catch(() => {});
}

// VOLUME HANDLER
function setVolume(val) {
  state.volume = parseInt(val, 10);
  if (heroVolume) heroVolume.value = state.volume;
  if (rightVolumeSlider) rightVolumeSlider.value = state.volume;
  if (volumeValDisplay) volumeValDisplay.innerText = `${state.volume}%`;
  fetch('/api/volume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ volume: state.volume })
  }).catch(() => {});
}

// WEBSOCKET FOR LIVE BOT SYNCHRONIZATION
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  let ws = null;
  try {
    ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "PLAYER_UPDATE") {
          if (data.current) {
            state.currentTrack = {
              title: data.current.title,
              artist: data.current.author || "Unknown",
              duration: formatTime(Math.floor(data.current.duration_ms / 1000)),
              durSec: Math.floor(data.current.duration_ms / 1000),
              thumb: data.current.artwork || state.currentTrack.thumb,
              genre: "Live Stream"
            };
            state.positionSec = Math.floor(data.position_ms / 1000);
            state.durationSec = Math.floor(data.current.duration_ms / 1000);
            state.isPlaying = data.playing;
            state.volume = data.volume;
            updatePlayerUI();
          }
          if (data.queue) {
            state.queue = data.queue.map((q, idx) => ({
              id: idx,
              title: q.title,
              artist: q.author,
              duration: formatTime(Math.floor(q.duration_ms / 1000)),
              thumb: q.artwork || DEFAULT_TRACKS[1].thumb
            }));
            renderQueue();
          }
        }
      } catch (err) {
        console.error("WS Parse error", err);
      }
    };
    ws.onclose = () => {
      setTimeout(initWebSocket, 3000);
    };
  } catch (e) {
    console.warn("WebSocket not available yet.");
  }
}

// SETUP EVENT LISTENERS
function setupListeners() {
  if (heroPlayBtn) heroPlayBtn.addEventListener("click", togglePlayPause);
  if (dockPlayBtn) dockPlayBtn.addEventListener("click", togglePlayPause);

  const heroNext = document.getElementById("hero-next");
  const dockNext = document.getElementById("dock-next");
  if (heroNext) heroNext.addEventListener("click", skipTrack);
  if (dockNext) dockNext.addEventListener("click", skipTrack);

  const heroPrev = document.getElementById("hero-prev");
  const dockPrev = document.getElementById("dock-prev");
  if (heroPrev) heroPrev.addEventListener("click", prevTrack);
  if (dockPrev) dockPrev.addEventListener("click", prevTrack);

  if (heroVolume) heroVolume.addEventListener("input", (e) => setVolume(e.target.value));
  if (rightVolumeSlider) rightVolumeSlider.addEventListener("input", (e) => setVolume(e.target.value));

  const scrubBar = document.getElementById("scrub-bar");
  if (scrubBar) {
    scrubBar.addEventListener("click", (e) => {
      const rect = scrubBar.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const pct = clickX / rect.width;
      state.positionSec = Math.floor(pct * state.durationSec);
      updatePlayerUI();
      fetch('/api/seek', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position_ms: state.positionSec * 1000 })
      }).catch(() => {});
    });
  }

  // Quick Action: Clear Queue
  const btnClearQueue = document.getElementById("btn-clear-queue");
  const rightClearQueue = document.getElementById("right-clear-queue");
  const clearHandler = () => {
    state.queue = state.currentTrack ? [state.currentTrack] : [];
    renderQueue();
    fetch('/api/clearqueue', { method: 'POST' }).catch(() => {});
  };
  if (btnClearQueue) btnClearQueue.addEventListener("click", clearHandler);
  if (rightClearQueue) rightClearQueue.addEventListener("click", clearHandler);

  // Quick Action: Shuffle
  const btnShuffle = document.getElementById("btn-shuffle-queue");
  const heroShuffle = document.getElementById("hero-shuffle");
  const dockShuffle = document.getElementById("dock-shuffle");
  const shuffleHandler = () => {
    const first = state.queue[0];
    const rest = state.queue.slice(1);
    for (let i = rest.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [rest[i], rest[j]] = [rest[j], rest[i]];
    }
    state.queue = [first, ...rest];
    renderQueue();
    fetch('/api/shuffle', { method: 'POST' }).catch(() => {});
  };
  if (btnShuffle) btnShuffle.addEventListener("click", shuffleHandler);
  if (heroShuffle) heroShuffle.addEventListener("click", shuffleHandler);
  if (dockShuffle) dockShuffle.addEventListener("click", shuffleHandler);

  // Quick Action: Disconnect
  const btnDisconnect = document.getElementById("btn-disconnect");
  if (btnDisconnect) {
    btnDisconnect.addEventListener("click", () => {
      if (confirm("Disconnect Demon Music from voice channel?")) {
        fetch('/api/leave', { method: 'POST' }).catch(() => {});
        alert("Disconnect signal sent.");
      }
    });
  }

  // Tab Switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeTab = btn.getAttribute("data-tab");
      renderTrackTable();
    });
  });

  // Global Search Box
  if (globalSearch) {
    globalSearch.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const query = globalSearch.value.trim();
        if (query) {
          queueSong(query);
          globalSearch.value = "";
        }
      }
    });
  }

  // Theme Toggle
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const html = document.documentElement;
      if (html.getAttribute("data-theme") === "dark") {
        html.setAttribute("data-theme", "light");
        themeIcon.innerText = "☀️";
      } else {
        html.setAttribute("data-theme", "dark");
        themeIcon.innerText = "🌙";
      }
    });
  }
}

// SOUNDWAVE VISUALIZER CANVAS ANIMATION
function initSoundwave() {
  const canvas = document.getElementById("soundwave");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function resize() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = 28;
  }
  window.addEventListener("resize", resize);
  resize();

  let phase = 0;
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const barWidth = 4;
    const gap = 3;
    const totalBars = Math.floor(canvas.width / (barWidth + gap));

    phase += 0.05;

    for (let i = 0; i < totalBars; i++) {
      const x = i * (barWidth + gap);
      const amp = state.isPlaying
        ? Math.abs(Math.sin(phase + i * 0.15)) * 0.8 + 0.2
        : 0.15;
      const barHeight = amp * (canvas.height - 4);
      const y = (canvas.height - barHeight) / 2;

      const grad = ctx.createLinearGradient(0, y, 0, y + barHeight);
      grad.addColorStop(0, "#a855f7");
      grad.addColorStop(1, "#ec4899");

      ctx.fillStyle = grad;
      ctx.fillRect(x, y, barWidth, barHeight);
    }

    requestAnimationFrame(draw);
  }
  draw();
}

// SIMULATE TIMELINE PROGRESSION
setInterval(() => {
  if (state.isPlaying && state.positionSec < state.durationSec) {
    state.positionSec++;
    updatePlayerUI();
  } else if (state.isPlaying && state.positionSec >= state.durationSec) {
    skipTrack();
  }
}, 1000);

// INITIALIZE ON LOAD
document.addEventListener("DOMContentLoaded", () => {
  setupListeners();
  updatePlayerUI();
  initSoundwave();
  initWebSocket();
});
