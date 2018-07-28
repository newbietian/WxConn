# coding=utf8
import base64
# 不支持大文件
# 将小文件按照下面格式输入
images = [
    {"name": "bottom_share", "path": r"bottom_share.png"},
    {"name": "pure_code_w_214", "path": r"pure_code_w_214.png"},
]

if __name__ == "__main__":
    target = open("html_images.py", "a")
    for file_dict in images:
        name = file_dict["name"]
        path = file_dict["path"]
        with open(path, "rb") as f:
            base64_data = base64.b64encode(f.read())
            target.write('%s = "%s"' % (name, base64_data))
            target.write("\n")
            f.close()
    target.close()