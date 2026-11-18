import fs from "fs";
import path from "path";

let cachedCatalog = null;

function loadCatalog() {
    if (cachedCatalog) {
        return cachedCatalog;
    }
    const filePath = path.join(process.cwd(), "data", "tv_catalog.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    cachedCatalog = JSON.parse(raw);
    return cachedCatalog;
}

export default async function handler(req, res) {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=600");

    if (req.method === "OPTIONS") {
        return res.status(200).end();
    }

    try {
        const all = loadCatalog();
        const tab = String(req.query.tab || "bg").toLowerCase(); // bg | sub | series | all
        const q = String(req.query.q || "").trim().toLowerCase();
        const genre = String(req.query.genre || "").trim().toLowerCase();
        const page = Math.max(1, parseInt(req.query.page || "1", 10) || 1);
        const limit = Math.min(60, Math.max(6, parseInt(req.query.limit || "30", 10) || 30));

        let filtered = all;

        if (tab === "bg") {
            filtered = filtered.filter((m) => m.bg === 1 && m.tp !== "s");
        } else if (tab === "sub") {
            filtered = filtered.filter((m) => m.sub === 1 && m.tp !== "s");
        } else if (tab === "series") {
            filtered = filtered.filter((m) => m.tp === "s");
        }

        if (genre) {
            filtered = filtered.filter(
                (m) => Array.isArray(m.g) && m.g.some((g) => String(g).toLowerCase() === genre)
            );
        }

        if (q) {
            filtered = filtered.filter((m) => {
                const t = (m.t || "").toLowerCase();
                const ot = (m.ot || "").toLowerCase();
                return t.includes(q) || ot.includes(q);
            });
        }

        const total = filtered.length;
        const start = (page - 1) * limit;
        const items = filtered.slice(start, start + limit);

        return res.status(200).json({
            page,
            limit,
            total,
            hasMore: start + limit < total,
            items
        });
    } catch (err) {
        return res.status(500).json({ error: String(err && err.message ? err.message : err) });
    }
}
