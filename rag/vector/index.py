"""Pinned local embeddings and persistent Qdrant receipts with portable restore."""
import http.client
import json
import math
from pathlib import Path
import struct
import time
from uuid import UUID

from .data import (corpus, digest, identity, load, passages, save, seal,
                   verified, verify_model)


class Encoder:
    def __init__(self, config):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.config = config
        path = verify_model(config)
        torch.set_num_threads(config['embedding_threads'])
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        self.model = AutoModel.from_pretrained(path, local_files_only=True, trust_remote_code=False).eval()

    def encode(self, texts, *, query=False):
        import torch
        if query:
            texts = [self.config['query_prefix'] + x for x in texts]
        tokens = self.tokenizer(texts, padding=True, truncation=False, return_tensors='pt', verbose=False)
        if tokens['input_ids'].shape[1] > self.config['embedding_max_tokens']:
            raise ValueError('Embedding input exceeds token budget')
        with torch.inference_mode():
            vectors = self.model(**tokens).last_hidden_state[:, 0]
            vectors = torch.nn.functional.normalize(vectors, p=2, dim=1).cpu().tolist()
        if any(len(v) != 384 or not all(math.isfinite(x) for x in v)
               or abs(sum(x*x for x in v)-1) > 1e-4 for v in vectors):
            raise ValueError('Invalid embedding projection')
        return vectors


def embedding_text(chunk):
    return chunk['title'] + '\n' + chunk['content']


def read_vectors(directory):
    m = verified(directory)
    content = (Path(directory)/'vectors.f32').read_bytes()
    if len(content) != m['chunk_count'] * 384 * 4:
        raise ValueError('Vector file shape mismatch')
    values = struct.unpack('<' + str(len(content)//4) + 'f', content)
    vectors = [list(values[i:i+384]) for i in range(0, len(values), 384)]
    if any(not all(math.isfinite(x) for x in v) or abs(sum(x*x for x in v)-1) > 1e-4 for v in vectors):
        raise ValueError('Invalid persisted vectors')
    return vectors


def build(release, directory, config, *, reuse=None, encoder=None):
    directory = Path(directory)
    if directory.resolve().is_relative_to(Path(release).resolve()):
        raise ValueError('Build cannot modify source release')
    directory.mkdir(parents=True, exist_ok=False)
    encoder = encoder or Encoder(config)
    records = corpus(release, config)
    chunks = [chunk for r in records for chunk in passages(r, encoder.tokenizer, config)]
    if not chunks or len(chunks) > config['maximum_chunks']:
        raise ValueError('Chunk inventory limit')
    import inspect
    from importlib.metadata import version
    environment = {k: version(k) for k in ['torch', 'transformers', 'tokenizers', 'numpy']}
    signature = identity([config['embedding_files_sha256'], 'title-newline-content-cls-normalized-v2',
                          inspect.getsource(Encoder), environment])
    previous = {}
    if reuse:
        old = verified(reuse)
        if old['embedding_signature'] != signature:
            raise ValueError('Incompatible embedding reuse')
        old_chunks = load(Path(reuse)/'chunks.json')
        for c, v in zip(old_chunks, read_vectors(reuse), strict=True):
            previous[identity(embedding_text(c))] = v
    vectors = [None] * len(chunks)
    pending = []
    reused = 0
    for i, chunk in enumerate(chunks):
        key = identity(embedding_text(chunk))
        if key in previous:
            vectors[i] = previous[key]
            reused += 1
        else:
            pending.append(i)
    for start in range(0, len(pending), config['embedding_batch_size']):
        ids = pending[start:start+config['embedding_batch_size']]
        for i, v in zip(ids, encoder.encode([embedding_text(chunks[j]) for j in ids]), strict=True):
            vectors[i] = v
    save(directory/'documents.json', records)
    save(directory/'chunks.json', chunks)
    save(directory/'configuration.json', config)
    with (directory/'vectors.f32').open('xb') as stream:
        for v in vectors:
            stream.write(struct.pack('<384f', *v))
    metadata = {'format_version': '1.0.0', 'release_id': config['release_id'],
                'release_manifest_sha256': config['release_manifest_sha256'],
                'configuration_sha256': identity(config),
                'preparation_sources_sha256': {str(p.relative_to(Path(__file__).resolve().parents[2])): digest(p)
                    for p in [Path(__file__), Path(__file__).with_name('data.py')]},
                'document_count': len(records),
                'chunk_count': len(chunks), 'dimension': 384, 'vector_format': 'little-endian-float32',
                'embedding_signature': signature, 'embedding_environment': environment, 'reused_embeddings': reused,
                'new_embeddings': len(chunks)-reused, 'predecessor_build_sha256': digest(Path(reuse)/'manifest.json') if reuse else None}
    seal(directory, metadata)
    return verified(directory)


class Qdrant:
    """Only shared-container loopback; no client-controlled remote endpoints."""
    def __init__(self, port=6333, timeout=30):
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Invalid store port')
        self.port, self.timeout = port, timeout

    def request(self, method, path, body=None, *, raw=None, content_type='application/json', binary=False):
        if not path.startswith('/') or '\r' in path or '\n' in path:
            raise ValueError('Invalid store path')
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=self.timeout)
        payload = raw if raw is not None else json.dumps(body, allow_nan=False).encode() if body is not None else None
        try:
            conn.request(method, path, payload, {'Content-Type': content_type})
            response = conn.getresponse()
            data = response.read(128*1024**2+1)
            if len(data) > 128*1024**2 or not 200 <= response.status < 300:
                raise ValueError('Vector store request failed')
            return data if binary else json.loads(data)
        finally:
            conn.close()

    @staticmethod
    def name(name):
        import re
        if not re.fullmatch(r'cs_[a-f0-9]{24}(?:_restore)?', name):
            raise ValueError('Invalid collection name')
        return name

    def ready(self):
        for _ in range(60):
            try:
                version = self.request('GET', '/')['version']
                if version != '1.20.0':
                    raise ValueError('Unexpected Qdrant version')
                return
            except (OSError, ValueError, KeyError):
                time.sleep(0.5)
        raise ValueError('Vector store unavailable')

    def info(self, collection):
        return self.request('GET', '/collections/'+self.name(collection))['result']

    def query(self, collection, vector, limit, *, sources=(), documents=(), threshold=None):
        must = []
        for key, values in [('source', sources), ('document_id', documents)]:
            if values:
                must.append({'key': key, 'match': {'any': list(values)}})
        body = {'query': vector, 'limit': limit, 'with_payload': True, 'with_vector': True}
        if must:
            body['filter'] = {'must': must}
        if threshold is not None:
            body['score_threshold'] = threshold
        return self.request('POST', '/collections/'+self.name(collection)+'/points/query', body)['result']['points']


def point_id(chunk_id):
    return str(UUID(hex=identity(chunk_id)[:32]))


def payload(chunk, build_sha):
    return {k: chunk[k] for k in ['chunk_id', 'document_id', 'content_sha256', 'source']} | {'build_sha256': build_sha}


def publish(directory, receipt, store=None):
    store = store or Qdrant()
    store.ready()
    m = verified(directory)
    chunks = load(Path(directory)/'chunks.json')
    vectors = read_vectors(directory)
    build_sha = digest(Path(directory)/'manifest.json')
    collection = 'cs_' + build_sha[:24]
    # Creating an existing collection fails rather than overwriting it.
    store.request('PUT', '/collections/'+collection,
                  {'vectors': {'size': 384, 'distance': 'Cosine'}, 'on_disk_payload': True})
    for start in range(0, len(chunks), 32):
        points = [{'id': point_id(c['chunk_id']), 'vector': v, 'payload': payload(c, build_sha)}
                  for c, v in zip(chunks[start:start+32], vectors[start:start+32], strict=True)]
        store.request('PUT', '/collections/'+collection+'/points?wait=true', {'points': points})
    info = store.info(collection)
    if info['points_count'] != m['chunk_count']:
        raise ValueError('Published point count mismatch')
    record = {'collection': collection, 'build_sha256': build_sha, 'point_count': m['chunk_count'],
              'dimension': 384, 'metric': 'Cosine', 'qdrant_version': '1.20.0'}
    save(receipt, record)
    return record


def snapshot(directory, receipt, path, store=None):
    store = store or Qdrant()
    r = load(receipt)
    if r['build_sha256'] != digest(Path(directory)/'manifest.json'):
        raise ValueError('Receipt/build mismatch')
    name = store.request('POST', '/collections/'+store.name(r['collection'])+'/snapshots')['result']['name']
    from urllib.parse import quote
    data = store.request('GET', '/collections/'+r['collection']+'/snapshots/'+quote(name, safe=''), binary=True)
    with Path(path).open('xb') as stream:
        stream.write(data)
    save(str(path)+'.json', {'snapshot_sha256': digest(path), 'receipt': r})


def restore(directory, snapshot_path, receipt, store=None):
    store = store or Qdrant()
    store.ready()
    m = verified(directory)
    info = load(str(snapshot_path)+'.json')
    if (digest(snapshot_path) != info['snapshot_sha256']
            or digest(Path(directory)/'manifest.json') != info['receipt']['build_sha256']):
        raise ValueError('Snapshot identity mismatch')
    collection = info['receipt']['collection'] + '_restore'
    if collection in [c['name'] for c in store.request('GET', '/collections')['result']['collections']]:
        raise ValueError('Restore destination exists')
    boundary = 'vector-snapshot-boundary'
    raw = ('--'+boundary+'\r\nContent-Disposition: form-data; name="snapshot"; filename="index.snapshot"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
    raw += Path(snapshot_path).read_bytes() + ('\r\n--'+boundary+'--\r\n').encode()
    store.request('POST', '/collections/'+collection+'/snapshots/upload?priority=snapshot', raw=raw,
                  content_type='multipart/form-data; boundary='+boundary)
    if store.info(collection)['points_count'] != m['chunk_count']:
        raise ValueError('Restored count mismatch')
    save(receipt, {**info['receipt'], 'collection': collection, 'restored_from_sha256': info['snapshot_sha256']})
