const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_URL = isLocal ? 'http://localhost:8000' : 'https://aadiljm-drpet.hf.space';
let chartInstance = null;
let lastAnalysisData = null;
let streamInterval = null;
let streamSocket = null;
let currentSessionId = null;
let synthesisReady = false;
let live_sessions_markers_count = 0;

// Persistent Session ID (Client-side node)
let nodeId = localStorage.getItem('drpet_node_id');
if (!nodeId) {
    nodeId = 'node_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('drpet_node_id', nodeId);
}

// UI Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadProgress = document.getElementById('upload-progress');
const analysisResults = document.getElementById('analysis-results');
const insightIdle = document.getElementById('insight-idle');
const apiStatusPill = document.getElementById('api-status-pill');
const apiStatusText = document.getElementById('api-status-text');

// Initialize API Health Check
checkApiHealth();
setInterval(checkApiHealth, 10000);

async function checkApiHealth() {
    try {
        const res = await fetch(`${API_URL}/api/health`);
        const data = await res.json();
        if (data.status === 'healthy') {
            apiStatusPill.classList.add('online');
            apiStatusText.innerText = 'System Online';
        }
    } catch (e) {
        apiStatusPill.classList.remove('online');
        apiStatusText.innerText = 'Offline';
    }
}

// Drag and Drop Logic
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-active');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-active');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-active');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleUpload(files[0]);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleUpload(e.target.files[0]);
});

// Toast Utility
function showToast(msg, icon = '✅') {
    const toast = document.getElementById('toast');
    document.getElementById('toast-msg').innerText = msg;
    document.getElementById('toast-icon').innerText = icon;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Main Upload Handler
async function handleUpload(file) {
    if (!file.type.startsWith('video/')) {
        showToast('Please upload a video file', '⚠️');
        return;
    }

    // Prepare UI
    document.querySelector('.upload-dropzone').classList.add('hidden');
    uploadProgress.classList.remove('hidden');
    updateStep('step-upload');

    const formData = new FormData();
    formData.append('file', file);

    try {
        showToast('Starting analysis...', '🚀');
        const response = await fetch(`${API_URL}/analyze/video`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.file_id) {
            pollResults(data.file_id);
        }
    } catch (error) {
        console.error('Upload failed:', error);
        showToast('Server connection failed', '❌');
        // Fallback for demo if needed
        // simulateResults(); 
    }
}

function updateStep(stepId) {
    const steps = ['step-upload', 'step-vision', 'step-acoustic', 'step-report'];
    const currentIdx = steps.indexOf(stepId);

    steps.forEach((id, idx) => {
        const el = document.getElementById(id);
        if (idx <= currentIdx) el.classList.add('step-active');
        else el.classList.remove('step-active');
    });

    const progressPct = ((currentIdx + 1) / steps.length) * 100;
    document.getElementById('progress-bar').style.width = `${progressPct}%`;
    document.getElementById('progress-pct').innerText = `${Math.round(progressPct)}%`;
}

async function pollResults(fileId) {
    let phase = 0;
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/results/${fileId}`);
            const data = await response.json();

            // Fake phase progression for better UX during wait
            phase++;
            if (phase === 3) updateStep('step-vision');
            if (phase === 6) updateStep('step-acoustic');

            if (data.status === "completed" || data.metrics) {
                clearInterval(interval);
                showToast("Analysis complete", "✨");
                updateStep('step-report');
                setTimeout(() => displayResults(data), 500);
            } else if (data.status === "error") {
                clearInterval(interval);
                showToast("Analysis failed", "❌");
                resetUI();
            }
        } catch (error) {
            console.warn('Polling error...');
        }
    }, 2000);
}

function displayResults(data) {
    lastAnalysisData = data;

    // Switch Panels
    insightIdle.classList.add('hidden');
    analysisResults.classList.remove('hidden');
    uploadProgress.classList.add('hidden');
    document.getElementById('metrics-card').classList.add('active');

    const placeholder = document.getElementById('vision-placeholder');
    if (placeholder) placeholder.classList.add('hidden');

    // Update Banner & Ring (Circumference is ~628 for r=100)
    const score = data.metrics.happiness_score;
    const sentiment = data.ai_insights ? data.ai_insights.emotional_state : data.metrics.acoustic_sentiment;

    document.getElementById('emotion-value').innerText = sentiment;
    if (document.getElementById('emotion-value-hud')) {
        document.getElementById('emotion-value-hud').innerText = sentiment;
        document.getElementById('hud-stats').style.opacity = '1';
        document.getElementById('hud-stats').style.transform = 'translateY(0)';
    }

    document.getElementById('ring-pct').innerText = `${Math.round(score)}%`;
    const offset = (score / 100) * 628;
    document.getElementById('ring-fill').style.strokeDasharray = `${offset}, 628`;

    // Show Analysis Container
    if (document.getElementById('analysis-ready-state')) {
        document.getElementById('analysis-ready-state').classList.remove('hidden');
    }

    // Update Icons based on sentiment
    const iconMap = {
        'Happy': '😊', 'Playful': '🎾', 'Excited': '✨',
        'Anxious': '😟', 'Fearful': '🌑', 'Aggressive': '⚠️',
        'Stable': '😐', 'Balanced': '⚖️', 'Relaxed': '🍃'
    };
    const emotionIcon = Object.entries(iconMap).find(([k]) => sentiment.includes(k))?.[1] || '🐕';
    document.getElementById('emotion-icon').innerText = emotionIcon;

    // Sidebar Metrics
    const happinessEl = document.getElementById('happiness-score-text');
    happinessEl.innerText = `${score.toFixed(1)}%`;
    happinessEl.style.color = score > 70 ? '#10b981' : (score > 40 ? '#f59e0b' : '#ef4444');

    document.getElementById('acoustic-sentiment').innerText = data.metrics.acoustic_sentiment;

    const anomalyEl = document.getElementById('anomaly-status');
    const isAnomaly = data.temporal_intelligence.is_anomaly;
    anomalyEl.innerText = isAnomaly ? "Pattern Shift" : "Stable Pattern";
    anomalyEl.style.color = isAnomaly ? '#ef4444' : '#10b981';

    // Summary Text
    document.getElementById('analysis-summary').innerText = data.analysis;

    // Key Point List
    const keyPointsList = document.getElementById('keyPointsList');
    keyPointsList.innerHTML = (data.ai_insights?.key_points || ["Visual behavior tracking active", "Acoustic signature processed"])
        .map(p => `<li>${p}</li>`).join('');

    // Breed Card Logic
    const ragBox = document.getElementById('rag-box');
    const card = data.breed_card;
    if (card && card.breed) {
        const traits = (card.temperament_traits || []).map(t => `<span class="breed-trait-pill">${t}</span>`).join('');
        ragBox.innerHTML = `
            <div class="breed-card">
                <div class="breed-card-header">
                    <span class="breed-name">${card.breed}</span>
                    <span class="card-badge card-badge-green">${card.source_quality || 'AI verified'}</span>
                </div>
                <div class="breed-meta">
                    <span>📍 ${card.origin || 'Global'}</span>
                    <span>📏 ${card.size || 'Mixed'}</span>
                    <span>⚡ ${card.energy_level || 'Moderate'}</span>
                </div>
                <p class="breed-known-for">${card.known_for || 'Affectionate and intelligent companion.'}</p>
                <div class="breed-section-label">Temperament</div>
                <div class="breed-traits">${traits}</div>
                <div class="breed-section-label">Expert Advice</div>
                <p class="breed-advice">💡 ${card.owner_advice || 'Maintain consistent routine and mental stimulation.'}</p>
            </div>
        `;
    }

    // Recommendations
    const recList = document.getElementById('recommendations');
    recList.innerHTML = data.recommendations.map(r => `<li>${r}</li>`).join('');

    // Download Button
    const downloadBtn = document.getElementById('downloadAuditBtn');
    if (data.clinical_audit_url) {
        downloadBtn.onclick = () => window.open(`${API_URL}${data.clinical_audit_url}`, '_blank');
        downloadBtn.parentElement.classList.remove('hidden');
    }

    // Charts
    initBehaviorChart();

    showToast('Analysis complete', '✨');
}

function initBehaviorChart() {
    const ctx = document.getElementById('behaviorChart').getContext('2d');
    if (chartInstance) chartInstance.destroy();

    const labels = Array.from({ length: 20 }, (_, i) => `${i}s`);
    const mockData = labels.map(() => Math.sin(Date.now() / 1000) * 10 + 20 + Math.random() * 5);

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: mockData,
                borderColor: '#3525cd',
                backgroundColor: (context) => {
                    const chart = context.chart;
                    const { ctx, chartArea } = chart;
                    if (!chartArea) return null;
                    const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                    gradient.addColorStop(0, 'rgba(53, 37, 205, 0.1)');
                    gradient.addColorStop(1, 'rgba(53, 37, 205, 0)');
                    return gradient;
                },
                fill: true,
                tension: 0.5,
                borderWidth: 2,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { display: false, min: 0, max: 50 },
                x: { display: false }
            }
        }
    });
}



// Live Stream Logic
async function startLiveStream() {
    const video = document.getElementById('live-video');
    const canvas = document.getElementById('live-canvas');
    const ctx = canvas.getContext('2d');
    const liveIndicator = document.getElementById('live-indicator');
    const placeholder = document.getElementById('vision-placeholder');

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        video.classList.remove('hidden');
        placeholder.classList.add('hidden');
        liveIndicator.classList.remove('hidden');

        document.getElementById('live-stream-btn').classList.add('hidden');
        document.getElementById('stop-stream-btn').classList.remove('hidden');

        console.log(`Attempting Secure WebSocket for ${nodeId}`);
        const wsProtocol = isLocal ? 'ws' : 'wss';
        const wsHost = isLocal ? `${window.location.hostname}:8000` : 'aadiljm-drpet.hf.space';
        streamSocket = new WebSocket(`${wsProtocol}://${wsHost}/ws/stream?node_id=${nodeId}`);

        // Reveal results panel immediately for visual feedback
        document.getElementById('analysis-results').classList.remove('hidden');
        document.getElementById('insight-idle').classList.add('hidden');
        document.getElementById('api-status-text').innerText = "Establishing Neural Link...";

        streamSocket.onopen = () => {
            console.log("WebSocket connected to behavioral engine.");
            showToast("Camera Link Active", "📡");

            // Start the frame capture loop
            streamInterval = setInterval(() => {
                if (streamSocket.readyState === WebSocket.OPEN) {
                    // Optimization: Downscale to 640px MAX for bandwidth stability
                    const scale = Math.min(640 / video.videoWidth, 1.0);
                    canvas.width = video.videoWidth * scale;
                    canvas.height = video.videoHeight * scale;

                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob((blob) => {
                        if (blob) streamSocket.send(blob);
                    }, 'image/jpeg', 0.5); // Fast JPEG for real-time
                }
            }, 400); // 2.5 FPS is good for live tracking
        };

        streamSocket.onerror = (e) => {
            console.error("WebSocket Connection Error:", e);
            showToast('System Link Failed', '❌');
            document.getElementById('api-status-text').innerText = "Offline";
        };

        streamSocket.onclose = () => {
            console.log("WebSocket Connection Closed");
            if (streamInterval) clearInterval(streamInterval);
        };

        live_sessions_markers_count = 0;

        streamSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.status === "active") {
                currentSessionId = data.session_id;
                const metrics = data.live_metrics;

                if (metrics.pet_detected) {
                    // Update main UI visibility
                    document.getElementById('metrics-card').classList.add('active');

                    const liveScore = Math.round(metrics.confidence * 100);
                    document.getElementById('ring-pct').innerText = `${liveScore}%`;
                    const offset = (metrics.confidence) * 628;
                    document.getElementById('ring-fill').style.strokeDasharray = `${offset}, 628`;

                    document.getElementById('emotion-value').innerText = metrics.behavior;
                    if (document.getElementById('emotion-value-hud')) {
                        document.getElementById('emotion-value-hud').innerText = metrics.behavior;
                        document.getElementById('hud-stats').style.opacity = '1';
                        document.getElementById('hud-stats').style.transform = 'translateY(0)';
                    }

                    document.getElementById('happiness-score-text').innerText = `${liveScore}%`;
                    document.getElementById('api-status-text').innerText = `Tracking: ${metrics.type}`;

                    // Heartbeat / Marker Accumulation
                    if (data.heartbeat) {
                        const h = data.heartbeat;
                        const log = document.getElementById('marker-log');
                        h.markers.forEach(m => {
                            live_sessions_markers_count++;
                            const pill = document.createElement('span');
                            pill.className = 'marker-pill';
                            pill.innerText = `📎 ${m}`;
                            log.prepend(pill);
                        });

                        if (h.is_ready && !synthesisReady) {
                            synthesisReady = true;
                            document.getElementById('synthesis-ready-banner').classList.remove('hidden');
                            showToast("Observation complete. Ready for analysis.", "🧠");
                        }
                    }
                } else {
                    document.getElementById('api-status-text').innerText = `Searching...`;
                }
            }
        };

    } catch (err) {
        console.error("Camera Initialisation Error:", err);
        showToast(err.message || 'Camera access denied or device locked', '❌');
    }
}

// Global Synthesis Function
window.finalizeLiveSession = async () => {
    if (!currentSessionId) {
        console.warn("SYNTHESIS: No active session ID found.");
        return;
    }

    // UI Feedback: Synthesis Mode
    const banner = document.getElementById('synthesis-ready-banner');
    const summary = document.getElementById('analysis-summary');

    banner.innerHTML = `<div class="synthesis-banner-content"><span>⚙️ Processing Session Evidence...</span><div class="spinner-sm"></div></div>`;
    summary.innerHTML = `<div class="synthesis-mode"><strong>SYNTHESIS MODE:</strong> Deep AI is aggregating ${live_sessions_markers_count || 'multiple'} observations into a clinical record. Please wait...</div>`;

    console.log("SYNTHESIS: Triggering fetch for session:", currentSessionId);
    showToast("Deep Synthesis Started...", "🧠");

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // Increased to 30s

        const res = await fetch(`${API_URL}/api/live/synthesis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        const report = await res.json();
        console.log("SYNTHESIS: Received result:", report);

        banner.classList.add('hidden');
        document.getElementById('marker-log').innerHTML = '';

        displayResults(report);
        currentSessionId = null;
        synthesisReady = false;
        showToast("Diagnosis Complete!", "✅");
    } catch (e) {
        console.error("SYNTHESIS FAILURE:", e);
        showToast("Synthesis timed out", "❌");
        banner.innerHTML = `<div class="synthesis-banner-content"><span>❌ Problem reaching AI brain.</span><button class="btn btn-sm" onclick="finalizeLiveSession()">Retry Synthesis</button></div>`;
    }
};

function stopLiveStream() {
    if (streamInterval) clearInterval(streamInterval);
    if (streamSocket) streamSocket.close();

    const video = document.getElementById('live-video');
    const stream = video.srcObject;
    if (stream) stream.getTracks().forEach(track => track.stop());

    video.srcObject = null;
    video.classList.add('hidden');
    document.getElementById('vision-placeholder').classList.remove('hidden');
    document.getElementById('live-indicator').classList.add('hidden');

    document.getElementById('live-stream-btn').classList.remove('hidden');
    document.getElementById('stop-stream-btn').classList.add('hidden');

    // Trigger Synthesis if markers were collected
    window.finalizeLiveSession();
}

function sendFeedback(isAccurate) {
    if (!lastAnalysisData) return;
    fetch(`${API_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: lastAnalysisData.file_id, is_accurate: isAccurate })
    }).then(() => {
        showToast('Feedback recorded. Thank you!');
    });
}

function resetUI() {
    location.reload();
}

// Distance calculation helper (Haversine Formula)
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

// Opening hours status helper
function getOpeningStatus(hours) {
    const now = new Date();
    const hour = now.getHours();
    const day = now.getDay(); // 0=Sun, 6=Sat

    if (!hours) {
        if (day >= 1 && day <= 5) {
            if (hour >= 9 && hour <= 18) return { label: 'Open Now', pill: 'bg-green-600' };
        } else if (day === 0 || day === 6) {
            if (hour >= 10 && hour <= 15) return { label: 'Open Now', pill: 'bg-green-600' };
        }
        return { label: 'Status Unknown', pill: 'bg-slate-400' };
    }

    if (hours.toLowerCase().includes('24/7')) return { label: 'Open 24/7', pill: 'bg-indigo-600' };

    try {
        if (day >= 1 && day <= 5) {
            if (hour >= 9 && hour <= 19) return { label: 'Open Now', pill: 'bg-green-600' };
            return { label: 'Closed Now', pill: 'bg-red-600' };
        } else {
            if (hour >= 9 && hour <= 16) return { label: 'Open Now (Weekend)', pill: 'bg-green-600' };
            return { label: 'Closed for Weekend', pill: 'bg-red-600' };
        }
    } catch (e) {
        return { label: 'Check Schedule', pill: 'bg-amber-500' };
    }
}

// === VET LINK LOGIC (DYNAMIC INTELLIGENCE) ===
window.findNearbyVets = async function () {
    const modal = document.getElementById('vet-modal');
    const content = document.getElementById('vet-modal-content');
    const loading = document.getElementById('vet-loading');
    const grid = document.getElementById('vet-results-grid');

    // Show Modal
    modal.classList.remove('hidden');
    setTimeout(() => {
        content.classList.remove('scale-95', 'opacity-0');
        content.classList.add('scale-100', 'opacity-100');
    }, 10);

    // Reset State
    loading.classList.remove('hidden');
    grid.classList.add('hidden');
    grid.innerHTML = '';

    const executeSearch = async (latitude, longitude) => {
        const query = `[out:json];
        (
          node["amenity"="veterinary"](around:50000, ${latitude}, ${longitude});
          way["amenity"="veterinary"](around:50000, ${latitude}, ${longitude});
        );
        out center;`;

        try {
            const response = await fetch('https://overpass-api.de/api/interpreter', {
                method: 'POST',
                body: query
            });
            const data = await response.json();

            loading.classList.add('hidden');
            grid.classList.remove('hidden');

            if (data.elements.length === 0) {
                grid.innerHTML = `<div class="col-span-full py-12 text-center opacity-40">No veterinary clinics found within 50km of ${latitude.toFixed(2)}, ${longitude.toFixed(2)}.</div>`;
                return;
            }

            data.elements.forEach(vet => {
                const name = vet.tags.name || "Regional Veterinary Clinic";
                const lat = vet.lat || vet.center?.lat;
                const lon = vet.lon || vet.center?.lon;

                const distance = calculateDistance(latitude, longitude, lat, lon).toFixed(1);
                const status = getOpeningStatus(vet.tags.opening_hours);

                const addrParts = [];
                if (vet.tags["addr:housenumber"]) addrParts.push(vet.tags["addr:housenumber"]);
                if (vet.tags["addr:street"]) addrParts.push(vet.tags["addr:street"]);
                if (vet.tags["addr:suburb"]) addrParts.push(vet.tags["addr:suburb"]);
                if (vet.tags["addr:city"]) addrParts.push(vet.tags["addr:city"]);

                const address = addrParts.length > 0 ? addrParts.join(', ') : `Coordinate: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;

                // Extract genuine OpenStreetMap Tags
                const phone = vet.tags.phone || vet.tags["contact:phone"] || undefined;
                const email = vet.tags.email || vet.tags["contact:email"] || undefined;
                const website = vet.tags.website || vet.tags["contact:website"] || undefined;

                const card = document.createElement('div');
                card.className = "p-6 rounded-[24px] bg-surface-container-low/50 border border-on-surface-variant/5 hover:bg-white hover:shadow-xl transition-all group";
                card.innerHTML = `
                    <div class="flex justify-between items-start mb-4">
                        <div class="flex items-center gap-4">
                            <div class="w-14 h-14 rounded-3xl bg-indigo-50 flex items-center justify-center text-primary shadow-sm">
                                <span class="material-symbols-outlined text-2xl font-bold">local_hospital</span>
                            </div>
                            <div class="flex flex-col gap-2">
                                <div class="px-3 py-1.5 rounded-xl ${status.pill} flex items-center gap-2 shadow-sm transition-all">
                                    <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                                    <span class="text-[10px] font-black text-white uppercase tracking-widest leading-none">${status.label}</span>
                                </div>
                                <div class="text-[11px] font-bold text-on-surface-variant/40 uppercase tracking-[0.1em] flex items-center gap-1 ml-1">
                                    <span class="material-symbols-outlined text-[14px]">near_me</span>
                                    ${distance} km away
                                </div>
                            </div>
                        </div>
                        <span class="text-[9px] font-bold text-success bg-success/10 px-3 py-1 rounded-full uppercase tracking-tighter">Live Sync</span>
                    </div>
                    <h4 class="font-bold text-lg text-on-surface mb-1">${name}</h4>
                    <p class="text-[13px] text-on-surface-variant font-medium mb-5 flex items-start gap-2">
                        <span class="material-symbols-outlined text-[16px] text-primary/40 shrink-0">location_on</span> 
                        <span>${address}</span>
                    </p>
                    <div class="flex gap-2 pt-2">
                        <button class="flex-1 py-3 bg-primary text-white rounded-xl text-[10px] font-bold tracking-widest hover:shadow-lg transition-all" onclick="showContactInfo(\`${name.replace(/`/g, '')}\`, \`${address.replace(/`/g, '')}\`, \`${phone}\`, \`${email}\`, \`${website}\`)">CONTACT</button>
                        <button class="flex-1 py-3 bg-white border border-surface-container-highest text-on-surface rounded-xl text-[10px] font-bold tracking-widest hover:bg-on-surface-variant/5 transition-all" onclick="window.open('https://www.google.com/maps/search/?api=1&query=${lat},${lon}', '_blank')">ON MAP</button>
                    </div>
                `;
                grid.appendChild(card);
            });
        } catch (e) {
            showToast("Satellite Sync Failed", "❌");
        }
    };

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => executeSearch(pos.coords.latitude, pos.coords.longitude),
            async () => {
                try {
                    const res = await fetch('https://ipapi.co/json/');
                    const data = await res.json();
                    if (data.latitude) executeSearch(data.latitude, data.longitude);
                    else throw new Error();
                } catch (e) {
                    showToast("Location denied. Using default scan...", "⚠️");
                    executeSearch(40.7128, -74.0060); // NY Default
                }
            }
        );
    } else {
        executeSearch(40.7128, -74.0060);
    }
};

window.closeVetModal = function () {
    const modal = document.getElementById('vet-modal');
    const content = document.getElementById('vet-modal-content');
    content.classList.add('scale-95', 'opacity-0');
    content.classList.remove('scale-100', 'opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
};

// === LICENSE MODAL LOGIC ===
window.openLicenseModal = function () {
    const modal = document.getElementById('license-modal');
    const content = document.getElementById('license-modal-content');

    modal.classList.remove('hidden');
    setTimeout(() => {
        content.classList.remove('scale-95', 'opacity-0');
        content.classList.add('scale-100', 'opacity-100');
    }, 10);
};

window.closeLicenseModal = function () {
    const modal = document.getElementById('license-modal');
    const content = document.getElementById('license-modal-content');

    content.classList.add('scale-95', 'opacity-0');
    content.classList.remove('scale-100', 'opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
};

// === CONTACT MODAL LOGIC ===
window.showContactInfo = function (name, address, phone, email, website) {
    document.getElementById('contact-name').innerText = name;
    document.getElementById('contact-address').innerText = address;

    const container = document.getElementById('contact-methods-container');
    container.innerHTML = '';
    let hasContactInfo = false;

    if (phone && phone !== "Contact via Map" && phone !== "undefined") {
        hasContactInfo = true;
        container.innerHTML += `
            <a href="tel:${phone}" class="w-full p-4 rounded-xl bg-surface-container-low border border-surface-container-highest hover:border-primary transition-all flex flex-col items-center group !border-b-4 decoration-none">
                <span class="text-[9px] font-bold text-on-surface-variant/40 tracking-widest uppercase block mb-1">DIRECT LINE</span>
                <span class="text-xl font-black text-primary group-hover:text-primary-container transition-colors">${phone}</span>
            </a>
        `;
    }

    if (email && email !== "undefined" && email !== "null") {
        hasContactInfo = true;
        container.innerHTML += `
            <a href="mailto:${email}" class="w-full p-4 rounded-xl bg-surface-container-low border border-surface-container-highest hover:border-primary transition-all flex flex-col items-center group !border-b-4 decoration-none">
                <span class="text-[9px] font-bold text-on-surface-variant/40 tracking-widest uppercase block mb-1">EMAIL</span>
                <span class="text-sm font-bold text-primary group-hover:text-primary-container transition-colors break-all">${email}</span>
            </a>
        `;
    }

    if (website && website !== "undefined" && website !== "null") {
        hasContactInfo = true;
        const validUrl = website.startsWith('http') ? website : 'https://' + website;
        container.innerHTML += `
            <a href="${validUrl}" target="_blank" rel="noopener noreferrer" class="w-full p-4 rounded-xl bg-surface-container-low border border-surface-container-highest hover:border-primary transition-all flex flex-col items-center group !border-b-4 decoration-none">
                <span class="text-[9px] font-bold text-on-surface-variant/40 tracking-widest uppercase block mb-1">WEBSITE</span>
                <span class="text-xs font-bold text-primary group-hover:text-primary-container transition-colors break-all">${website}</span>
            </a>
        `;
    }

    if (!hasContactInfo) {
        container.innerHTML = `
            <div class="w-full p-6 py-8 rounded-xl bg-surface-container-low border border-surface-container-highest text-center flex flex-col gap-2 items-center">
                <span class="material-symbols-outlined opacity-20 text-4xl mb-2">location_off</span>
                <span class="text-xs font-bold text-on-surface-variant/60">No contact info attached to map data.</span>
                <span class="text-[9px] font-semibold text-on-surface-variant/40 uppercase tracking-widest mt-1">Please use the "ON MAP" button to search directly.</span>
            </div>
        `;
    }

    const modal = document.getElementById('contact-modal');
    const content = document.getElementById('contact-modal-content');

    modal.classList.remove('hidden');
    setTimeout(() => {
        content.classList.remove('scale-95', 'opacity-0');
        content.classList.add('scale-100', 'opacity-100');
    }, 10);
};

window.closeContactModal = function () {
    const modal = document.getElementById('contact-modal');
    const content = document.getElementById('contact-modal-content');

    content.classList.add('scale-95', 'opacity-0');
    content.classList.remove('scale-100', 'opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
};

// === SUPPORT MODAL LOGIC ===
window.openSupportModal = function () {
    const modal = document.getElementById('support-modal');
    const content = document.getElementById('support-modal-content');

    modal.classList.remove('hidden');
    setTimeout(() => {
        content.classList.remove('scale-95', 'opacity-0');
        content.classList.add('scale-100', 'opacity-100');
    }, 10);
};

window.closeSupportModal = function () {
    const modal = document.getElementById('support-modal');
    const content = document.getElementById('support-modal-content');

    content.classList.add('scale-95', 'opacity-0');
    content.classList.remove('scale-100', 'opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
};
