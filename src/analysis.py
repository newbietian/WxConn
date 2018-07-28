# coding=utf8
import json
import time
import os
import base64
import shutil
import threading
import sys
import images

import itchat
from pypinyin import lazy_pinyin

# [linux] sudo apt-get install python-pandas
import pandas as pd

from PIL import Image, ImageDraw, ImageFont

# 解决matplotlib图例无法显示中文
# import matplotlib
# print(matplotlib.matplotlib_fname())
# 查看输出配置文件位置 如：
# /usr/local/lib/python2.7/dist-packages/matplotlib/mpl-data/matplotlibrc
# 修改其中的 #font.family: sans-serif -> font.family: Microsoft YaHei
# 参考https://www.zhihu.com/question/25404709

class Worker(threading.Thread):
    def __init__(self, target, queue=None):
        threading.Thread.__init__(self)
        self.target = target
        self.com_queue = queue

    def run(self):
        self.target(self.com_queue)

# ------------------------------------------------------------------
# 定义全局变量
# 好友列表
all_friend_list = []
# 群聊好友数， 去重后
friends_in_chatrooms = 0
# 重复个数
duplicate = 0

# 防止qrcode多次回调的flag
has_return_qr = False

# 后续用到变量
base_path = './WxConnData/how_many_friends_in_your_wechat'
result_path = base_path + '/results'

title_path = result_path + '/0.png'
summary_path = result_path + '/1.png'
shixoong_qr_path = result_path + '/999.png'

user_qrcode_name = 'qrcode.png'
user_qrcode_path =  base_path + '/' + user_qrcode_name
user_header = base_path + '/user_header.png'
user_nickname = ''

# 好友数量
friends_num = 0
# 备注好友
remarked_friends = 0
# 星标好友
star_friends = 0


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# callback
# 获取二维码，请扫描
callback_got_qr=None
# 提示在手机端确认
callback_please_confirm = None
# 登录成功回调
callback_login_success = None
# 进度条更新
callback_update_progress = None
# 分析完成回调
callback_analysis_done = None
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ------------------------------------------------------------------
# Friend类定义
class Friend(object):
    def __init__(self, user_name, sex=0, province='', city='', remark=0, star=0):
        """
        构造方法，初始化Friend类
        :param user_name: 每次登陆后，系统为所有相关人生成的「一次性」唯一标识
        :param sex: 1为男，2为女，0为unknown
        :param province: 省份
        :param city: 城市
        :param remark: 是否备注 RemarkName
        :param star: 星标好友 StarFriend 0 不是，1是
        """
        self.user_name = user_name
        self.sex = sex
        self.province = province
        self.city = city
        self.remark = remark
        self.star = star

    def __eq__(self, other):
        """
        根据唯一标识UserName，判断两个Friend对象是否相等
        :param other: 另一个Friend对象
        :return: True即相等，False则不等
        """
        if other is None:
            return False
        if type(other) is not Friend:
            return False
        return self.user_name == other.user_name

    def __str__(self):
        return self.__dict__


# 用于解决Friend无法直接转换成json数据的问题
class FriendEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Friend):
            return obj.__str__()
        return json.JSONEncoder.default(self, obj)


# ------------------------------------------------------------------
# 定义：合并图片
def combine_images(imgs_path, result_w=800, inner_img_w=700, inner_img_spacing=50, top_margin=30, bottom_margin=30,
                   bk_color='white'):
    imgs_path = imgs_path
    width = inner_img_w
    result_width = result_w
    result_height = 0
    image_spacing = inner_img_spacing
    image_margin_top = top_margin
    image_margin_bottom = bottom_margin
    bk_color = bk_color

    imgs_h = []
    for path in imgs_path:
        im = Image.open(path)
        scale = float(im.size[0]) / im.size[1]
        h = int(width / scale)
        imgs_h.append(h)
        # print "path = %s, height = %d" % (path, h)

    qr_code_margin_ext = 100
    result_height += sum(imgs_h) + (len(imgs_h) - 1) * image_spacing + image_margin_top + image_margin_bottom + qr_code_margin_ext
    # print result_height

    bk = Image.new('RGB', (result_width, result_height), bk_color)
    x_paste = (result_width - width) / 2
    for index, path in enumerate(imgs_path):
        # print "path = %s, index = %d" % (path, index)
        im = Image.open(path).resize((width, imgs_h[index]))
        # if is first picture y coordinate is 0
        # else equals to sum of previous images and sum of spacing
        y_paste = (image_margin_top if index == 0
                   else (image_margin_top + sum(imgs_h[0:index - 1]) + imgs_h[index - 1] + image_spacing * index))
        # paste qrcode
        if index == len(imgs_path) - 1:
            y_paste = y_paste + qr_code_margin_ext
        # print y_paste
        bk.paste(im, (x_paste, y_paste))
        im.close()
    return bk


# ------------------------------------------------------------------
# 定义生成Summary
def generate_summary(all_friends, remarked, star):
    global summary_path, user_header
    width = 700
    im = Image.open(summary_path)
    #fnt_path = '/usr/share/fonts/truetype/ttf-liberation/LiberationMono-Bold.ttf'
    fnt_path = "./WxConnData/resource/STXINGKA.TTF"
    color_all = "#000000"
    color_remark = "#000000"
    color_star = "#000000"

    # 支持调节1位到99w位的
    fnt_all_size = 100
    fnt_all_start = (340, 198)
    all_friends_len = len(str(all_friends))
    if all_friends_len == 1:
        fnt_all_start = (395, 168)  #
        fnt_all_size = 120
    elif all_friends_len == 2:
        fnt_all_start = (370, 178)  #
        fnt_all_size = 110
    elif all_friends_len == 3:
        fnt_all_start = (345, 182)  #
        fnt_all_size = 100
    elif all_friends_len == 4:
        fnt_all_start = (340, 188)  #
        fnt_all_size = 80
    elif all_friends_len == 5:
        fnt_all_start = (340, 198)  #
        fnt_all_size = 65
    elif all_friends_len == 6:
        fnt_all_start = (340, 206)
        fnt_all_size = 50
    fnt_all = ImageFont.truetype(fnt_path, size=fnt_all_size)

    # 支持调节1位到4999位的
    fnt_remarked_size = 100
    fnt_remarked_start = (455, 308)
    remarked_len = len(str(remarked))
    if remarked_len == 1:
        fnt_remarked_size = 100
        fnt_remarked_start = (485, 292)  #
    elif remarked_len == 2:
        fnt_remarked_size = 80
        fnt_remarked_start = (468, 300)  #
    elif remarked_len == 3:
        fnt_remarked_size = 60
        fnt_remarked_start = (457, 310)  #
    elif remarked_len == 4:
        fnt_remarked_size = 50
        fnt_remarked_start = (455, 318)  #
    fnt_remarked = ImageFont.truetype(fnt_path, size=fnt_remarked_size)

    # 支持调节1-999位
    fnt_star_size = 70
    fnt_star_start = (450, 415)
    star_len = len(str(star))
    if star_len == 1:
        fnt_star_size = 90
        fnt_star_start = (474, 400)  #
    elif star_len == 2:
        fnt_star_size = 70
        fnt_star_start = (455, 413)  #
    elif star_len == 3:
        fnt_star_size = 50
        fnt_star_start = (450, 423)  #
    fnt_star = ImageFont.truetype(fnt_path, size=fnt_star_size)

    draw = ImageDraw.Draw(im)
    # 338-528,198
    draw.text(fnt_all_start, str(all_friends), fill=color_all, font=fnt_all)
    # 455-569,305
    draw.text(fnt_remarked_start, str(remarked), fill=color_remark, font=fnt_remarked)
    # 454 - 546, 415
    draw.text(fnt_star_start, str(star), fill=color_star, font=fnt_star)

    # paste avator
    # 130 * 130
    avator_w, avator_h = (130, 130)
    avator_im = Image.open(user_header).resize((avator_w, avator_h))

    bigsize = (avator_im.size[0] * 3, avator_im.size[1] * 3)
    # 遮罩对象
    mask = Image.new('L', bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(avator_im.size, Image.ANTIALIAS)
    avator_im.putalpha(mask)

    avator_margin = (width - avator_w) / 2
    im.paste(avator_im, (avator_margin, 0), avator_im)
    im.save(summary_path)
    im.close()
    avator_im.close()


# ------------------------------------------------------------------
# 定义微信二维码显示方法
def qrcode_handle(uuid, status, qrcode):
    global has_return_qr, base_path, user_qrcode_path
    if has_return_qr:
        return
    img_file = user_qrcode_path
    img = open(img_file, 'wb')
    img.write(qrcode)
    img.close()

    # 在网页版需放开
    # qr_img = Image.open(img_file)
    # plt.figure("Image")  # 图像窗口名称
    # plt.imshow(qr_img)
    # plt.axis('off')  # 关掉坐标轴为 off
    # plt.title('Scan QR to login')  # 图像题目
    # plt.show()
    # has_return_qr = True


# ------------------------------------------------------------------
"""
定义初始化函数
检查当前目录下以下内容：

检查并新建文件夹：./how_many_friends_in_your_wechat
创建结果存放文件夹：./how_many_friends_in_your_wechat/results/
相关需要图片准备：如模板、水印。
"""


def init():
    global base_path, result_path, title_path, summary_path, shixoong_qr_path
    # 在当前目录创建base文件夹
    # 判断是否已存在
    if os.path.isdir(base_path):
        # 删除已存在
        #os.system("rm -rf " + '"' + base_path + '"')
        # os.removedirs(base_path) 非空会报错
        shutil.rmtree(base_path)
    # 创建base文件夹
    os.mkdir(base_path)
    # 创建results文件夹
    os.mkdir(result_path)

    with open(title_path, 'wb') as f1:
        file_data = base64.b64decode(images.title_base64)
        f1.write(file_data)
        f1.close()

    with open(summary_path, 'wb') as f3:
        summary_data = base64.b64decode(images.summary_base64)
        f3.write(summary_data)
        f3.close()

    with open(shixoong_qr_path, 'wb') as f2:
        sx_qr_data = base64.b64decode(images.shixoong_base64)
        f2.write(sx_qr_data)
        f2.close()


# init()
# !ls how_many_friends_in_your_wechat
# !ls how_many_friends_in_your_wechat/results/
# !pwd

def open_qr(com_queue=None):
    for get_count in range(10):
        print ('Getting uuid')
        uuid = itchat.get_QRuuid()
        while uuid is None:
            uuid = itchat.get_QRuuid();
            time.sleep(1)
        print ('Getting QR Code')
        if itchat.get_QR(uuid, enableCmdQR=True, qrCallback=qrcode_handle):
            break
        elif get_count >= 9:
            print ('Failed to get QR Code, please restart the program')
            sys.exit()
    print ('Please scan the QR Code')
    # todo 更新手机显示
    if com_queue:
        com_queue.put({"mode": 1})
    return uuid

# ------------------------------------------------------------------
def analysis(com_queue=None):
    global all_friend_list, friends_in_chatrooms, duplicate, has_return_qr,\
        base_path, result_path, title_path, summary_path, shixoong_qr_path,\
        user_header, user_nickname, \
        friends_num, remarked_friends, star_friends

    # 扫码登录微信
    init()

    if itchat.check_login():
        itchat.logout()

    # 登录微信，需要扫面下方输出结果的二维码
    # 网页版
    # itchat.auto_login(enableCmdQR=True, qrCallback=qrcode_handle)
    # PC版
    uuid = open_qr(com_queue=com_queue)
    waitForConfirm = False
    while 1:
        status = itchat.check_login(uuid)
        if status == '200':
            if com_queue:
                com_queue.put({"mode": 6})
            break
        elif status == '201':
            if not waitForConfirm:
                print ('Please press confirm')
                # TODO 提示手机确认
                if com_queue:
                    com_queue.put({"mode":2})
                waitForConfirm = True
        elif status == '408':
            print ('Reloading QR Code')
            uuid = open_qr(com_queue=com_queue)
            waitForConfirm = False
    itchat.web_init()
    itchat.show_mobile_login()

    # ------------------------------------------------------------------
    """
    获取数据并去重
    联系人列表
    已保存到通讯录中群聊的人员
    """
    # 获取当前好友列表
    _friends_list = itchat.get_friends(update=True)

    # 获取头像并保存本地待用
    user = _friends_list[0]
    user.get_head_image(user_header)
    # 获取昵称
    user_nickname = user.NickName

    # todo 回调登录成功
    if com_queue:
        com_queue.put({"mode":3})

    # 好友个数
    friends_num = len(_friends_list[1:])

    # 将好友列表加入最终朋友列表，去除自己
    for one in _friends_list[1:]:
        remark = 0
        star = 0

        # 备注
        if one.RemarkName and one.RemarkName is not "":
            remark = 1
            remarked_friends += 1

        # 星标
        if one.StarFriend and one.StarFriend == 1:
            star = 1
            star_friends += 1

        friend = Friend(one.UserName, one.Sex, one.Province, one.City, remark, star)
        all_friend_list.append(friend)

    # 获取当前所有群聊列表
    chat_room_list = itchat.get_chatrooms(update=True)

    # 获取微信群聊中的所有成员
    if chat_room_list is None:
        print("你连一个群聊都没有找到~")
    else:
        print u"共找到群聊：%d个\n" % len(chat_room_list)
        #for room in tqdm(chat_room_list):
        for index, room in enumerate(chat_room_list):
            room_updated = itchat.update_chatroom(room.UserName, detailedMember=True)
            # print "正在处理:%d/%d，请稍后" % ((index + 1), len(chat_room_list)), '\r',

            # 获取一个群聊中，所有群成员的公开信息
            # print "memberlist = %d/%d" % (len(room_updated.MemberList),len(chat_room_list)), '\r',
            for member in room_updated.MemberList:
                friend = Friend(member.UserName, member.Sex, member.Province, member.City)
                if friend not in all_friend_list:
                    all_friend_list.append(friend)
                    friends_in_chatrooms += 1
                else:
                    duplicate += 1
                    # break # for test

            progress = int((index+1) / float(len(chat_room_list)) * 100)
            # todo 更新进度条
            if com_queue:
                com_queue.put({"mode":4, "progress": progress})

    print u"\n连接了%d人, 群聊人数%d, 好友人数%d." % (len(all_friend_list), friends_in_chatrooms, friends_num)

    # ------------------------------------------------------------------
    # 绘制数据
    # 初始化表格元组数据
    data_json = json.dumps(all_friend_list, cls=FriendEncoder)
    print '1'
    df = pd.read_json(data_json, orient="records")

    # 获取性别数据
    male_number = len(df[df['sex'] == 1])
    female_number = len(df[df['sex'] == 2])
    unknown_sex_number = len(df[df['sex'] == 0])
    sex_data = [male_number, female_number, unknown_sex_number]

    # 统计省份数据
    # 省份名称集合
    provinces = []
    # 各省份人数
    provinces_people = []
    # 饼图中哪个突出
    provinces_explode = [0.1]

    # 获得省份数据副本,已按数量排序
    province_df = df['province'].value_counts().copy()

    # 丢弃其中省份为空的好友数据
    # 统计前6省份
    for p in province_df.keys():
        if len(provinces) >= 6:
            break
        if not p:
            continue
        # 转为拼音
        provinces.append("".join(lazy_pinyin(p)).title())
        provinces_people.append(province_df[p])
        provinces_explode.append(0)

    # 删除多余的一个0
    provinces_explode.pop()

    # 进行城市数据显示
    # 城市
    cities = []
    # 各城市对应人数
    city_people = []

    city_df = df['city'].value_counts().copy()

    # 丢弃其中城市为空的好友数据城
    for c in city_df.keys():
        if len(cities) >= 5:
            break
        if not c:
            continue
        # 转为拼音
        cities.append("".join(lazy_pinyin(c)).title())
        city_people.append(city_df[c])

    # todo 注意由于plt在子线程中使用会出现问题，此处将plt生成图片部分转到主线程中执行。
    if com_queue:
        com_queue.put({"mode": 10,
                       "sex_data": sex_data,
                       "provinces_data": {"provinces_people": provinces_people, "provinces": provinces, "provinces_explode": provinces_explode},
                       "city_data": {"cities": cities, "city_people": city_people}
                       })
    print threading.currentThread()


def generate_result(com_queue=None):
    global friends_num, remarked_friends, star_friends
    # ------------------------------------------------------------------
    # 结果生成
    # 删除之前可能错在的png
    # !rm - rf how_many_friends_in_your_wechat / results / result.png
    # !ls -al how_many_friends_in_your_wechat/results

    print "generate_result..."
    img_path = result_path
    imgs = []
    [imgs.append(img_path + "/" + fn) for fn in os.listdir(img_path) if fn.endswith('.png')]
    imgs.sort()
    # print imgs

    final_img = result_path + "/result.png"

    # 生成summary
    generate_summary(friends_num + friends_in_chatrooms, remarked_friends, star_friends)

    # 生成最终结果
    bk = combine_images(imgs, inner_img_spacing=60)

    # 保存最终结果
    bk.save(final_img)
    bk.close()

    # 将最终结果发到手机端「文件传输助手」
    itchat.send_image(final_img, toUserName='filehelper')

    # todo 提示完成
    if com_queue:
        com_queue.put({"mode": 5})

    print u"已生成！请在手机端的「文件传输助手」查看结果，记得分享和关注猿湿Xoong喔！"
    print u"已生成！请在手机端的「文件传输助手」查看结果，记得分享和关注猿湿Xoong喔！"
    print u"已生成！请在手机端的「文件传输助手」查看结果，记得分享和关注猿湿Xoong喔！"

    print threading.currentThread()

    # while True:
    #     time.sleep(10)