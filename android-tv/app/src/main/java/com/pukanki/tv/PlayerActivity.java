package com.pukanki.tv;

import android.annotation.SuppressLint;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.datasource.DefaultHttpDataSource;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory;
import androidx.media3.ui.PlayerView;

import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class PlayerActivity extends AppCompatActivity {
    private static final long SEEK_STEP_MS = 15000L;
    private static final long SNIFF_TIMEOUT_MS = 11000L;
    private static final String DESKTOP_UA =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

    private WebView snifferWebView;
    private PlayerView exoPlayerView;
    private LinearLayout playerTopHud, loadingOverlay;
    private TextView hudMovieTitle, hudSourceInfo, seekFeedbackText, loadingStatusText, loadingSubText;
    private Button hudNextSourceBtn, hudWebFallbackBtn, loadingNextBtn;

    private ExoPlayer exoPlayer;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private String movieTitle = "";
    private List<MovieItem.PlayerSource> sources;
    private int currentIndex = 0;

    private volatile boolean streamCaptured = false;
    private boolean isWebFallbackMode = false;
    private int attemptToken = 0;

    private final Runnable hideFeedbackRunnable = () -> {
        if (seekFeedbackText != null) seekFeedbackText.setVisibility(View.GONE);
    };
    private final Runnable hideHudRunnable = () -> {
        if (playerTopHud != null && !hudNextSourceBtn.hasFocus() && !hudWebFallbackBtn.hasFocus()) {
            playerTopHud.setVisibility(View.GONE);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        hideSystemUI();
        setContentView(R.layout.activity_player);

        snifferWebView = findViewById(R.id.snifferWebView);
        exoPlayerView = findViewById(R.id.exoPlayerView);
        playerTopHud = findViewById(R.id.playerTopHud);
        loadingOverlay = findViewById(R.id.loadingOverlay);
        hudMovieTitle = findViewById(R.id.hudMovieTitle);
        hudSourceInfo = findViewById(R.id.hudSourceInfo);
        seekFeedbackText = findViewById(R.id.seekFeedbackText);
        loadingStatusText = findViewById(R.id.loadingStatusText);
        loadingSubText = findViewById(R.id.loadingSubText);
        hudNextSourceBtn = findViewById(R.id.hudNextSourceBtn);
        hudWebFallbackBtn = findViewById(R.id.hudWebFallbackBtn);
        loadingNextBtn = findViewById(R.id.loadingNextBtn);

        movieTitle = getIntent().getStringExtra("title");
        if (movieTitle == null) movieTitle = "Пуканки TV";
        sources = MovieItem.sourcesFromJson(getIntent().getStringExtra("sources_json"));
        currentIndex = getIntent().getIntExtra("start_index", 0);
        if (currentIndex < 0 || currentIndex >= sources.size()) currentIndex = 0;

        hudMovieTitle.setText(movieTitle);

        hudNextSourceBtn.setOnClickListener(v -> switchToNextSource());
        loadingNextBtn.setOnClickListener(v -> switchToNextSource());
        hudWebFallbackBtn.setOnClickListener(v -> enterWebFallbackMode());

        setupSnifferWebView();

        if (sources == null || sources.isEmpty()) {
            Toast.makeText(this, "Няма плеъри.", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }
        loadSource(currentIndex);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupSnifferWebView() {
        WebSettings ws = snifferWebView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        ws.setSupportMultipleWindows(false);
        ws.setJavaScriptCanOpenWindowsAutomatically(false);
        ws.setUseWideViewPort(true);
        ws.setLoadWithOverviewMode(true);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        ws.setUserAgentString(DESKTOP_UA);

        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(snifferWebView, true);

        snifferWebView.setWebChromeClient(new WebChromeClient());
        snifferWebView.setWebViewClient(new WebViewClient() {
            @Nullable
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (!streamCaptured && !isWebFallbackMode && request != null && request.getUrl() != null) {
                    String reqUrl = request.getUrl().toString();
                    if (isLikelyVideoStream(reqUrl)) {
                        streamCaptured = true;
                        final int token = attemptToken;
                        final Map<String, String> headers = new HashMap<>();
                        Map<String, String> reqHeaders = request.getRequestHeaders();
                        if (reqHeaders != null) {
                            for (Map.Entry<String, String> e : reqHeaders.entrySet()) {
                                if (e.getKey() != null && e.getValue() != null) {
                                    String k = e.getKey();
                                    if (k.equalsIgnoreCase("Referer") || k.equalsIgnoreCase("Origin") || k.equalsIgnoreCase("User-Agent")) {
                                        headers.put(k, e.getValue());
                                    }
                                }
                            }
                        }
                        if (!headers.containsKey("User-Agent")) {
                            headers.put("User-Agent", DESKTOP_UA);
                        }
                        String cookie = CookieManager.getInstance().getCookie(reqUrl);
                        if (cookie != null && !cookie.isEmpty()) {
                            headers.put("Cookie", cookie);
                        }
                        handler.post(() -> {
                            if (token == attemptToken && !isFinishing()) {
                                startExoPlayer(reqUrl, headers);
                            }
                        });
                    }
                }
                return super.shouldInterceptRequest(view, request);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && request != null && request.isForMainFrame()) {
                    Uri uri = request.getUrl();
                    if (uri != null && isAdDomain(uri.toString())) {
                        return true;
                    }
                }
                return false;
            }
        });
    }

    private boolean isAdDomain(String url) {
        String low = url.toLowerCase(Locale.ROOT);
        return low.contains("doubleclick") || low.contains("googlesyndication")
            || low.contains("popads") || low.contains("popcash") || low.contains("adsterra")
            || low.contains("exoclick") || low.contains("juicyads") || low.contains("trafficjunky")
            || low.contains("bet365") || low.contains("1xbet") || low.contains("propellerads")
            || low.contains("onclickalgo") || low.contains("acscdn");
    }

    private boolean isLikelyVideoStream(String url) {
        if (url == null || url.length() < 12) return false;
        String low = url.toLowerCase(Locale.ROOT);
        if (isAdDomain(low)) return false;
        if (low.contains("analytics") || low.contains("pixel") || low.contains("tracker")
            || low.contains("vast") || low.contains("ima3") || low.contains("favicon")
            || low.endsWith(".js") || low.endsWith(".css") || low.endsWith(".png")
            || low.endsWith(".jpg") || low.endsWith(".jpeg") || low.endsWith(".webp")
            || low.endsWith(".svg") || low.endsWith(".woff2") || low.endsWith(".vtt")) {
            return false;
        }
        // Known direct video patterns across Streamtape, VOE, Vidon, OK.ru, Filemoon, Uqload, Vsembed
        if (low.contains("streamtape.com/get_video") || low.contains("tapecontent.net")) return true;
        if (low.contains(".m3u8")) return true;
        if (low.contains("master.txt") && (low.contains("voe") || low.contains("cdn") || low.contains("hls"))) return true;
        if (low.contains(".mp4") && !low.contains(".mp4.jpg") && !low.contains("thumb") && !low.contains("preview")) return true;
        if ((low.contains("okcdn.ru") || low.contains("mycdn.me")) && (low.contains("ct=0") || low.contains("type=") || low.contains("/video"))) return true;
        return false;
    }

    private void loadSource(int index) {
        handler.removeCallbacksAndMessages(null);
        releaseExoPlayer();

        currentIndex = index;
        attemptToken++;
        final int token = attemptToken;
        streamCaptured = false;
        isWebFallbackMode = false;

        MovieItem.PlayerSource src = sources.get(currentIndex);
        exoPlayerView.setVisibility(View.GONE);
        snifferWebView.setVisibility(View.INVISIBLE);
        playerTopHud.setVisibility(View.GONE);
        loadingOverlay.setVisibility(View.VISIBLE);
        loadingStatusText.setText("Зареждане: " + src.name + " (" + (currentIndex + 1) + "/" + sources.size() + ")");
        loadingSubText.setText("Прихващане на директен видео поток за ExoPlayer...");
        loadingNextBtn.setVisibility(sources.size() > 1 ? View.VISIBLE : View.GONE);

        String embedUrl = src.url;
        if (embedUrl.toLowerCase(Locale.ROOT).contains("vidon.to/")) {
            loadVidonInSniffer(embedUrl);
        } else {
            Map<String, String> initHeaders = new HashMap<>();
            initHeaders.put("Referer", embedUrl);
            snifferWebView.loadUrl(embedUrl, initHeaders);
        }

        // Auto-tap center of hidden WebView at 1.4s and 3.2s to trigger click-to-play hosts (Streamtape, Filemoon, VOE)
        handler.postDelayed(() -> {
            if (token == attemptToken && !streamCaptured && !isWebFallbackMode) {
                tapWebViewCenter();
            }
        }, 1400);

        handler.postDelayed(() -> {
            if (token == attemptToken && !streamCaptured && !isWebFallbackMode) {
                tapWebViewCenter();
            }
        }, 3200);

        // If no direct stream was captured after timeout, switch smoothly to Web Fallback mode
        handler.postDelayed(() -> {
            if (token == attemptToken && !streamCaptured && !isWebFallbackMode && !isFinishing()) {
                enterWebFallbackMode();
            }
        }, SNIFF_TIMEOUT_MS);
    }

    private void loadVidonInSniffer(String embedUrl) {
        Matcher m = Pattern.compile("vidon\\.to/(?:e|embed-)?([A-Za-z0-9]+)").matcher(embedUrl);
        if (m.find()) {
            String code = m.group(1);
            String html = "<html><body style='background:#000' onload='document.forms[0].submit()'>"
                + "<form method='POST' action='https://vidon.to/dl'>"
                + "<input type='hidden' name='op' value='embed'/>"
                + "<input type='hidden' name='file_code' value='" + code + "'/>"
                + "<input type='hidden' name='auto' value='1'/>"
                + "</form></body></html>";
            snifferWebView.loadDataWithBaseURL("https://vidon.to/", html, "text/html", "UTF-8", null);
        } else {
            snifferWebView.loadUrl(embedUrl);
        }
    }

    private void startExoPlayer(String streamUrl, Map<String, String> headers) {
        // Stop sniffer WebView immediately to save TV RAM/CPU and kill any background scripts
        snifferWebView.stopLoading();
        snifferWebView.loadUrl("about:blank");
        snifferWebView.setVisibility(View.GONE);

        loadingOverlay.setVisibility(View.GONE);
        exoPlayerView.setVisibility(View.VISIBLE);

        MovieItem.PlayerSource src = sources.get(currentIndex);
        hudSourceInfo.setText("Нативен ExoPlayer • " + src.name + " (" + (currentIndex + 1) + "/" + sources.size() + ") • OK=Пауза | ◀▶=±15с | ▲=Меню");

        DefaultHttpDataSource.Factory httpFactory = new DefaultHttpDataSource.Factory()
            .setUserAgent(headers.containsKey("User-Agent") ? headers.get("User-Agent") : DESKTOP_UA)
            .setAllowCrossProtocolRedirects(true)
            .setConnectTimeoutMs(12000)
            .setReadTimeoutMs(15000);

        Map<String, String> extraHeaders = new HashMap<>(headers);
        extraHeaders.remove("User-Agent");
        if (!extraHeaders.isEmpty()) {
            httpFactory.setDefaultRequestProperties(extraHeaders);
        }

        exoPlayer = new ExoPlayer.Builder(this)
            .setMediaSourceFactory(new DefaultMediaSourceFactory(httpFactory))
            .build();

        exoPlayerView.setPlayer(exoPlayer);
        exoPlayer.addListener(new Player.Listener() {
            @Override
            public void onPlayerError(PlaybackException error) {
                Toast.makeText(PlayerActivity.this, "Потокът отказа (" + src.name + "), пробвам резервен режим...", Toast.LENGTH_SHORT).show();
                enterWebFallbackMode();
            }
        });

        MediaItem mediaItem = MediaItem.fromUri(Uri.parse(streamUrl));
        exoPlayer.setMediaItem(mediaItem);
        exoPlayer.prepare();
        exoPlayer.setPlayWhenReady(true);

        showTopHudTemporarily();
        showCenterFeedback("▶ " + src.name);
    }

    private void enterWebFallbackMode() {
        releaseExoPlayer();
        isWebFallbackMode = true;
        loadingOverlay.setVisibility(View.GONE);
        exoPlayerView.setVisibility(View.GONE);
        snifferWebView.setVisibility(View.VISIBLE);
        snifferWebView.requestFocus();

        MovieItem.PlayerSource src = sources.get(currentIndex);
        String currentWebUrl = snifferWebView.getUrl();
        if (currentWebUrl == null || currentWebUrl.equals("about:blank")) {
            snifferWebView.loadUrl(src.url);
        }
        hudSourceInfo.setText("Уеб режим • " + src.name + " • OK=Докосни центъра | ▲=Следващ плеър");
        showTopHudTemporarily();
        Toast.makeText(this, "Уеб режим (" + src.name + ") — натисни OK за пускане/пауза", Toast.LENGTH_SHORT).show();
    }

    private void switchToNextSource() {
        if (sources == null || sources.size() <= 1) {
            Toast.makeText(this, "Няма друг наличен плеър за този филм.", Toast.LENGTH_SHORT).show();
            return;
        }
        int next = (currentIndex + 1) % sources.size();
        loadSource(next);
    }

    private void tapWebViewCenter() {
        if (snifferWebView == null) return;
        int w = snifferWebView.getWidth();
        int h = snifferWebView.getHeight();
        if (w <= 0 || h <= 0) return;
        float x = w * 0.5f;
        float y = h * 0.5f;
        long t = SystemClock.uptimeMillis();
        MotionEvent down = MotionEvent.obtain(t, t, MotionEvent.ACTION_DOWN, x, y, 0);
        MotionEvent up = MotionEvent.obtain(t, t + 50, MotionEvent.ACTION_UP, x, y, 0);
        snifferWebView.dispatchTouchEvent(down);
        snifferWebView.dispatchTouchEvent(up);
        down.recycle();
        up.recycle();
    }

    private void showCenterFeedback(String text) {
        handler.removeCallbacks(hideFeedbackRunnable);
        seekFeedbackText.setText(text);
        seekFeedbackText.setVisibility(View.VISIBLE);
        handler.postDelayed(hideFeedbackRunnable, 1300);
    }

    private void showTopHudTemporarily() {
        handler.removeCallbacks(hideHudRunnable);
        playerTopHud.setVisibility(View.VISIBLE);
        handler.postDelayed(hideHudRunnable, 4000);
    }

    private String formatTime(long ms) {
        if (ms < 0) ms = 0;
        long totalSec = ms / 1000;
        long hrs = totalSec / 3600;
        long mins = (totalSec % 3600) / 60;
        long secs = totalSec % 60;
        if (hrs > 0) {
            return String.format(Locale.US, "%d:%02d:%02d", hrs, mins, secs);
        }
        return String.format(Locale.US, "%02d:%02d", mins, secs);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            int code = event.getKeyCode();

            if (code == KeyEvent.KEYCODE_BACK) {
                if (playerTopHud.getVisibility() == View.VISIBLE && (hudNextSourceBtn.hasFocus() || hudWebFallbackBtn.hasFocus())) {
                    playerTopHud.setVisibility(View.GONE);
                    exoPlayerView.requestFocus();
                    return true;
                }
                finish();
                return true;
            }

            // If user is navigating the top HUD buttons, let Android handle Left/Right/OK on those buttons
            if (playerTopHud.getVisibility() == View.VISIBLE && (hudNextSourceBtn.hasFocus() || hudWebFallbackBtn.hasFocus())) {
                if (code == KeyEvent.KEYCODE_DPAD_DOWN) {
                    playerTopHud.setVisibility(View.GONE);
                    exoPlayerView.requestFocus();
                    return true;
                }
                return super.dispatchKeyEvent(event);
            }

            // If loading overlay is visible, let loadingNextBtn handle clicks
            if (loadingOverlay.getVisibility() == View.VISIBLE) {
                return super.dispatchKeyEvent(event);
            }

            // UP arrow opens top quick HUD (Next Player / Web Mode)
            if (code == KeyEvent.KEYCODE_DPAD_UP) {
                playerTopHud.setVisibility(View.VISIBLE);
                hudNextSourceBtn.requestFocus();
                return true;
            }

            // Native ExoPlayer Remote Control
            if (exoPlayer != null && !isWebFallbackMode) {
                if (code == KeyEvent.KEYCODE_DPAD_CENTER || code == KeyEvent.KEYCODE_ENTER || code == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE || code == KeyEvent.KEYCODE_SPACE) {
                    if (exoPlayer.isPlaying()) {
                        exoPlayer.pause();
                        showCenterFeedback("⏸ Пауза (" + formatTime(exoPlayer.getCurrentPosition()) + ")");
                    } else {
                        exoPlayer.play();
                        showCenterFeedback("▶ Възпроизвеждане");
                    }
                    exoPlayerView.showController();
                    showTopHudTemporarily();
                    return true;
                }
                if (code == KeyEvent.KEYCODE_DPAD_RIGHT || code == KeyEvent.KEYCODE_MEDIA_FAST_FORWARD) {
                    long dur = exoPlayer.getDuration();
                    long target = exoPlayer.getCurrentPosition() + SEEK_STEP_MS;
                    if (dur > 0 && target > dur) target = dur;
                    exoPlayer.seekTo(target);
                    exoPlayerView.showController();
                    showCenterFeedback("⏩ +15 сек (" + formatTime(target) + ")");
                    return true;
                }
                if (code == KeyEvent.KEYCODE_DPAD_LEFT || code == KeyEvent.KEYCODE_MEDIA_REWIND) {
                    long target = Math.max(0, exoPlayer.getCurrentPosition() - SEEK_STEP_MS);
                    exoPlayer.seekTo(target);
                    exoPlayerView.showController();
                    showCenterFeedback("⏪ -15 сек (" + formatTime(target) + ")");
                    return true;
                }
                if (code == KeyEvent.KEYCODE_DPAD_DOWN) {
                    exoPlayerView.showController();
                    showTopHudTemporarily();
                    return true;
                }
            } else if (isWebFallbackMode) {
                if (code == KeyEvent.KEYCODE_DPAD_CENTER || code == KeyEvent.KEYCODE_ENTER || code == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE) {
                    tapWebViewCenter();
                    showCenterFeedback("⏯ Пусни / Пауза");
                    return true;
                }
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private void releaseExoPlayer() {
        if (exoPlayer != null) {
            exoPlayer.release();
            exoPlayer = null;
        }
        if (exoPlayerView != null) {
            exoPlayerView.setPlayer(null);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (exoPlayer != null) exoPlayer.pause();
        if (snifferWebView != null) snifferWebView.onPause();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        releaseExoPlayer();
        if (snifferWebView != null) {
            snifferWebView.stopLoading();
            snifferWebView.destroy();
        }
        super.onDestroy();
    }

    private void hideSystemUI() {
        View decorView = getWindow().getDecorView();
        decorView.setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );
    }
}
