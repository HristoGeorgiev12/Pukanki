package com.pukanki.tv;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

public class WatchHistoryStore {
    private static final String PREF_NAME = "pukanki_watch_history_v1";
    private static final String KEY_ITEMS = "unfinished_items";
    private static final int MAX_ITEMS = 50;

    private static SharedPreferences prefs(Context ctx) {
        return ctx.getApplicationContext().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    public static synchronized void saveProgress(Context ctx, String movieJsonStr, String historyKey, long posMs, long durMs) {
        if (ctx == null || historyKey == null || historyKey.isEmpty()) return;
        if (posMs < 10000L) return; // Ignore < 10 seconds

        boolean isFinished = durMs > 60000L && ((double) posMs / (double) durMs) >= 0.92;
        List<JSONObject> list = loadRawList(ctx);

        // Remove existing entry for this movie
        for (int i = list.size() - 1; i >= 0; i--) {
            if (historyKey.equals(list.get(i).optString("k", ""))) {
                list.remove(i);
            }
        }

        if (!isFinished && movieJsonStr != null && !movieJsonStr.isEmpty()) {
            try {
                JSONObject entry = new JSONObject();
                entry.put("k", historyKey);
                entry.put("pos", posMs);
                entry.put("dur", durMs);
                entry.put("ts", System.currentTimeMillis());
                entry.put("item", new JSONObject(movieJsonStr));
                list.add(0, entry);
                while (list.size() > MAX_ITEMS) {
                    list.remove(list.size() - 1);
                }
            } catch (Exception ignored) {}
        }

        saveRawList(ctx, list);
    }

    public static synchronized long getSavedPositionMs(Context ctx, String historyKey) {
        if (ctx == null || historyKey == null || historyKey.isEmpty()) return 0L;
        for (JSONObject entry : loadRawList(ctx)) {
            if (historyKey.equals(entry.optString("k", ""))) {
                return entry.optLong("pos", 0L);
            }
        }
        return 0L;
    }

    public static synchronized int getUnfinishedCount(Context ctx) {
        return loadRawList(ctx).size();
    }

    public static synchronized List<MovieItem> getUnfinishedMovies(Context ctx) {
        List<JSONObject> raw = loadRawList(ctx);
        Collections.sort(raw, (a, b) -> Long.compare(b.optLong("ts", 0L), a.optLong("ts", 0L)));
        List<MovieItem> out = new ArrayList<>();
        for (JSONObject entry : raw) {
            JSONObject itemObj = entry.optJSONObject("item");
            if (itemObj != null) {
                MovieItem item = MovieItem.fromJson(itemObj);
                item.resumePositionMs = entry.optLong("pos", 0L);
                item.resumeDurationMs = entry.optLong("dur", 0L);
                out.add(item);
            }
        }
        return out;
    }

    public static String formatProgressShort(long posMs, long durMs) {
        long posMin = Math.max(1, posMs / 60000L);
        if (durMs > 60000L) {
            long durMin = Math.max(1, durMs / 60000L);
            return String.format(Locale.US, "▶ %d / %d мин", posMin, durMin);
        }
        return String.format(Locale.US, "▶ %d мин", posMin);
    }

    private static String activeItemsKey(Context ctx) {
        String pid = ProfileStore.getActiveProfileId(ctx);
        return ProfileStore.DEFAULT_ID.equals(pid) ? KEY_ITEMS : (KEY_ITEMS + "_" + pid);
    }

    private static List<JSONObject> loadRawList(Context ctx) {
        List<JSONObject> out = new ArrayList<>();
        String raw = prefs(ctx).getString(activeItemsKey(ctx), "[]");
        try {
            JSONArray arr = new JSONArray(raw);
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.optJSONObject(i);
                if (o != null) out.add(o);
            }
        } catch (Exception ignored) {}
        return out;
    }

    private static void saveRawList(Context ctx, List<JSONObject> list) {
        JSONArray arr = new JSONArray();
        for (JSONObject o : list) arr.put(o);
        prefs(ctx).edit().putString(activeItemsKey(ctx), arr.toString()).apply();
    }
}
