// Chat feature. Enhancements only: the page works without any of this.
document.addEventListener("DOMContentLoaded", function () {
    const log = document.getElementById("chat-log");
    const newButton = document.getElementById("chat-new");

    // ---- Start at the newest message -------------------------------------
    if (log) { log.scrollTop = log.scrollHeight; }

    // ---- Lock Send after a valid submit (no double posts) ----------------
    document.querySelectorAll("form.chat-form").forEach(function (form) {
        form.addEventListener("submit", function () {
            if (form.checkValidity()) {
                form.querySelectorAll("button[type='submit']").forEach(function (b) { b.disabled = true; });
            }
        });
    });
    window.addEventListener("pageshow", function (event) {
        // Back button restores the page with Send still locked; undo that.
        if (event.persisted) {
            document.querySelectorAll("button[type='submit']:disabled").forEach(function (b) { b.disabled = false; });
        }
    });

    // ---- Live updates -----------------------------------------------------
    if (!log || !log.dataset.pollUrl) { return; }

    const POLL_MS = 4000;
    const MAX_BACKOFF_MS = 30000;
    let lastId = Number(log.dataset.lastId) || 0;
    let delay = POLL_MS;
    let timer = null;
    let inFlight = false;
    let stopped = false;

    function nearBottom() {
        return log.scrollHeight - log.scrollTop - log.clientHeight < 80;
    }

    function showNewButton(show) {
        if (newButton) { newButton.hidden = !show; }
    }

    function append(data) {
        const wasAtBottom = nearBottom();
        const empty = log.querySelector(".chat-empty");
        if (empty) { empty.remove(); }
        // The HTML is built by the server, which escapes everything people typed.
        document.getElementById("latest").insertAdjacentHTML("beforebegin", data.html);
        lastId = data.last_id;
        log.dataset.lastId = String(lastId);
        if (wasAtBottom) {
            log.scrollTop = log.scrollHeight;
        } else {
            showNewButton(true);   // don't yank the page while someone is reading older messages
        }
    }

    function schedule() {
        clearTimeout(timer);
        if (!stopped && document.visibilityState !== "hidden") {
            timer = setTimeout(poll, delay);
        }
    }

    async function poll() {
        if (inFlight || stopped) { return; }
        inFlight = true;
        try {
            const response = await fetch(log.dataset.pollUrl + "?after=" + lastId, {
                credentials: "same-origin",
                cache: "no-store",
                headers: { "Accept": "application/json" },
            });
            if (response.redirected || response.status === 403 || response.status === 404) {
                stopped = true;          // logged out, left the Hub, or Hub gone: stop quietly
                return;
            }
            if (!response.ok) { throw new Error("poll failed: " + response.status); }
            const data = await response.json();
            delay = POLL_MS;
            if (data.count > 0) { append(data); }
        } catch (error) {
            delay = Math.min(delay * 2, MAX_BACKOFF_MS);   // be gentler after a failure
        } finally {
            inFlight = false;
            schedule();
        }
    }

    // Pause while the tab is hidden; catch up straight away when it comes back.
    document.addEventListener("visibilitychange", function () {
        clearTimeout(timer);
        if (document.visibilityState === "visible" && !stopped) { poll(); }
    });

    log.addEventListener("scroll", function () { if (nearBottom()) { showNewButton(false); } });
    if (newButton) {
        newButton.addEventListener("click", function () {
            log.scrollTop = log.scrollHeight;
            showNewButton(false);
            log.focus();
        });
    }

    schedule();
});
