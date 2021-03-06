# coding:utf-8

'''
@author = super_fazai
@File    : zhe_800_pintuan.py
@Time    : 2017/12/18 17:09
@connect : superonesfazai@gmail.com
'''

from random import randint
import json
import requests
import re
import time
from pprint import pprint
import gc
import pytz
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from time import sleep
import os

import sys
sys.path.append('..')

from settings import HEADERS, IS_BACKGROUND_RUNNING, ZHE_800_PINTUAN_SLEEP_TIME
from zhe_800_pintuan_parse import Zhe800PintuanParse
from my_pipeline import SqlServerMyPageInfoSaveItemPipeline
import datetime
from my_requests import MyRequests
from my_utils import get_shanghai_time, daemon_init

class Zhe800Pintuan(object):
    def __init__(self):
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            # 'Accept-Encoding:': 'gzip',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Host': 'pina.m.zhe800.com',
            'User-Agent': HEADERS[randint(0, 34)]  # 随机一个请求头
        }

    def get_pintuan_goods_info(self):
        '''
        模拟构造得到data的url, 得到近期所有的限时拼团商品信息
        :return:
        '''
        zid_list = []
        for page in range(0, 100):
            tmp_url = 'https://pina.m.zhe800.com/nnc/list/deals.json?page={0}&size=500'.format(
                str(page)
            )
            print('正在抓取的页面地址为: ', tmp_url)

            tmp_body = MyRequests.get_url_body(url=tmp_url, headers=self.headers)
            if tmp_body == '':
                tmp_body = '{}'
            try:
                tmp_data = json.loads(tmp_body)
                tmp_data = tmp_data.get('objects', [])
            except:
                print('json.loads转换tmp_data时出错!')
                tmp_data = []
            # print(tmp_data)

            if tmp_data == []:
                print('该tmp_url得到的object为空list, 此处跳过!')
                break

            tmp_zid_list = [(item.get('product', {}).get('zid', ''), page) for item in tmp_data]
            # print(tmp_zid_list)

            for item in tmp_zid_list:
                if item != '':
                    zid_list.append(item)

        zid_list = list(set(zid_list))
        print('该zid_list的总个数为: ', len(zid_list))
        print(zid_list)

        zhe_800_pintuan = Zhe800PintuanParse()
        my_pipeline = SqlServerMyPageInfoSaveItemPipeline()
        if my_pipeline.is_connect_success:
            db_goods_id_list = [item[0] for item in list(my_pipeline.select_zhe_800_pintuan_all_goods_id())]
            for item in zid_list:
                if item[0] in db_goods_id_list:
                    print('该goods_id已经存在于数据库中, 此处跳过')
                    pass
                else:
                    tmp_url = 'https://pina.m.zhe800.com/detail/detail.html?zid=' + str(item[0])
                    goods_id = zhe_800_pintuan.get_goods_id_from_url(tmp_url)

                    zhe_800_pintuan.get_goods_data(goods_id=goods_id)
                    goods_data = zhe_800_pintuan.deal_with_data()

                    if goods_data == {}:    # 返回的data为空则跳过
                        pass
                    else:                   # 否则就解析并且插入
                        goods_data['goods_id'] = str(item[0])
                        goods_data['spider_url'] = tmp_url
                        goods_data['username'] = '18698570079'
                        goods_data['page'] = str(item[1])
                        goods_data['pintuan_begin_time'], goods_data['pintuan_end_time'] = self.get_pintuan_begin_time_and_pintuan_end_time(schedule=goods_data.get('schedule', [])[0])

                        # print(goods_data)
                        zhe_800_pintuan.insert_into_zhe_800_pintuan_table(data=goods_data, pipeline=my_pipeline)
                    sleep(ZHE_800_PINTUAN_SLEEP_TIME)
                    gc.collect()

        else:
            pass
        try:
            del zhe_800_pintuan
        except:
            pass
        gc.collect()

    def get_pintuan_begin_time_and_pintuan_end_time(self, schedule):
        '''
        返回拼团开始和结束时间
        :param miaosha_time:
        :return: tuple  pintuan_begin_time, pintuan_end_time
        '''
        pintuan_begin_time = schedule.get('begin_time')
        pintuan_end_time = schedule.get('end_time')
        # 将字符串转换为datetime类型
        pintuan_begin_time = datetime.datetime.strptime(pintuan_begin_time, '%Y-%m-%d %H:%M:%S')
        pintuan_end_time = datetime.datetime.strptime(pintuan_end_time, '%Y-%m-%d %H:%M:%S')

        return pintuan_begin_time, pintuan_end_time

    def __del__(self):
        gc.collect()

def just_fuck_run():
    while True:
        print('一次大抓取即将开始'.center(30, '-'))
        zhe_800_pintuan = Zhe800Pintuan()
        zhe_800_pintuan.get_pintuan_goods_info()
        # try:
        #     del zhe_800_pintuan
        # except:
        #     pass
        gc.collect()
        print('一次大抓取完毕, 即将重新开始'.center(30, '-'))
        sleep(60*3)

def main():
    '''
    这里的思想是将其转换为孤儿进程，然后在后台运行
    :return:
    '''
    print('========主函数开始========')  # 在调用daemon_init函数前是可以使用print到标准输出的，调用之后就要用把提示信息通过stdout发送到日志系统中了
    daemon_init()  # 调用之后，你的程序已经成为了一个守护进程，可以执行自己的程序入口了
    print('--->>>| 孤儿进程成功被init回收成为单独进程!')
    # time.sleep(10)  # daemon化自己的程序之后，sleep 10秒，模拟阻塞
    just_fuck_run()


if __name__ == '__main__':
    if IS_BACKGROUND_RUNNING:
        main()
    else:
        just_fuck_run()