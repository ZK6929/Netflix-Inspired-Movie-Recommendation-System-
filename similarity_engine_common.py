#similarity engine — user-user collaborative filtering
#uses cosine similarity from sparse_matrix to find similar users

from sparse_matrix_zun import cosine_similarity_sparmat, get_row_ent, get_sparmat
from weighted_score_common import compute_weighted_score, normalise_vote_counts


# O(U) where U = total number of users in the matrix
def get_similar_users(target_id, ratings_matrix, n=5):
    #find n most similar users to target using cosine similarity
    if target_id not in ratings_matrix:
        return []

    similarities = []
    for user_id in ratings_matrix:
        if user_id == target_id:
            continue
        sim_score = cosine_similarity_sparmat(ratings_matrix, target_id, user_id)
        if sim_score > 0:
            similarities.append((user_id, round(sim_score, 4)))

    similarities.sort(key=lambda pair: pair[1], reverse=True)
    return similarities[:n]


# O(K * R + C * U) where K = similar users, R = their ratings, C = candidates, U = all users
def get_similar_user_recommendations(target_id, ratings_matrix,
                                     genres_map, top_n=5, k=5):
    #"people like you also watched" engine
    #from top-k similar users, gather unseen movies rated >=4 and rank by weighted score

    target_ratings = get_row_ent(ratings_matrix, target_id)
    if not target_ratings:
        return []  # cold start

    similar_users = get_similar_users(target_id, ratings_matrix, n=k)
    if not similar_users:
        return []

    candidates = {}
    for sim_user, _ in similar_users:
        sim_ratings = get_row_ent(ratings_matrix, sim_user)
        for movie_id in sim_ratings:
            rating = sim_ratings[movie_id]
            if rating < 4.0:
                continue
            if get_sparmat(ratings_matrix, target_id, movie_id) != 0:
                continue
            if movie_id not in candidates:
                candidates[movie_id] = {'sum': 0.0, 'votes': 0}
            candidates[movie_id]['sum']   += rating
            candidates[movie_id]['votes'] += 1

    if not candidates:
        return []

    #build genre profile of target user for genre_match scoring
    target_genre_counts = {}
    for movie_id in target_ratings:
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
