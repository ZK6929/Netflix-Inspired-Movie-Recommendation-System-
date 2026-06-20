#hybrid recommender — combines collab, item-item, and genre scores
# final = 0.5*collab + 0.3*item_item + 0.2*genre

from sparse_matrix_zun import get_row_ent, get_sparmat, get_col_ent
from similarity_engine_common import get_similar_user_recommendations
from item_item_sidrah import get_item_item_recommendations


# O(U * G) where U = users rated in genre, G = top genres considered
def _genre_scores(target_id, ratings_matrix, movie_genre_matrix, genres_map, top_n=20):
    #internal helper — score unseen movies by genre match with user's taste
    target_row = get_row_ent(ratings_matrix, target_id)
    if not target_row:
        return {}

    genre_weights = {}
    for movie_id in target_row:
        rating = target_row[movie_id]
        for genre in genres_map.get(str(movie_id), []):
            if genre not in genre_weights:
                genre_weights[genre] = 0.0
            genre_weights[genre] += rating

    if not genre_weights:
        return {}

    #normalise genre weights to 0-1
    max_w = max(genre_weights.values())
    for g in genre_weights:
        genre_weights[g] = genre_weights[g] / max_w

    #sort genres by weight and take top 5
    sorted_genres = sorted(genre_weights.items(), key=lambda x: x[1], reverse=True)
    top_genres = sorted_genres[:5]

    scored = {}
    for genre, gw in top_genres:
        for movie_id in get_col_ent(movie_genre_matrix, genre):
            if get_sparmat(ratings_matrix, target_id, movie_id) != 0:
                continue
            if movie_id not in scored:
                scored[movie_id] = 0.0
            scored[movie_id] += gw

    if scored:
        max_s = max(scored.values())
        for mid in scored:
            scored[mid] = scored[mid] / max_s

    #return only top N
    sorted_scored = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    result = {}
    for mid, s in sorted_scored[:top_n]:
        result[mid] = s
    return result


# O(C + I + G) where C = collab candidates, I = item-item, G = genre candidates
def get_hybrid_recommendations(target_id, ratings_matrix,
                                movie_genre_matrix, genres_map,
                                top_n=5):
    #combine collab, item-item and genre into one score
    target_row = get_row_ent(ratings_matrix, target_id)
    if not target_row:
        return []  # cold start, no data

    collab_list = get_similar_user_recommendations(target_id, ratings_matrix, genres_map, top_n=20)
    ii_list     = get_item_item_recommendations(target_id, ratings_matrix, genres_map, top_n=20)
    genre_dict  = _genre_scores(target_id, ratings_matrix, movie_genre_matrix, genres_map, top_n=20)

    #convert lists to dicts for easy lookup
    collab_dict = {}
    for mid, score in collab_list:
        collab_dict[mid] = score

    ii_dict = {}
    for mid, score in ii_list:
        ii_dict[mid] = score

    all_ids = set(collab_dict.keys())
    for mid in ii_dict:
        all_ids.add(mid)
    for mid in genre_dict:
        all_ids.add(mid)

    if not all_ids:
        return []

    final = []
    for mid in all_ids:
        c = collab_dict.get(mid, 0.0)
        i = ii_dict.get(mid, 0.0)
        g = genre_dict.get(mid, 0.0)
        combined = 0.5 * c + 0.3 * i + 0.2 * g
        final.append((mid, round(combined, 4)))

    final.sort(key=lambda x: x[1], reverse=True)
    return final[:top_n]
