#weighted score functions used across all recommendation modules

import math
from sparse_matrix_zun import get_col_ent


# O(1) - just arithmetic
def compute_weighted_score(avg_rating, vote_count, vote_count_norm, genre_match, recency=0.5):
    #central formula - score based on rating, popularity, genre and recency
    # score = (avg * 0.4) + (vote_norm * 0.3) + (genre * 0.2) + (recency * 0.1)

    avg_norm = avg_rating / 5.0   #bring rating to 0-1 range

    score = (avg_norm        * 0.4
           + vote_count_norm * 0.3
           + genre_match     * 0.2
           + recency         * 0.1)
    return round(score, 4)


# O(U + M) where U = users, M = unique movies
def get_trending(ratings_matrix, top_n=10):
    #trending list for new users (cold start)
    #uses avg_rating * log(vote_count+1) so quality and popularity both matter

    all_movie_ids = set()
    for row_key in ratings_matrix:
        for col_key in ratings_matrix[row_key]:
            all_movie_ids.add(col_key)

    trending_list = []

    for movie_id in all_movie_ids:
        col_data = get_col_ent(ratings_matrix, movie_id)

        if not col_data:
            continue

        all_ratings = list(col_data.values())
        total_votes  = len(all_ratings)
        avg_rating   = sum(all_ratings) / total_votes

        # log dampens pure popularity so quality still counts
        trending_score = avg_rating * math.log(total_votes + 1)
        trending_list.append((movie_id, round(trending_score, 4)))

    trending_list.sort(key=lambda x: x[1], reverse=True)
    return trending_list[:top_n]


# O(M) where M = number of movies in the dict
def normalise_vote_counts(vote_counts):
    #normalise dict of {movie_id: count} to 0-1 range
    if not vote_counts:
        return {}
    max_votes = max(vote_counts.values())
    if max_votes == 0:
        return {k: 0.0 for k in vote_counts}
    normalised = {}
    for k in vote_counts:
        normalised[k] = vote_counts[k] / max_votes
    return normalised
