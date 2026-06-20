#DATA LOADING FUNCTIONS

from sparse_matrix_zun import create_sparmat, insert_sparmat, get_sparmat, row_keys_sparmat

# Genre order from u.item col 6-24
GENRE_COLUMNS = [
    'unknown', 'Action', 'Adventure', 'Animation', "Children's",
    'Comedy', 'Crime', 'Documentary', 'Drama', 'Fantasy',
    'Film-Noir', 'Horror', 'Musical', 'Mystery', 'Romance',
    'Sci-Fi', 'Thriller', 'War', 'Western'
]

def load_movie_titles(filepath='u.item'):
    #parses u.item for title and genre maps
    title_map = {}
    genres_map = {}

    try:
        with open(filepath, 'r', encoding='latin-1') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) < 6:
                    continue
                
                movie_id = parts[0]
                title = parts[1]
                title_map[movie_id] = title

                # parse the 0/1 genre flags
                genre_flags = parts[5:5 + len(GENRE_COLUMNS)]
                movie_genres = []
                for i, flag in enumerate(genre_flags):
                    if flag == '1' and i < len(GENRE_COLUMNS):
                        movie_genres.append(GENRE_COLUMNS[i])
                genres_map[movie_id] = movie_genres

    except FileNotFoundError:
        print(f"[Warning] '{filepath}' not found.")

    return title_map, genres_map


def load_data(ratings_filepath='u.data', item_filepath='u.item', progress_filepath=None):
    #create sparse matrxs of ratings, genres, and progress.

    #ratings_matrix is userid[movieid] = rating
    ratings_matrix = create_sparmat()
    with open(ratings_filepath, 'r') as f:
        for line in f:
            columns = line.strip().split('\t')
            if len(columns) < 3:
                continue
            insert_sparmat(ratings_matrix, columns[0], columns[1], float(columns[2]))

    #movie metadata
    title_map, genres_map = load_movie_titles(item_filepath)

    #movie_genre_matrix is movieid[genre] = 0-1
    movie_genre_matrix = create_sparmat()
    for movie_id, genres in genres_map.items():
        for g in genres:
            insert_sparmat(movie_genre_matrix, movie_id, g, 1.0)

    #watch_progress_matrix...Continue wathcing
    watch_progress_matrix = create_sparmat()
    if progress_filepath:
        try:
            with open(progress_filepath, 'r') as f:
                next(f) 
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        insert_sparmat(watch_progress_matrix, parts[0], parts[1], float(parts[2]))
        except FileNotFoundError:
            pass

    return ratings_matrix, movie_genre_matrix, watch_progress_matrix, title_map, genres_map


### [HELPERS]:-

def get_rating(user_id, movie_id, ratings_matrix):
    #get specific rating or 0
    return get_sparmat(ratings_matrix, user_id, movie_id)


def get_all_user_ids(ratings_matrix):
    #get list of all user ids
    return row_keys_sparmat(ratings_matrix)


def get_movie_title(movie_id, title_map):
    #get title from id
    return title_map.get(str(movie_id), f"Movie #{movie_id}")


def get_movie_genres(movie_id, genres_map):
    #get list of genres for a movie
    return genres_map.get(str(movie_id), [])