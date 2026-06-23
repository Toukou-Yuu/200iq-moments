# 200iq Retrieval Integration

## Service Boundary

`200iq-moments` owns Case source data in Markdown and frontmatter. `retrieval-api` owns derived keyword and vector indexes. Retrieval data can be rebuilt from 200iq exports.

## Docker Topology

```text
200iq-api / 200iq-sync-worker
  -> http://retrieval-api:8000
  -> embedding-api / qdrant
```

All services join the `agent-services` Docker network. No service exposes an inter-service API through a host port.

## Collection

200iq uses the `200iq_cases` collection.

Each Case maps to one retrieval document:

```json
{
  "id": "200iq:case:001",
  "source": "200iq-moments",
  "doc_type": "case",
  "title": "Case title",
  "text": "Searchable case text",
  "metadata": {
    "case_id": "001",
    "slug": "case-slug",
    "status": "published",
    "date": "2025-06-20",
    "tags": ["subscription"],
    "loss_amount": 19.9,
    "loss_currency": "CNY",
    "loss_types": ["money"],
    "source_path": "data/cases/001-case-slug.md",
    "updated_at": "2026-06-23T12:00:00+08:00"
  },
  "updated_at": "2026-06-23T12:00:00+08:00"
}
```

## Synchronization

| 200iq change | Retrieval request |
| --- | --- |
| Create or update Case | `POST /v1/documents/upsert` |
| Archive Case | `POST /v1/documents/{collection}/{document_id}/archive` |
| Restore Case | `POST /v1/documents/{collection}/{document_id}/restore` |
| Soft delete Case | `DELETE /v1/documents/{collection}/{document_id}` |
| Rebuild index | `POST /v1/index/rebuild-collection` |

200iq persists a sync job after writing its source data. A failed retrieval request never rolls back the Case; the job records its error and can be retried.

## Export

`GET /v1/export/documents` returns a `collection` field and a `documents` list using the document contract above. It is the source for full index rebuilds.
