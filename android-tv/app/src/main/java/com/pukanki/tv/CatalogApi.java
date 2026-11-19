package com.pukanki.tv;

import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class CatalogApi {
    private static final String BASE_URL = "https://pukanki.vercel.app/api/catalog";
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    public static class FilterParams {
        public String tab = "bg";
        public String genre = "";
        public String excludeGenre = "";
        public String query = "";
        public int yearFrom = 0;
        public int yearTo = 0;
        public String duration = "";
        public String player = "";
        public String sort = "default";
    }

    public static class PageResult {
        public int page;
        public int total;
        public boolean hasMore;
        public List<MovieItem> items = new ArrayList<>();
    }

    public interface Callback {
        void onSuccess(PageResult result);
        void onError(String message);
    }

    public static void fetchPage(final FilterParams f, final int page, final int limit, final Callback cb) {
        executor.execute(() -> {
            HttpURLConnection conn = null;
            try {
                StringBuilder sb = new StringBuilder(BASE_URL);
                sb.append("?tab=").append(URLEncoder.encode(f.tab != null ? f.tab : "bg", "UTF-8"));
                sb.append("&page=").append(page);
                sb.append("&limit=").append(limit);

                if (f.genre != null && !f.genre.trim().isEmpty()) {
                    sb.append("&genre=").append(URLEncoder.encode(f.genre.trim(), "UTF-8"));
                }
                if (f.excludeGenre != null && !f.excludeGenre.trim().isEmpty()) {
                    sb.append("&excludeGenre=").append(URLEncoder.encode(f.excludeGenre.trim(), "UTF-8"));
                }
                if (f.query != null && !f.query.trim().isEmpty()) {
                    sb.append("&q=").append(URLEncoder.encode(f.query.trim(), "UTF-8"));
                }
                if (f.yearFrom > 0) {
                    sb.append("&yearFrom=").append(f.yearFrom);
                }
                if (f.yearTo > 0) {
                    sb.append("&yearTo=").append(f.yearTo);
                }
                if (f.duration != null && !f.duration.isEmpty()) {
                    sb.append("&duration=").append(URLEncoder.encode(f.duration, "UTF-8"));
                }
                if (f.player != null && !f.player.isEmpty()) {
                    sb.append("&player=").append(URLEncoder.encode(f.player, "UTF-8"));
                }
                if (f.sort != null && !f.sort.isEmpty() && !"default".equals(f.sort)) {
                    sb.append("&sort=").append(URLEncoder.encode(f.sort, "UTF-8"));
                }

                URL url = new URL(sb.toString());
                conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(12000);
                conn.setRequestProperty("User-Agent", "PukankiTV/2.0");

                int code = conn.getResponseCode();
                if (code != 200) {
                    throw new Exception("HTTP " + code);
                }

                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "UTF-8"));
                StringBuilder json = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) {
                    json.append(line);
                }
                br.close();

                JSONObject root = new JSONObject(json.toString());
                PageResult res = new PageResult();
                res.page = root.optInt("page", page);
                res.total = root.optInt("total", 0);
                res.hasMore = root.optBoolean("hasMore", false);

                JSONArray arr = root.optJSONArray("items");
                if (arr != null) {
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject itemObj = arr.optJSONObject(i);
                        if (itemObj != null) {
                            res.items.add(MovieItem.fromJson(itemObj));
                        }
                    }
                }

                mainHandler.post(() -> cb.onSuccess(res));
            } catch (Exception e) {
                final String msg = e.getMessage() != null ? e.getMessage() : "Грешка при връзка";
                mainHandler.post(() -> cb.onError(msg));
            } finally {
                if (conn != null) conn.disconnect();
            }
        });
    }
}
