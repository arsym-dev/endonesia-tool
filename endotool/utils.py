from shutil import which

basedir = ''

def read_in_chunks(file_object, chunk_size = 4, size = 0):
    currentsize = 0
    while True:
        ## Only read new data if we haven't exceeded the size
        if (size > 0 and size <= currentsize):
            break

        data = file_object.read(chunk_size)
        if not data:
            break
        currentsize += chunk_size
        yield data

def csv_find(pointer, csv, text = False):
    size = len(csv)
    for row in range(0, size):
        if pointer == int(csv[row][0], 16) and (not text or text == int(csv[row][1], 16)):
            return row
    return -1

def check_bin(name):
    return which(name) is not None

def pad_to_nearest(input, k=16):
    ## Add enough zeros to pad it to the nearest multiple of k
    num_zeros = (k - (len(input) % k)) % k
    return input + bytes(num_zeros)