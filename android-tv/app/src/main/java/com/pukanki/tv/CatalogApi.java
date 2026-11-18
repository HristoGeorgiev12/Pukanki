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
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class CatalogApi {
    private static final String BASE_URL = "https://pukanki.vercel.app/api/catalog";
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

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

    public static void fetchPage(final String tab, final String query, final int page, final int limit, final Callback cb) {
        executor.execute(() -> {
            HttpURLConnection conn = null;
            try {
                StringBuilder sb = new StringBuilder(BASE_URL);
                sb.append("?tab=").append(URLEncoder.encode(tab, "UTF-8"));
                sb.append("&page=").append(page);
                sb.append("&limit=").append(limit);
                if (query != null && !query.trim().isEmpty()) {
                    sb.append("&q=").append(URLEncoder.encode(query.trim(), "UTF-8"));
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

                BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8)
                );
                StringBuilder jsonBuf = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonBuf.append(line);
                }
                reader.close();

                JSONObject root = new JSONObject(jsonBuf.toString());
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
