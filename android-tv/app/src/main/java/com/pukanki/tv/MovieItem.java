package com.pukanki.tv;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

public class MovieItem {
    public String title;
    public String originalTitle;
    public int year;
    public double rating;
    public int duration;
    public String posterUrl;
    public String backdropUrl;
    public String overview;
    public boolean isBgAudio;
    public boolean isSubtitled;
    public String type; // "m" or "s"
    public List<String> genres = new ArrayList<>();
    public List<PlayerSource> sources = new ArrayList<>();
    public long resumePositionMs = 0L;
    public long resumeDurationMs = 0L;

    public String getHistoryKey() {
        return (title != null ? title.trim().toLowerCase() : "") + "|" + year;
    }

    public JSONObject toJsonObject() {
        JSONObject obj = new JSONObject();
        try {
            obj.put("t", title != null ? title : "");
            obj.put("ot", originalTitle != null ? originalTitle : "");
            obj.put("y", year);
            obj.put("r", rating);
            obj.put("d", duration);
            obj.put("p", posterUrl != null ? posterUrl : "");
            obj.put("b", backdropUrl != null ? backdropUrl : "");
            obj.put("o", overview != null ? overview : "");
            obj.put("bg", isBgAudio ? 1 : 0);
            obj.put("sub", isSubtitled ? 1 : 0);
            obj.put("tp", type != null ? type : "m");
            JSONArray gArr = new JSONArray();
            for (String g : genres) gArr.put(g);
            obj.put("g", gArr);
            JSONArray sArr = new JSONArray();
            for (PlayerSource s : sources) {
                JSONArray row = new JSONArray();
                row.put(s.name);
                row.put(s.group);
                row.put(s.url);
                sArr.put(row);
            }
            obj.put("s", sArr);
        } catch (Exception ignored) {}
        return obj;
    }

    public static class PlayerSource {
        public String name;
        public String group;
        public String url;

        public PlayerSource(String name, String group, String url) {
            this.name = name;
            this.group = group;
            this.url = url;
        }
    }

    public static MovieItem fromJson(JSONObject obj) {
        MovieItem item = new MovieItem();
        item.title = obj.optString("t", "");
        item.originalTitle = obj.optString("ot", "");
        item.year = obj.optInt("y", 0);
        item.rating = obj.optDouble("r", 0.0);
        item.duration = obj.optInt("d", 0);
        item.posterUrl = obj.optString("p", "");
        item.backdropUrl = obj.optString("b", "");
        item.overview = obj.optString("o", "");
        item.isBgAudio = obj.optInt("bg", 0) == 1;
        item.isSubtitled = obj.optInt("sub", 0) == 1;
        item.type = obj.optString("tp", "m");

        JSONArray gArr = obj.optJSONArray("g");
        if (gArr != null) {
            for (int i = 0; i < gArr.length(); i++) {
                String g = gArr.optString(i, "").trim();
                if (!g.isEmpty()) item.genres.add(g);
            }
        }

        JSONArray sArr = obj.optJSONArray("s");
        if (sArr != null) {
            for (int i = 0; i < sArr.length(); i++) {
                JSONArray pair = sArr.optJSONArray(i);
                if (pair != null && pair.length() >= 3) {
                    item.sources.add(new PlayerSource(
                        pair.optString(0, "Плеър"),
                        pair.optString(1, "bg"),
                        pair.optString(2, "")
                    ));
                }
            }
        }
        return item;
    }

    public static String sourcesToJson(List<PlayerSource> list) {
        JSONArray arr = new JSONArray();
        if (list != null) {
            for (PlayerSource s : list) {
                JSONArray row = new JSONArray();
                row.put(s.name);
                row.put(s.group);
                row.put(s.url);
                arr.put(row);
            }
        }
        return arr.toString();
    }

    public static List<PlayerSource> sourcesFromJson(String jsonStr) {
        List<PlayerSource> out = new ArrayList<>();
        if (jsonStr == null || jsonStr.isEmpty()) return out;
        try {
            JSONArray arr = new JSONArray(jsonStr);
            for (int i = 0; i < arr.length(); i++) {
                JSONArray row = arr.optJSONArray(i);
                if (row != null && row.length() >= 3) {
                    out.add(new PlayerSource(
                        row.optString(0, "Плеър"),
                        row.optString(1, "bg"),
                        row.optString(2, "")
                    ));
                }
            }
        } catch (Exception ignored) {}
        return out;
    }
}
