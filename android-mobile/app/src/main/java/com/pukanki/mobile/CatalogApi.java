package com.pukanki.mobile;

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
    private static final String BASE_URL = "https://pukanki.vercel.app/api/mobile-catalog";
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    public static class FilterParams {
        public String tab = "bg";
        public String query = "";
        public String genresCsv = "";
        public String excludeGenresCsv = "";
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

    public static void fetchPage(FilterParams params, int page, int limit, Callback cb) {
        executor.execute(() -> {
            HttpURLConnection conn = null;
            try {
                StringBuilder sb = new StringBuilder(BASE_URL);
                sb.append("?tab=").append(URLEncoder.encode(params.tab != null ? params.tab : "bg", "UTF-8"));
                sb.append("&page=").append(page);
                sb.append("&limit=").append(limit);

                if (params.query != null && !params.query.trim().isEmpty()) {
                    sb.append("&q=").append(URLEncoder.encode(params.query.trim(), "UTF-8"));
                }
                if (params.genresCsv != null && !params.genresCsv.isEmpty()) {
                    sb.append("&genre=").append(URLEncoder.encode(params.genresCsv, "UTF-8"));
                }
                if (params.excludeGenresCsv != null && !params.excludeGenresCsv.isEmpty()) {
                    sb.append("&excludeGenre=").append(URLEncoder.encode(params.excludeGenresCsv, "UTF-8"));
                }
                if (params.yearFrom > 0) {
                    sb.append("&yearFrom=").append(params.yearFrom);
                }
                if (params.yearTo > 0) {
                    sb.append("&yearTo=").append(params.yearTo);
                }
                if (params.duration != null && !params.duration.isEmpty()) {
                    sb.append("&duration=").append(URLEncoder.encode(params.duration, "UTF-8"));
                }
                if (params.player != null && !params.player.isEmpty()) {
                    sb.append("&player=").append(URLEncoder.encode(params.player, "UTF-8"));
                }
                if (params.sort != null && !params.sort.isEmpty() && !"default".equals(params.sort)) {
                    sb.append("&sort=").append(URLEncoder.encode(params.sort, "UTF-8"));
                }

                URL url = new URL(sb.toString());
                conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(12000);
                conn.setReadTimeout(15000);
                conn.setRequestProperty("Accept", "application/json");
                conn.setRequestProperty("User-Agent", "PukankiMobile/1.0");

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

                JSONArray itemsArr = root.optJSONArray("items");
                if (itemsArr != null) {
                    for (int i = 0; i < itemsArr.length(); i++) {
                        JSONObject o = itemsArr.optJSONObject(i);
                        if (o != null) {
                            res.items.add(MovieItem.fromJson(o));
                        }
                    }
                }

                mainHandler.post(() -> cb.onSuccess(res));
            } catch (Exception e) {
                String msg = e.getMessage() != null ? e.getMessage() : "Мрежова грешка";
                mainHandler.post(() -> cb.onError(msg));
            } finally {
                if (conn != null) conn.disconnect();
            }
        });
    }
}
