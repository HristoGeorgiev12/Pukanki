package com.pukanki.tv;

import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.bumptech.glide.Glide;
import com.bumptech.glide.load.engine.DiskCacheStrategy;

import java.util.ArrayList;
import java.util.List;

public class MovieAdapter extends RecyclerView.Adapter<MovieAdapter.VH> {
    public interface OnMovieClickListener {
        void onMovieClick(MovieItem item, int position, View itemView);
    }

    public interface OnNearEndListener {
        void onNearEnd();
    }

    private final List<MovieItem> items = new ArrayList<>();
    private final OnMovieClickListener clickListener;
    private final OnNearEndListener nearEndListener;

    public MovieAdapter(OnMovieClickListener clickListener, OnNearEndListener nearEndListener) {
        this.clickListener = clickListener;
        this.nearEndListener = nearEndListener;
    }

    public void setItems(List<MovieItem> newItems) {
        items.clear();
        items.addAll(newItems);
        notifyDataSetChanged();
    }

    public void appendItems(List<MovieItem> moreItems) {
        int start = items.size();
        items.addAll(moreItems);
        notifyItemRangeInserted(start, moreItems.size());
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_movie_card, parent, false);
        return new VH(v);
    }

    @Override
    public void onBindViewHolder(@NonNull VH h, int position) {
        MovieItem item = items.get(position);
        h.title.setText(item.title);

        if (item.resumePositionMs > 0) {
            h.meta.setText(WatchHistoryStore.formatProgressShort(item.resumePositionMs, item.resumeDurationMs));
            h.meta.setTextColor(Color.parseColor("#34D399"));
        } else {
            StringBuilder meta = new StringBuilder();
            if (item.year > 0) meta.append(item.year);
            if (item.duration > 0) {
                if (meta.length() > 0) meta.append(" • ");
                meta.append(item.duration).append(" мин");
            }
            h.meta.setText(meta.toString());
            h.meta.setTextColor(Color.parseColor("#94A3B8"));
        }

        if (item.rating > 0) {
            h.rating.setVisibility(View.VISIBLE);
            h.rating.setText(String.format("★ %.1f", item.rating));
        } else {
            h.rating.setVisibility(View.GONE);
        }

        if (item.isBgAudio) {
            h.badge.setText("BG");
            h.badge.setBackgroundColor(Color.parseColor("#D910B981"));
        } else {
            h.badge.setText("SUB");
            h.badge.setBackgroundColor(Color.parseColor("#D93B82F6"));
        }

        Glide.with(h.poster.getContext())
            .load(item.posterUrl)
            .diskCacheStrategy(DiskCacheStrategy.ALL)
            .centerCrop()
            .override(240, 360)
            .into(h.poster);

        h.itemView.setOnFocusChangeListener((v, hasFocus) -> {
            float scale = hasFocus ? 1.06f : 1.0f;
            v.animate().scaleX(scale).scaleY(scale).setDuration(120).start();
            v.setElevation(hasFocus ? 12f : 0f);
        });

        h.itemView.setOnClickListener(v -> {
            int pos = h.getBindingAdapterPosition();
            if (pos != RecyclerView.NO_POSITION && clickListener != null) {
                clickListener.onMovieClick(items.get(pos), pos, v);
            }
        });

        if (nearEndListener != null && position >= items.size() - 12) {
            nearEndListener.onNearEnd();
        }
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class VH extends RecyclerView.ViewHolder {
        ImageView poster;
        TextView badge;
        TextView rating;
        TextView title;
        TextView meta;

        VH(@NonNull View itemView) {
            super(itemView);
            poster = itemView.findViewById(R.id.cardPoster);
            badge = itemView.findViewById(R.id.cardBadge);
            rating = itemView.findViewById(R.id.cardRating);
            title = itemView.findViewById(R.id.cardTitle);
            meta = itemView.findViewById(R.id.cardMeta);
        }
    }
}
