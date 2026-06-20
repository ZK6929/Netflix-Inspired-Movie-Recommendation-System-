#user profile functions — all milestones
# M1: continue watching
# M2: genre recs
# M3: fav actor
# M4: new user onboarding
# M5: title display via movie_info

from sparse_matrix_zun import (
    create_sparmat, insert_sparmat, get_sparmat, get_row_ent, get_col_ent,
    update_sparmat
)
from movie_info_zainab import format_movie, get_genres, get_title
from weighted_score_common import compute_weighted_score, normalise_vote_counts, get_trending


### [DATA LOADERS]:-

# O(A) where A = rows in actors.csv
def load_actor_movie_matrix(filepath='actors.csv'):
    #reads actors.csv and builds actor->movie sparse matrix + name lookup
    actor_movie_matrix = create_sparmat()
    actor_names = {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            next(f)  # skip header line
            for line in f:
                parts = line.strip().split(',')
                if len(parts) < 3:
                    continue
                actor_id = parts[0].strip()
                name     = parts[1].strip()
                movie_id = parts[2].strip()
                insert_sparmat(actor_movie_matrix, actor_id, movie_id, 1)
                actor_names[actor_id] = name
    except FileNotFoundError:
        print(f"[Warning] '{filepath}' not found — actor feature disabled.")

    return actor_movie_matrix, actor_names


### [MILESTONE 1 — Continue Watching]:-

# O(W) where W = movies in user's watch progress row
def get_continue_watching(user_id, watch_progress_matrix, movie_info, top_n=10):
    #return movies user started but didnt finish (progress 1-99)
    progress_row = get_row_ent(watch_progress_matrix, user_id)

    in_progress = []
    for movie_id in progress_row:
        pct = progress_row[movie_id]
        if 1 <= pct <= 99:
            in_progress.append((movie_id, pct))

    #closest to done comes first
    in_progress.sort(key=lambda x: x[1], reverse=True)

    result = []
    idx = 0
    while idx < len(in_progress) and idx < top_n:
        movie_id, pct = in_progress[idx]
        label = format_movie(movie_id, movie_info)
        result.append((label, pct))
        idx += 1
    return result


# O(1)
def update_watch_progress(user_id, movie_id, progress_pct, watch_progress_matrix):
    #update or record watch progress for a movie
    update_sparmat(watch_progress_matrix, str(user_id), str(movie_id), float(progress_pct))


### [MILESTONE 2 — Genre Recs]:-

# O(R * G + C * U) where R=rated movies, G=genres, C=candidates, U=users
def get_genre_recommendations(user_id, ratings_matrix, movie_genre_matrix,
                               movie_info, top_n=10):
    #recommend movies based on genres the user likes most
    #builds a genre preference profile then finds unseen movies in top 3 genres

    user_ratings = get_row_ent(ratings_matrix, str(user_id))
    if not user_ratings:
        return []

    watched_ids = set(user_ratings.keys())

    #step 1: build genre preference weights from user's rated movies
    genre_score = {}
    for movie_id in user_ratings:
        rating = user_ratings[movie_id]
        movie_genres_row = get_row_ent(movie_genre_matrix, movie_id)
        for genre in movie_genres_row:
            if genre not in genre_score:
                genre_score[genre] = 0.0
            genre_score[genre] += rating

    if not genre_score:
        return []

    #top 3 genres by accumulated rating weight
    sorted_genres = sorted(genre_score, key=genre_score.get, reverse=True)
    top_genres = sorted_genres[:3]

    #step 2: collect candidate movies from those genres
    candidates = {}  # movie_id -> {sum, votes, genre_hits}

    for genre in top_genres:
        movies_in_genre = get_col_ent(movie_genre_matrix, genre)
        for movie_id in movies_in_genre:
            if movie_id in watched_ids:
                continue
            if movie_id not in candidates:
                candidates[movie_id] = {'sum': 0.0, 'votes': 0, 'genre_hits': 0}
            candidates[movie_id]['genre_hits'] += 1

    if not candidates:
        return []

    #step 3: gather global rating stats for each candidate
    to_remove = []
    for movie_id in candidates:
        col_data = get_col_ent(ratings_matrix, movie_id)
        if not col_data:
            to_remove.append(movie_id)
            continue
        all_ratings = list(col_data.values())
        candidates[movie_id]['sum']   = sum(all_ratings)
        candidates[movie_id]['votes'] = len(all_ratings)

    for mid in to_remove:
        candidates.pop(mid)

    if not candidates:
        return []

    #step 4: score and rank using weighted formula
    vote_counts = {}
    for mid in candidates:
        vote_counts[mid] = candidates[mid]['votes']

    vote_norms = normalise_vote_counts(vote_counts)

    max_hits = 1
    for d in candidates.values():
        if d['genre_hits'] > max_hits:
            max_hits = d['genre_hits']

    scored = []
    for movie_id in candidates:
        data        = candidates[movie_id]
        avg_rating  = data['sum'] / data['votes']
        vote_norm   = vote_norms[movie_id]
        genre_match = data['genre_hits'] / max_hits
        ws = compute_weighted_score(avg_rating, data['votes'], vote_norm, genre_match)
        scored.append((movie_id, ws))

    scored.sort(key=lambda x: x[1], reverse=True)

    result = []
    for mid, score in scored[:top_n]:
        result.append((format_movie(mid, movie_info), score))
    return result


### [MILESTONE 3 — Fav Actor]:-

# O(F * M + C * U) where F=fav actors, M=movies per actor, C=candidates, U=users
def get_actor_recommendations(user_id, favourite_actor_ids,
                               actor_movie_matrix, ratings_matrix,
                               movie_info, top_n=10):
    #recommend unseen movies featuring the user's fav actors
    user_id    = str(user_id)
    candidates = {}  # movie_id -> {actor_count}

    for actor_id in favourite_actor_ids:
        actor_movies = get_row_ent(actor_movie_matrix, str(actor_id))
        for movie_id in actor_movies:
            #skip if already watched
            if get_sparmat(ratings_matrix, user_id, movie_id) != 0:
                continue
            if movie_id not in candidates:
                candidates[movie_id] = {'actor_count': 0}
            candidates[movie_id]['actor_count'] += 1

    if not candidates:
        return []

    #gather rating stats for each candidate
    to_remove = []
    for movie_id in candidates:
        col_data = get_col_ent(ratings_matrix, movie_id)
        if not col_data:
            to_remove.append(movie_id)
            continue
        all_ratings = list(col_data.values())
        candidates[movie_id]['sum']   = sum(all_ratings)
        candidates[movie_id]['votes'] = len(all_ratings)

    for mid in to_remove:
        candidates.pop(mid)

    if not candidates:
        return []

    vote_counts = {}
    for mid in candidates:
        vote_counts[mid] = candidates[mid]['votes']

    vote_norms  = normalise_vote_counts(vote_counts)

    max_actors = 1
    for d in candidates.values():
        if d['actor_count'] > max_actors:
            max_actors = d['actor_count']

    scored = []
    for movie_id in candidates:
        data        = candidates[movie_id]
        avg_rating  = data['sum'] / data['votes']
        vote_norm   = vote_norms[movie_id]
        genre_match = data['actor_count'] / max_actors  #more fav actors = higher match
        ws = compute_weighted_score(avg_rating, data['votes'], vote_norm, genre_match)
        scored.append((movie_id, ws))

    scored.sort(key=lambda x: x[1], reverse=True)

    result = []
    for mid, score in scored[:top_n]:
        result.append((format_movie(mid, movie_info), score))
    return result


### [MILESTONE 4 — New User Onboarding]:-

AVAILABLE_GENRES = [
    'Action', 'Adventure', 'Animation', "Children's", 'Comedy',
    'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir',
    'Horror', 'Musical', 'Mystery', 'Romance', 'Sci-Fi',
    'Thriller', 'War', 'Western'
]


# O(1)
def is_new_user(user_id, ratings_matrix):
    #return True if user has no ratings yet
    return len(get_row_ent(ratings_matrix, str(user_id))) == 0


# O(T) where T = trending computation cost
def onboard_new_user(user_id, ratings_matrix, movie_genre_matrix,
                     movie_info, actor_movie_matrix=None, actor_names=None):
    #interactive setup for brand new users
    # 1. pick 3 genres
    # 2. optionally pick a fav actor
    # 3. show trending movies until they have 5 ratings

    user_id = str(user_id)
    user_genre_matrix = create_sparmat()

    print("\n" + "=" * 50)
    print("  Welcome! Lets set up your profile.")
    print("=" * 50)

    #step 1: genre selection
    print("\n  Available genres:")
    idx = 0
    while idx < len(AVAILABLE_GENRES):
        print(f"    {idx+1:2}. {AVAILABLE_GENRES[idx]}")
        idx += 1

    chosen_genres = []
    while len(chosen_genres) < 3:
        remaining = 3 - len(chosen_genres)
        raw = input(f"\n  Enter genre number ({remaining} remaining): ").strip()
        if not raw.isdigit():
            print("  Please enter a number.")
            continue
        pick = int(raw) - 1
        if pick < 0 or pick >= len(AVAILABLE_GENRES):
            print(f"  Enter a number between 1 and {len(AVAILABLE_GENRES)}.")
            continue
        genre = AVAILABLE_GENRES[pick]
        if genre in chosen_genres:
            print(f"  '{genre}' already selected.")
            continue
        chosen_genres.append(genre)
        print(f"  Added '{genre}'  ({len(chosen_genres)}/3)")

    #seed genre prefs into the matrix
    for genre in chosen_genres:
        insert_sparmat(user_genre_matrix, user_id, genre, 1.0)

    print(f"\n  Your genres: {', '.join(chosen_genres)}")

    #step 2: optional fav actor
    if actor_movie_matrix and actor_names:
        print("\n  Want to pick a favourite actor? (y/n): ", end='')
        ans = input().strip().lower()
        if ans == 'y':
            print("\n  Available actors:")
            actor_list = sorted(actor_names.items(), key=lambda x: int(x[0]))
            for actor_id, name in actor_list:
                print(f"    {actor_id:>3}. {name}")
            raw = input("\n  Enter actor number (or Enter to skip): ").strip()
            if raw.isdigit() and raw in actor_names:
                fav_actor = actor_names[raw]
                insert_sparmat(user_genre_matrix, user_id, f"actor:{raw}", 1.0)
                print(f"  Fav actor set to {fav_actor}")

    #step 3: show trending until 5 ratings
    rating_count = len(get_row_ent(ratings_matrix, user_id))

    if rating_count < 5:
        print(f"\n  You have {rating_count} rating(s). Rate atleast 5 to unlock personalised recs.")
        print("\n  Trending movies to get you started:\n")
        trending = get_trending(ratings_matrix, top_n=10)
        rank = 1
        for movie_id, score in trending:
            label = format_movie(movie_id, movie_info)
            print(f"  {rank:2}. {label}  (score: {score:.2f})")
            rank += 1
        print("\n  Use option 8 from main menu to rate movies.")
    else:
        print("\n  You're all set! Personalised recs are available.")

    return user_genre_matrix


# O(G * M + C * U) similar to genre recs above
def get_seeded_genre_recommendations(user_id, user_genre_matrix,
                                     movie_genre_matrix, ratings_matrix,
                                     movie_info, top_n=10):
    #genre recs for new users based on onboarding prefs (not rated movies)
    user_id     = str(user_id)
    user_genres = get_row_ent(user_genre_matrix, user_id)

    if not user_genres:
        return []

    #exclude actor:* keys
    genre_keys = []
    for g in user_genres:
        if not g.startswith('actor:'):
            genre_keys.append(g)

    watched = set(get_row_ent(ratings_matrix, user_id).keys())

    candidates = {}
    for genre in genre_keys:
        for movie_id in get_col_ent(movie_genre_matrix, genre):
            if movie_id in watched:
                continue
            if movie_id not in candidates:
                candidates[movie_id] = {'genre_hits': 0}
            candidates[movie_id]['genre_hits'] += 1

    if not candidates:
        return []

    to_remove = []
    for movie_id in candidates:
        col_data = get_col_ent(ratings_matrix, movie_id)
        if not col_data:
            to_remove.append(movie_id)
            continue
        all_ratings = list(col_data.values())
        candidates[movie_id]['sum']   = sum(all_ratings)
        candidates[movie_id]['votes'] = len(all_ratings)

    for mid in to_remove:
        candidates.pop(mid)

    if not candidates:
        return []

    vote_counts = {}
    for mid in candidates:
        vote_counts[mid] = candidates[mid]['votes']

    vote_norms = normalise_vote_counts(vote_counts)

    max_hits = 1
    for d in candidates.values():
        if d['genre_hits'] > max_hits:
            max_hits = d['genre_hits']

    scored = []
    for mid in candidates:
        d = candidates[mid]
        ws = compute_weighted_score(
            d['sum'] / d['votes'],
            d['votes'],
            vote_norms[mid],
            d['genre_hits'] / max_hits
        )
        scored.append((mid, ws))

    scored.sort(key=lambda x: x[1], reverse=True)

    result = []
    for mid, score in scored[:top_n]:
        result.append((format_movie(mid, movie_info), score))
    return result
