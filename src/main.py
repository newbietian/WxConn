# coding=utf8
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import analysis as ALS
import base64
import os
import shutil
import images
import Queue
import threading

# [linux] sudo apt-get install python-numpy python-matplotlib
import matplotlib
import matplotlib.pyplot as plt

# 路径常量定义
VERSION = "v1.0"
DATA = "./WxConnData"
RESOURCE = DATA + "/resource"
RES_APP_TITLE = RESOURCE + "/app_title.png"
RES_APP_ICON = RESOURCE + "/app_icon.ico"

PUBLIC_QR = DATA + "/qrcodes"
PUBLIC_QR_1 = PUBLIC_QR + "/ads_1.png"
PUBLIC_QR_2 = PUBLIC_QR + "/ads_2.png"
PUBLIC_QR_HONGBAO = PUBLIC_QR + "/alipay_hongbao.png"

ASSETS_TTF = RESOURCE + "/STXINGKA.TTF"

# 静态常量定义
WHAT_GOT_QR = 1
WHAT_NOTIFY_CONFIRM = 2
WHAT_LOGIN_SUCCESS = 3
WHAT_UPDATE_PROGRESS = 4
WHAT_DONE = 5
WHAT_PRE_LOGIN_SUCCESS = 6
WHAT_ANALYSIS_DATA = 10


def _init_resource():
    # 在当前目录创建base文件夹
    # 判断是否已存在
    if os.path.isdir(DATA):
        # 删除已存在
        # os.system("rm -rf " + '"' + base_path + '"')
        # os.removedirs(base_path) 非空会报错
        shutil.rmtree(DATA)
    # 创建base文件夹
    os.mkdir(DATA)
    os.mkdir(RESOURCE)
    os.mkdir(PUBLIC_QR)

    with open(RES_APP_TITLE, 'wb') as f1:
        app_title = base64.b64decode(images.res_app_title)
        f1.write(app_title)
        f1.close()

    with open(RES_APP_ICON, 'wb') as f2:
        app_icon = base64.b64decode(images.res_app_icon)
        f2.write(app_icon)
        f2.close()

    # ads
    with open(PUBLIC_QR_1, 'wb') as ads1:
        pic_ads1 = base64.b64decode(images.ads_1)
        ads1.write(pic_ads1)
        ads1.close()

    with open(PUBLIC_QR_2, 'wb') as ads2:
        pic_ads2 = base64.b64decode(images.ads_2)
        ads2.write(pic_ads2)
        ads2.close()

    with open(PUBLIC_QR_HONGBAO, 'wb') as hongbao:
        pic_hongbao = base64.b64decode(images.zhifubao_hongbao)
        hongbao.write(pic_hongbao)
        hongbao.close()


def _init_ttf():
    import assets

    with open(ASSETS_TTF, 'wb') as ttf:
        ttf_data = base64.b64decode(assets.stxingka_ttf)
        ttf.write(ttf_data)
        ttf.close()


class UI(object):
    def __init__(self, master=None, *args, **kwargs):
        self.master = master

        # 初始化plt todo，因为plt在子线程中执行会出现自动弹出弹框并阻塞主线程的行为，plt行为均放在主线程中
        self._init_plt()

        self.running = True
        self.queue = Queue.Queue()
        self.periodicCall()

        self.intro = Introduction(master, *args, **kwargs)
        self.intro.pack(fill=tk.BOTH, expand=1)
        self.intro.on_click = self.gotoQrcode

        self.qrscan = QrScan(master, *args, **kwargs)
        self.qrscan.pack(fill=tk.BOTH, expand=1)

        self.main = Main(master, *args, **kwargs)
        self.main.pack(fill=tk.BOTH, expand=1)

        self.analyst = threading.Thread(target=ALS.analysis, args=(self.queue,))
        self.analyst.setDaemon(True)
        self.generator = threading.Thread(target=ALS.generate_result, args=(self.queue,))
        self.generator.setDaemon(True)

        self.master.protocol("WM_DELETE_WINDOW", self.onClose)

    def onClose(self):
        self.running = False
        self.intro.destroy()
        self.qrscan.destroy()
        self.main.destroy()
        import sys
        sys.exit(0)

    def periodicCall(self):
        """
        Check every 200 ms if there is something new in the queue.
        """
        self.processIncoming()
        if self.running:
            self.master.after(200, self.periodicCall)

    def processIncoming(self):
        """Handle all messages currently in the queue, if any."""
        while self.queue.qsize():
            print "processIncoming"
            try:
                msg = self.queue.get(0)
                print msg
                if msg['mode'] == WHAT_GOT_QR:
                    self.qrscan.update_qrcode()
                elif msg['mode'] == WHAT_NOTIFY_CONFIRM:
                    self.qrscan.update_to_confirm()
                elif msg['mode'] == WHAT_LOGIN_SUCCESS:
                    self.gotoMain()
                elif msg['mode'] == WHAT_UPDATE_PROGRESS:
                    progress = msg['progress']
                    self.main.update_progress(value=progress)
                elif msg['mode'] == WHAT_DONE:
                    self.main.done()
                elif msg['mode'] == WHAT_ANALYSIS_DATA:
                    self.generate_sex_pic(msg['sex_data'])
                    self.generate_city_pic(msg['city_data'])
                    self.generate_province_pic(msg['provinces_data'])
                    self.generator.start()
                elif msg['mode'] == WHAT_PRE_LOGIN_SUCCESS:
                    self.qrscan.update_to_pre_login_success()
                    #ALS.generate_result(com_queue=self.queue)
                # Check contents of message and do whatever is needed. As a
                # simple test, print it (in real life, you would
                # suitably update the GUI's display in a richer fashion).
            except Queue.Empty:
                # just on general principles, although we don't
                # expect this branch to be taken in this case
                pass

    def start(self):
        self.intro.draw()

    def gotoQrcode(self):
        self.intro.destroy()
        # 运行线程
        self.analyst.start()
        # 显示qrscan
        self.qrscan.draw()

    def gotoMain(self):
        self.qrscan.destroy()
        self.main.set_header(path=ALS.user_header)
        self.main.draw()

    def _init_plt(self):
        font = {'family': ['xkcd', 'Humor Sans', 'Comic Sans MS'],
                'weight': 'bold',
                'size': 14}
        matplotlib.rc('font', **font)
        # 这行代码使用「手绘风格图片」，有兴趣小伙伴可以google搜索「xkcd」，有好玩的。
        plt.xkcd()
        self.bar_color = ('#55A868', '#4C72B0', '#C44E52', '#8172B2', '#CCB974', '#64B5CD')
        self.title_font_size = 'x-large'

    def generate_sex_pic(self, sex_data):
        """
        生成性别数据图片
        因为plt在子线程中执行会出现自动弹出弹框并阻塞主线程的行为，plt行为均放在主线程中
        :param sex_data:
        :return:
        """
        # 绘制「性别分布」柱状图
        # 'steelblue'
        bar_figure = plt.bar(range(3), sex_data, align='center', color=self.bar_color, alpha=0.8)
        # 添加轴标签
        plt.ylabel(u'Number')
        # 添加标题
        plt.title(u'Male/Female in your Wechat', fontsize=self.title_font_size)
        # 添加刻度标签
        plt.xticks(range(3), [u'Male', u'Female', u'UnKnown'])
        # 设置Y轴的刻度范围
        # 0, male; 1, female; 2, unknown
        max_num = max(sex_data[0], max(sex_data[1], sex_data[2]))
        plt.ylim([0, max_num * 1.1])

        # 为每个条形图添加数值标签
        for x, y in enumerate(sex_data):
            plt.text(x, y + 5, y, ha='center')

        # 保存图片
        plt.savefig(ALS.result_path + '/2.png')
        # todo 如果不调用此处的关闭，就会导致生成最后一个图像出现折叠、缩小的混乱
        #bar_figure.remove()
        plt.clf()
        plt.delaxes()
        #plt.close()

        # 显示图形
        # plt.show()

    def generate_province_pic(self, provinces_data):
        """
        生成省份数据图片
        因为plt在子线程中执行会出现自动弹出弹框并阻塞主线程的行为，plt行为均放在主线程中
        :param data:
        :return:
        """
        provinces_people = provinces_data["provinces_people"]
        provinces_explode = provinces_data["provinces_explode"]
        provinces = provinces_data["provinces"]

        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = int(round(pct * total / 100.0))
                return '{v:d}'.format(p=pct, v=val)
            return my_autopct
        province_fig, ax1 = plt.subplots()
        ax1.pie(provinces_people, explode=provinces_explode, colors=self.bar_color, labels=provinces,
                autopct=make_autopct(provinces_people), shadow=True, startangle=90)
        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        plt.title('Top 6 Provinces of your friends distributed', fontsize=self.title_font_size)  # 图像题目
        plt.savefig(ALS.result_path + '/3.png')
        # todo 如果不调用此处的关闭，就会导致生成最后一个图像出现折叠、缩小的混乱
        #plt.close()
        # plt.show()

    def generate_city_pic(self, city_data):
        """
        生成城市数据图片
        因为plt在子线程中执行会出现自动弹出弹框并阻塞主线程的行为，plt行为均放在主线程中
        :param data:
        :return:
        """
        font = {'family': ['xkcd', 'Humor Sans', 'Comic Sans MS'],
                'weight': 'bold',
                'size': 12}
        matplotlib.rc('font', **font)
        cities = city_data['cities']
        city_people = city_data['city_people']

        # 绘制「性别分布」柱状图
        plt.barh(range(len(cities)), width=city_people, align='center', color=self.bar_color, alpha=0.8)
        # 添加轴标签
        plt.xlabel(u'Number of People')
        # 添加标题
        plt.title(u'Top %d Cities of your friends distributed' % len(cities), fontsize=self.title_font_size)
        # 添加刻度标签
        plt.yticks(range(len(cities)), cities)
        # 设置X轴的刻度范围
        plt.xlim([0, city_people[0] * 1.1])

        # 为每个条形图添加数值标签
        for x, y in enumerate(city_people):
            plt.text(y + 5, x, y, ha='center')

        # 显示图形
        plt.savefig(ALS.result_path + '/4.png')
        # todo 如果调用此处的关闭，就会导致应用本身也被关闭
        # plt.close()
        # plt.show()


class Introduction(tk.Frame):
    def __init__(self, master=None, *args, **kwargs):
        tk.Frame.__init__(self, master=master, *args, **kwargs)
        self.bgcolor = 'white'
        self.on_click = None

    def draw(self):
        self.title_canvas = tk.Canvas(self, bg=self.bgcolor, width=250, height=80, bd=0, highlightthickness=0, relief='ridge')
        self.title_pic = self._resize_ads_qrcode(RES_APP_TITLE, size=(250, 80))
        self.title_canvas.create_image(0, 0, anchor='nw', image=self.title_pic)
        self.title_canvas.pack(padx=35, pady=10)

        # 作者
        self.lable = tk.Label(self,
                     text='作者：湿兄ptt\n微信公众号：猿湿Xoong',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     font=('Times',10),  # 字体和字体大小
                     width=15, height=2  # 标签长宽
                     )
        self.lable.pack(fill=tk.BOTH)  # 固定窗口位置

        # 提示
        self.lable_3 = tk.Label(self,
                     text='基于微信网页版\nbased on github itchat',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     fg='blue',
                     font=('Times',8),  # 字体和字体大小
                     width=15, height=2  # 标签长宽
                     )
        self.lable_3.pack(pady=2, fill=tk.BOTH)  # 固定窗口位置

        # 群提示
        self.about_qun = tk.Label(self,
                     text='★网页版获取群聊★\n★需先将其保存到手机微信通讯录★',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     font=('Times',12),  # 字体和字体大小
                     width=15, height=2 # 标签长宽
                     )
        self.about_qun.pack(pady=5, fill=tk.BOTH)  # 固定窗口位置

        # 第一点提示
        self.lable_1 = tk.Label(self,
                     text='1.本程序不收集或上传任何信息\n所有网络活动均是与微信服务器进行',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     font=('Times',12),  # 字体和字体大小
                     width=15, height=2  # 标签长宽
                     )
        self.lable_1.pack(pady=2, fill=tk.X)  # 固定窗口位置

        # 第二点提示
        self.lable_2 = tk.Label(self,
                     text='2.为防止程序被恶意篡改请确保\n程序是从湿兄或他的小伙伴那获取的',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     font=('Times',12),  # 字体和字体大小
                     width=15, height=2  # 标签长宽
                     )
        self.lable_2.pack(pady=2,fill=tk.BOTH)  # 固定窗口位置

        # 第三点提示
        self.lable_3 = tk.Label(self,
                     text='3.将exe文件的MD5与公众号后台\nMD5对比，即可判断是否被恶意篡改',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     font=('Times',12),  # 字体和字体大小
                     width=15, height=2  # 标签长宽
                     )
        self.lable_3.pack(pady=2,fill=tk.BOTH)  # 固定窗口位置

        # 法律声明
        self.law = tk.Label(self,
                     text='本软件开源免费，请在遵守中国\n相关法律法规与微信使用规范的前提下使用\n请勿用于非法用途，如产生法律纠纷与开发者无关。',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     fg='red',
                     font=('Times',9),  # 字体和字体大小
                     width=15, height=4  # 标签长宽
                     )
        self.law.pack(pady=2,fill=tk.BOTH)  # 固定窗口位置

        # Button
        btn_enter = tk.Button(self, text='我知道了',bg='#25BF2F',fg='white',font=('Times',11),
                              width=13, height=2,
                              bd=0, highlightthickness=0, relief='ridge',command=self.on_click)  # 定义一个`button`按钮，名为`Login`,触发命令为`usr_login`
        btn_enter.pack(pady=10)

    def _resize_ads_qrcode(self, path, size=(100,100)):
        image_qr = Image.open(path)
        image_qr = image_qr.resize(size, Image.ANTIALIAS)
        return ImageTk.PhotoImage(image=image_qr)


class QrScan(tk.Frame):
    def __init__(self, master=None, *args, **kwargs):
        tk.Frame.__init__(self, master=master, *args, **kwargs)
        self.qrcode = None
        self.bgcolor = 'white'

    def draw(self):
        self.title_canvas = tk.Canvas(self, bg=self.bgcolor, width=250, height=80, bd=0, highlightthickness=0, relief='ridge')
        self.title_pic = self._resize_ads_qrcode(RES_APP_TITLE, size=(250, 80))
        self.title_canvas.create_image(0, 0, anchor='nw', image=self.title_pic)
        self.title_canvas.pack(padx=35, pady=15)

        self.qrcode = tk.Canvas(self, bg=self.bgcolor, width=200, height=200)
        #self.qrcode_pic = self._resize_ads_qrcode('qrcode.png', size=(200, 200))
        #self.qrcode.create_image(0, 0, anchor='nw', image=self.qrcode_pic)
        self.qrcode.pack(pady=30)


        # 提示
        self.lable_tip = tk.Label(self,
                     text='请稍等',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     font=('Times',12),  # 字体和字体大小
                     width=15, height=2  # 标签长宽
                     )
        self.lable_tip.pack(pady=2,fill=tk.BOTH)  # 固定窗口位置

    def update_qrcode(self):
        self.lable_tip.config(text='请用微信扫一扫登录')
        self.lable_tip.update()

        self.qrcode_pic = self._resize_ads_qrcode(ALS.user_qrcode_path, size=(200, 200))
        self.qrcode.create_image(0, 0, anchor='nw', image=self.qrcode_pic)

    def update_to_confirm(self):
        self.lable_tip.config(text='请在手机上确认登录')
        self.lable_tip.update()

    def update_to_pre_login_success(self):
        self.lable_tip.config(text='登录成功，请稍等')
        self.lable_tip.update()

    def _resize_ads_qrcode(self, path, size=(100, 100)):
        image_qr = Image.open(path)
        image_qr = image_qr.resize(size, Image.ANTIALIAS)
        return ImageTk.PhotoImage(image=image_qr)


class Main(tk.Frame):
    def __init__(self, master=None, *args, **kwargs):
        tk.Frame.__init__(self, master=master, *args, **kwargs)
        self.canvas=None
        self.header_path = 'header.jpg'
        self.bgcolor='white'
        self.success = None
        # 推广公众号的二维码路径
        self.set_ads_qr_path = os.listdir(PUBLIC_QR)
        # 当前ads的下标
        self.ads_index = 0

    def draw(self):
        # 进度条
        # frm_progress=tk.Frame(window, bg='white')
        # frm_progress.pack(side='top')
        # app = Progress(window, width=120, height=120, bg='White')
        # progress_image = Image.open('progress.png')
        # progress_image = progress_image.resize((120,120))
        # pri
        # mycanvas = tk.Canvas(window, width=120, height=120, bg='White')
        # #tkimage=tk.PhotoImage(file='xoong-100.gif')
        # tkimage = ImageTk.PhotoImage(image=progress_image.rotate(10))
        # mycanvas.create_image(0, 0, anchor='nw', image=tkimage)
        # mycanvas.config()
        # mycanvas.pack()

        # 头像
        header_size = 60
        self.header_canvas = tk.Canvas(self, bg=self.bgcolor, height=header_size, width=header_size, bd=0, highlightthickness=0, relief='ridge')
        self.header = Image.open(self.header_path)
        self.header = self.header.resize((header_size, header_size))
        self.tkheader = ImageTk.PhotoImage(image=self.header)
        self.header_canvas.create_image(0, 0, anchor='nw', image=self.tkheader)
        self.header_canvas.pack(pady=35)

        # 进度指示
        self.lable_progress = tk.Label(self,
                     text='正在统计连接数...0%',  # 标签的文字
                     bg=self.bgcolor,  # 背景颜色
                     font=('Arial', 12),  # 字体和字体大小
                     width=15, height=2  # 标签长宽
                     )
        self.lable_progress.pack(fill=tk.X)  # 固定窗口位置

        # Button
        btn_enter = tk.Button(self, text='支\n付\n宝\n红\n包',bg='#db2d32',fg='white',font=('Times',11),
                              width=2, height=5,
                              highlightthickness=0,relief='ridge',bd=0, command=self.show_alipay_hongbao)  # 定义一个`button`按钮，名为`Login`,触发命令为`usr_login`
        btn_enter.place(x=300, y=20, anchor=tk.NW)

        # 进度条
        self.progress = ttk.Progressbar(self, orient='horizontal', length=200, mode='determinate')
        self.progress['maximum'] = 100
        self.progress['value'] = 0
        self.progress.pack()

        # 底部广告栏
        self.frm_ads = tk.Frame(self, width=width, height=height, bg='white')
        self.frm_ads.pack(fill=tk.BOTH, expand=1)

        self.ads = tk.Frame(self.frm_ads, width=width, height=height, bg='white')
        self.ads.pack(side='bottom',fill=tk.BOTH, expand=1)

        # you need to keep a reference to the photo object, otherwise, it will be out of the scope and be garbage collected.
        self.canvas = tk.Canvas(self.ads, bg='white', height=216, width=width)

        # 添加二维码
        # if self.set_ads_qr_path and len(self.set_ads_qr_path) == 6:
        #     self.qr_1 = self._resize_ads_qrcode(self.set_ads_qr_path[0])
        #     image = self.canvas.create_image(7, 0, anchor='nw', image=self.qr_1)
        #
        #     self.qr_2 = self._resize_ads_qrcode(self.set_ads_qr_path[1])
        #     image = self.canvas.create_image(111, 0, anchor='nw', image=self.qr_2)
        #
        #     self.qr_3 = self._resize_ads_qrcode(self.set_ads_qr_path[2])
        #     image = self.canvas.create_image(214, 0, anchor='nw', image=self.qr_3)
        #
        #     self.qr_4 = self._resize_ads_qrcode(self.set_ads_qr_path[3])
        #     image = self.canvas.create_image(7, 100, anchor='nw', image=self.qr_4)
        #
        #     self.qr_5 = self._resize_ads_qrcode(self.set_ads_qr_path[4])
        #     image = self.canvas.create_image(111, 100, anchor='nw', image=self.qr_5)
        #
        #     self.qr_6 = self._resize_ads_qrcode(self.set_ads_qr_path[5])
        #     image = self.canvas.create_image(214, 100, anchor='nw', image=self.qr_6)

        self.canvas.pack(side='bottom')

        l = tk.Label(self.ads,
                     text='优质技术公众号推荐',  # 标签的文字
                     bg='white',  # 背景颜色
                     fg='red',
                     font=('Arial', 12),  # 字体和字体大小
                     width=15, height=1  # 标签长宽
                     )
        l.pack(side='bottom')  # 固定窗口位置

        self.ads_animation()

        # import threading
        # thread = threading.Thread(target=self.test)
        # thread.setDaemon(True)
        # thread.start()
        #self.test()

    def show_alipay_hongbao(self):
        hongbao_window = tk.Toplevel()
        hww = 200
        hwh = 300
        img = self._resize_ads_qrcode(PUBLIC_QR_HONGBAO, size=(hww, hwh))
        canvas = tk.Canvas(hongbao_window, width=hww, height=hwh, bg='white')
        canvas.create_image(0, 0, image=img, anchor="nw")
        canvas.pack()

        hongbao_x = window.winfo_x() - hww - 10
        if window.winfo_x() < hww + 10:
            hongbao_x = window.winfo_x() + width + 10

        hongbao_window.geometry('{w}x{h}+{x}+{y}'.format(w=hww, h=hwh, x=hongbao_x, y=window.winfo_y()))
        hongbao_window.mainloop()

    # def test(self):
    #     import matplotlib.pyplot as plt
    #     import matplotlib
    #     plt.bar(range(3), [1, 2, 3], align='center', color='white', alpha=0.8)

    def ads_animation(self):
        if self.ads_index % 2 == 0:
            self.ads_1 = self._resize_ads_qrcode(PUBLIC_QR_1, size=(318, 214))
            image = self.canvas.create_image(0, 0, anchor='nw', image=self.ads_1)
        elif self.ads_index % 2 == 1:
            self.ads_2 = self._resize_ads_qrcode(PUBLIC_QR_2, size=(318, 214))
            image = self.canvas.create_image(0, 0, anchor='nw', image=self.ads_2)
        self.ads_index = (self.ads_index + 1) % 2
        self.master.after(10000, self.ads_animation)

    def _resize_ads_qrcode(self, path, size=(100,100)):
        image_qr = Image.open(path)
        image_qr = image_qr.resize(size, Image.ANTIALIAS)
        return ImageTk.PhotoImage(image=image_qr)

    def set_header(self, path):
        self.header_path = path

    def set_ads_qr_path(self, path):
        self.ads_qrpath = path

    def update_progress(self, value):
        text = '正在统计连接数...{value}%'
        self.lable_progress.config(text=text.format(value=value))
        self.lable_progress.update()
        self.progress.config(value=value)
        self.progress.update()

    def done(self):
        text = '统计成功\n请在微信"文件传输助手"查看'
        self.lable_progress.config(text=text)
        self.lable_progress.update()


if __name__ == "__main__":
    # 初始化资源
    _init_resource()
    # 初始化字体
    ttf_init_thread = threading.Thread(target=_init_ttf)
    ttf_init_thread.start()

    window = tk.Tk()
    # 不可更改窗口大小
    window.resizable(False, False)
    # 标题
    window.title('你的微信到底连接多少人'+ VERSION)
    # icon
    window.wm_iconbitmap(default=RES_APP_ICON)
    # 背景颜色
    window.config(background="white")

    # 窗口大小和位置
    width = 320
    height = 500
    x = (window.winfo_screenwidth() - width) / 2
    y = (window.winfo_screenheight() - height) / 2
    window.geometry('{w}x{h}+{x}+{y}'.format(w=width, h=height, x=x, y=y))

    # main = Main(window, width=width, height=500, bg='white')
    # main.pack(fill=tk.BOTH, expand=1)
    # main.set_header('1.jpg')
    # main.draw()
    # main.update_progress(56)

    # timer = threading.Timer(1, main.set_progress, args=(100,))
    # timer.start()

    # introduction = Introduction(window, width=width, height=500, bg='white')
    # introduction.pack(fill=tk.BOTH, expand=1)
    # introduction.draw()

    # qrscan = QrScan(window, width=width, height=height, bg='white')
    # qrscan.pack(fill=tk.BOTH, expand=1)
    # qrscan.draw()
    #
    # timer = threading.Timer(1, qrscan.update_qrcode)
    # timer.start()

    ui = UI(window, width=width, height=height, bg='white')
    ui.start()

    window.mainloop()
