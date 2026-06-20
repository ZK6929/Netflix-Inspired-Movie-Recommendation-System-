###MOVIE METADETA


GENRE_COLUMNS = [
    'unknown', 'Action', 'Adventure', 'Animation', "Children's",
    'Comedy', 'Crime', 'Documentary', 'Drama', 'Fantasy',
    'Film-Noir', 'Horror', 'Musical', 'Mystery', 'Romance',
    'Sci-Fi', 'Thriller', 'War', 'Western'
]

def load_movie_info(filepath='u.item'):
    #parses u.item into a lookup dict for titles and genres
    movie_info = {}

    try:
        with open(filepath, 'r', encoding='latin-1') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) < 6:
                    continue

                movie_id = parts[0].strip()
                raw_title = parts[1].strip()

                #year from title
                year = ''
                if raw_title.endswith(')') and '(' in raw_title:
                    open_paren = raw_title.rfind('(')
                    maybe_year = raw_title[open_paren + 1:-1]
                    if maybe_year.isdigit() and len(maybe_year) == 4:
                        year = maybe_year

                #collect genre names for flag =1
                genre_flags = parts[5:5 + len(GENRE_COLUMNS)]
                genres = [
                    GENRE_COLUMNS[i]
                    for i, flag in enumerate(genre_flags)
                    if flag.strip() == '1' and i < len(GENRE_COLUMNS)
                ]

                movie_info[movie_id] = {
                    'title':  raw_title,
                    'year':   year,
                    'genres': genres,
                }

    except FileNotFoundError:
        print(f"[Warning] '{filepath}' not found.")

    return movie_info


### [HELPERS]:-

def format_movie(movie_id, movie_info):
    #return Title(Year)[Genres]
    movie_id = str(movie_id)
    info = movie_info.get(movie_id)

    if not info:
        return f"Movie #{movie_id}"

    title = info['title']
    genres = info['genres']

    if genres:
        genre_str = ', '.join(genres)
        return f"{title} [{genre_str}]"
    return title


def get_title(movie_id, movie_info):
    #get just the title string
    movie_id = str(movie_id)
    info = movie_info.get(movie_id)
    if not info:
        return f"Movie #{movie_id}"
    return info['title']


def get_genres(movie_id, movie_info):
    #get the list of gnres
    movie_id = str(movie_id)
    info = movie_info.get(movie_id)
    if not info:
        return []
    return info['genres']