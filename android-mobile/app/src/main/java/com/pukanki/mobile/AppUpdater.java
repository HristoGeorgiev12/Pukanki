package com.pukanki.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class AppUpdater {
    private static final String RELEASES_API = "https://api.github.com/repos/HristoGeorgiev12/Pukanki/releases?per_page=12";
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    public static void checkForUpdate(final Activity activity, final String tagPrefix, final String apkAssetName) {
        if (activity == null || activity.isFinishing()) return;
        final String currentVer = getCurrentVersionName(activity);

        executor.execute(() -> {
            HttpURLConnection conn = null;
            try {
                conn = (HttpURLConnection) new URL(RELEASES_API).openConnection();
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(10000);
                conn.setRequestProperty("Accept", "application/vnd.github+json");
                conn.setRequestProperty("User-Agent", "PukankiUpdater/1.0");
                if (conn.getResponseCode() != 200) return;

                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "UTF-8"));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) sb.append(line);
                br.close();

                JSONArray releases = new JSONArray(sb.toString());
                String bestVer = null;
                String bestUrl = null;

                for (int i = 0; i < releases.length(); i++) {
                    JSONObject rel = releases.optJSONObject(i);
                    if (rel == null) continue;
                    String tag = rel.optString("tag_name", "");
                    if (!tag.startsWith(tagPrefix)) continue;

                    String ver = tag.substring(tagPrefix.length()).trim();
                    JSONArray assets = rel.optJSONArray("assets");
                    String apkUrl = null;
                    if (assets != null) {
                        for (int j = 0; j < assets.length(); j++) {
                            JSONObject a = assets.optJSONObject(j);
                            if (a != null && a.optString("name", "").toLowerCase().endsWith(".apk")) {
                                apkUrl = a.optString("browser_download_url", "");
                                break;
                            }
                        }
                    }
                    if (apkUrl != null && !apkUrl.isEmpty()) {
                        if (bestVer == null || compareVersions(ver, bestVer) > 0) {
                            bestVer = ver;
                            bestUrl = apkUrl;
                        }
                    }
                }

                if (bestVer != null && bestUrl != null && compareVersions(bestVer, currentVer) > 0) {
                    final String fVer = bestVer;
                    final String fUrl = bestUrl;
                    mainHandler.post(() -> {
                        if (!activity.isFinishing()) {
                            showUpdateDialog(activity, fVer, fUrl);
                        }
                    });
                }
            } catch (Exception ignored) {
            } finally {
                if (conn != null) conn.disconnect();
            }
        });
    }

    private static void showUpdateDialog(Activity activity, String newVersion, String apkUrl) {
        new AlertDialog.Builder(activity)
            .setTitle("Налична е нова версия v" + newVersion)
            .setMessage("Искаш ли да изтеглиш и инсталираш обновлението директно?")
            .setPositiveButton("Обнови сега", (d, w) -> downloadAndInstall(activity, apkUrl))
            .setNegativeButton("По-късно", null)
            .show();
    }

    private static void downloadAndInstall(Activity activity, String apkUrl) {
        Toast.makeText(activity, "Сваляне на новата версия...", Toast.LENGTH_LONG).show();
        executor.execute(() -> {
            HttpURLConnection conn = null;
            try {
                File dir = new File(activity.getCacheDir(), "updates");
                if (!dir.exists()) dir.mkdirs();
                File outFile = new File(dir, "update.apk");

                conn = openFollowingRedirects(apkUrl);
                if (conn.getResponseCode() != 200) {
                    throw new Exception("HTTP " + conn.getResponseCode());
                }

                try (InputStream in = conn.getInputStream();
                     FileOutputStream out = new FileOutputStream(outFile)) {
                    byte[] buf = new byte[16384];
                    int n;
                    while ((n = in.read(buf)) > 0) {
                        out.write(buf, 0, n);
                    }
                }

                mainHandler.post(() -> {
                    if (activity.isFinishing()) return;
                    try {
                        Uri uri;
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                            uri = FileProvider.getUriForFile(
                                activity,
                                activity.getPackageName() + ".fileprovider",
                                outFile
                            );
                        } else {
                            uri = Uri.fromFile(outFile);
                        }
                        Intent intent = new Intent(Intent.ACTION_VIEW);
                        intent.setDataAndType(uri, "application/vnd.android.package-archive");
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        activity.startActivity(intent);
                    } catch (Exception e) {
                        Toast.makeText(activity, "Грешка при инсталация: " + e.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    if (!activity.isFinishing()) {
                        Toast.makeText(activity, "Грешка при сваляне: " + e.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
            } finally {
                if (conn != null) conn.disconnect();
            }
        });
    }

    private static HttpURLConnection openFollowingRedirects(String urlStr) throws Exception {
        String current = urlStr;
        for (int i = 0; i < 6; i++) {
            HttpURLConnection c = (HttpURLConnection) new URL(current).openConnection();
            c.setInstanceFollowRedirects(false);
            c.setConnectTimeout(12000);
            c.setReadTimeout(30000);
            c.setRequestProperty("User-Agent", "PukankiUpdater/1.0");
            int code = c.getResponseCode();
            if (code == HttpURLConnection.HTTP_MOVED_PERM
                || code == HttpURLConnection.HTTP_MOVED_TEMP
                || code == HttpURLConnection.HTTP_SEE_OTHER
                || code == 307 || code == 308) {
                String loc = c.getHeaderField("Location");
                c.disconnect();
                if (loc == null || loc.isEmpty()) break;
                current = loc;
            } else {
                return c;
            }
        }
        throw new Exception("Too many redirects");
    }

    private static String getCurrentVersionName(Activity activity) {
        try {
            PackageInfo pi = activity.getPackageManager().getPackageInfo(activity.getPackageName(), 0);
            return pi.versionName != null ? pi.versionName : "0.0.0";
        } catch (Exception e) {
            return "0.0.0";
        }
    }

    private static int compareVersions(String a, String b) {
        String[] pa = a.replaceAll("[^0-9.]", "").split("\\.");
        String[] pb = b.replaceAll("[^0-9.]", "").split("\\.");
        int len = Math.max(pa.length, pb.length);
        for (int i = 0; i < len; i++) {
            int va = i < pa.length && !pa[i].isEmpty() ? Integer.parseInt(pa[i]) : 0;
            int vb = i < pb.length && !pb[i].isEmpty() ? Integer.parseInt(pb[i]) : 0;
            if (va != vb) return Integer.compare(va, vb);
        }
        return 0;
    }
}
