from operator import itemgetter

from django.conf import settings
from django.urls import reverse

import regex
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan as scanner

from . import cts


es = Elasticsearch(
    hosts=settings.ELASTICSEARCH_HOSTS,
    sniff_on_start=settings.ELASTICSEARCH_SNIFF_ON_START,
    sniff_on_connection_fail=settings.ELASTICSEARCH_SNIFF_ON_CONNECTION_FAIL,
)


class SearchQuery:

    def __init__(
        self, q, search_type, scope=None, sort_by=None, aggregate_field=None,
        kind="form", fragments=5, size=10, offset=0
    ):
        self.q = q
        self.search_type = search_type
        self.scope = {} if scope is None else scope
        self.sort_by = sort_by
        self.aggregate_field = aggregate_field
        self.kind = kind
        self.fragments = fragments
        self.size = size
        self.offset = offset
        self.total_count = None

    def query_index(self):
        return {
            "index": "scaife-viewer",
            "doc_type": "text",
        }

    def query_sort(self):
        if not self.sort_by:
            return {}
        if self.sort_by == "document":
            return {"sort": [{"sort_idx": "asc"}]}

    def query_aggs(self):
        if not self.aggregate_field:
            return {}
        return {
            "aggs": {
                f"filtered_{self.aggregate_field}": {
                    "terms": {
                        "field": self.aggregate_field,
                        "size": 300,
                    },
                },
            },
        }

    def query(self):
        q = {}
        if self.kind == "lemma":
            fields = ["lemma_content"]
        elif self.kind == "form":
            if self.search_type == 'library':
                fields = ["raw_content"]
            else:
                fields = ["content"]
        sq = {
            "simple_query_string": {
                "query": self.q,
                "fields": fields,
                "default_operator": "and",
            }
        }
        if self.scope:
            q = {
                "bool": {
                    "must": sq,
                    "filter": {"term": self.scope},
                },
            }
        else:
            q = {**sq}
        return q

    def query_highlight(self):
        if self.kind == "lemma":
            fields = {"lemma_content": {}}
        elif self.kind == "form":
            if self.search_type == 'library':
                fields = {"raw_content": {}}
            else:
                fields = {"content": {}}
        return {
            "highlight": {
                "type": "fvh",
                "number_of_fragments": self.fragments,
                "fragment_size": 60,
                "fields": fields,
            }
        }

    def search_kwargs(self, size=10, offset=0):
        return {
            "body": {
                **self.query_sort(),
                **self.query_highlight(),
                "query": self.query(),
                **self.query_aggs(),
            },
            "size": size,
            "from_": offset,
            **self.query_index()
        }

    def search_window(self, **kwargs):
        results = es.search(**self.search_kwargs(**kwargs))
        return SearchResultSet(results, self.search_type, self.kind)

    def __iter__(self):
        return iter(self.search_window())

    def count(self):
        if self.total_count is None:
            self.total_count = es.count(**{
                "body": {"query": self.query()},
                **self.query_index()
            })["count"]
        return self.total_count

    def scan(self):
        return scanner(
            es,
            query={
                **self.query_sort(),
                "_source": False,
                "query": self.query(),
            },
            preserve_order=bool(self.sort_by),
            raise_on_error=False,
        )

    def __getitem__(self, key):
        if isinstance(key, slice):
            size = len(range(*key.indices(self.total_count)))
            return self.search_window(size=size, offset=key.start)
        raise NotImplementedError()


class SearchResultSet:

    def __init__(self, response, search_type, kind):
        self.response = response
        self.search_type = search_type
        self.kind = kind

    def __iter__(self):
        for hit in self.response["hits"]["hits"]:
            yield self.result(hit)

    def result(self, hit):
        return SearchResult(hit)

    def filtered_text_groups(self):
        buckets = []
        for bucket in self.response["aggregations"]["filtered_text_group"]["buckets"]:
            buckets.append({
                "text_group": cts.collection(bucket["key"]).as_json(),
                "count": bucket["doc_count"],
            })
        return sorted(buckets, key=itemgetter("count"), reverse=True)


class SearchResult:

    def __init__(self, hit):
        self.hit = hit
        self.passage = cts.passage(hit["_id"])
        self.link_urn = self.passage.urn  # @@@ consider dynamically chunking and giving a better passage URN
        self.raw_content = hit["highlight"].get("raw_content", [""])
        self.content_highlights = hit["highlight"].get("content", [""])[0]
        self.lemma_highlights = hit["highlight"].get("lemma_content", [""])[0]
        self.highlighter = Highlighter(
            self.passage,
            self.content_highlights if self.content_highlights else self.lemma_highlights,
        )
        self.sort_idx = hit["_source"]["sort_idx"]

    def __getitem__(self, key):
        missing = object()
        value = getattr(self, key, missing)
        if value is missing:
            raise KeyError(key)
        return value

    @property
    def content(self):
        return self.highlighter.fragments()

    @property
    def highlights(self):
        return self.highlighter.tokens()

    @property
    def link(self):
        return reverse("reader", kwargs={"urn": self.link_urn})


w_re = regex.compile(fr"(?:<em>)?(?:\w[-\w]*|{chr(0xfffd)})(?:</em>)?")


class Highlighter:

    def __init__(self, passage, highlights):
        self.passage = passage
        self.highlights = highlights

    def tokens(self):
        if not hasattr(self, "_tokens"):
            acc = set()
            it = zip(
                self.highlights.split(" "),
                [(t["w"], t["i"]) for t in self.passage.tokenize(whitespace=False)]
            )
            for hw, (sw, si) in it:
                if hw:
                    if w_re.match(hw):
                        if "<em>" in hw:
                            acc.add((sw, si))
            self._tokens = acc
        return self._tokens

    def content(self):
        if not hasattr(self, "_content"):
            acc = []
            highlighted_tokens = self.tokens()
            for token in self.passage.tokenize():
                if (token["w"], token["i"]) in highlighted_tokens:
                    acc.extend(["<em>", token["w"], "</em>"])
                else:
                    acc.append(token["w"])
            self._content = "".join(acc)
        return self._content

    def fragments(self, context=5):
        content = self.content()
        L = content.split(" ")
        acc = []
        for i, w in enumerate(L):
            fragment = []
            if regex.match(r"</?em>", w):
                fragment.extend(L[max(0, i - context):i])
                fragment.append(w)
                fragment.extend(L[i + 1:i + context + 1])
                acc.append(" ".join(fragment))
        return acc
