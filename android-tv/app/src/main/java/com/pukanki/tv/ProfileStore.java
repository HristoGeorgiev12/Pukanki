package com.pukanki.tv;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class ProfileStore {
    private static final String PREF_NAME = "pukanki_profiles_v1";
    private static final String KEY_PROFILES = "profiles_list";
    private static final String KEY_ACTIVE_ID = "active_profile_id";
    private static final String KEY_FILTERS_PREFIX = "profile_filters_";
    public static final String DEFAULT_ID = "default";

    private static final int[] AVATAR_COLORS = new int[]{
        0xFF7C3AED, 0xFF059669, 0xFFDC2626, 0xFF2563EB, 0xFFD97706, 0xFFDB2777
    };

    public static class Profile {
        public String id;
        public String name;
        public int color;

        public Profile(String id, String name, int color) {
            this.id = id;
            this.name = name;
            this.color = color;
        }
    }

    private static SharedPreferences prefs(Context ctx) {
        return ctx.getApplicationContext().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    public static synchronized List<Profile> getProfiles(Context ctx) {
        List<Profile> list = new ArrayList<>();
        String raw = prefs(ctx).getString(KEY_PROFILES, "");
        if (!raw.isEmpty()) {
            try {
                JSONArray arr = new JSONArray(raw);
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject o = arr.optJSONObject(i);
                    if (o != null) {
                        list.add(new Profile(
                            o.optString("id", DEFAULT_ID),
                            o.optString("name", "Основен"),
                            o.optInt("color", AVATAR_COLORS[i % AVATAR_COLORS.length])
                        ));
                    }
                }
            } catch (Exception ignored) {}
        }
        if (list.isEmpty()) {
            list.add(new Profile(DEFAULT_ID, "Основен", AVATAR_COLORS[0]));
            saveProfiles(ctx, list);
        }
        return list;
    }

    public static synchronized String getActiveProfileId(Context ctx) {
        String id = prefs(ctx).getString(KEY_ACTIVE_ID, DEFAULT_ID);
        List<Profile> list = getProfiles(ctx);
        for (Profile p : list) {
            if (p.id.equals(id)) return id;
        }
        return list.get(0).id;
    }

    public static synchronized Profile getActiveProfile(Context ctx) {
        String id = getActiveProfileId(ctx);
        for (Profile p : getProfiles(ctx)) {
            if (p.id.equals(id)) return p;
        }
        return getProfiles(ctx).get(0);
    }

    public static synchronized void setActiveProfileId(Context ctx, String profileId) {
        prefs(ctx).edit().putString(KEY_ACTIVE_ID, profileId).apply();
    }

    public static synchronized Profile createProfile(Context ctx, String name) {
        List<Profile> list = getProfiles(ctx);
        String cleanName = (name != null && !name.trim().isEmpty()) ? name.trim() : ("Профил " + (list.size() + 1));
        String id = "p_" + UUID.randomUUID().toString().substring(0, 8);
        int color = AVATAR_COLORS[list.size() % AVATAR_COLORS.length];
        Profile p = new Profile(id, cleanName, color);
        list.add(p);
        saveProfiles(ctx, list);
        setActiveProfileId(ctx, id);
        return p;
    }

    public static synchronized void deleteProfile(Context ctx, String profileId) {
        if (DEFAULT_ID.equals(profileId)) return;
        List<Profile> list = getProfiles(ctx);
        for (int i = list.size() - 1; i >= 0; i--) {
            if (profileId.equals(list.get(i).id)) {
                list.remove(i);
            }
        }
        saveProfiles(ctx, list);
        prefs(ctx).edit().remove(KEY_FILTERS_PREFIX + profileId).apply();
        if (profileId.equals(getActiveProfileId(ctx))) {
            setActiveProfileId(ctx, list.get(0).id);
        }
    }

    public static synchronized void saveFiltersJson(Context ctx, String profileId, JSONObject filtersObj) {
        if (profileId == null || filtersObj == null) return;
        prefs(ctx).edit().putString(KEY_FILTERS_PREFIX + profileId, filtersObj.toString()).apply();
    }

    public static synchronized JSONObject loadFiltersJson(Context ctx, String profileId) {
        if (profileId == null) return null;
        String raw = prefs(ctx).getString(KEY_FILTERS_PREFIX + profileId, "");
        if (raw.isEmpty()) return null;
        try {
            return new JSONObject(raw);
        } catch (Exception e) {
            return null;
        }
    }

    private static void saveProfiles(Context ctx, List<Profile> list) {
        JSONArray arr = new JSONArray();
        for (Profile p : list) {
            try {
                JSONObject o = new JSONObject();
                o.put("id", p.id);
                o.put("name", p.name);
                o.put("color", p.color);
                arr.put(o);
            } catch (Exception ignored) {}
        }
        prefs(ctx).edit().putString(KEY_PROFILES, arr.toString()).apply();
    }
}
