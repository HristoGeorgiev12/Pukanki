export default async function handler(req, res) {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");

    if (req.method === "OPTIONS") {
        return res.status(200).end();
    }

    let urls = [];
    if (req.method === "POST") {
        try {
            const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
            urls = Array.isArray(body.urls) ? body.urls : [];
        } catch (e) {
            urls = [];
        }
    }

    if (urls.length === 0 && req.query.urls) {
        const qUrls = req.query.urls;
        urls = (Array.isArray(qUrls) ? qUrls : qUrls.split(",")).map(u => decodeURIComponent(u.trim())).filter(Boolean);
    }

    if (urls.length === 0) {
        return res.status(200).json({ activeIndex: 0, results: [] });
    }

    const DEAD_PATTERNS = [
        "404 not found",
        "404 - не е намерен",
        "не е намерен",
        "file was deleted",
        "file has been removed",
        "video has been removed",
        "video not found",
        "file not found",
        "deleted due to copyright",
        "not found or deleted",
        "file no longer exists",
        "the video was deleted",
        "file is no longer available",
        "expired or has been deleted",
        "the file expired",
        "video record missing"
    ];

    async function checkSingleUrl(url) {
        if (!url || typeof url !== "string" || !url.startsWith("http")) {
            return { url, alive: false, status: 0 };
        }

        // YouTube is always treated as alive
        if (url.includes("youtube.com") || url.includes("youtu.be")) {
            return { url, alive: true, status: 200 };
        }

        // 1. Byse / Filemoon: check the actual video record API (works fast from Vercel)
        const fmoMatch = url.match(/(?:filemoon\.(?:sx|to|in|me|net)|byse[a-z0-9]*\.com)\/e\/([a-zA-Z0-9_-]+)/i);
        if (fmoMatch && fmoMatch[1]) {
            const vidId = fmoMatch[1];
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2200);
                const apiResp = await fetch(`https://bysesukior.com/api/videos/${vidId}/`, {
                    method: "GET",
                    signal: controller.signal,
                    headers: {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept": "application/json"
                    }
                });
                clearTimeout(timeoutId);
                if (apiResp.status === 200) {
                    return { url, alive: true, status: 200 };
                }
                if (apiResp.status === 404 || apiResp.status === 410) {
                    return { url, alive: false, status: 404, reason: "filemoon video missing" };
                }
            } catch (err) {
                return { url, alive: true, status: 200, uncertain: true };
            }
        }

        // 2. Vidon: check POST /dl with file_code (if reachable; on datacenter timeout assume alive)
        const vidonMatch = url.match(/vidon\.(?:to|me|cc)\/e\/([a-zA-Z0-9_-]+)/i);
        if (vidonMatch && vidonMatch[1]) {
            const fileCode = vidonMatch[1].replace(/\.html$/i, "").split("-").pop();
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 1400);
                const dlResp = await fetch("https://vidon.to/dl", {
                    method: "POST",
                    signal: controller.signal,
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": `https://vidon.to/e/${fileCode}`
                    },
                    body: `op=embed&file_code=${encodeURIComponent(fileCode)}&auto=1`
                });
                clearTimeout(timeoutId);
                if (dlResp.status === 404 || dlResp.status === 410) {
                    return { url, alive: false, status: dlResp.status };
                }
                const bodyText = (await dlResp.text()).toLowerCase();
                if (bodyText.includes("expired or has been deleted") || bodyText.includes("file is no longer available")) {
                    return { url, alive: false, status: 404, reason: "vidon deleted" };
                }
                if (bodyText.includes("jwplayer") || bodyText.includes("sources") || bodyText.includes(".m3u8")) {
                    return { url, alive: true, status: 200 };
                }
                return { url, alive: true, status: 200 };
            } catch (err) {
                // Vidon drops/throttles US datacenter IPs (Vercel iad1); do not falsely mark as dead
                return { url, alive: true, status: 200, uncertain: true };
            }
        }

        // 3. General GET check for all other providers (VOE, Streamtape, VidLink, etc.)
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);

            const resp = await fetch(url, {
                method: "GET",
                signal: controller.signal,
                headers: {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            });
            clearTimeout(timeoutId);

            if (resp.status === 404 || resp.status === 410 || resp.status >= 500) {
                return { url, alive: false, status: resp.status };
            }

            const chunk = (await resp.text()).slice(0, 4000).toLowerCase();
            for (let i = 0; i < DEAD_PATTERNS.length; i++) {
                if (chunk.includes(DEAD_PATTERNS[i])) {
                    return { url, alive: false, status: 404, reason: DEAD_PATTERNS[i] };
                }
            }

            return { url, alive: true, status: resp.status };
        } catch (err) {
            if (url.includes("voe.sx")) {
                return { url, alive: false, status: 404, error: err.message };
            }
            return { url, alive: true, status: 200, uncertain: true };
        }
    }

    // Check candidate sources concurrently
    const toCheck = urls.slice(0, 8);
    const results = await Promise.all(toCheck.map(u => checkSingleUrl(u)));

    let firstAliveIdx = results.findIndex(r => r.alive);
    if (firstAliveIdx === -1) {
        firstAliveIdx = 0;
    }

    return res.status(200).json({
        activeIndex: firstAliveIdx,
        activeUrl: toCheck[firstAliveIdx],
        results
    });
}
