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
        "the video was deleted"
    ];

    async function checkSingleUrl(url) {
        if (!url || typeof url !== "string" || !url.startsWith("http")) {
            return { url, alive: false, status: 0 };
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2200);

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

            const chunk = (await resp.text()).slice(0, 3000).toLowerCase();
            for (let i = 0; i < DEAD_PATTERNS.length; i++) {
                if (chunk.includes(DEAD_PATTERNS[i])) {
                    return { url, alive: false, status: 404, reason: DEAD_PATTERNS[i] };
                }
            }

            return { url, alive: true, status: resp.status };
        } catch (err) {
            return { url, alive: false, error: err.message };
        }
    }

    // Limit to first 6 sources max for fastest response
    const toCheck = urls.slice(0, 6);
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
