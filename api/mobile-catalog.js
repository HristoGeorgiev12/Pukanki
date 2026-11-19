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
        const genreParam = String(req.query.genre || "").trim().toLowerCase();
        const excludeGenreParam = String(req.query.excludeGenre || "").trim().toLowerCase();
        const yearFrom = parseInt(req.query.yearFrom || "0", 10) || 0;
        const yearTo = parseInt(req.query.yearTo || "0", 10) || 0;
        const duration = String(req.query.duration || "").toLowerCase(); // short | medium | long
        const player = String(req.query.player || "").trim().toLowerCase();
        const sort = String(req.query.sort || "default").toLowerCase();
        const page = Math.max(1, parseInt(req.query.page || "1", 10) || 1);
        const limit = Math.min(60, Math.max(6, parseInt(req.query.limit || "30", 10) || 30));

        const includedGenres = genreParam
            ? genreParam.split(",").map((g) => g.trim()).filter(Boolean)
            : [];
        const excludedGenres = excludeGenreParam
            ? excludeGenreParam.split(",").map((g) => g.trim()).filter(Boolean)
            : [];

        let filtered = all;

        if (tab === "bg") {
            filtered = filtered.filter((m) => m.bg === 1 && m.tp !== "s");
        } else if (tab === "sub") {
            filtered = filtered.filter((m) => m.sub === 1 && m.tp !== "s");
        } else if (tab === "series") {
            filtered = filtered.filter((m) => m.tp === "s");
        }

        if (includedGenres.length > 0) {
            filtered = filtered.filter((m) => {
                if (!Array.isArray(m.g)) return false;
                const itemGenres = m.g.map((g) => String(g).toLowerCase());
                return includedGenres.every((inc) => itemGenres.includes(inc));
            });
        }

        if (excludedGenres.length > 0) {
            filtered = filtered.filter((m) => {
                if (!Array.isArray(m.g)) return true;
                const itemGenres = m.g.map((g) => String(g).toLowerCase());
                return !excludedGenres.some((exc) => itemGenres.includes(exc));
            });
        }

        if (yearFrom > 0) {
            filtered = filtered.filter((m) => (m.y || 0) >= yearFrom);
        }
        if (yearTo > 0) {
            filtered = filtered.filter((m) => (m.y || 0) > 0 && (m.y || 0) <= yearTo);
        }

        if (duration === "short") {
            filtered = filtered.filter((m) => (m.d || 0) > 0 && m.d < 90);
        } else if (duration === "medium") {
            filtered = filtered.filter((m) => (m.d || 0) >= 90 && m.d <= 120);
        } else if (duration === "long") {
            filtered = filtered.filter((m) => (m.d || 0) > 120);
        }

        if (player) {
            filtered = filtered.filter((m) => {
                if (!Array.isArray(m.s)) return false;
                return m.s.some((pair) => {
                    const name = String(pair[0] || "").toLowerCase();
                    const url = String(pair[2] || "").toLowerCase();
                    return name.includes(player) || url.includes(player);
                });
            });
        }

        if (q) {
            filtered = filtered.filter((m) => {
                const t = (m.t || "").toLowerCase();
                const ot = (m.ot || "").toLowerCase();
                return t.includes(q) || ot.includes(q);
            });
        }

        if (sort !== "default") {
            filtered = [...filtered];
            if (sort === "newest") {
                filtered.sort((a, b) => (b.y || 0) - (a.y || 0) || (b.r || 0) - (a.r || 0));
            } else if (sort === "oldest") {
                filtered.sort((a, b) => (a.y || 9999) - (b.y || 9999) || (b.r || 0) - (a.r || 0));
            } else if (sort === "rating") {
                const eff = (r) => (r >= 9.7 ? 6.0 : r || 0);
                filtered.sort((a, b) => eff(b.r) - eff(a.r) || (b.y || 0) - (a.y || 0));
            } else if (sort === "title") {
                filtered.sort((a, b) => String(a.t || "").localeCompare(String(b.t || ""), "bg"));
            } else if (sort === "shortest") {
                filtered.sort((a, b) => (a.d || 9999) - (b.d || 9999));
            } else if (sort === "longest") {
                filtered.sort((a, b) => (b.d || 0) - (a.d || 0));
            }
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
