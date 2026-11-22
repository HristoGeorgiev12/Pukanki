package com.pukanki.mobile;

import android.app.AlertDialog;
import android.content.Intent;
import android.content.res.Configuration;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.bumptech.glide.Glide;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class MainActivity extends AppCompatActivity {
    private static final int PAGE_SIZE = 30;

    private static final String[] GENRES = new String[]{
        "Екшън", "Комедия", "Анимация", "Трилър", "Фантастика",
        "Драма", "Ужаси", "Приключенски", "Фентъзи", "Криминален",
        "Семеен", "Романтичен", "Мистерия", "Военен", "Исторически",
        "Документален", "Музикален"
    };

    private static final String[] SORT_LABELS = new String[]{
        "Препоръчани", "Най-нови", "Най-стари", "Най-висок рейтинг", "А – Я", "Най-кратки", "Най-дълги"
    };
    private static final String[] SORT_VALUES = new String[]{
        "default", "newest", "oldest", "rating", "title", "shortest", "longest"
    };

    private static final String[] YEAR_LABELS = new String[]{
        "Всички", "2025", "2024", "2023", "2022", "2021", "2020", "2018", "2015", "2010", "2000", "1990"
    };
    private static final int[] YEAR_VALUES = new int[]{
        0, 2025, 2024, 2023, 2022, 2021, 2020, 2018, 2015, 2010, 2000, 1990
    };

    private static final String[] DURATION_LABELS = new String[]{
        "Всички", "До 90 мин", "90 – 120 мин", "Над 120 мин"
    };
    private static final String[] DURATION_VALUES = new String[]{
        "", "short", "medium", "long"
    };

    private static final String[] PLAYER_LABELS = new String[]{
        "Всички плеъри", "VOE", "Vidon", "Streamtape", "OK.ru", "Filemoon"
    };
    private static final String[] PLAYER_VALUES = new String[]{
        "", "voe", "vidon", "streamtape", "ok.ru", "filemoon"
    };

    private Button tabContinueBtn, tabFavBtn, tabLaterBtn, tabBgBtn, tabSubBtn, tabSeriesBtn, tabAllBtn;
    private Button openProfileBtn, openFiltersBtn, searchGoBtn, searchClearBtn;
    private EditText searchInput;
    private TextView statusText, emptyText;
    private ProgressBar mainProgress;
    private RecyclerView moviesRecycler;
    private GridLayoutManager gridLayoutManager;
    private MovieAdapter adapter;

    private HorizontalScrollView activeFiltersScroll;
    private LinearLayout activeFiltersContainer;

    // Filters Modal
    private LinearLayout filtersOverlay;
    private Button filtersCloseBtn, filtersResetBtn, filtersApplyBtn;
    private Spinner sortSpinner, yearFromSpinner, yearToSpinner, durationSpinner, playerSpinner;
    private LinearLayout filterGenresWrap;
    private final Map<String, Integer> genreStates = new LinkedHashMap<>(); // 0=neutral, 1=include, 2=exclude
    private final Map<String, Button> genreButtons = new LinkedHashMap<>();

    // Detail Overlay
    private FrameLayout detailOverlay;
    private ImageView detailBackdrop, detailPoster;
    private TextView detailTitle, detailMeta, detailOverview;
    private Button detailPlayBtn, detailFavBtn, detailLaterBtn, detailBackBtn;
    private LinearLayout detailSourcesContainer;

    private final CatalogApi.FilterParams filters = new CatalogApi.FilterParams();
    private int currentPage = 1;
    private boolean hasMore = false;
    private boolean isLoading = false;
    private int totalCount = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        bindViews();
        setupSpinners();
        buildGenreFilterChips();
        setupRecycler();
        setupListeners();
        loadActiveProfileState();
        AppUpdater.checkForUpdate(this, "mobile-v", "Pukanki-Mobile.apk");
    }

    private void bindViews() {
        tabContinueBtn = findViewById(R.id.tabContinueBtn);
        tabFavBtn = findViewById(R.id.tabFavBtn);
        tabLaterBtn = findViewById(R.id.tabLaterBtn);
        tabBgBtn = findViewById(R.id.tabBgBtn);
        tabSubBtn = findViewById(R.id.tabSubBtn);
        tabSeriesBtn = findViewById(R.id.tabSeriesBtn);
        tabAllBtn = findViewById(R.id.tabAllBtn);

        openProfileBtn = findViewById(R.id.openProfileBtn);
        openFiltersBtn = findViewById(R.id.openFiltersBtn);
        searchInput = findViewById(R.id.searchInput);
        searchGoBtn = findViewById(R.id.searchGoBtn);
        searchClearBtn = findViewById(R.id.searchClearBtn);
        statusText = findViewById(R.id.statusText);
        emptyText = findViewById(R.id.emptyText);
        mainProgress = findViewById(R.id.mainProgress);
        moviesRecycler = findViewById(R.id.moviesRecycler);

        activeFiltersScroll = findViewById(R.id.activeFiltersScroll);
        activeFiltersContainer = findViewById(R.id.activeFiltersContainer);

        filtersOverlay = findViewById(R.id.filtersOverlay);
        filtersCloseBtn = findViewById(R.id.filtersCloseBtn);
        filtersResetBtn = findViewById(R.id.filtersResetBtn);
        filtersApplyBtn = findViewById(R.id.filtersApplyBtn);
        sortSpinner = findViewById(R.id.sortSpinner);
        yearFromSpinner = findViewById(R.id.yearFromSpinner);
        yearToSpinner = findViewById(R.id.yearToSpinner);
        durationSpinner = findViewById(R.id.durationSpinner);
        playerSpinner = findViewById(R.id.playerSpinner);
        filterGenresWrap = findViewById(R.id.filterGenresWrap);

        detailOverlay = findViewById(R.id.detailOverlay);
        detailBackdrop = findViewById(R.id.detailBackdrop);
        detailPoster = findViewById(R.id.detailPoster);
        detailTitle = findViewById(R.id.detailTitle);
        detailMeta = findViewById(R.id.detailMeta);
        detailOverview = findViewById(R.id.detailOverview);
        detailPlayBtn = findViewById(R.id.detailPlayBtn);
        detailFavBtn = findViewById(R.id.detailFavBtn);
        detailLaterBtn = findViewById(R.id.detailLaterBtn);
        detailBackBtn = findViewById(R.id.detailBackBtn);
        detailSourcesContainer = findViewById(R.id.detailSourcesContainer);
    }

    private void setupSpinners() {
        setupSpinner(sortSpinner, SORT_LABELS);
        String[] fromLabels = new String[YEAR_LABELS.length];
        String[] toLabels = new String[YEAR_LABELS.length];
        fromLabels[0] = "От: Всички";
        toLabels[0] = "До: Всички";
        for (int i = 1; i < YEAR_LABELS.length; i++) {
            fromLabels[i] = "От: " + YEAR_LABELS[i];
            toLabels[i] = "До: " + YEAR_LABELS[i];
        }
        setupSpinner(yearFromSpinner, fromLabels);
        setupSpinner(yearToSpinner, toLabels);
        setupSpinner(durationSpinner, DURATION_LABELS);
        setupSpinner(playerSpinner, PLAYER_LABELS);
    }

    private void setupSpinner(Spinner spinner, String[] items) {
        ArrayAdapter<String> arr = new ArrayAdapter<>(
            this, android.R.layout.simple_spinner_item, items
        );
        arr.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(arr);
    }

    private void buildGenreFilterChips() {
        filterGenresWrap.removeAllViews();
        genreStates.clear();
        genreButtons.clear();

        float d = getResources().getDisplayMetrics().density;
        int margin = (int) (4 * d);
        int chipHeight = (int) (36 * d);
        int perRow = 3;

        LinearLayout currentRow = null;
        for (int i = 0; i < GENRES.length; i++) {
            final String genre = GENRES[i];
            genreStates.put(genre, 0);

            if (i % perRow == 0) {
                currentRow = new LinearLayout(this);
                currentRow.setOrientation(LinearLayout.HORIZONTAL);
                LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                );
                rlp.bottomMargin = (int) (6 * d);
                currentRow.setLayoutParams(rlp);
                filterGenresWrap.addView(currentRow);
            }

            Button btn = new Button(this);
            btn.setText(genre);
            btn.setAllCaps(false);
            btn.setTextColor(0xFFE2E8F0);
            btn.setTextSize(12f);
            btn.setBackgroundResource(R.drawable.bg_chip_neutral);
            btn.setPadding((int) (6 * d), 0, (int) (6 * d), 0);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, chipHeight, 1f);
            lp.setMargins(margin, 0, margin, 0);
            btn.setLayoutParams(lp);
            btn.setOnClickListener(v -> {
                int cur = genreStates.get(genre);
                int next = (cur + 1) % 3;
                genreStates.put(genre, next);
                updateGenreChipVisual(btn, genre, next);
            });
            genreButtons.put(genre, btn);
            currentRow.addView(btn);
        }
    }

    private void updateGenreChipVisual(Button btn, String genre, int state) {
        if (state == 1) {
            btn.setBackgroundResource(R.drawable.bg_chip_include);
            btn.setText("✓ " + genre);
            btn.setTextColor(0xFFFFFFFF);
        } else if (state == 2) {
            btn.setBackgroundResource(R.drawable.bg_chip_exclude);
            btn.setText("✕ " + genre);
            btn.setTextColor(0xFFFFFFFF);
        } else {
            btn.setBackgroundResource(R.drawable.bg_chip_neutral);
            btn.setText(genre);
            btn.setTextColor(0xFFE2E8F0);
        }
    }

    private void setupRecycler() {
        int spanCount = getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE ? 5 : 3;
        gridLayoutManager = new GridLayoutManager(this, spanCount);
        moviesRecycler.setLayoutManager(gridLayoutManager);
        adapter = new MovieAdapter(this::openDetails);
        moviesRecycler.setAdapter(adapter);

        moviesRecycler.addOnScrollListener(new RecyclerView.OnScrollListener() {
            @Override
            public void onScrolled(@NonNull RecyclerView rv, int dx, int dy) {
                if (dy > 0 && !isLoading && hasMore) {
                    int visible = gridLayoutManager.getChildCount();
                    int total = gridLayoutManager.getItemCount();
                    int first = gridLayoutManager.findFirstVisibleItemPosition();
                    if ((visible + first) >= total - 9) {
                        loadPage(currentPage + 1, false);
                    }
                }
            }
        });
    }

    @Override
    public void onConfigurationChanged(@NonNull Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        if (gridLayoutManager != null) {
            int span = newConfig.orientation == Configuration.ORIENTATION_LANDSCAPE ? 5 : 3;
            gridLayoutManager.setSpanCount(span);
        }
    }

    private void setupListeners() {
        tabContinueBtn.setOnClickListener(v -> selectTab("continue"));
        tabFavBtn.setOnClickListener(v -> selectTab("favorites"));
        tabLaterBtn.setOnClickListener(v -> selectTab("later"));
        tabBgBtn.setOnClickListener(v -> selectTab("bg"));
        tabSubBtn.setOnClickListener(v -> selectTab("sub"));
        tabSeriesBtn.setOnClickListener(v -> selectTab("series"));
        tabAllBtn.setOnClickListener(v -> selectTab("all"));

        searchGoBtn.setOnClickListener(v -> performSearch());
        searchClearBtn.setOnClickListener(v -> {
            searchInput.setText("");
            filters.query = "";
            hideKeyboard();
            loadPage(1, true);
        });

        searchInput.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                searchClearBtn.setVisibility(s != null && s.length() > 0 ? View.VISIBLE : View.GONE);
            }
            @Override public void afterTextChanged(Editable s) {}
        });

        searchInput.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEARCH) {
                performSearch();
                return true;
            }
            return false;
        });

        openProfileBtn.setOnClickListener(v -> showProfileSwitcherDialog());
        openFiltersBtn.setOnClickListener(v -> {
            hideKeyboard();
            filtersOverlay.setVisibility(View.VISIBLE);
        });
        filtersCloseBtn.setOnClickListener(v -> filtersOverlay.setVisibility(View.GONE));

        filtersResetBtn.setOnClickListener(v -> {
            resetAllFilters();
            filtersOverlay.setVisibility(View.GONE);
            loadPage(1, true);
        });

        filtersApplyBtn.setOnClickListener(v -> {
            applyFiltersFromModal();
            filtersOverlay.setVisibility(View.GONE);
            loadPage(1, true);
        });

        detailBackBtn.setOnClickListener(v -> closeDetails());
    }

    private void performSearch() {
        filters.query = searchInput.getText().toString().trim();
        hideKeyboard();
        loadPage(1, true);
    }

    private void selectTab(String tab) {
        filters.tab = tab;
        tabContinueBtn.setSelected("continue".equals(tab));
        tabFavBtn.setSelected("favorites".equals(tab));
        tabLaterBtn.setSelected("later".equals(tab));
        tabBgBtn.setSelected("bg".equals(tab));
        tabSubBtn.setSelected("sub".equals(tab));
        tabSeriesBtn.setSelected("series".equals(tab));
        tabAllBtn.setSelected("all".equals(tab));
        if ("continue".equals(tab)) {
            loadLocalMovieList(WatchHistoryStore.getUnfinishedMovies(this), "недовършени");
        } else if ("favorites".equals(tab)) {
            loadLocalMovieList(UserListsStore.getFavorites(this), "любими");
        } else if ("later".equals(tab)) {
            loadLocalMovieList(UserListsStore.getWatchLater(this), "за по-късно");
        } else {
            loadPage(1, true);
        }
    }

    private void updateUnfinishedBadge() {
        int n = WatchHistoryStore.getUnfinishedCount(this);
        tabContinueBtn.setText(n > 0 ? "⏱ Недовършени (" + n + ")" : "⏱ Недовършени");
        tabContinueBtn.setBackgroundResource(n > 0 ? R.drawable.bg_tab_unfinished_active : R.drawable.bg_tab_selector);
        int favN = UserListsStore.getFavoritesCount(this);
        tabFavBtn.setText(favN > 0 ? "❤️ Любими (" + favN + ")" : "❤️ Любими");
        int laterN = UserListsStore.getWatchLaterCount(this);
        tabLaterBtn.setText(laterN > 0 ? "🔖 За по-късно (" + laterN + ")" : "🔖 За по-късно");
    }

    private void loadLocalMovieList(List<MovieItem> list, String label) {
        isLoading = false;
        hasMore = false;
        mainProgress.setVisibility(View.GONE);
        adapter.setItems(list);
        moviesRecycler.scrollToPosition(0);
        emptyText.setVisibility(list.isEmpty() ? View.VISIBLE : View.GONE);
        statusText.setText(list.size() + " " + label + " • v1.4.0");
        updateUnfinishedBadge();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateUnfinishedBadge();
        if ("continue".equals(filters.tab)) {
            loadLocalMovieList(WatchHistoryStore.getUnfinishedMovies(this), "недовършени");
        } else if ("favorites".equals(filters.tab)) {
            loadLocalMovieList(UserListsStore.getFavorites(this), "любими");
        } else if ("later".equals(filters.tab)) {
            loadLocalMovieList(UserListsStore.getWatchLater(this), "за по-късно");
        }
    }

    private void applyFiltersFromModal() {
        filters.sort = SORT_VALUES[sortSpinner.getSelectedItemPosition()];
        filters.yearFrom = YEAR_VALUES[yearFromSpinner.getSelectedItemPosition()];
        filters.yearTo = YEAR_VALUES[yearToSpinner.getSelectedItemPosition()];
        filters.duration = DURATION_VALUES[durationSpinner.getSelectedItemPosition()];
        filters.player = PLAYER_VALUES[playerSpinner.getSelectedItemPosition()];

        List<String> inc = new ArrayList<>();
        List<String> exc = new ArrayList<>();
        for (Map.Entry<String, Integer> entry : genreStates.entrySet()) {
            if (entry.getValue() == 1) inc.add(entry.getKey());
            else if (entry.getValue() == 2) exc.add(entry.getKey());
        }
        filters.genresCsv = joinCsv(inc);
        filters.excludeGenresCsv = joinCsv(exc);
        saveActiveProfileFilters();
        refreshActiveFiltersStrip();
    }

    private void saveActiveProfileFilters() {
        try {
            JSONObject obj = new JSONObject();
            boolean isLocalTab = "continue".equals(filters.tab) || "favorites".equals(filters.tab) || "later".equals(filters.tab);
            obj.put("tab", isLocalTab ? "bg" : filters.tab);
            obj.put("sortIdx", sortSpinner.getSelectedItemPosition());
            obj.put("yearFromIdx", yearFromSpinner.getSelectedItemPosition());
            obj.put("yearToIdx", yearToSpinner.getSelectedItemPosition());
            obj.put("durIdx", durationSpinner.getSelectedItemPosition());
            obj.put("playerIdx", playerSpinner.getSelectedItemPosition());
            JSONObject gObj = new JSONObject();
            for (Map.Entry<String, Integer> entry : genreStates.entrySet()) {
                if (entry.getValue() != 0) gObj.put(entry.getKey(), entry.getValue());
            }
            obj.put("genres", gObj);
            ProfileStore.saveFiltersJson(this, ProfileStore.getActiveProfileId(this), obj);
        } catch (Exception ignored) {}
    }

    private void loadActiveProfileState() {
        ProfileStore.Profile p = ProfileStore.getActiveProfile(this);
        openProfileBtn.setText("👤 " + p.name);
        JSONObject obj = ProfileStore.loadFiltersJson(this, p.id);

        sortSpinner.setSelection(0);
        yearFromSpinner.setSelection(0);
        yearToSpinner.setSelection(0);
        durationSpinner.setSelection(0);
        playerSpinner.setSelection(0);
        for (Map.Entry<String, Button> entry : genreButtons.entrySet()) {
            genreStates.put(entry.getKey(), 0);
            updateGenreChipVisual(entry.getValue(), entry.getKey(), 0);
        }

        String savedTab = "bg";
        if (obj != null) {
            savedTab = obj.optString("tab", "bg");
            sortSpinner.setSelection(Math.min(SORT_VALUES.length - 1, Math.max(0, obj.optInt("sortIdx", 0))));
            yearFromSpinner.setSelection(Math.min(YEAR_VALUES.length - 1, Math.max(0, obj.optInt("yearFromIdx", 0))));
            yearToSpinner.setSelection(Math.min(YEAR_VALUES.length - 1, Math.max(0, obj.optInt("yearToIdx", 0))));
            durationSpinner.setSelection(Math.min(DURATION_VALUES.length - 1, Math.max(0, obj.optInt("durIdx", 0))));
            playerSpinner.setSelection(Math.min(PLAYER_VALUES.length - 1, Math.max(0, obj.optInt("playerIdx", 0))));
            JSONObject gObj = obj.optJSONObject("genres");
            if (gObj != null) {
                for (Map.Entry<String, Button> entry : genreButtons.entrySet()) {
                    int st = gObj.optInt(entry.getKey(), 0);
                    if (st == 1 || st == 2) {
                        genreStates.put(entry.getKey(), st);
                        updateGenreChipVisual(entry.getValue(), entry.getKey(), st);
                    }
                }
            }
        }
        applyFiltersFromModal();
        updateUnfinishedBadge();
        selectTab(savedTab);
    }

    private void showProfileSwitcherDialog() {
        final List<ProfileStore.Profile> profiles = ProfileStore.getProfiles(this);
        final String activeId = ProfileStore.getActiveProfileId(this);
        String[] labels = new String[profiles.size() + 1];
        for (int i = 0; i < profiles.size(); i++) {
            ProfileStore.Profile p = profiles.get(i);
            labels[i] = (p.id.equals(activeId) ? "✓ " : "   ") + p.name;
        }
        labels[profiles.size()] = "➕ Създай нов профил";

        new AlertDialog.Builder(this)
            .setTitle("👤 Избери профил")
            .setItems(labels, (dialog, which) -> {
                if (which == profiles.size()) {
                    showCreateProfileDialog();
                } else {
                    ProfileStore.Profile chosen = profiles.get(which);
                    ProfileStore.setActiveProfileId(this, chosen.id);
                    loadActiveProfileState();
                    Toast.makeText(this, "👤 Профил: " + chosen.name, Toast.LENGTH_SHORT).show();
                }
            })
            .setNegativeButton("Затвори", null)
            .show();
    }

    private void showCreateProfileDialog() {
        final EditText input = new EditText(this);
        input.setHint("Име (напр. Христо, Мария, Деца)");
        input.setSingleLine(true);
        new AlertDialog.Builder(this)
            .setTitle("➕ Нов локален профил")
            .setView(input)
            .setPositiveButton("Създай", (d, w) -> {
                String name = input.getText().toString().trim();
                if (!name.isEmpty()) {
                    ProfileStore.Profile created = ProfileStore.createProfile(this, name);
                    loadActiveProfileState();
                    Toast.makeText(this, "Създаден профил: " + created.name, Toast.LENGTH_SHORT).show();
                }
            })
            .setNegativeButton("Отказ", null)
            .show();
    }

    private void resetAllFilters() {
        sortSpinner.setSelection(0);
        yearFromSpinner.setSelection(0);
        yearToSpinner.setSelection(0);
        durationSpinner.setSelection(0);
        playerSpinner.setSelection(0);
        for (Map.Entry<String, Button> entry : genreButtons.entrySet()) {
            genreStates.put(entry.getKey(), 0);
            updateGenreChipVisual(entry.getValue(), entry.getKey(), 0);
        }
        filters.sort = "default";
        filters.yearFrom = 0;
        filters.yearTo = 0;
        filters.duration = "";
        filters.player = "";
        filters.genresCsv = "";
        filters.excludeGenresCsv = "";
        refreshActiveFiltersStrip();
    }

    private String joinCsv(List<String> list) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(list.get(i));
        }
        return sb.toString();
    }

    private void refreshActiveFiltersStrip() {
        activeFiltersContainer.removeAllViews();
        int count = 0;

        if (!"default".equals(filters.sort)) {
            addActiveChip("↕ " + SORT_LABELS[sortSpinner.getSelectedItemPosition()], R.drawable.bg_chip_neutral, () -> {
                sortSpinner.setSelection(0);
                filters.sort = "default";
                refreshActiveFiltersStrip();
                loadPage(1, true);
            });
            count++;
        }

        for (Map.Entry<String, Integer> entry : genreStates.entrySet()) {
            final String g = entry.getKey();
            int st = entry.getValue();
            if (st == 1 || st == 2) {
                addActiveChip((st == 1 ? "✓ " : "✕ ") + g,
                    st == 1 ? R.drawable.bg_chip_include : R.drawable.bg_chip_exclude,
                    () -> {
                        genreStates.put(g, 0);
                        Button b = genreButtons.get(g);
                        if (b != null) updateGenreChipVisual(b, g, 0);
                        applyFiltersFromModal();
                        loadPage(1, true);
                    });
                count++;
            }
        }

        if (filters.yearFrom > 0 || filters.yearTo > 0) {
            String lbl = (filters.yearFrom > 0 ? filters.yearFrom : "…") + "–" + (filters.yearTo > 0 ? filters.yearTo : "…");
            addActiveChip("📅 " + lbl, R.drawable.bg_chip_neutral, () -> {
                yearFromSpinner.setSelection(0);
                yearToSpinner.setSelection(0);
                filters.yearFrom = 0;
                filters.yearTo = 0;
                refreshActiveFiltersStrip();
                loadPage(1, true);
            });
            count++;
        }

        if (!filters.duration.isEmpty()) {
            addActiveChip("⏱ " + DURATION_LABELS[durationSpinner.getSelectedItemPosition()], R.drawable.bg_chip_neutral, () -> {
                durationSpinner.setSelection(0);
                filters.duration = "";
                refreshActiveFiltersStrip();
                loadPage(1, true);
            });
            count++;
        }

        if (!filters.player.isEmpty()) {
            addActiveChip("▶ " + PLAYER_LABELS[playerSpinner.getSelectedItemPosition()], R.drawable.bg_chip_neutral, () -> {
                playerSpinner.setSelection(0);
                filters.player = "";
                refreshActiveFiltersStrip();
                loadPage(1, true);
            });
            count++;
        }

        if (count > 0) {
            activeFiltersScroll.setVisibility(View.VISIBLE);
            openFiltersBtn.setText("⚙ Филтри (" + count + ")");
        } else {
            activeFiltersScroll.setVisibility(View.GONE);
            openFiltersBtn.setText("⚙ Филтри");
        }
    }

    private void addActiveChip(String label, int bgRes, Runnable onRemove) {
        float d = getResources().getDisplayMetrics().density;
        Button chip = new Button(this);
        chip.setText(label + "  ✕");
        chip.setAllCaps(false);
        chip.setTextColor(0xFFFFFFFF);
        chip.setTextSize(11f);
        chip.setBackgroundResource(bgRes);
        chip.setPadding((int) (10 * d), 0, (int) (10 * d), 0);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, (int) (30 * d)
        );
        lp.setMarginEnd((int) (6 * d));
        chip.setLayoutParams(lp);
        chip.setOnClickListener(v -> onRemove.run());
        activeFiltersContainer.addView(chip);
    }

    private void loadPage(int page, boolean reset) {
        isLoading = true;
        if (reset) {
            currentPage = 1;
            mainProgress.setVisibility(View.VISIBLE);
            emptyText.setVisibility(View.GONE);
        }

        CatalogApi.fetchPage(filters, page, PAGE_SIZE, new CatalogApi.Callback() {
            @Override
            public void onSuccess(CatalogApi.PageResult result) {
                isLoading = false;
                mainProgress.setVisibility(View.GONE);
                currentPage = result.page;
                hasMore = result.hasMore;
                totalCount = result.total;

                if (reset) {
                    adapter.setItems(result.items);
                    moviesRecycler.scrollToPosition(0);
                    emptyText.setVisibility(result.items.isEmpty() ? View.VISIBLE : View.GONE);
                } else {
                    adapter.appendItems(result.items);
                }
                statusText.setText(totalCount + " заглавия • v1.4.0");
            }

            @Override
            public void onError(String message) {
                isLoading = false;
                mainProgress.setVisibility(View.GONE);
                statusText.setText("Грешка при зареждане");
                Toast.makeText(MainActivity.this, "Грешка: " + message, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void openDetails(MovieItem item) {
        hideKeyboard();
        detailTitle.setText(item.title);

        StringBuilder meta = new StringBuilder();
        if (item.year > 0) meta.append(item.year);
        if (item.rating > 0) meta.append(meta.length() > 0 ? "  •  " : "").append(String.format(Locale.US, "★ %.1f", item.rating));
        if (item.duration > 0) meta.append(meta.length() > 0 ? "  •  " : "").append(item.duration).append(" мин");
        meta.append(meta.length() > 0 ? "\n" : "").append(item.isBgAudio ? "🇧🇬 БГ Аудио" : "💬 БГ Субтитри");
        if (!item.genres.isEmpty()) {
            meta.append("  •  ");
            for (int i = 0; i < Math.min(3, item.genres.size()); i++) {
                if (i > 0) meta.append(", ");
                meta.append(item.genres.get(i));
            }
        }
        detailMeta.setText(meta.toString());
        detailOverview.setText(item.overview != null && !item.overview.isEmpty() ? item.overview : "Няма описание.");

        Glide.with(this).load(item.posterUrl).centerCrop().into(detailPoster);
        String bgUrl = (item.backdropUrl != null && !item.backdropUrl.isEmpty()) ? item.backdropUrl : item.posterUrl;
        Glide.with(this).load(bgUrl).centerCrop().into(detailBackdrop);

        detailPlayBtn.setOnClickListener(v -> launchPlayer(item, 0));

        updateDetailListButtons(item);
        detailFavBtn.setOnClickListener(v -> {
            boolean added = UserListsStore.toggleFavorite(this, item);
            updateDetailListButtons(item);
            updateUnfinishedBadge();
            Toast.makeText(this, added ? "❤️ Добавен в Любими" : "Премахнат от Любими", Toast.LENGTH_SHORT).show();
            if ("favorites".equals(filters.tab)) {
                loadLocalMovieList(UserListsStore.getFavorites(this), "любими");
            }
        });
        detailLaterBtn.setOnClickListener(v -> {
            boolean added = UserListsStore.toggleWatchLater(this, item);
            updateDetailListButtons(item);
            updateUnfinishedBadge();
            Toast.makeText(this, added ? "🔖 Добавен в „За по-късно“" : "Премахнат от „За по-късно“", Toast.LENGTH_SHORT).show();
            if ("later".equals(filters.tab)) {
                loadLocalMovieList(UserListsStore.getWatchLater(this), "за по-късно");
            }
        });

        detailSourcesContainer.removeAllViews();
        float d = getResources().getDisplayMetrics().density;
        int marginEnd = (int) (8 * d);
        for (int i = 0; i < item.sources.size(); i++) {
            final int idx = i;
            MovieItem.PlayerSource src = item.sources.get(i);
            Button btn = new Button(this);
            btn.setText(src.name);
            btn.setAllCaps(false);
            btn.setTextColor(0xFFFFFFFF);
            btn.setTextSize(13f);
            btn.setBackgroundResource(R.drawable.bg_btn_secondary);
            btn.setPadding((int) (14 * d), 0, (int) (14 * d), 0);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, (int) (38 * d)
            );
            lp.setMarginEnd(marginEnd);
            btn.setLayoutParams(lp);
            btn.setOnClickListener(v -> launchPlayer(item, idx));
            detailSourcesContainer.addView(btn);
        }

        detailOverlay.setVisibility(View.VISIBLE);
    }

    private void updateDetailListButtons(MovieItem item) {
        boolean isFav = UserListsStore.isFavorite(this, item.getHistoryKey());
        boolean isLater = UserListsStore.isWatchLater(this, item.getHistoryKey());
        detailFavBtn.setText(isFav ? "❤️ Любим ✓" : "🤍 Любим");
        detailFavBtn.setSelected(isFav);
        detailLaterBtn.setText(isLater ? "🔖 Запазен ✓" : "🔖 За по-късно");
        detailLaterBtn.setSelected(isLater);
    }

    private void closeDetails() {
        detailOverlay.setVisibility(View.GONE);
    }

    private void launchPlayer(MovieItem item, int startIndex) {
        if (item.sources == null || item.sources.isEmpty()) {
            Toast.makeText(this, "Няма налични плеъри за това заглавие.", Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(this, PlayerActivity.class);
        intent.putExtra("title", item.title);
        intent.putExtra("history_key", item.getHistoryKey());
        intent.putExtra("movie_json", item.toJsonObject().toString());
        intent.putExtra("sources_json", MovieItem.sourcesToJson(item.sources));
        intent.putExtra("start_index", startIndex);
        startActivity(intent);
    }

    private void hideKeyboard() {
        View view = getCurrentFocus();
        if (view != null) {
            InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (imm != null) imm.hideSoftInputFromWindow(view.getWindowToken(), 0);
        }
    }

    @Override
    public void onBackPressed() {
        if (detailOverlay.getVisibility() == View.VISIBLE) {
            closeDetails();
        } else if (filtersOverlay.getVisibility() == View.VISIBLE) {
            filtersOverlay.setVisibility(View.GONE);
        } else {
            super.onBackPressed();
        }
    }
}
