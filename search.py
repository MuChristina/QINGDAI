import os.path

import fitz
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from PyInquirer import prompt

from build_index import INDEX_DIR, DummyAnalyzer

PDF_FILES_DIR = "pdf_files"
OCR_RESULTS_DIR = "ocr_results"
TEMP_DIR = "temp"

INPUT = [
    {
        'type': "input",
        "name": "inp",
        "message": "請輸入帶查詢內容, 或輸入 q 退出:",
    },
]


if __name__ == "__main__":
    if not os.path.exists(TEMP_DIR):
        os.mkdir(TEMP_DIR)

    ix = open_dir(INDEX_DIR)
    searcher = ix.searcher()
    content_t_cn_parser = QueryParser("content_t_cn", ix.schema)
    # content_s_cn_parser = QueryParser("content_s_cn", ix.schema)
    content_raw_parser = QueryParser("content_raw", ix.schema)

    while True:
        for f in os.listdir(TEMP_DIR):
            os.remove(f"{TEMP_DIR}/{f}")

        inp_answer = prompt(INPUT)
        inp = inp_answer.get("inp")
        if inp in ("q", "exit", "quit"):
            break

        if len(inp) == 1:
            query = content_raw_parser.parse(inp)
        else:
            query = content_t_cn_parser.parse(inp)

        cont = True
        start_page = 1
        while cont:
            cont = False
            results = searcher.search_page(query, pagenum=start_page, pagelen=10)
            choices = []
            choice_to_hit = {}
            for hit in results:
                vol = hit["vol"]
                page = hit["page"]
                content: str = hit["content_raw"]
                idx = content.find(inp)
                content = content[max(idx - 10, 0): min(idx + 10, len(content))]
                side = "上半" if hit["side"] == 0 else "下半"
                choice = f"[{hit.rank}] {vol} 卷 {page} 頁 {side} 部分 {content}"
                choice_to_hit[choice] = hit
                choices.append(choice)
            if results.pagenum < results.pagecount:
                choices.append("下一頁")
            choices.append("退出")
            options = [
                {
                    'type': 'list',
                    'name': 'choice',
                    'message': f'第 {results.pagenum} 页, 共 {results.pagecount} 頁, 選中打開對應頁',
                    'choices': choices
                },
            ]
            choice_answer = prompt(options)
            choice = choice_answer.get("choice")
            if choice == "退出":
                break
            elif choice == "下一頁":
                start_page += 1
                cont = True
            else:
                hit = choice_to_hit[choice]
                vol = hit["vol"]
                page = hit["page"]
                side = hit["side"]

                pdf_file_path = f"{PDF_FILES_DIR}/{vol}.pdf"
                temp_img_path = f"{TEMP_DIR}/{vol}_{page}.jpg"
                pdf_document = fitz.Document(pdf_file_path)
                pdf_page = pdf_document[int(page)]
                pdf_page.get_pixmap(dpi=500).save(temp_img_path)

                img = mpimg.imread(temp_img_path)
                plt.imshow(img)
                plt.show()
                cont = True