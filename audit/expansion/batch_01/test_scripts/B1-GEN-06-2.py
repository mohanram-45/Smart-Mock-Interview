def hnsw_memory_gb(n, dim, bytes_per_dim=4.0, m=16, link_bytes=4, replicas=1):
    """Rough in-RAM size estimate in decimal GB (1e9 bytes) for an HNSW index.

    vectors: n * dim * bytes_per_dim
    layer 0: up to 2*m links per node
    upper layers: about n/(m-1) node-layer memberships with up to m links each
    Real engines add per-node headers, ids, alignment and allocator overhead.
    """
    vec = n * dim * bytes_per_dim
    base_links = n * 2 * m * link_bytes
    upper_links = n / (m - 1) * m * link_bytes
    total = (vec + base_links + upper_links) * replicas
    return total / 1e9

n, d = 50_000_000, 768
assert round(hnsw_memory_gb(n, d), 1) == 160.2
assert round(hnsw_memory_gb(n, d, replicas=3), 1) == 480.6
assert round(hnsw_memory_gb(n, d, bytes_per_dim=1), 1) == 45.0
# product quantisation, 96 one-byte codes per vector (8 dims per sub-vector)
assert round(hnsw_memory_gb(n, 96, bytes_per_dim=1), 1) == 11.4
# links alone, independent of dimension
assert round(hnsw_memory_gb(n, 0), 1) == 6.6
print("ok")
