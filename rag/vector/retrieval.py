"""Verified filtered retrieval; packets bind input, index and configuration identities."""
import math
from pathlib import Path
import time

from .data import digest, identity, incidents, load, save, seal, verified
from .index import Encoder, Qdrant, payload, point_id, read_vectors


class Retriever:
    def __init__(self, directory, receipt, config, *, store=None, encoder=None):
        self.directory, self.config = Path(directory), config
        self.build = verified(directory)
        self.receipt = load(receipt)
        self.build_sha = digest(Path(directory)/'manifest.json')
        if (self.receipt['build_sha256'] != self.build_sha
                or self.build['release_manifest_sha256'] != config['release_manifest_sha256']):
            raise ValueError('Index/source mismatch')
        saved = load(Path(directory)/'configuration.json')
        for key in ['embedding_files_sha256', 'embedding_dimension', 'query_prefix']:
            if saved[key] != config[key]:
                raise ValueError('Index/encoder mismatch')
        chunks = load(Path(directory)/'chunks.json')
        docs = {r['document_id']: r for r in load(Path(directory)/'documents.json')}
        self.chunks = {c['chunk_id']: c for c in chunks}
        if len(self.chunks) != self.build['chunk_count']:
            raise ValueError('Chunk inventory mismatch')
        for c in chunks:
            doc = docs[c['document_id']]
            if doc['content'][c['start']:c['end']] != c['content']:
                raise ValueError('Citation span mismatch')
        self.vectors = dict(zip(self.chunks, read_vectors(directory), strict=True))
        self.store = store or Qdrant()
        self.store.ready()
        info = self.store.info(self.receipt['collection'])
        vp = info['config']['params']['vectors']
        if info['points_count'] != len(chunks) or vp['size'] != 384 or vp['distance'] != 'Cosine':
            raise ValueError('Index state mismatch')
        # Verify all vectors/payloads, not merely a convenient health/count response.
        ids = list(self.chunks)
        for start in range(0, len(ids), 128):
            batch = ids[start:start+128]
            found = self.store.request('POST', '/collections/'+self.receipt['collection']+'/points',
                                       {'ids': [point_id(x) for x in batch], 'with_payload': True,
                                        'with_vector': True})['result']
            if len(found) != len(batch):
                raise ValueError('Missing index points')
            for hit in found:
                self._check_hit(hit)
        self.encoder = encoder or Encoder(config)

    def _check_hit(self, hit):
        c = self.chunks.get(hit['payload'].get('chunk_id'))
        if (c is None or hit['id'] != point_id(c['chunk_id'])
                or hit['payload'] != payload(c, self.build_sha)
                or len(hit['vector']) != 384
                or any(not math.isfinite(x) or abs(x-y) > 1e-5
                       for x, y in zip(hit['vector'], self.vectors[c['chunk_id']], strict=True))):
            raise ValueError('Index point integrity mismatch')
        return c

    def search(self, query, *, sources=(), documents=()):
        if not isinstance(query, str) or not query.strip() or len(query) > 4000:
            raise ValueError('Invalid retrieval query')
        if (any(x not in {'mitre_attack', 'cve', 'cwe', 'playbook'} for x in sources)
                or any(x not in {c['document_id'] for c in self.chunks.values()} for x in documents)):
            raise ValueError('Invalid retrieval filter')
        started = time.monotonic()
        vector = self.encoder.encode([query], query=True)[0]
        hits = self.store.query(self.receipt['collection'], vector, min(100, self.config['top_k']*8),
                                sources=sources, documents=documents, threshold=self.config['score_threshold'])
        result, seen = [], set()
        for hit in hits:
            c = self._check_hit(hit)
            score = hit['score']
            if (not math.isfinite(score) or abs(score-sum(x*y for x, y in zip(vector, self.vectors[c['chunk_id']], strict=True))) > 1e-4
                    or (sources and c['source'] not in sources)
                    or (documents and c['document_id'] not in documents)):
                raise ValueError('Invalid retrieval score/filter')
            if c['document_id'] in seen:
                continue
            seen.add(c['document_id'])
            result.append({**c, 'score': score})
            if len(result) == self.config['top_k']:
                break
        return {'query': query, 'sources': list(sources), 'documents': list(documents),
                'build_sha256': self.build_sha, 'configuration_sha256': identity(self.config),
                'configuration': self.config, 'elapsed_seconds': time.monotonic()-started,
                'candidate_depth': min(100, self.config['top_k']*8), 'evidence': result,
                'status': 'ok' if result else 'empty'}


def incident_query(incident):
    """Search the observed event topic, not missing-context boilerplate or user IDs."""
    import re
    text = re.sub(r'^Synthetic(?: vulnerability-review)? scenario\.\s*', '', incident['description'], flags=re.I)
    text = re.split(r'(?<=\.)\s+(?=[A-Z])', text)[0]
    text = re.sub(r'\b\d{4}-\d\d-\d\dT[0-9:]+Z\b', ' ', text)
    for entity in incident['entities']:
        if entity['type'] in {'host', 'user', 'ip', 'domain', 'file'}:
            text = text.replace(entity['value'], ' ')
    family = re.sub(r'[-_]', ' ', incident['source'].split(':')[-1])
    return re.sub(r'\s+', ' ', family+'. Technical documentation: '+text).strip()


def incident_packets(release, directory, output, receipt, config):
    inputs, _ = incidents(release, config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    retriever = Retriever(directory, receipt, config)
    records = []
    for incident in inputs:
        packet = retriever.search(incident_query(incident))
        packet['query_strategy'] = config['incident_query_version']
        packet.update(incident_id=incident['incident_id'], incident_sha256=identity(incident),
                      release_manifest_sha256=config['release_manifest_sha256'])
        save(output/(incident['incident_id']+'.json'), packet)
        records.append({'case_id': incident['incident_id'], 'status': packet['status'],
                        'documents': [e['document_id'] for e in packet['evidence']]})
    seal(output, {'format_version': '1.0.0', 'build_sha256': retriever.build_sha,
                  'configuration_sha256': identity(config), 'cases': records})
    return records
