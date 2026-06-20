
###[SPARSE MATRIX ADT FUNCTIONS]:-

def create_sparmat():
    #creates empty sparse matrix.
    return {}

def insert_sparmat(m, row, col, val):
    #stores value at row and col
    if row not in m:
        m[row] = {}
    m[row][col] = val


def get_sparmat(m, row, col):
    #gets value at sparse matrix[row][col] if empty return 0.
    if row in m and col in m[row]:
        return m[row][col]
    return 0

def update_sparmat(m, row, col, val):
    #update at spase matrix[row][col] the value 
    insert_sparmat(m, row, col, val)


def count_non_zero_sparmat(m):
    #gives num of non nzero entries
    count = 0
    for row in m:
        count += len(m[row])
    return count


def row_keys_sparmat(m):
    #give row keys
    return list(m.keys())


def get_row_ent(m, row):
    #give dict at specifc row 
    if row in m:
        return dict(m[row])
    return {}


def get_col_ent(m, col):
    #give dict at specifc col 
    result = {}
    for row in m:
        if col in m[row]:
            result[row] = m[row][col]
    return result


def transpose_sparmat(m):
    #giuve new matrix with row and col both swapped
    t = create_sparmat
    for row in m:
        for col in m[row]:
            insert_sparmat(t, col, row, m[row][col])
    return t



### [CALCULATION]:-

def dot_product_sparmat(m, r1, r2):
    #calc dot product b/w two rows
    row1 = get_row_ent(m, r1)
    row2 = get_row_ent(m, r2)

    if len(row1) > len(row2):
        row1, row2 = row2, row1

    dot = 0.0
    for col, val in row1.items():
        if col in row2:
            dot += val * row2[col]
    return dot


def magnitude_sparmat(m, row):
    #find eucledian magnitude of a row
    row_data = get_row_ent(m, row)
    if not row_data:
        return 0.0
    return sum(v ** 2 for v in row_data.values()) ** 0.5


def cosine_similarity_sparmat(m, r1, r2):
    #find cosine similarity b/w two rows. 
    mag1 = magnitude_sparmat(m, r1)
    mag2 = magnitude_sparmat(m, r2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product_sparmat(m, r1, r2) / (mag1 * mag2)