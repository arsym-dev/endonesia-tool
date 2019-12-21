def read_in_chunks(file_object, chunk_size = 4, size = 0):
    currentsize = 0
    while True:
        data = file_object.read(chunk_size)
        if not data or (size > 0 and size <= currentsize):
            break
        currentsize += chunk_size
        yield data

