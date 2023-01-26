import json
import os
import shutil
from typing import TYPE_CHECKING

from jieba.analyse import ChineseAnalyzer
from whoosh.analysis import Token, Tokenizer
from whoosh.fields import NUMERIC, TEXT, Schema
from whoosh.index import create_in
from zhconv import convert

if TYPE_CHECKING:
    from whoosh.index import Index


INDEX_DIR = "index"
RECOGNITION_RESULTS_DIR = "ocr_results_temp"
PROB_THRESHOLD = 0.2


class DummyAnalyzer(Tokenizer):
    def __call__(self, text, **kargs):
        words = list(text)
        cur_pos = 0
        for word in words:
            token = Token()
            token.original = token.text = word
            token.pos = cur_pos
            token.startchar = cur_pos
            token.endchar = cur_pos
            cur_pos += 1
            yield token


def initialize() -> "Index":
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)

    analyzer = ChineseAnalyzer()
    schema = Schema(
        vol=NUMERIC(stored=True),
        page=NUMERIC(stored=True),
        side=NUMERIC(stored=True),
        content_t_cn=TEXT(stored=True, analyzer=analyzer),
        content_s_cn=TEXT(stored=True, analyzer=analyzer),
        content_raw=TEXT(stored=True, analyzer=DummyAnalyzer()),
    )
    os.mkdir(INDEX_DIR)
    return create_in(INDEX_DIR, schema)


def build(idx: "Index"):
    writer = idx.writer()
    files = os.listdir(RECOGNITION_RESULTS_DIR)

    for i in range(len(files)):
        f = files[i]
        if not f.endswith(".json"):
            continue

        print(f"{f}, progress: {i}/{len(files)}")
        with open(f"{RECOGNITION_RESULTS_DIR}/{f}") as fd:
            j = json.load(fd)

        chars = []
        for char_id in j["char_ids"]:
            if j["char_probs"][char_id] > PROB_THRESHOLD:
                chars.append(j["chars"][char_id])

        content_t_cn = "".join(chars)
        content_s_cn = convert(content_t_cn, "zh-cn")
        vol, page, side = f[:-5].split("_")
        writer.add_document(
            vol=vol,
            page=page,
            side=side,
            content_t_cn=content_t_cn,
            content_s_cn=content_s_cn,
            content_raw=content_s_cn,
        )
    writer.commit()


if __name__ == "__main__":
    idx = initialize()
    build(idx)