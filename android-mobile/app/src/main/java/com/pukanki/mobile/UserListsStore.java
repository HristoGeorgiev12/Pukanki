package com.pukanki.mobile;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class UserListsStore {
    private static final String PREF_NAME = "pukanki_user_lists_v1";
    private static final String TYPE_FAV = "favorites";
    private static final String TYPE_LATER = "watch_later";
    private static final int MAX_ITEMS = 200;

    private static SharedPreferences prefs(Context ctx) {
        return ctx.getApplicationContext().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    private static String listKey(Context ctx, String type) {
        String pid = ProfileStore.getActiveProfileId(ctx);
        return type + "_" + pid;
    }

    public static synchronized boolean isFavorite(Context ctx, String historyKey) {
        return contains(ctx, TYPE_FAV, historyKey);
    }

    public static synchronized boolean isWatchLater(Context ctx, String historyKey) {
        return contains(ctx, TYPE_LATER, historyKey);
    }

    public static synchronized boolean toggleFavorite(Context ctx, MovieItem item) {
        return toggle(ctx, TYPE_FAV, item);
    }

    public static synchronized boolean toggleWatchLater(Context ctx, MovieItem item) {
        return toggle(ctx, TYPE_LATER, item);
    }

    public static synchronized int getFavoritesCount(Context ctx) {
        return loadRawList(ctx, TYPE_FAV).size();
    }

    public static synchronized int getWatchLaterCount(Context ctx) {
        return loadRawList(ctx, TYPE_LATER).size();
    }

    public static synchronized List<MovieItem> getFavorites(Context ctx) {
        return loadMovies(ctx, TYPE_FAV);
    }

    public static synchronized List<MovieItem> getWatchLater(Context ctx) {
        return loadMovies(ctx, TYPE_LATER);
    }

    private static boolean contains(Context ctx, String type, String historyKey) {
        if (ctx == null || historyKey == null || historyKey.isEmpty()) return false;
        for (JSONObject entry : loadRawList(ctx, type)) {
            if (historyKey.equals(entry.optString("k", ""))) return true;
        }
        return false;
    }

    private static boolean toggle(Context ctx, String type, MovieItem item) {
        if (ctx == null || item == null) return false;
        String key = item.getHistoryKey();
        List<JSONObject> list = loadRawList(ctx, type);
        boolean removed = false;
        for (int i = list.size() - 1; i >= 0; i--) {
            if (key.equals(list.get(i).optString("k", ""))) {
                list.remove(i);
                removed = true;
            }
        }
        if (!removed) {
            try {
                JSONObject entry = new JSONObject();
                entry.put("k", key);
                entry.put("ts", System.currentTimeMillis());
                entry.put("item", item.toJsonObject());
                list.add(0, entry);
                while (list.size() > MAX_ITEMS) {
                    list.remove(list.size() - 1);
                }
            } catch (Exception ignored) {}
        }
        saveRawList(ctx, type, list);
        return !removed;
    }

    private static List<MovieItem> loadMovies(Context ctx, String type) {
        List<JSONObject> raw = loadRawList(ctx, type);
        Collections.sort(raw, (a, b) -> Long.compare(b.optLong("ts", 0L), a.optLong("ts", 0L)));
        List<MovieItem> out = new ArrayList<>();
        for (JSONObject entry : raw) {
            JSONObject itemObj = entry.optJSONObject("item");
            if (itemObj != null) {
                out.add(MovieItem.fromJson(itemObj));
            }
        }
        return out;
    }

    private static List<JSONObject> loadRawList(Context ctx, String type) {
        List<JSONObject> out = new ArrayList<>();
        String raw = prefs(ctx).getString(listKey(ctx, type), "[]");
        try {
            JSONArray arr = new JSONArray(raw);
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.optJSONObject(i);
                if (o != null) out.add(o);
            }
        } catch (Exception ignored) {}
        return out;
    }

    private static void saveRawList(Context ctx, String type, List<JSONObject> list) {
        JSONArray arr = new JSONArray();
        for (JSONObject o : list) arr.put(o);
        prefs(ctx).edit().putString(listKey(ctx, type), arr.toString()).apply();
    }
}
