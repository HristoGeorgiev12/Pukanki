package com.pukanki.tv;

import android.content.Intent;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
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

import java.util.List;

public class MainActivity extends AppCompatActivity {
    private static final int PAGE_SIZE = 30;

    private Button tabBgBtn, tabSubBtn, tabSeriesBtn, tabGenreBtn, tabSearchBtn, searchGoBtn;
    private LinearLayout searchRow, genreChipsContainer;
    private View genreScrollRow;
    private EditText searchInput;
    private TextView statusText, emptyText;
    private ProgressBar mainProgress;
    private RecyclerView moviesRecycler;
    private MovieAdapter adapter;

    private FrameLayout detailOverlay;
    private ImageView detailBackdrop, detailPoster;
    private TextView detailTitle, detailMeta, detailOverview;
    private Button detailPlayBtn, detailBackBtn;
    private LinearLayout detailSourcesContainer;

    private String currentTab = "bg";
    private String currentGenre = "";
    private String currentQuery = "";
    private int currentPage = 1;
    private boolean hasMore = false;
    private boolean isLoading = false;
    private int totalCount = 0;

    private static final String[] GENRES = new String[]{
        "Всички", "Екшън", "Комедия", "Анимация", "Трилър", "Фантастика",
        "Драма", "Ужаси", "Приключенски", "Фентъзи", "Криминален", "Семеен", "Романтичен"
    };

    private MovieItem activeDetailItem = null;
    private View lastFocusedCardView = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        hideSystemUI();
        setContentView(R.layout.activity_main);

        bindViews();
        setupRecycler();
        setupListeners();
        selectTab("bg");
    }

    private void bindViews() {
        tabBgBtn = findViewById(R.id.tabBgBtn);
        tabSubBtn = findViewById(R.id.tabSubBtn);
        tabSeriesBtn = findViewById(R.id.tabSeriesBtn);
        tabGenreBtn = findViewById(R.id.tabGenreBtn);
        tabSearchBtn = findViewById(R.id.tabSearchBtn);
        genreScrollRow = findViewById(R.id.genreScrollRow);
        genreChipsContainer = findViewById(R.id.genreChipsContainer);
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
        detailBackBtn = findViewById(R.id.detailBackBtn);
        detailSourcesContainer = findViewById(R.id.detailSourcesContainer);

        buildGenreChips();
    }

    private void buildGenreChips() {
        genreChipsContainer.removeAllViews();
        float d = getResources().getDisplayMetrics().density;
        int marginEnd = (int) (8 * d);
        int heightPx = (int) (34 * d);
        for (final String g : GENRES) {
            Button chip = new Button(this);
            chip.setText(g);
            chip.setAllCaps(false);
            chip.setTextColor(0xFFFFFFFF);
            chip.setTextSize(12f);
            chip.setBackgroundResource(R.drawable.bg_tab_selector);
            chip.setPadding((int) (14 * d), 0, (int) (14 * d), 0);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, heightPx
            );
            lp.setMarginEnd(marginEnd);
            chip.setLayoutParams(lp);
            chip.setSelected("Всички".equals(g));
            chip.setOnClickListener(v -> {
                currentGenre = "Всички".equals(g) ? "" : g;
                tabGenreBtn.setText(currentGenre.isEmpty() ? "🎭 Жанр" : "🎭 " + currentGenre);
                for (int i = 0; i < genreChipsContainer.getChildCount(); i++) {
                    View child = genreChipsContainer.getChildAt(i);
                    child.setSelected(child == chip);
                }
                genreScrollRow.setVisibility(View.GONE);
                loadPage(1, true);
            });
            genreChipsContainer.addView(chip);
        }
    }

    private void setupRecycler() {
        GridLayoutManager glm = new GridLayoutManager(this, 6);
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

    private void setupListeners() {
        tabBgBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            currentQuery = "";
            selectTab("bg");
        });
        tabSubBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            currentQuery = "";
            selectTab("sub");
        });
        tabSeriesBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            genreScrollRow.setVisibility(View.GONE);
            currentQuery = "";
            selectTab("series");
        });
        tabGenreBtn.setOnClickListener(v -> {
            searchRow.setVisibility(View.GONE);
            if (genreScrollRow.getVisibility() == View.VISIBLE) {
                genreScrollRow.setVisibility(View.GONE);
            } else {
                genreScrollRow.setVisibility(View.VISIBLE);
                if (genreChipsContainer.getChildCount() > 0) {
                    genreChipsContainer.getChildAt(0).requestFocus();
                }
            }
        });
        tabSearchBtn.setOnClickListener(v -> {
            genreScrollRow.setVisibility(View.GONE);
            if (searchRow.getVisibility() == View.VISIBLE) {
                searchRow.setVisibility(View.GONE);
            } else {
                searchRow.setVisibility(View.VISIBLE);
                searchInput.requestFocus();
                InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
                if (imm != null) imm.showSoftInput(searchInput, InputMethodManager.SHOW_IMPLICIT);
            }
        });

        searchGoBtn.setOnClickListener(v -> performSearch());
        searchInput.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEARCH || actionId == EditorInfo.IME_ACTION_DONE
                || (event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER)) {
                performSearch();
                return true;
            }
            return false;
        });

        detailBackBtn.setOnClickListener(v -> closeDetails());
        detailPlayBtn.setOnClickListener(v -> {
            if (activeDetailItem != null) {
                launchPlayer(activeDetailItem, 0);
            }
        });
    }

    private void performSearch() {
        currentQuery = searchInput.getText().toString().trim();
        InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (imm != null) imm.hideSoftInputFromWindow(searchInput.getWindowToken(), 0);
        currentTab = "all";
        updateTabStyles();
        loadPage(1, true);
    }

    private void selectTab(String tab) {
        currentTab = tab;
        updateTabStyles();
        loadPage(1, true);
    }

    private void updateTabStyles() {
        tabBgBtn.setSelected("bg".equals(currentTab));
        tabSubBtn.setSelected("sub".equals(currentTab));
        tabSeriesBtn.setSelected("series".equals(currentTab));
        tabSearchBtn.setSelected("all".equals(currentTab));
    }

    private void loadPage(final int page, final boolean reset) {
        isLoading = true;
        if (reset) {
            mainProgress.setVisibility(View.VISIBLE);
            emptyText.setVisibility(View.GONE);
            statusText.setText("Зареждане...");
        }

        CatalogApi.fetchPage(currentTab, currentGenre, currentQuery, page, PAGE_SIZE, new CatalogApi.Callback() {
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
                                && genreScrollRow.getVisibility() != View.VISIBLE) {
                                first.itemView.requestFocus();
                            }
                        });
                    }
                } else {
                    adapter.appendItems(result.items);
                }
                statusText.setText(totalCount + " заглавия • v2.0.2");
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
        if (item.rating > 0) meta.append(meta.length() > 0 ? "  •  " : "").append(String.format("★ %.1f", item.rating));
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

        // Populate optional player buttons below Play button
        detailSourcesContainer.removeAllViews();
        List<MovieItem.PlayerSource> sources = item.sources;
        int marginPx = (int) (8 * getResources().getDisplayMetrics().density);
        for (int i = 0; i < sources.size(); i++) {
            final int idx = i;
            MovieItem.PlayerSource src = sources.get(i);
            Button btn = new Button(this);
            btn.setText(src.name);
            btn.setAllCaps(false);
            btn.setTextColor(0xFFFFFFFF);
            btn.setTextSize(13f);
            btn.setBackgroundResource(R.drawable.bg_btn_secondary);
            btn.setPadding(24, 8, 24, 8);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                (int) (38 * getResources().getDisplayMetrics().density)
            );
            lp.setMarginEnd(marginPx);
            btn.setLayoutParams(lp);
            btn.setOnClickListener(v -> launchPlayer(item, idx));
            detailSourcesContainer.addView(btn);
        }

        detailOverlay.setVisibility(View.VISIBLE);
        detailPlayBtn.post(() -> detailPlayBtn.requestFocus());
    }

    private void closeDetails() {
        detailOverlay.setVisibility(View.GONE);
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
            if (genreScrollRow.getVisibility() == View.VISIBLE) {
                genreScrollRow.setVisibility(View.GONE);
                tabGenreBtn.requestFocus();
                return true;
            }
            if (searchRow.getVisibility() == View.VISIBLE) {
                searchRow.setVisibility(View.GONE);
                if (!currentQuery.isEmpty()) {
                    currentQuery = "";
                    selectTab("bg");
                }
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        hideSystemUI();
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
