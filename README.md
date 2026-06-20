# 🎬 Movie Recommendation System

A Netflix-inspired movie recommendation engine built from scratch in Python for a Data Structures & Algorithms semester project — no ML libraries, no `pandas`, no `scikit-learn`. Every data structure and similarity formula is hand-implemented.

Runs in two modes: a terminal CLI and a browser-based GUI (Netflix-style dark theme), both powered by the same underlying recommendation logic.

## Features

- **Trending** — ranked list using a log-dampened popularity formula
- **Continue Watching** — resumes in-progress titles with progress bars
- **Genre Recommendations** — personalized picks based on a user's genre history
- **You Might Also Like** — item-item collaborative filtering
- **People Like You Watched** — user-user collaborative filtering
- **Actor Picks** — recommendations filtered by favorite actors
- **Hybrid Recommendations** — blended score combining all engines
- **New User Onboarding** — cold-start handling via seeded genre preferences
- **Rate a Movie** — updates the ratings matrix in real time

## Tech Stack

- **Language:** Python 3 (standard library only — no external dependencies)
- **CLI Interface:** `main_integ(zainab).py`
- **GUI Interface:** `gui.py` — vanilla HTML/CSS/JS served via Python's built-in `http.server`, no frameworks
- **Dataset:** [MovieLens 100K](https://grouplens.org/datasets/movielens/100k/) (`u.data`, `u.item`)

## Core Algorithms

| Concept | Implementation |
|---|---|
| **Sparse Matrix ADT** | Hash-map-of-hash-maps (`{row: {col: value}}`) storing only non-zero entries — avoids wasting memory on millions of unrated user-movie pairs |
| **Cosine Similarity** | Computed manually via dot product and magnitude over sparse rows, used to find similar users and similar movies |
| **Item-Item CF** | Transposes the ratings matrix (rows become movies) and finds similar items by shared user ratings |
| **User-User CF** | Finds the *k* most similar users by taste vector, then surfaces their highly-rated unseen movies |
| **Hybrid Score** | `0.5 × collaborative + 0.3 × item-item + 0.2 × genre match` |
| **Trending Formula** | `avg_rating × log(vote_count + 1)` — dampens pure popularity so quality still counts |
| **Cold Start** | New users are seeded with genre preferences before any rating data exists |

## Project Structure

```
DSA/
├── main_integ(zainab).py       # CLI entry point — menu-driven interface
├── gui.py                      # Browser-based GUI (Netflix-style)
├── sparse_matrix_zun.py        # Sparse matrix ADT + similarity math
├── load_data_zun.py            # Parses u.data / u.item into matrices
├── movie_info_zainab.py        # Movie title/genre/year lookups
├── user_profiles_zainab.py     # Continue watching, genre recs, actor recs, onboarding
├── similarity_engine_common.py # User-user collaborative filtering
├── item_item_sidrah.py         # Item-item collaborative filtering
├── recommender_sidrah.py       # Hybrid recommendation engine
├── weighted_score_common.py    # Central scoring formula + trending
├── actors.csv                  # Actor → movie mapping
├── watch_progress.csv          # Per-user watch progress
├── u.data / u.item             # MovieLens 100K dataset
```

## How to Run

**Clone the repo:**
```bash
git clone https://github.com/yourusername/movie-recommendation-system.git
cd movie-recommendation-system
```

**Option 1 — CLI version:**
```bash
python "main_integ(zainab).py"
```

**Option 2 — GUI version:**
```bash
python gui.py
```
Then open **http://localhost:5000** in your browser.

No external packages required — only the Python standard library.

## Team

Built by **[Your Name]**, **Sidrah Bilal**, and **Zunairah Iqbal** for our Data Structures & Algorithms course.

## License

MIT
