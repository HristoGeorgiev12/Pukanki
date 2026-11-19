package com.pukanki.mobile;

import android.annotation.SuppressLint;
import android.content.Intent;
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

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.datasource.DefaultHttpDataSource;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory;
import androidx.media3.ui.PlayerView;
import androidx.mediarouter.app.MediaRouteButton;

import com.google.android.gms.cast.MediaInfo;
import com.google.android.gms.cast.MediaLoadRequestData;
import com.google.android.gms.cast.MediaMetadata;
import com.google.android.gms.cast.framework.CastButtonFactory;
import com.google.android.gms.cast.framework.CastContext;
import com.google.android.gms.cast.framework.CastSession;
import com.google.android.gms.cast.framework.SessionManager;
import com.google.android.gms.cast.framework.SessionManagerListener;
import com.google.android.gms.cast.framework.media.RemoteMediaClient;

import java.io.ByteArrayInputStream;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class PlayerActivity extends AppCompatActivity {
    private static final long SEEK_STEP_MS = 15000L;
    private static final long SNIFF_TIMEOUT_MS = 12000L;
    private static final String DESKTOP_UA =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

    private WebView snifferWebView;
    private PlayerView exoPlayerView;
    private LinearLayout playerTopHud, loadingOverlay;
    private TextView hudMovieTitle, hudSourceInfo, loadingStatusText;
    private Button hudBackBtn, hudNextSourceBtn, loadingNextBtn;
    private MediaRouteButton mediaRouteButton;

    private ExoPlayer exoPlayer;
    private CastContext castContext;
    private SessionManager castSessionManager;
    private CastSession castSession;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private String movieTitle = "";
    private List<MovieItem.PlayerSource> sources;
    private int currentIndex = 0;

    private volatile boolean streamCaptured = false;
    private volatile String currentEmbedHost = "";
    private volatile String currentEmbedUrl = "";
    private volatile String currentVideoId = "";
    private volatile boolean isVoeSource = false;
    private volatile String currentStreamUrl = "";
    private boolean isWebFallbackMode = false;
    private int attemptToken = 0;

    private final Runnable hideHudRunnable = () -> {
        if (playerTopHud != null) {
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
        loadingStatusText = findViewById(R.id.loadingStatusText);
        hudBackBtn = findViewById(R.id.hudBackBtn);
        mediaRouteButton = findViewById(R.id.mediaRouteButton);
        hudNextSourceBtn = findViewById(R.id.hudNextSourceBtn);
        loadingNextBtn = findViewById(R.id.loadingNextBtn);

        movieTitle = getIntent().getStringExtra("title");
        if (movieTitle == null) movieTitle = "Пуканки";
        sources = MovieItem.sourcesFromJson(getIntent().getStringExtra("sources_json"));
        currentIndex = getIntent().getIntExtra("start_index", 0);
        if (currentIndex < 0 || currentIndex >= sources.size()) currentIndex = 0;

        hudMovieTitle.setText(movieTitle);

        hudBackBtn.setOnClickListener(v -> finish());
        hudNextSourceBtn.setOnClickListener(v -> switchToNextSource());
        loadingNextBtn.setOnClickListener(v -> switchToNextSource());

        setupGoogleCast();

        exoPlayerView.setControllerVisibilityListener((PlayerView.ControllerVisibilityListener) visibility -> {
            if (playerTopHud != null) {
                playerTopHud.setVisibility(visibility);
            }
        });

        setupSnifferWebView();

        if (sources == null || sources.isEmpty()) {
            Toast.makeText(this, "Няма плеъри.", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }
        loadSource(currentIndex);
    }

    private final SessionManagerListener<CastSession> castSessionListener = new SessionManagerListener<CastSession>() {
        @Override public void onSessionStarting(@NonNull CastSession session) {}
        @Override public void onSessionStarted(@NonNull CastSession session, @NonNull String sessionId) {
            castSession = session;
            loadCurrentStreamOnCast();
        }
        @Override public void onSessionStartFailed(@NonNull CastSession session, int error) {
            Toast.makeText(PlayerActivity.this, "Неуспешно свързване с Cast устройство.", Toast.LENGTH_SHORT).show();
        }
        @Override public void onSessionEnding(@NonNull CastSession session) {}
        @Override public void onSessionEnded(@NonNull CastSession session, int error) {
            castSession = null;
            if (exoPlayer != null) {
                exoPlayer.play();
            }
        }
        @Override public void onSessionResuming(@NonNull CastSession session, @NonNull String sessionId) {}
        @Override public void onSessionResumed(@NonNull CastSession session, boolean wasSuspended) {
            castSession = session;
            loadCurrentStreamOnCast();
        }
        @Override public void onSessionResumeFailed(@NonNull CastSession session, int error) {}
        @Override public void onSessionSuspended(@NonNull CastSession session, int reason) {}
    };

    private void setupGoogleCast() {
        try {
            castContext = CastContext.getSharedInstance(this);
            castSessionManager = castContext.getSessionManager();
            castSession = castSessionManager.getCurrentCastSession();
            if (mediaRouteButton != null) {
                CastButtonFactory.setUpMediaRouteButton(getApplicationContext(), mediaRouteButton);
            }
        } catch (Exception ignored) {
            if (mediaRouteButton != null) {
                mediaRouteButton.setVisibility(View.GONE);
            }
        }
    }

    private void loadCurrentStreamOnCast() {
        if (castSession == null || !castSession.isConnected()) return;
        if (currentStreamUrl == null || currentStreamUrl.isEmpty()) return;
        try {
            RemoteMediaClient remote = castSession.getRemoteMediaClient();
            if (remote == null) return;

            MediaMetadata metadata = new MediaMetadata(MediaMetadata.MEDIA_TYPE_MOVIE);
            metadata.putString(MediaMetadata.KEY_TITLE, movieTitle);

            String contentType = currentStreamUrl.toLowerCase(Locale.ROOT).contains(".m3u8")
                ? "application/x-mpegURL"
                : "video/mp4";

            MediaInfo mediaInfo = new MediaInfo.Builder(currentStreamUrl)
                .setStreamType(MediaInfo.STREAM_TYPE_BUFFERED)
                .setContentType(contentType)
                .setMetadata(metadata)
                .build();

            long pos = (exoPlayer != null) ? Math.max(0, exoPlayer.getCurrentPosition()) : 0;
            if (exoPlayer != null && exoPlayer.isPlaying()) {
                exoPlayer.pause();
            }

            remote.load(new MediaLoadRequestData.Builder()
                .setMediaInfo(mediaInfo)
                .setAutoplay(true)
                .setCurrentTime(pos)
                .build());

            Toast.makeText(this, "📺 Предаване към телевизора...", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "Грешка при Cast: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private String getRootDomain(String host) {
        if (host == null) return "";
        String h = host.toLowerCase(Locale.ROOT);
        String[] parts = h.split("\\.");
        if (parts.length >= 2) {
            return parts[parts.length - 2] + "." + parts[parts.length - 1];
        }
        return h;
    }

    private boolean isStreamtapeEmbed() {
        return currentEmbedHost.contains("streamtape") || currentEmbedHost.contains("streamta.pe");
    }

    private WebResourceResponse emptyBlockedResponse() {
        return new WebResourceResponse("text/plain", "utf-8", new ByteArrayInputStream(new byte[0]));
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
                if (request == null || request.getUrl() == null) {
                    return super.shouldInterceptRequest(view, request);
                }
                String reqUrl = request.getUrl().toString();
                String reqHost = request.getUrl().getHost();
                String lowHost = reqHost != null ? reqHost.toLowerCase(Locale.ROOT) : "";

                // STRICT AD BLOCKER: For Streamtape and VOE, block ALL third-party ad networks/scripts/videos completely!
                if (isStreamtapeEmbed()) {
                    boolean allowed = lowHost.contains("streamtape") || lowHost.contains("streamta.pe")
                        || lowHost.contains("tapecontent") || lowHost.contains("cloudflare")
                        || lowHost.contains("plyr");
                    if (!allowed) {
                        return emptyBlockedResponse();
                    }
                } else if (isVoeSource) {
                    if (isAdDomain(reqUrl)) {
                        return emptyBlockedResponse();
                    }
                    String lowReq = reqUrl.toLowerCase(Locale.ROOT);
                    String embedRoot = getRootDomain(currentEmbedHost);
                    boolean isSameMirror = (!embedRoot.isEmpty() && lowHost.contains(embedRoot))
                        || lowHost.contains("voe.");
                    boolean isMirrorRedirect = currentVideoId.length() >= 6 && lowReq.contains(currentVideoId.toLowerCase(Locale.ROOT));
                    boolean isCoreLib = lowHost.contains("cdnjs.cloudflare.com");
                    boolean isMediaStream = lowReq.contains(".m3u8") || lowReq.contains("master.txt")
                        || lowReq.contains(".ts") || lowReq.contains(".m4s") || lowReq.contains("/hls/");
                    if (!isSameMirror && !isMirrorRedirect && !isCoreLib && !isMediaStream) {
                        return emptyBlockedResponse();
                    }
                } else if (isAdDomain(reqUrl)) {
                    return emptyBlockedResponse();
                }

                if (!streamCaptured && !isWebFallbackMode) {
                    if (isStrictMovieStream(reqUrl, lowHost)) {
                        streamCaptured = true;
                        final int token = attemptToken;
                        final Map<String, String> headers = buildHeaders(request.getRequestHeaders(), reqUrl);
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
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (streamCaptured || isWebFallbackMode) return;
                final int token = attemptToken;
                // Extract Streamtape robotlink / ideoolink directly via DOM JS (ZERO ad clicks!)
                handler.postDelayed(() -> {
                    if (token == attemptToken && !streamCaptured && !isWebFallbackMode) {
                        extractStreamFromDom(token);
                    }
                }, 450);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && request != null && request.isForMainFrame()) {
                    Uri uri = request.getUrl();
                    if (uri != null) {
                        String urlStr = uri.toString();
                        String host = uri.getHost() != null ? uri.getHost().toLowerCase(Locale.ROOT) : "";
                        String path = uri.getPath() != null ? uri.getPath() : "";
                        String embedRoot = getRootDomain(currentEmbedHost);

                        // Allow legitimate mirror redirects (e.g. voe.sx/e/<id> -> mirror-domain/e/<id>)
                        if (currentVideoId.length() >= 6 && path.contains(currentVideoId) && !isAdDomain(urlStr)) {
                            currentEmbedHost = host;
                            currentEmbedUrl = urlStr;
                            return false;
                        }
                        // Block ANY other top-level redirect away from the video embed host!
                        if (!embedRoot.isEmpty() && !host.contains(embedRoot) && !host.contains("tapecontent")) {
                            return true;
                        }
                    }
                }
                return false;
            }
        });
    }

    private void extractStreamFromDom(final int token) {
        if (snifferWebView == null || streamCaptured) return;
        String js = "(function(){"
            + "try{"
            + "  var el = document.getElementById('robotlink') || document.getElementById('ideoolink');"
            + "  if (el && el.textContent && el.textContent.indexOf('get_video') !== -1) {"
            + "    var u = el.textContent.trim();"
            + "    if (u.indexOf('//') === 0) u = 'https:' + u;"
            + "    else if (u.indexOf('/') === 0) u = 'https:/' + u;"
            + "    if (u.indexOf('stream=1') === -1) u += '&stream=1';"
            + "    return u;"
            + "  }"
            + "  if (typeof jwplayer === 'function') {"
            + "    var p = jwplayer();"
            + "    if (p) {"
            + "      var item = p.getPlaylistItem ? p.getPlaylistItem() : null;"
            + "      if (item && item.file && item.file.indexOf('http') === 0) return item.file;"
            + "      if (item && item.sources && item.sources.length) {"
            + "        for (var i = 0; i < item.sources.length; i++) {"
            + "          if (item.sources[i].file && item.sources[i].file.indexOf('http') === 0) return item.sources[i].file;"
            + "        }"
            + "      }"
            + "      if (p.play) p.play(true);"
            + "    }"
            + "  }"
            + "  var v = document.querySelector('video');"
            + "  if (v && v.src && v.src.indexOf('http') === 0 && v.src.indexOf('blob:') !== 0) return v.src;"
            + "}catch(e){}"
            + "return '';"
            + "})()";

        snifferWebView.evaluateJavascript(js, value -> {
            if (token != attemptToken || streamCaptured || isFinishing() || value == null) return;
            String clean = value.trim();
            if (clean.startsWith("\"") && clean.endsWith("\"") && clean.length() >= 2) {
                clean = clean.substring(1, clean.length() - 1).replace("\\/", "/");
            }
            if (clean.startsWith("https://") || clean.startsWith("http://")) {
                Uri u = Uri.parse(clean);
                String h = u.getHost() != null ? u.getHost().toLowerCase(Locale.ROOT) : "";
                if (clean.contains("streamtape.com/get_video") || clean.contains("streamta.pe/get_video")
                    || isStrictMovieStream(clean, h)) {
                    streamCaptured = true;
                    Map<String, String> headers = new HashMap<>();
                    headers.put("User-Agent", DESKTOP_UA);
                    headers.put("Referer", currentEmbedUrl);
                    String cookie = CookieManager.getInstance().getCookie(clean);
                    if (cookie != null && !cookie.isEmpty()) {
                        headers.put("Cookie", cookie);
                    }
                    startExoPlayer(clean, headers);
                }
            }
        });
    }

    private Map<String, String> buildHeaders(@Nullable Map<String, String> reqHeaders, String reqUrl) {
        Map<String, String> headers = new HashMap<>();
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
        if (!headers.containsKey("Referer") && currentEmbedUrl != null && !currentEmbedUrl.isEmpty()) {
            headers.put("Referer", currentEmbedUrl);
        }
        String cookie = CookieManager.getInstance().getCookie(reqUrl);
        if (cookie != null && !cookie.isEmpty()) {
            headers.put("Cookie", cookie);
        }
        return headers;
    }

    private boolean isAdDomain(String url) {
        String low = url.toLowerCase(Locale.ROOT);
        return low.contains("doubleclick") || low.contains("googlesyndication")
            || low.contains("popads") || low.contains("popcash") || low.contains("adsterra")
            || low.contains("exoclick") || low.contains("juicyads") || low.contains("trafficjunky")
            || low.contains("bet365") || low.contains("1xbet") || low.contains("propellerads")
            || low.contains("onclickalgo") || low.contains("acscdn") || low.contains("realsrv")
            || low.contains("tsyndicate") || low.contains("stripchat") || low.contains("chaturbate")
            || low.contains("bongacams") || low.contains("livejasmin") || low.contains("magsrv")
            || low.contains("adspyglass") || low.contains("clickadu") || low.contains("hilltopads")
            || low.contains("monetag") || low.contains("vast") || low.contains("ima3")
            || low.contains("imasdk") || low.contains("ads-twitter") || low.contains("adservice")
            || low.contains("adsystem") || low.contains("vpaid") || low.contains("phruk")
            || low.contains("trafficstars") || low.contains("ero-advertising")
            || low.contains("popunder") || low.contains("commercial");
    }

    private boolean isStrictMovieStream(String url, String lowHost) {
        if (url == null || url.length() < 12) return false;
        String low = url.toLowerCase(Locale.ROOT);
        if (isAdDomain(low)) return false;
        if (low.contains("analytics") || low.contains("pixel") || low.contains("tracker")
            || low.contains("favicon") || low.endsWith(".js") || low.endsWith(".css")
            || low.endsWith(".png") || low.endsWith(".jpg") || low.endsWith(".jpeg")
            || low.endsWith(".webp") || low.endsWith(".svg") || low.endsWith(".woff2")
            || low.endsWith(".vtt") || low.contains("/ads/") || low.contains("preroll")
            || low.contains("banner") || low.contains("promo")) {
            return false;
        }

        // 1. Streamtape: ONLY official get_video or tapecontent stream! NEVER third-party .mp4!
        if (isStreamtapeEmbed()) {
            return low.contains("streamtape.com/get_video")
                || low.contains("streamta.pe/get_video")
                || lowHost.contains("tapecontent");
        }

        // 2. OK.ru: ONLY official okcdn / mycdn streams
        if (currentEmbedHost.contains("ok.ru")) {
            return (lowHost.contains("okcdn.ru") || lowHost.contains("mycdn.me"))
                && (low.contains("ct=0") || low.contains(".m3u8") || low.contains("/video"));
        }

        // 3. HLS (.m3u8) streams across VOE, Vidon, Filemoon, Byse, Dropload, Vsembed
        if (low.contains(".m3u8")) {
            return true;
        }
        if (low.contains("master.txt") && (low.contains("hls") || low.contains("voe") || low.contains("cdn"))) {
            return true;
        }

        // 4. Direct .mp4 ONLY if hosted on the SAME root domain as the embed player (e.g. Uqload/Vidon), NEVER random ad domains!
        if (low.contains(".mp4") && !low.contains("thumb") && !low.contains("preview")) {
            String embedRoot = getRootDomain(currentEmbedHost);
            if (!embedRoot.isEmpty() && lowHost.contains(embedRoot)) {
                return true;
            }
        }
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
        currentEmbedUrl = src.url != null ? src.url : "";
        Uri parsed = Uri.parse(currentEmbedUrl);
        currentEmbedHost = parsed.getHost() != null ? parsed.getHost().toLowerCase(Locale.ROOT) : "";
        isVoeSource = currentEmbedHost.contains("voe.")
            || (src.name != null && src.name.toLowerCase(Locale.ROOT).contains("voe"));
        currentVideoId = "";
        List<String> segs = parsed.getPathSegments();
        if (segs != null && !segs.isEmpty()) {
            String last = segs.get(segs.size() - 1);
            if (last != null) {
                currentVideoId = last.replace(".html", "").trim();
            }
        }

        exoPlayerView.setVisibility(View.GONE);
        snifferWebView.setVisibility(View.INVISIBLE);
        playerTopHud.setVisibility(View.GONE);
        currentStreamUrl = "";
        loadingOverlay.setVisibility(View.VISIBLE);
        loadingStatusText.setText("Зареждане: " + src.name + " (" + (currentIndex + 1) + "/" + sources.size() + ")");
        loadingNextBtn.setVisibility(sources.size() > 1 ? View.VISIBLE : View.GONE);

        if (currentEmbedUrl.toLowerCase(Locale.ROOT).contains("vidon.to/")) {
            loadVidonInSniffer(currentEmbedUrl);
        } else {
            Map<String, String> initHeaders = new HashMap<>();
            initHeaders.put("Referer", currentEmbedUrl);
            snifferWebView.loadUrl(currentEmbedUrl, initHeaders);
        }

        // NEVER auto-tap Streamtape or VOE (clicking triggers invisible ad overlays!). Extract directly via DOM/JWPlayer JS.
        if (!isStreamtapeEmbed() && !isVoeSource) {
            handler.postDelayed(() -> {
                if (token == attemptToken && !streamCaptured && !isWebFallbackMode) {
                    tapWebViewCenter();
                }
            }, 1800);
        } else {
            handler.postDelayed(() -> {
                if (token == attemptToken && !streamCaptured && !isWebFallbackMode) {
                    extractStreamFromDom(token);
                }
            }, 1800);
            handler.postDelayed(() -> {
                if (token == attemptToken && !streamCaptured && !isWebFallbackMode) {
                    extractStreamFromDom(token);
                }
            }, 3500);
        }

        handler.postDelayed(() -> {
            if (token == attemptToken && !streamCaptured && !isWebFallbackMode && !isFinishing()) {
                if (sources.size() > 1) {
                    Toast.makeText(this, src.name + " не отговаря, пробвам следващия плеър...", Toast.LENGTH_SHORT).show();
                    switchToNextSource();
                } else {
                    enterWebFallbackMode();
                }
            }
        }, SNIFF_TIMEOUT_MS);
    }

    private void loadVidonInSniffer(String embedUrl) {
        Matcher m = Pattern.compile("vidon\\.to/(?:e/|embed-)([A-Za-z0-9]+)").matcher(embedUrl);
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
        currentStreamUrl = streamUrl;
        snifferWebView.stopLoading();
        snifferWebView.loadUrl("about:blank");
        snifferWebView.setVisibility(View.GONE);

        loadingOverlay.setVisibility(View.GONE);
        exoPlayerView.setVisibility(View.VISIBLE);

        MovieItem.PlayerSource src = sources.get(currentIndex);
        hudSourceInfo.setText("Чист поток • " + src.name + " (" + (currentIndex + 1) + "/" + sources.size() + ")");

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
                Toast.makeText(PlayerActivity.this, "Плеърът (" + src.name + ") отказа — опитай следващ.", Toast.LENGTH_SHORT).show();
                if (sources.size() > 1) {
                    switchToNextSource();
                } else {
                    enterWebFallbackMode();
                }
            }
        });

        MediaItem mediaItem = MediaItem.fromUri(Uri.parse(streamUrl));
        exoPlayer.setMediaItem(mediaItem);
        exoPlayer.prepare();
        exoPlayer.setPlayWhenReady(true);

        if (castSession != null && castSession.isConnected()) {
            loadCurrentStreamOnCast();
        }

        showTopHudTemporarily();
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
        hudSourceInfo.setText("Уеб режим • " + src.name + " • OK=Пусни/Пауза | ▲=Следващ плеър");
        showTopHudTemporarily();
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

    private void showTopHudTemporarily() {
        handler.removeCallbacks(hideHudRunnable);
        playerTopHud.setVisibility(View.VISIBLE);
        handler.postDelayed(hideHudRunnable, 3500);
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
    protected void onResume() {
        super.onResume();
        if (castSessionManager != null) {
            castSessionManager.addSessionManagerListener(castSessionListener, CastSession.class);
            castSession = castSessionManager.getCurrentCastSession();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (castSessionManager != null) {
            castSessionManager.removeSessionManagerListener(castSessionListener, CastSession.class);
        }
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
