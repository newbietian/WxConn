# coding=utf8
import base64
images = [
    {"name": "zhifubao_hongbao", "path": r"zhifubao.png"},
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