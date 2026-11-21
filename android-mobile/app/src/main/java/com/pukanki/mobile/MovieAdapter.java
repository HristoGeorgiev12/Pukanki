package com.pukanki.mobile;

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
import java.util.Locale;

public class MovieAdapter extends RecyclerView.Adapter<MovieAdapter.MovieViewHolder> {

    public interface OnMovieClickListener {
        void onMovieClick(MovieItem item);
    }

    private final List<MovieItem> items = new ArrayList<>();
    private final OnMovieClickListener clickListener;

    public MovieAdapter(OnMovieClickListener clickListener) {
        this.clickListener = clickListener;
    }

    public void setItems(List<MovieItem> newItems) {
        items.clear();
        if (newItems != null) {
            items.addAll(newItems);
        }
        notifyDataSetChanged();
    }

    public void appendItems(List<MovieItem> moreItems) {
        if (moreItems == null || moreItems.isEmpty()) return;
        int start = items.size();
        items.addAll(moreItems);
        notifyItemRangeInserted(start, moreItems.size());
    }

    @NonNull
    @Override
    public MovieViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_movie_card, parent, false);
        return new MovieViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull MovieViewHolder h, int position) {
        MovieItem item = items.get(position);
        h.title.setText(item.title);

        if (item.resumePositionMs > 0) {
            h.subtitle.setText(WatchHistoryStore.formatProgressShort(item.resumePositionMs, item.resumeDurationMs));
            h.subtitle.setTextColor(0xFF34D399);
        } else {
            StringBuilder sub = new StringBuilder();
            if (item.year > 0) sub.append(item.year);
            if (item.duration > 0) {
                if (sub.length() > 0) sub.append(" • ");
                sub.append(item.duration).append("м");
            }
            h.subtitle.setText(sub.toString());
            h.subtitle.setTextColor(0xFF94A3B8);
        }

        if (item.rating > 0) {
            h.rating.setVisibility(View.VISIBLE);
            h.rating.setText(String.format(Locale.US, "★ %.1f", item.rating));
        } else {
            h.rating.setVisibility(View.GONE);
        }

        if (item.isBgAudio) {
            h.badge.setText("BG");
            h.badge.setBackgroundColor(0xD910B981);
        } else {
            h.badge.setText("SUB");
            h.badge.setBackgroundColor(0xD93B82F6);
        }

        if (item.posterUrl != null && !item.posterUrl.isEmpty()) {
            Glide.with(h.poster.getContext())
                .load(item.posterUrl)
                .diskCacheStrategy(DiskCacheStrategy.AUTOMATIC)
                .centerCrop()
                .into(h.poster);
        } else {
            h.poster.setImageDrawable(null);
        }

        h.itemView.setOnClickListener(v -> {
            if (clickListener != null) {
                clickListener.onMovieClick(item);
            }
        });
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class MovieViewHolder extends RecyclerView.ViewHolder {
        ImageView poster;
        TextView title, subtitle, rating, badge;

        MovieViewHolder(@NonNull View itemView) {
            super(itemView);
            poster = itemView.findViewById(R.id.cardPoster);
            title = itemView.findViewById(R.id.cardTitle);
            subtitle = itemView.findViewById(R.id.cardSubtitle);
            rating = itemView.findViewById(R.id.cardRating);
            badge = itemView.findViewById(R.id.cardBadge);
        }
    }
}
