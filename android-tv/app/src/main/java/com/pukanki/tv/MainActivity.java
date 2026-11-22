package com.pukanki.tv;

import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.bumptech.glide.Glide;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class MainActivity extends AppCompatActivity {
    private static final int PAGE_SIZE = 30;

    private static final String[] GENRES = new String[]{
        "Екшън", "Комедия", "Анимация", "Трилър", "Фантастика", "Драма", "Ужаси", "Приключенски",
        "Фентъзи", "Криминален", "Семеен", "Романтичен", "Мистерия", "Военен", "Исторически", "Документален"
    };

    private static final String[] SORT_LABELS = new String[]{
        "Препоръчани", "Най-нови", "Най-стари", "Рейтинг ↓", "А – Я", "Най-кратки", "Най-дълги"
    };
    private static final String[] SORT_VALUES = new String[]{
        "default", "newest", "oldest", "rating", "title", "shortest", "longest"
    };

    private static final String[] YEAR_LABELS = new String[]{
        "Всички", "2024–2025", "2020+", "2015+", "2010+", "2000–2015", "Класики (<2000)"
    };
    private static final int[] YEAR_FROM = new int[]{0, 2024, 2020, 2015, 2010, 2000, 0};
    private static final int[] YEAR_TO   = new int[]{0, 2025, 0,    0,    0,    2015, 1999};

    private static final String[] DURATION_LABELS = new String[]{
        "Всички", "До 90 мин", "90 – 120 мин", "Над 120 мин"
    };
    private static final String[] DURATION_VALUES = new String[]{
        "", "short", "medium", "long"
    };

    private static final String[] PLAYER_LABELS = new String[]{
        "Всички", "VOE", "Vidon", "Streamtape", "OK.ru", "Filemoon"
    };
    private static final String[] PLAYER_VALUES = new String[]{
        "", "voe", "vidon", "streamtape", "ok.ru", "filemoon"
    };

    private Button tabContinueBtn, tabFavBtn, tabLaterBtn, tabBgBtn, tabSubBtn, tabSeriesBtn, tabGenreBtn, tabSearchBtn, tabProfileBtn, searchGoBtn;
    private LinearLayout profileOverlay, profileCardsRow;
    private Button profileAddBtn, profileCloseBtn;
    private LinearLayout leftSidebar, searchRow;
    private EditText searchInput;
    private TextView sidebarLogoText, statusText, emptyText;
    private boolean isSidebarExpanded = true;
    private int activeFilterCount = 0;
    private ProgressBar mainProgress;
    private RecyclerView moviesRecycler;
    private MovieAdapter adapter;

    private ViewGroup browseContainer;
    private FrameLayout detailOverlay;
    private ImageView detailBackdrop, detailPoster;
    private TextView detailTitle, detailMeta, detailOverview;
    private Button detailPlayBtn, detailFavBtn, detailLaterBtn, detailBackBtn;
    private LinearLayout detailSourcesContainer;

    // Dedicated TV Filters & Sort Overlay
    private LinearLayout filtersOverlay;
    private Button filtersApplyBtn, filtersResetBtn, filtersCloseBtn;
    private LinearLayout filterSortRow, filterGenresWrap, filterYearRow, filterDurationRow, filterPlayerRow;

    private final List<Button> sortBtns = new ArrayList<>();
    private final List<Button> yearBtns = new ArrayList<>();
    private final List<Button> durationBtns = new ArrayList<>();
    private final List<Button> playerBtns = new ArrayList<>();
    private final Map<String, Integer> genreStates = new LinkedHashMap<>(); // 0=neutral, 1=include, 2=exclude
    private final Map<String, Button> genreBtns = new LinkedHashMap<>();

    private int selectedSortIdx = 0;
    private int selectedYearIdx = 0;
    private int selectedDurationIdx = 0;
    private int selectedPlayerIdx = 0;

    private final CatalogApi.FilterParams filters = new CatalogApi.FilterParams();
    private int currentPage = 1;
    private boolean hasMore = false;
    private boolean isLoading = false;
    private int totalCount = 0;

    private MovieItem activeDetailItem = null;
    private View lastFocusedCardView = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        hideSystemUI();
        setContentView(R.layout.activity_main);

        bindViews();
        buildFiltersOverlay();
        setupRecycler();
        setupListeners();
        loadActiveProfileState();
        AppUpdater.checkForUpdate(this, "tv-v", "Pukanki-TV.apk");
        if (ProfileStore.getProfiles(this).size() > 1) {
            openProfileOverlay();
        }
    }

    private void bindViews() {
        browseContainer = findViewById(R.id.browseContainer);
        leftSidebar = findViewById(R.id.leftSidebar);
        sidebarLogoText = findViewById(R.id.sidebarLogoText);
        tabContinueBtn = findViewById(R.id.tabContinueBtn);
        tabFavBtn = findViewById(R.id.tabFavBtn);
        tabLaterBtn = findViewById(R.id.tabLaterBtn);
        tabBgBtn = findViewById(R.id.tabBgBtn);
        tabSubBtn = findViewById(R.id.tabSubBtn);
        tabSeriesBtn = findViewById(R.id.tabSeriesBtn);
        tabGenreBtn = findViewById(R.id.tabGenreBtn);
        tabSearchBtn = findViewById(R.id.tabSearchBtn);
        tabProfileBtn = findViewById(R.id.tabProfileBtn);
        profileOverlay = findViewById(R.id.profileOverlay);
        profileCardsRow = findViewById(R.id.profileCardsRow);
        profileAddBtn = findViewById(R.id.profileAddBtn);
        profileCloseBtn = findViewById(R.id.profileCloseBtn);
        searchRow = findViewById(R.id.searchRow);
        searchInput = findViewById(R.id.searchInput);
        searchGoBtn = findViewById(R.id.searchGoBtn);
        statusText = findViewById(R.id.statusText);
        emptyText = findViewById(R.id.emptyText);
        mainProgress = findViewById(R.id.mainProgress);
        moviesRecycler = findViewById(R.id.moviesRecycler);

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

        filtersOverlay = findViewById(R.id.filtersOverlay);
        filtersApplyBtn = findViewById(R.id.filtersApplyBtn);
        filtersResetBtn = findViewById(R.id.filtersResetBtn);
        filtersCloseBtn = findViewById(R.id.filtersCloseBtn);
        filterSortRow = findViewById(R.id.filterSortRow);
        filterGenresWrap = findViewById(R.id.filterGenresWrap);
        filterYearRow = findViewById(R.id.filterYearRow);
        filterDurationRow = findViewById(R.id.filterDurationRow);
        filterPlayerRow = findViewById(R.id.filterPlayerRow);
    }

    private Button createTvChip(String text) {
        float d = getResources().getDisplayMetrics().density;
        Button b = new Button(this);
        b.setId(View.generateViewId());
        b.setText(text);
        b.setAllCaps(false);
        b.setTextColor(0xFFFFFFFF);
        b.setTextSize(12.5f);
        b.setBackgroundResource(R.drawable.bg_tab_selector);
        b.setPadding((int) (14 * d), 0, (int) (14 * d), 0);
        b.setFocusable(true);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, (int) (36 * d)
        );
        lp.setMarginEnd((int) (8 * d));
        b.setLayoutParams(lp);
        return b;
    }

    private void buildFiltersOverlay() {
        // 1. Sort chips
        filterSortRow.removeAllViews();
        sortBtns.clear();
        for (int i = 0; i < SORT_LABELS.length; i++) {
            final int idx = i;
            Button b = createTvChip(SORT_LABELS[i]);
            b.setSelected(idx == selectedSortIdx);
            b.setOnClickListener(v -> {
                selectedSortIdx = idx;
                updateSingleSelectRow(sortBtns, selectedSortIdx);
            });
            sortBtns.add(b);
            filterSortRow.addView(b);
        }

        // 2. Genres grid (2 rows x 8 chips) with Include / Exclude 3-state toggle
        filterGenresWrap.removeAllViews();
        genreStates.clear();
        genreBtns.clear();
        float d = getResources().getDisplayMetrics().density;
        int perRow = 8;
        LinearLayout row = null;
        for (int i = 0; i < GENRES.length; i++) {
            final String g = GENRES[i];
            genreStates.put(g, 0);
            if (i % perRow == 0) {
                row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
                );
                rlp.bottomMargin = (int) (8 * d);
                row.setLayoutParams(rlp);
                filterGenresWrap.addView(row);
            }
            Button b = new Button(this);
            b.setId(View.generateViewId());
            b.setText(g);
            b.setAllCaps(false);
            b.setTextColor(0xFFFFFFFF);
            b.setTextSize(11.5f);
            b.setBackgroundResource(R.drawable.bg_tab_selector);
            b.setPadding((int) (6 * d), 0, (int) (6 * d), 0);
            b.setFocusable(true);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, (int) (36 * d), 1f);
            lp.setMarginEnd((int) (6 * d));
            b.setLayoutParams(lp);
            b.setOnClickListener(v -> {
                int cur = genreStates.containsKey(g) ? genreStates.get(g) : 0;
                int next = (cur + 1) % 3;
                genreStates.put(g, next);
                updateGenreChipVisual(b, g, next);
            });
            genreBtns.put(g, b);
            row.addView(b);
        }

        // 3. Year preset chips
        filterYearRow.removeAllViews();
        yearBtns.clear();
        for (int i = 0; i < YEAR_LABELS.length; i++) {
            final int idx = i;
            Button b = createTvChip(YEAR_LABELS[i]);
            b.setSelected(idx == selectedYearIdx);
            b.setOnClickListener(v -> {
                selectedYearIdx = idx;
                updateSingleSelectRow(yearBtns, selectedYearIdx);
            });
            yearBtns.add(b);
            filterYearRow.addView(b);
        }

        // 4. Duration chips
        filterDurationRow.removeAllViews();
        durationBtns.clear();
        for (int i = 0; i < DURATION_LABELS.length; i++) {
            final int idx = i;
            Button b = createTvChip(DURATION_LABELS[i]);
            b.setSelected(idx == selectedDurationIdx);
            b.setOnClickListener(v -> {
                selectedDurationIdx = idx;
                updateSingleSelectRow(durationBtns, selectedDurationIdx);
            });
            durationBtns.add(b);
            filterDurationRow.addView(b);
        }

        // 5. Player chips
        filterPlayerRow.removeAllViews();
        playerBtns.clear();
        for (int i = 0; i < PLAYER_LABELS.length; i++) {
            final int idx = i;
            Button b = createTvChip(PLAYER_LABELS[i]);
            b.setSelected(idx == selectedPlayerIdx);
            b.setOnClickListener(v -> {
                selectedPlayerIdx = idx;
                updateSingleSelectRow(playerBtns, selectedPlayerIdx);
            });
            playerBtns.add(b);
            filterPlayerRow.addView(b);
        }
    }

    private void updateSingleSelectRow(List<Button> btns, int selectedIdx) {
        for (int i = 0; i < btns.size(); i++) {
            btns.get(i).setSelected(i == selectedIdx);
        }
    }

    private void updateGenreChipVisual(Button chip, String genre, int state) {
        if (state == 1) {
            chip.setBackgroundResource(R.drawable.bg_tv_chip_include);
            chip.setText("✓ " + genre);
        } else if (state == 2) {
            chip.setBackgroundResource(R.drawable.bg_tv_chip_exclude);
            chip.setText("✕ " + genre);
        } else {
            chip.setBackgroundResource(R.drawable.bg_tab_selector);
            chip.setSelected(false);
            chip.setText(genre);
        }
    }

    private void openFiltersOverlay() {
        searchRow.setVisibility(View.GONE);
        browseContainer.setDescendantFocusability(ViewGroup.FOCUS_BLOCK_DESCENDANTS);
        filtersOverlay.setVisibility(View.VISIBLE);
        if (!sortBtns.isEmpty()) {
            sortBtns.get(selectedSortIdx).post(() -> sortBtns.get(selectedSortIdx).requestFocus());
        } else {
            filtersApplyBtn.post(() -> filtersApplyBtn.requestFocus());
        }
    }

    private void closeFiltersOverlay() {
        filtersOverlay.setVisibility(View.GONE);
        browseContainer.setDescendantFocusability(ViewGroup.FOCUS_AFTER_DESCENDANTS);
        tabGenreBtn.post(() -> tabGenreBtn.requestFocus());
    }

    private void applyFiltersAndClose() {
        filters.sort = SORT_VALUES[selectedSortIdx];
        filters.yearFrom = YEAR_FROM[selectedYearIdx];
        filters.yearTo = YEAR_TO[selectedYearIdx];
        filters.duration = DURATION_VALUES[selectedDurationIdx];
        filters.player = PLAYER_VALUES[selectedPlayerIdx];

        List<String> inc = new ArrayList<>();
        List<String> exc = new ArrayList<>();
        for (Map.Entry<String, Integer> e : genreStates.entrySet()) {
            if (e.getValue() == 1) inc.add(e.getKey());
            else if (e.getValue() == 2) exc.add(e.getKey());
        }
        filters.genre = joinCsv(inc);
        filters.excludeGenre = joinCsv(exc);

        int activeCount = inc.size() + exc.size();
        if (selectedSortIdx > 0) activeCount++;
        if (selectedYearIdx > 0) activeCount++;
        if (selectedDurationIdx > 0) activeCount++;
        if (selectedPlayerIdx > 0) activeCount++;

        activeFilterCount = activeCount;
        saveActiveProfileFilters();
        updateSidebarVisuals();

        filtersOverlay.setVisibility(View.GONE);
        browseContainer.setDescendantFocusability(ViewGroup.FOCUS_AFTER_DESCENDANTS);
        loadPage(1, true);
    }

    private void saveActiveProfileFilters() {
        try {
            JSONObject obj = new JSONObject();
            boolean isLocalTab = "continue".equals(filters.tab) || "favorites".equals(filters.tab) || "later".equals(filters.tab);
            obj.put("tab", isLocalTab ? "bg" : filters.tab);
            obj.put("sortIdx", selectedSortIdx);
            obj.put("yearIdx", selectedYearIdx);
            obj.put("durIdx", selectedDurationIdx);
            obj.put("playerIdx", selectedPlayerIdx);
            JSONObject gObj = new JSONObject();
            for (Map.Entry<String, Integer> e : genreStates.entrySet()) {
                if (e.getValue() != 0) gObj.put(e.getKey(), e.getValue());
            }
            obj.put("genres", gObj);
            ProfileStore.saveFiltersJson(this, ProfileStore.getActiveProfileId(this), obj);
        } catch (Exception ignored) {}
    }

    private void loadActiveProfileState() {
        String pid = ProfileStore.getActiveProfileId(this);
        JSONObject obj = ProfileStore.loadFiltersJson(this, pid);
        selectedSortIdx = 0;
        selectedYearIdx = 0;
        selectedDurationIdx = 0;
        selectedPlayerIdx = 0;
        String savedTab = "bg";

        for (Map.Entry<String, Button> e : genreBtns.entrySet()) {
            genreStates.put(e.getKey(), 0);
            updateGenreChipVisual(e.getValue(), e.getKey(), 0);
        }

        if (obj != null) {
            savedTab = obj.optString("tab", "bg");
            selectedSortIdx = Math.min(SORT_VALUES.length - 1, Math.max(0, obj.optInt("sortIdx", 0)));
            selectedYearIdx = Math.min(YEAR_FROM.length - 1, Math.max(0, obj.optInt("yearIdx", 0)));
            selectedDurationIdx = Math.min(DURATION_VALUES.length - 1, Math.max(0, obj.optInt("durIdx", 0)));
            selectedPlayerIdx = Math.min(PLAYER_VALUES.length - 1, Math.max(0, obj.optInt("playerIdx", 0)));
            JSONObject gObj = obj.optJSONObject("genres");
            if (gObj != null) {
                for (Map.Entry<String, Button> e : genreBtns.entrySet()) {
                    int st = gObj.optInt(e.getKey(), 0);
                    if (st == 1 || st == 2) {
                        genreStates.put(e.getKey(), st);
                        updateGenreChipVisual(e.getValue(), e.getKey(), st);
                    }
                }
            }
        }

        updateSingleSelectRow(sortBtns, selectedSortIdx);
        updateSingleSelectRow(yearBtns, selectedYearIdx);
        updateSingleSelectRow(durationBtns, selectedDurationIdx);
        updateSingleSelectRow(playerBtns, selectedPlayerIdx);

        filters.sort = SORT_VALUES[selectedSortIdx];
        filters.yearFrom = YEAR_FROM[selectedYearIdx];
        filters.yearTo = YEAR_TO[selectedYearIdx];
        filters.duration = DURATION_VALUES[selectedDurationIdx];
        filters.player = PLAYER_VALUES[selectedPlayerIdx];

        List<String> inc = new ArrayList<>();
        List<String> exc = new ArrayList<>();
        for (Map.Entry<String, Integer> e : genreStates.entrySet()) {
            if (e.getValue() == 1) inc.add(e.getKey());
            else if (e.getValue() == 2) exc.add(e.getKey());
        }
        filters.genre = joinCsv(inc);
        filters.excludeGenre = joinCsv(exc);

        int activeCount = inc.size() + exc.size();
        if (selectedSortIdx > 0) activeCount++;
        if (selectedYearIdx > 0) activeCount++;
        if (selectedDurationIdx > 0) activeCount++;
        if (selectedPlayerIdx > 0) activeCount++;
        activeFilterCount = activeCount;

        updateSidebarVisuals();
        selectTab(savedTab);
    }

    private void openProfileOverlay() {
        searchRow.setVisibility(View.GONE);
        profileCardsRow.removeAllViews();
        List<ProfileStore.Profile> profiles = ProfileStore.getProfiles(this);
        String activeId = ProfileStore.getActiveProfileId(this);
        float d = getResources().getDisplayMetrics().density;

        Button firstFocusBtn = null;
        for (final ProfileStore.Profile p : profiles) {
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setGravity(Gravity.CENTER);
            LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            );
            clp.setMargins((int) (10 * d), 0, (int) (10 * d), 0);
            card.setLayoutParams(clp);

            Button btn = new Button(this);
            String initial = p.name.isEmpty() ? "?" : p.name.substring(0, 1).toUpperCase(Locale.ROOT);
            btn.setText(initial + "\n" + p.name + (p.id.equals(activeId) ? " ✓" : ""));
            btn.setAllCaps(false);
            btn.setTextColor(0xFFFFFFFF);
            btn.setTextSize(15f);
            btn.setBackgroundResource(R.drawable.bg_tab_selector);
            btn.setSelected(p.id.equals(activeId));
            btn.setFocusable(true);
            LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams((int) (140 * d), (int) (110 * d));
            btn.setLayoutParams(blp);
            btn.setOnClickListener(v -> {
                ProfileStore.setActiveProfileId(this, p.id);
                closeProfileOverlay();
                loadActiveProfileState();
                Toast.makeText(this, "👤 Профил: " + p.name, Toast.LENGTH_SHORT).show();
            });
            card.addView(btn);

            if (!ProfileStore.DEFAULT_ID.equals(p.id)) {
                Button del = new Button(this);
                del.setText("🗑 Изтрий");
                del.setAllCaps(false);
                del.setTextColor(0xFFFCA5A5);
                del.setTextSize(11f);
                del.setBackgroundResource(R.drawable.bg_btn_secondary);
                del.setFocusable(true);
                LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams((int) (110 * d), (int) (32 * d));
                dlp.topMargin = (int) (6 * d);
                del.setLayoutParams(dlp);
                del.setOnClickListener(v -> {
                    ProfileStore.deleteProfile(this, p.id);
                    openProfileOverlay();
                });
                card.addView(del);
            }

            if (firstFocusBtn == null || p.id.equals(activeId)) {
                firstFocusBtn = btn;
            }
            profileCardsRow.addView(card);
        }

        browseContainer.setDescendantFocusability(ViewGroup.FOCUS_BLOCK_DESCENDANTS);
        profileOverlay.setVisibility(View.VISIBLE);
        final Button focusTarget = firstFocusBtn != null ? firstFocusBtn : profileAddBtn;
        focusTarget.post(() -> focusTarget.requestFocus());
    }

    private void closeProfileOverlay() {
        profileOverlay.setVisibility(View.GONE);
        browseContainer.setDescendantFocusability(ViewGroup.FOCUS_AFTER_DESCENDANTS);
        tabProfileBtn.post(() -> tabProfileBtn.requestFocus());
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
                    closeProfileOverlay();
                    loadActiveProfileState();
                    Toast.makeText(this, "Създаден профил: " + created.name, Toast.LENGTH_SHORT).show();
                }
            })
            .setNegativeButton("Отказ", null)
            .show();
    }

    private void resetAllFilters() {
        selectedSortIdx = 0;
        selectedYearIdx = 0;
        selectedDurationIdx = 0;
        selectedPlayerIdx = 0;
        updateSingleSelectRow(sortBtns, 0);
        updateSingleSelectRow(yearBtns, 0);
        updateSingleSelectRow(durationBtns, 0);
        updateSingleSelectRow(playerBtns, 0);
        for (Map.Entry<String, Button> e : genreBtns.entrySet()) {
            genreStates.put(e.getKey(), 0);
            updateGenreChipVisual(e.getValue(), e.getKey(), 0);
        }
        applyFiltersAndClose();
    }

    private String joinCsv(List<String> list) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(list.get(i));
        }
        return sb.toString();
    }

    private void setupRecycler() {
        GridLayoutManager glm = new GridLayoutManager(this, 5);
        moviesRecycler.setLayoutManager(glm);
        moviesRecycler.setHasFixedSize(false);
        moviesRecycler.setItemAnimator(null);

        adapter = new MovieAdapter(
            (item, pos, view) -> {
                lastFocusedCardView = view;
                openDetails(item);
            },
            () -> {
                if (hasMore && !isLoading) {
                    loadPage(currentPage + 1, false);
                }
            }
        );
        moviesRecycler.setAdapter(adapter);
    }

    private boolean isAnySidebarChildFocused() {
        return tabContinueBtn.hasFocus() || tabFavBtn.hasFocus() || tabLaterBtn.hasFocus()
            || tabBgBtn.hasFocus() || tabSubBtn.hasFocus()
            || tabSeriesBtn.hasFocus() || tabGenreBtn.hasFocus() || tabSearchBtn.hasFocus()
            || tabProfileBtn.hasFocus();
    }

    private void setSidebarExpanded(boolean expanded) {
        if (isSidebarExpanded == expanded) return;
        isSidebarExpanded = expanded;
        updateSidebarVisuals();
    }

    private void updateSidebarVisuals() {
        float d = getResources().getDisplayMetrics().density;
        ViewGroup.LayoutParams lp = leftSidebar.getLayoutParams();
        lp.width = (int) ((isSidebarExpanded ? 176 : 66) * d);
        leftSidebar.setLayoutParams(lp);

        int padH = (int) ((isSidebarExpanded ? 14 : 8) * d);
        leftSidebar.setPadding(padH, (int) (18 * d), padH, (int) (16 * d));

        int btnPad = (int) ((isSidebarExpanded ? 14 : 0) * d);
        int grav = isSidebarExpanded ? (Gravity.START | Gravity.CENTER_VERTICAL) : Gravity.CENTER;

        Button[] navBtns = new Button[]{tabContinueBtn, tabFavBtn, tabLaterBtn, tabBgBtn, tabSubBtn, tabSeriesBtn, tabGenreBtn, tabSearchBtn, tabProfileBtn};
        for (Button b : navBtns) {
            b.setGravity(grav);
            b.setPadding(btnPad, 0, isSidebarExpanded ? (int) (10 * d) : 0, 0);
        }

        int unfinishedCount = WatchHistoryStore.getUnfinishedCount(this);
        int favCount = UserListsStore.getFavoritesCount(this);
        int laterCount = UserListsStore.getWatchLaterCount(this);
        ProfileStore.Profile activeProfile = ProfileStore.getActiveProfile(this);
        tabContinueBtn.setBackgroundResource(unfinishedCount > 0 ? R.drawable.bg_tab_unfinished_active : R.drawable.bg_tab_selector);
        if (isSidebarExpanded) {
            sidebarLogoText.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
            sidebarLogoText.setText("🍿 Пуканки");
            tabContinueBtn.setText(unfinishedCount > 0 ? "⏱  Недовършени (" + unfinishedCount + ")" : "⏱  Недовършени");
            tabFavBtn.setText(favCount > 0 ? "❤️  Любими (" + favCount + ")" : "❤️  Любими");
            tabLaterBtn.setText(laterCount > 0 ? "🔖  За по-късно (" + laterCount + ")" : "🔖  За по-късно");
            tabBgBtn.setText("🇧🇬  БГ Аудио");
            tabSubBtn.setText("💬  Субтитри");
            tabSeriesBtn.setText("📺  Сериали");
            tabGenreBtn.setText(activeFilterCount > 0 ? "⚙  Филтри (" + activeFilterCount + ")" : "⚙  Филтри");
            tabSearchBtn.setText("🔍  Търси");
            tabProfileBtn.setText("👤  " + activeProfile.name);
            statusText.setVisibility(View.VISIBLE);
        } else {
            sidebarLogoText.setGravity(Gravity.CENTER);
            sidebarLogoText.setText("🍿");
            tabContinueBtn.setText(unfinishedCount > 0 ? "⏱" + unfinishedCount : "⏱");
            tabFavBtn.setText(favCount > 0 ? "❤️" + favCount : "❤️");
            tabLaterBtn.setText(laterCount > 0 ? "🔖" + laterCount : "🔖");
            tabBgBtn.setText("🇧🇬");
            tabSubBtn.setText("💬");
            tabSeriesBtn.setText("📺");
            tabGenreBtn.setText(activeFilterCount > 0 ? "⚙" + activeFilterCount : "⚙");
            tabSearchBtn.setText("🔍");
            tabProfileBtn.setText("👤");
            statusText.setVisibility(View.GONE);
        }
    }

    private void setupListeners() {
        View.OnFocusChangeListener sidebarFocusListener = (v, hasFocus) -> {
            if (hasFocus) {
                setSidebarExpanded(true);
            } else {
                leftSidebar.post(() -> {
                    if (!isAnySidebarChildFocused()) {
                        setSidebarExpanded(false);
                    }
                });
            }
        };
        tabContinueBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabFavBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabLaterBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabBgBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabSubBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabSeriesBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabGenreBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabSearchBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabProfileBtn.setOnFocusChangeListener(sidebarFocusListener);
        tabProfileBtn.setOnClickListener(v -> openProfileOverlay());
        profileAddBtn.setOnClickListener(v -> showCreateProfileDialog());
        profileCloseBtn.setOnClickListener(v -> closeProfileOverlay());
        tabContinueBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            filters.query = "";
            selectTab("continue");
        });
        tabFavBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            filters.query = "";
            selectTab("favorites");
        });
        tabLaterBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            filters.query = "";
            selectTab("later");
        });
        tabBgBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            filters.query = "";
            selectTab("bg");
        });
        tabSubBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            filters.query = "";
            selectTab("sub");
        });
        tabSeriesBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            filters.query = "";
            selectTab("series");
        });
        tabGenreBtn.setOnClickListener(v -> openFiltersOverlay());
        tabSearchBtn.setOnClickListener(v -> {
            if (searchRow.getVisibility() == View.VISIBLE) {
                searchRow.setVisibility(View.GONE);
            } else {
                searchRow.setVisibility(View.VISIBLE);
                searchInput.requestFocus();
                InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
                if (imm != null) imm.showSoftInput(searchInput, InputMethodManager.SHOW_IMPLICIT);
            }
        });

        filtersApplyBtn.setOnClickListener(v -> applyFiltersAndClose());
        filtersResetBtn.setOnClickListener(v -> resetAllFilters());
        filtersCloseBtn.setOnClickListener(v -> closeFiltersOverlay());

        searchGoBtn.setOnClickListener(v -> performSearch());
        searchInput.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEARCH || actionId == EditorInfo.IME_ACTION_DONE) {
                performSearch();
                return true;
            }
            return false;
        });

        detailPlayBtn.setOnClickListener(v -> {
            if (activeDetailItem != null) {
                launchPlayer(activeDetailItem, 0);
            }
        });
        detailBackBtn.setOnClickListener(v -> closeDetails());
    }

    private void performSearch() {
        filters.query = searchInput.getText().toString().trim();
        InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (imm != null) imm.hideSoftInputFromWindow(searchInput.getWindowToken(), 0);
        filters.tab = "all";
        updateTabStyles();
        loadPage(1, true);
    }

    private void selectTab(String tab) {
        filters.tab = tab;
        updateTabStyles();
        if ("continue".equals(tab)) {
            loadLocalMovieList(WatchHistoryStore.getUnfinishedMovies(this), "Няма недовършени филми.", "недовършени");
        } else if ("favorites".equals(tab)) {
            loadLocalMovieList(UserListsStore.getFavorites(this), "Няма добавени любими филми.", "любими");
        } else if ("later".equals(tab)) {
            loadLocalMovieList(UserListsStore.getWatchLater(this), "Няма филми в „За по-късно“.", "за по-късно");
        } else {
            loadPage(1, true);
        }
    }

    private void loadLocalMovieList(List<MovieItem> list, String emptyMsg, String label) {
        isLoading = false;
        hasMore = false;
        mainProgress.setVisibility(View.GONE);
        adapter.setItems(list);
        moviesRecycler.scrollToPosition(0);
        if (list.isEmpty()) {
            emptyText.setText(emptyMsg);
            emptyText.setVisibility(View.VISIBLE);
        } else {
            emptyText.setVisibility(View.GONE);
            moviesRecycler.post(() -> {
                RecyclerView.ViewHolder first = moviesRecycler.findViewHolderForAdapterPosition(0);
                if (first != null && detailOverlay.getVisibility() != View.VISIBLE
                    && profileOverlay.getVisibility() != View.VISIBLE) {
                    first.itemView.requestFocus();
                    setSidebarExpanded(false);
                }
            });
        }
        statusText.setText(list.size() + " " + label + "\nv2.4.0");
        updateSidebarVisuals();
    }

    private void updateTabStyles() {
        tabContinueBtn.setSelected("continue".equals(filters.tab));
        tabFavBtn.setSelected("favorites".equals(filters.tab));
        tabLaterBtn.setSelected("later".equals(filters.tab));
        tabBgBtn.setSelected("bg".equals(filters.tab));
        tabSubBtn.setSelected("sub".equals(filters.tab));
        tabSeriesBtn.setSelected("series".equals(filters.tab));
        tabSearchBtn.setSelected("all".equals(filters.tab));
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateSidebarVisuals();
        if ("continue".equals(filters.tab)) {
            loadLocalMovieList(WatchHistoryStore.getUnfinishedMovies(this), "Няма недовършени филми.", "недовършени");
        } else if ("favorites".equals(filters.tab)) {
            loadLocalMovieList(UserListsStore.getFavorites(this), "Няма добавени любими филми.", "любими");
        } else if ("later".equals(filters.tab)) {
            loadLocalMovieList(UserListsStore.getWatchLater(this), "Няма филми в „За по-късно“.", "за по-късно");
        }
    }

    private void loadPage(final int page, final boolean reset) {
        isLoading = true;
        if (reset) {
            mainProgress.setVisibility(View.VISIBLE);
            emptyText.setVisibility(View.GONE);
            statusText.setText("Зареждане...");
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
                    if (result.items.isEmpty()) {
                        emptyText.setVisibility(View.VISIBLE);
                    } else {
                        emptyText.setVisibility(View.GONE);
                        moviesRecycler.post(() -> {
                            RecyclerView.ViewHolder first = moviesRecycler.findViewHolderForAdapterPosition(0);
                            if (first != null && detailOverlay.getVisibility() != View.VISIBLE
                                && searchRow.getVisibility() != View.VISIBLE
                                && filtersOverlay.getVisibility() != View.VISIBLE) {
                                first.itemView.requestFocus();
                                setSidebarExpanded(false);
                            }
                        });
                    }
                } else {
                    adapter.appendItems(result.items);
                }
                statusText.setText(totalCount + " заглавия\nv2.4.1");
            }

            @Override
            public void onError(String message) {
                isLoading = false;
                mainProgress.setVisibility(View.GONE);
                statusText.setText("Грешка: " + message);
                Toast.makeText(MainActivity.this, "Грешка при зареждане: " + message, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void openDetails(MovieItem item) {
        activeDetailItem = item;
        detailTitle.setText(item.title);

        StringBuilder meta = new StringBuilder();
        if (item.year > 0) meta.append(item.year);
        if (item.rating > 0) meta.append(meta.length() > 0 ? "  •  " : "").append(String.format(Locale.US, "★ %.1f", item.rating));
        if (item.duration > 0) meta.append(meta.length() > 0 ? "  •  " : "").append(item.duration).append(" мин");
        meta.append(meta.length() > 0 ? "  •  " : "").append(item.isBgAudio ? "🇧🇬 БГ Аудио" : "💬 БГ Субтитри");
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

        detailSourcesContainer.removeAllViews();
        List<MovieItem.PlayerSource> sources = item.sources;
        int marginPx = (int) (8 * getResources().getDisplayMetrics().density);
        Button prevBtn = null;
        Button firstBtn = null;
        for (int i = 0; i < sources.size(); i++) {
            final int idx = i;
            MovieItem.PlayerSource src = sources.get(i);
            Button btn = new Button(this);
            btn.setId(View.generateViewId());
            btn.setText(src.name);
            btn.setAllCaps(false);
            btn.setTextColor(0xFFFFFFFF);
            btn.setTextSize(13f);
            btn.setBackgroundResource(R.drawable.bg_btn_secondary);
            btn.setPadding(24, 8, 24, 8);
            btn.setFocusable(true);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                (int) (38 * getResources().getDisplayMetrics().density)
            );
            lp.setMarginEnd(marginPx);
            btn.setLayoutParams(lp);
            btn.setNextFocusUpId(R.id.detailPlayBtn);
            if (prevBtn != null) {
                btn.setNextFocusLeftId(prevBtn.getId());
                prevBtn.setNextFocusRightId(btn.getId());
            } else {
                firstBtn = btn;
            }
            prevBtn = btn;
            btn.setOnClickListener(v -> launchPlayer(item, idx));
            detailSourcesContainer.addView(btn);
        }
        if (firstBtn != null) {
            detailPlayBtn.setNextFocusDownId(firstBtn.getId());
            detailFavBtn.setNextFocusDownId(firstBtn.getId());
            detailLaterBtn.setNextFocusDownId(firstBtn.getId());
            detailBackBtn.setNextFocusDownId(firstBtn.getId());
        } else {
            detailPlayBtn.setNextFocusDownId(View.NO_ID);
            detailFavBtn.setNextFocusDownId(View.NO_ID);
            detailLaterBtn.setNextFocusDownId(View.NO_ID);
            detailBackBtn.setNextFocusDownId(View.NO_ID);
        }

        updateDetailListButtons(item);
        detailFavBtn.setOnClickListener(v -> {
            boolean added = UserListsStore.toggleFavorite(this, item);
            updateDetailListButtons(item);
            updateSidebarVisuals();
            Toast.makeText(this, added ? "❤️ Добавен в Любими" : "Премахнат от Любими", Toast.LENGTH_SHORT).show();
            if ("favorites".equals(filters.tab)) {
                loadLocalMovieList(UserListsStore.getFavorites(this), "Няма добавени любими филми.", "любими");
            }
        });
        detailLaterBtn.setOnClickListener(v -> {
            boolean added = UserListsStore.toggleWatchLater(this, item);
            updateDetailListButtons(item);
            updateSidebarVisuals();
            Toast.makeText(this, added ? "🔖 Добавен в „За по-късно“" : "Премахнат от „За по-късно“", Toast.LENGTH_SHORT).show();
            if ("later".equals(filters.tab)) {
                loadLocalMovieList(UserListsStore.getWatchLater(this), "Няма филми в „За по-късно“.", "за по-късно");
            }
        });

        browseContainer.setDescendantFocusability(ViewGroup.FOCUS_BLOCK_DESCENDANTS);
        detailOverlay.setVisibility(View.VISIBLE);
        detailPlayBtn.post(() -> detailPlayBtn.requestFocus());
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
        browseContainer.setDescendantFocusability(ViewGroup.FOCUS_AFTER_DESCENDANTS);
        activeDetailItem = null;
        if (lastFocusedCardView != null) {
            lastFocusedCardView.requestFocus();
        } else {
            moviesRecycler.requestFocus();
        }
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

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (detailOverlay.getVisibility() == View.VISIBLE) {
                closeDetails();
                return true;
            }
            if (profileOverlay.getVisibility() == View.VISIBLE) {
                closeProfileOverlay();
                return true;
            }
            if (filtersOverlay.getVisibility() == View.VISIBLE) {
                closeFiltersOverlay();
                return true;
            }
            if (searchRow.getVisibility() == View.VISIBLE) {
                searchRow.setVisibility(View.GONE);
                moviesRecycler.requestFocus();
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
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
