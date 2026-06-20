#all matrix access through ADT functions
#all output uses format_movie()

from load_data_zun import load_data
from movie_info_zainab import load_movie_info, format_movie
from weighted_score_common import get_trending
from similarity_engine_common import get_similar_users, get_similar_user_recommendations
from item_item_sidrah import get_item_item_recommendations
from user_profiles_zainab import (
    load_actor_movie_matrix, get_continue_watching,
    update_watch_progress, get_genre_recommendations,
    get_actor_recommendations, onboard_new_user, is_new_user,
    get_seeded_genre_recommendations
)
from recommender_sidrah import get_hybrid_recommendations
from sparse_matrix_zun import insert_sparmat, count_non_zero_sparmat, get_row_ent

user_genre_matrices = {}  


def print_header(title):
    print("\n" + "=" * 52)
    print(f"  {title}")
    print("=" * 52)


def print_ranked(items, label_col=44):
    if not items:
        print("  (no results)")
        return
    rank = 1
    for label, score in items:
        print(f"  {rank:2}. {label:<{label_col}}  score: {score:.4f}")
        rank += 1


def prompt_user_id(ratings_matrix, allow_new=False):
    uid = input("  Enter User ID: ").strip()
    if not uid:
        print("  No user ID entered.")
        return None
    if not allow_new and uid not in ratings_matrix:
        print(f"  User ID '{uid}' not found in ratings data.")
        return None
    return uid


def main():
    print("\n  Loading data, please wait...")
    ratings_matrix, movie_genre_matrix, watch_progress_matrix, title_map, genres_map = \
        load_data('u.data', 'u.item', progress_filepath='watch_progress.csv')
    movie_info = load_movie_info('u.item')
    actor_movie_matrix, actor_names = load_actor_movie_matrix('actors.csv')

    total_entries = count_non_zero_sparmat(ratings_matrix)
    print(f"  Loaded {len(ratings_matrix)} users, {total_entries} ratings, {len(movie_info)} movie titles.")

    while True:
        print_header("MOVIE RECOMMENDATION SYSTEM")
        print("   1. New user setup")
        print("   2. Continue watching")
        print("   3. Trending movies")
        print("   4. Genre recommendations")
        print("   5. You might also like (item-item)")
        print("   6. People like you watched (user-user)")
        print("   7. Actor picks")
        print("   8. Rate a movie")
        print("   9. System info")
        print("  10. Hybrid recommendations")
        print("  11. Exit")
        choice = input("  Select option (1-11): ").strip()

        if choice == '11':
            print("\n  Goodbye!\n")
            break

        elif choice == '3':
            print_header("TRENDING MOVIES")
            rank = 1
            for mid, score in get_trending(ratings_matrix, top_n=15):
                print(f"  {rank:2}. {format_movie(mid, movie_info):<50}  (score: {score:.2f})")
                rank += 1

        elif choice == '9':
            print_header("SYSTEM INFO")
            no_of_rating_entries   = count_non_zero_sparmat(ratings_matrix)
            no_of_genre_entries    = count_non_zero_sparmat(movie_genre_matrix)
            no_of_progress_entries = count_non_zero_sparmat(watch_progress_matrix)
            print(f"  Ratings matrix    — users: {len(ratings_matrix)}, entries: {no_of_rating_entries}")
            print(f"  Genre matrix      — movies: {len(movie_genre_matrix)}, entries: {no_of_genre_entries}")
            print(f"  Progress matrix   — entries: {no_of_progress_entries}")
            print(f"  Actor matrix      — actors: {len(actor_movie_matrix)}")
            print(f"  Movie info loaded : {len(movie_info)} titles")

        elif choice == '1':
            print_header("NEW USER SETUP")
            uid = prompt_user_id(ratings_matrix, allow_new=True)
            if uid is None: continue
            if not is_new_user(uid, ratings_matrix):
                print(f"  User '{uid}' already has ratings — onboarding skipped.")
                continue
            ugm = onboard_new_user(uid, ratings_matrix, movie_genre_matrix,
                                   movie_info, actor_movie_matrix, actor_names)
            user_genre_matrices[uid] = ugm

        elif choice == '2':
            print_header("CONTINUE WATCHING")
            uid = prompt_user_id(ratings_matrix)
            if uid is None: continue
            items = get_continue_watching(uid, watch_progress_matrix, movie_info)
            if not items:
                print("  No in-progress movies found.")
            else:
                rank = 1
                for label, pct in items:
                    filled = int(pct) // 10
                    bar    = chr(9608) * filled + chr(9617) * (10 - filled)
                    print(f"  {rank:2}. [{bar}] {int(pct):3}%  {label}")
                    rank += 1

        elif choice == '4':
            print_header("GENRE RECOMMENDATIONS")
            uid = prompt_user_id(ratings_matrix)
            if uid is None: continue
            if is_new_user(uid, ratings_matrix):
                ugm = user_genre_matrices.get(uid)
                if ugm:
                    recs = get_seeded_genre_recommendations(uid, ugm, movie_genre_matrix,
                                                            ratings_matrix, movie_info)
                else:
                    print("  New user: please run option 1 first.")
                    continue
            else:
                recs = get_genre_recommendations(uid, ratings_matrix, movie_genre_matrix, movie_info)
            print_ranked(recs)

        elif choice == '5':
            print_header("YOU MIGHT ALSO LIKE  (item-item CF)")
            uid = prompt_user_id(ratings_matrix)
            if uid is None: continue
            recs = get_item_item_recommendations(uid, ratings_matrix, genres_map)
            if not recs:
                print("  Not enough data for item-item recommendations.")
            else:
                display = []
                for mid, score in recs:
                    display.append((format_movie(mid, movie_info), score))
                print_ranked(display)

        elif choice == '6':
            print_header("PEOPLE LIKE YOU WATCHED  (user-user CF)")
            uid = prompt_user_id(ratings_matrix)
            if uid is None: continue
            similar = get_similar_users(uid, ratings_matrix, n=5)
            if not similar:
                print("  No similar users found.")
                continue
            recs = get_similar_user_recommendations(uid, ratings_matrix, genres_map, top_n=10)
            if not recs:
                print("  No unseen highly-rated movies from similar users.")
            else:
                display = []
                for mid, score in recs:
                    display.append((format_movie(mid, movie_info), score))
                print_ranked(display)

        elif choice == '7':
            print_header("ACTOR PICKS")
            uid = prompt_user_id(ratings_matrix)
            if uid is None: continue
            if not actor_names:
                print("  actors.csv not loaded.")
                continue
            print("\n  Available actors:")
            actor_list = sorted(actor_names.items(), key=lambda x: int(x[0]))
            for aid, name in actor_list:
                print(f"    {aid:>3}. {name}")
            raw = input("\n  Enter up to 3 actor numbers (comma-separated): ").strip()
            actor_ids = []
            for a in raw.split(','):
                a = a.strip()
                if a in actor_names:
                    actor_ids.append(a)
            if not actor_ids:
                print("  No valid actor IDs.")
                continue
            recs = get_actor_recommendations(uid, actor_ids, actor_movie_matrix,
                                             ratings_matrix, movie_info)
            if not recs:
                print("  No unseen movies for those actors.")
            else:
                print_ranked(recs)

        elif choice == '8':
            print_header("RATE A MOVIE")
            uid = prompt_user_id(ratings_matrix, allow_new=True)
            if uid is None: continue
            mid = input("  Enter Movie ID: ").strip()
            if not mid: continue
            label = format_movie(mid, movie_info)
            if label.startswith("Movie #"):
                print(f"  Movie ID '{mid}' not found.")
                continue
            rating = input(f"  Rate '{label}' (1-5): ").strip()
            try:
                rating = float(rating)
                if not 1 <= rating <= 5: raise ValueError
            except ValueError:
                print("  Rating must be a number between 1 and 5.")
                continue
            insert_sparmat(ratings_matrix, uid, mid, rating)
            update_watch_progress(uid, mid, 100, watch_progress_matrix)
            print(f"  Rated '{label}' -> {rating:.1f} stars")

        elif choice == '10':
            print_header("HYBRID RECOMMENDATIONS")
            uid = prompt_user_id(ratings_matrix)
            if uid is None: continue
            recs = get_hybrid_recommendations(uid, ratings_matrix,
                                              movie_genre_matrix, genres_map, top_n=5)
            if not recs:
                print("  No hybrid recommendations available. Try rating more movies.")
            else:
                display = []
                for mid, score in recs:
                    display.append((format_movie(mid, movie_info), score))
                print_ranked(display)

        else:
            print("  Invalid option. Please choose 1-11.")


if __name__ == "__main__":
    main()
