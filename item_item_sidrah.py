#item-item collaborative filtering — "you might also like"
#transposes the matrix so rows = moviesthen finds similar movies via cosine sim

from sparse_matrix_zun import transpose_sparmat, cosine_similarity_sparmat, get_row_ent, get_sparmat
from weighted_score_common import compute_weighted_score, normalise_vote_counts


# O(S * M) where S = seed movies, M = total movies in transposed matrix
def get_item_item_recommendations(target_id, ratings_matrix,
                                  genres_map, top_n=5,
                                  recently_watched=5, similar_per_movie=5):
    #for each of user's recently watched movies, find similar movies
    #similarity is based on shared user ratings (transposed matrix)

    target_row = get_row_ent(ratings_matrix, target_id)
    if not target_row:
        return []

    #use last N rated movies as seeds
    all_watched  = list(target_row.keys())
    seed_movies  = all_watched[-recently_watched:]
    transposed   = transpose_sparmat(ratings_matrix)  # rows = movies now

    candidates = {}
    for seed in seed_movies:
        similarities = []
        for movie_id in transposed:
            if movie_id == seed:
                continue
            if get_sparmat(ratings_matrix, target_id, movie_id) != 0:
                continue
            sim = cosine_similarity_sparmat(transposed, seed, movie_id)
            if sim > 0:
                similarities.append((movie_id, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)

        idx = 0
        while idx < len(similarities) and idx < similar_per_movie:
            movie_id, sim = similarities[idx]
            col_data = get_row_ent(transposed, movie_id)   #all user ratings for this movie
            if not col_data:
                idx += 1
                continue
            if movie_id not in candidates:
                candidates[movie_id] = {
                    'sum':     sum(col_data.values()),
                    'votes':   len(col_data),
                    'max_sim': 0.0
                }
            if sim > candidates[movie_id]['max_sim']:
                candidates[movie_id]['max_sim'] = sim
            idx += 1

    if not candidates:
        return []

    #genre profile of target user
    target_genre_counts = {}
    for movie_id in target_row:
        for genre in genres_map.get(str(movie_id), []):
            if genre not in target_genre_counts:
                target_genre_counts[genre] = 0
            target_genre_counts[genre] += 1

    genre_total = sum(target_genre_counts.values())
    if genre_total == 0:
        genre_total = 1

    vote_counts = {}
    for mid in candidates:
        vote_counts[mid] = candidates[mid]['votes']
    vote_norms = normalise_vote_counts(vote_counts)

    scored = []
    for movie_id in candidates:
        data = candidates[movie_id]
        avg  = data['sum'] / data['votes']
        norm = vote_norms[movie_id]

        candidate_genres = genres_map.get(str(movie_id), [])
        if candidate_genres:
            genre_match = 0.0
            for g in candidate_genres:
                genre_match += target_genre_counts.get(g, 0) / genre_total
            genre_match = genre_match / len(candidate_genres)
        else:
            genre_match = 0.0

        ws = compute_weighted_score(avg, data['votes'], norm, genre_match)
        scored.append((movie_id, ws))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]
