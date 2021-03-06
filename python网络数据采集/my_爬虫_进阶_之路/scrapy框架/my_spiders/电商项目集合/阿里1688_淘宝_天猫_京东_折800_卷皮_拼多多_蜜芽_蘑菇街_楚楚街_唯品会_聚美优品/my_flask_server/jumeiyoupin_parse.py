# coding:utf-8

'''
@author = super_fazai
@File    : jumeiyoupin_parse.py
@Time    : 2018/3/10 10:01
@connect : superonesfazai@gmail.com
'''

"""
聚美优品常规商品页面解析系统
"""

import time
from random import randint
import json
import requests
import re
from pprint import pprint
from decimal import Decimal

from time import sleep
import datetime
import gc
import pytz
from scrapy.selector import Selector

from settings import HEADERS
from my_ip_pools import MyIpPools
from my_requests import MyRequests

class JuMeiYouPinParse(object):
    def __init__(self):
        self.headers = {
            'Accept': 'application/json,text/javascript,*/*;q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            # 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Host': 'h5.jumei.com',
            'Referer': 'http://h5.jumei.com/product/detail?item_id=ht180310p3365132t1&type=global_deal',
            'Cache-Control': 'max-age=0',
            'User-Agent': HEADERS[randint(0, 34)],  # 随机一个请求头
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.result_data = {}

    def get_goods_data(self, goods_id):
        '''
        模拟构造得到data的url, 并得到相应数据
        :param goods_id:
        :return: data 类型dict
        '''
        if goods_id == []:
            self.result_data = {}
            return {}

        goods_url = 'https://h5.jumei.com/product/detail?item_id=' + str(goods_id[0]) + '&type=' + str(goods_id[1])
        print('------>>>| 对应的手机端地址为: ', goods_url)

        #** 获取ajaxStaticDetail请求中的数据
        tmp_url = 'https://h5.jumei.com/product/ajaxStaticDetail?item_id=' + goods_id[0] + '&type=' + str(goods_id[1])
        self.headers['Referer'] = goods_url
        body = MyRequests.get_url_body(url=tmp_url, headers=self.headers)
        # print(body)

        if body == '':
            print('获取到的body为空str!')
            self.result_data = {}
            return {}

        try:
            tmp_data = json.loads(body)
            # pprint(tmp_data)
        except Exception:
            print('json.loads转换body时出错!请检查!')
            self.result_data = {}
            return {}

        tmp_data = self.wash_data(data=tmp_data)
        # pprint(tmp_data)

        #** 获取ajaxDynamicDetail请求中的数据
        tmp_url_2 = 'https://h5.jumei.com/product/ajaxDynamicDetail?item_id=' + str(goods_id[0]) + '&type=' + str(goods_id[1])
        body_2 = MyRequests.get_url_body(url=tmp_url_2, headers=self.headers)
        # print(body)
        if body_2 == '':
            print('获取到的body为空str!')
            self.result_data = {}
            return {}

        try:
            tmp_data_2 = json.loads(body_2)
            # pprint(tmp_data_2)
        except Exception:
            print('json.loads转换body_2时出错!请检查!')
            self.result_data = {}
            return {}
        tmp_data_2 = self.wash_data_2(data=tmp_data_2)
        # pprint(tmp_data_2)

        tmp_data['data_2'] = tmp_data_2.get('data', {}).get('result', {})
        if tmp_data['data_2'] == {}:
            print('获取到的ajaxDynamicDetail中的数据为空值!请检查!')
            self.result_data = {}
            return {}

        # pprint(tmp_data)

        data = {}
        try:
            data['title'] = tmp_data.get('data', {}).get('name', '')
            data['sub_title'] = ''
            # print(data['title'])

            if data['title'] == '':
                print('获取到的title为空值, 请检查!')
                raise Exception

            # shop_name
            if tmp_data.get('data_2', {}).get('shop_info') == []:
                data['shop_name'] = ''
            else:
                data['shop_name'] = tmp_data.get('data_2', {}).get('shop_info', {}).get('store_title', '')
            # print(data['shop_name'])

            # 获取所有示例图片
            all_img_url = tmp_data.get('data', {}).get('image_url_set', {}).get('single_many', [])
            if all_img_url == []:
                print('获取到的all_img_url为空[], 请检查!')
                raise Exception
            else:
                all_img_url = [{
                    'img_url': item.get('800', ''),
                } for item in all_img_url]
            # pprint(all_img_url)
            data['all_img_url'] = all_img_url

            # 获取p_info
            p_info = self.get_p_info(tmp_data=tmp_data)
            # pprint(p_info)
            data['p_info'] = p_info

            # 获取每个商品的div_desc
            # 注意其商品的div_desc = description + description_usage + description_images
            div_desc = self.get_goods_div_desc(tmp_data=tmp_data)
            # print(div_desc)
            if div_desc == '':
                print('获取到的div_desc为空值! 请检查')
                raise Exception
            data['div_desc'] = div_desc

            '''
            上下架时间 (注意:聚美优品常规今日10点上新商品，销售时长都是24小时)
            '''
            sell_time = self.get_sell_time(
                begin_time=tmp_data.get('data_2', {}).get('start_time'),
                end_time=tmp_data.get('data_2', {}).get('end_time')
            )
            # pprint(sell_time)
            data['sell_time'] = sell_time

            # 设置detail_name_list
            detail_name_list = self.get_detail_name_list(size_attr=tmp_data.get('data_2', {}).get('size_attr', []))
            # print(detail_name_list)
            data['detail_name_list'] = detail_name_list

            '''
            获取每个规格对应价格跟规格以及库存
            '''
            true_sku_info = self.get_true_sku_info(size=tmp_data.get('data_2', {}).get('size', []))
            # pprint(true_sku_info)
            if true_sku_info == []:
                print('获取到的sku_info为空值, 请检查!')
                raise Exception
            else:
                data['price_info_list'] = true_sku_info

            '''
            is_delete
            '''
            if int(tmp_data.get('data_2', {}).get('end_time')) < int(time.time()):
                is_delete = 1
            else:
                all_stock = 0
                for item in true_sku_info:
                    all_stock += item.get('rest_number', 0)
                # print(all_stock)
                if all_stock == 0:
                    is_delete = 1
                else:
                    is_delete = 0
            # print(is_delete)
            data['is_delete'] = is_delete

            # all_sell_count
            all_sell_count = tmp_data.get('data_2', {}).get('buyer_number', '0')
            data['all_sell_count'] = all_sell_count

        except Exception as e:
            print('遇到错误如下: ', e)
            self.result_data = {}  # 重置下，避免存入时影响下面爬取的赋值
            return {}

        if data != {}:
            # pprint(data)
            self.result_data = data
            return data

        else:
            print('data为空!')
            self.result_data = {}  # 重置下，避免存入时影响下面爬取的赋值
            return {}

    def deal_with_data(self):
        '''
        处理得到规范的data数据
        :return: result 类型 dict
        '''
        data = self.result_data
        if data != {}:
            # 店铺名称
            shop_name = data['shop_name']

            # 掌柜
            account = ''

            # 商品名称
            title = data['title']

            # 子标题
            sub_title = data['sub_title']

            # 商品标签属性名称
            detail_name_list = data['detail_name_list']

            # 要存储的每个标签对应规格的价格及其库存
            price_info_list = data['price_info_list']

            # 所有示例图片地址
            all_img_url = data['all_img_url']

            # 详细信息标签名对应属性
            p_info = data['p_info']
            # pprint(p_info)

            # div_desc
            div_desc = data['div_desc']

            '''
            用于判断商品是否已经下架
            '''
            is_delete = data['is_delete']
            # print(is_delete)

            # 上下架时间
            schedule = data['sell_time']

            # 销售总量
            all_sell_count = data['all_sell_count']

            # 商品价格和淘宝价
            # pprint(data['price_info_list'])
            try:
                tmp_price_list = sorted([round(float(item.get('detail_price', '')), 2) for item in data['price_info_list']])
                price = tmp_price_list[-1]  # 商品价格
                taobao_price = tmp_price_list[0]  # 淘宝价
            except IndexError:
                print('获取price和taobao_price时出错, 请检查!')  # 商品下架时, detail_price为空str, 所以会IndexError报错
                self.result_data = {}
                price = 0.
                taobao_price = 0.
                is_delete = 1
                # return {}

            result = {
                'shop_name': shop_name,  # 店铺名称
                'account': account,  # 掌柜
                'title': title,  # 商品名称
                'sub_title': sub_title,  # 子标题
                'price': price,  # 商品价格
                'taobao_price': taobao_price,  # 淘宝价
                # 'goods_stock': goods_stock,           # 商品库存
                'detail_name_list': detail_name_list,  # 商品标签属性名称
                # 'detail_value_list': detail_value_list,# 商品标签属性对应的值
                'price_info_list': price_info_list,  # 要存储的每个标签对应规格的价格及其库存
                'all_img_url': all_img_url,  # 所有示例图片地址
                'p_info': p_info,  # 详细信息标签名对应属性
                'div_desc': div_desc,  # div_desc
                'schedule': schedule,  # 商品特价销售时间段
                'all_sell_count': all_sell_count,  # 销售总量
                'is_delete': is_delete  # 用于判断商品是否已经下架
            }
            # pprint(result)
            # print(result)
            # wait_to_send_data = {
            #     'reason': 'success',
            #     'data': result,
            #     'code': 1
            # }
            # json_data = json.dumps(wait_to_send_data, ensure_ascii=False)
            # print(json_data)
            self.result_data = {}
            return result

        else:
            print('待处理的data为空的dict, 该商品可能已经转移或者下架')
            self.result_data = {}
            return {}

    def insert_into_jumeiyoupin_xianshimiaosha_table(self, data, pipeline):
        data_list = data
        tmp = {}
        tmp['goods_id'] = data_list['goods_id']  # 官方商品id
        tmp['spider_url'] = data_list['goods_url']  # 商品地址

        '''
        时区处理，时间处理到上海时间
        '''
        tz = pytz.timezone('Asia/Shanghai')  # 创建时区对象
        now_time = datetime.datetime.now(tz)
        # 处理为精确到秒位，删除时区信息
        now_time = re.compile(r'\..*').sub('', str(now_time))
        # 将字符串类型转换为datetime类型
        now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')

        tmp['deal_with_time'] = now_time  # 操作时间
        tmp['modfiy_time'] = now_time  # 修改时间

        tmp['shop_name'] = data_list['shop_name']  # 公司名称
        tmp['title'] = data_list['title']  # 商品名称
        tmp['sub_title'] = data_list['sub_title']

        # 设置最高价price， 最低价taobao_price
        try:
            tmp['price'] = Decimal(data_list['price']).__round__(2)
            tmp['taobao_price'] = Decimal(data_list['taobao_price']).__round__(2)
        except:
            print('此处抓到的可能是聚美优品券所以跳过')
            return None

        tmp['detail_name_list'] = data_list['detail_name_list']  # 标签属性名称

        """
        得到sku_map
        """
        tmp['price_info_list'] = data_list.get('price_info_list')  # 每个规格对应价格及其库存

        tmp['all_img_url'] = data_list.get('all_img_url')  # 所有示例图片地址

        tmp['p_info'] = data_list.get('p_info')  # 详细信息
        tmp['div_desc'] = data_list.get('div_desc')  # 下方div

        tmp['miaosha_time'] = data_list.get('miaosha_time')
        tmp['page'] = data_list.get('page')

        # 采集的来源地
        tmp['site_id'] = 26  # 采集来源地(聚美优品10点上新的秒杀商品)

        tmp['miaosha_begin_time'] = data_list.get('miaosha_begin_time')
        tmp['miaosha_end_time'] = data_list.get('miaosha_end_time')

        tmp['is_delete'] = data_list.get('is_delete')  # 逻辑删除, 未删除为0, 删除为1
        # print('is_delete=', tmp['is_delete'])

        # print('------>>> | 待存储的数据信息为: |', tmp)
        print('------>>>| 待存储的数据信息为: |', tmp.get('goods_id'))

        pipeline.insert_into_jumeiyoupin_xianshimiaosha_table(tmp)

    def update_jumeiyoupin_xianshimiaosha_table(self, data, pipeline):
        data_list = data
        tmp = {}
        tmp['goods_id'] = data_list['goods_id']  # 官方商品id

        '''
        时区处理，时间处理到上海时间
        '''
        tz = pytz.timezone('Asia/Shanghai')  # 创建时区对象
        now_time = datetime.datetime.now(tz)
        # 处理为精确到秒位，删除时区信息
        now_time = re.compile(r'\..*').sub('', str(now_time))
        # 将字符串类型转换为datetime类型
        now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')

        tmp['modfiy_time'] = now_time  # 修改时间

        tmp['shop_name'] = data_list['shop_name']  # 公司名称
        tmp['title'] = data_list['title']  # 商品名称
        tmp['sub_title'] = data_list['sub_title']

        # 设置最高价price， 最低价taobao_price
        try:
            tmp['price'] = Decimal(data_list['price']).__round__(2)
            tmp['taobao_price'] = Decimal(data_list['taobao_price']).__round__(2)
        except:
            print('此处抓到的可能是聚美优品券所以跳过')
            return None

        tmp['detail_name_list'] = data_list['detail_name_list']  # 标签属性名称

        """
        得到sku_map
        """
        tmp['price_info_list'] = data_list.get('price_info_list')  # 每个规格对应价格及其库存

        tmp['all_img_url'] = data_list.get('all_img_url')  # 所有示例图片地址

        tmp['p_info'] = data_list.get('p_info')  # 详细信息
        tmp['div_desc'] = data_list.get('div_desc')  # 下方div

        tmp['miaosha_time'] = data_list.get('miaosha_time')

        # 采集的来源地
        # tmp['site_id'] = 26  # 采集来源地(聚美优品10点上新的秒杀商品)

        tmp['miaosha_begin_time'] = data_list.get('miaosha_begin_time')
        tmp['miaosha_end_time'] = data_list.get('miaosha_end_time')

        tmp['is_delete'] = data_list.get('is_delete')  # 逻辑删除, 未删除为0, 删除为1

        # print('------>>> | 待存储的数据信息为: |', tmp)
        print('------>>>| 待存储的数据信息为: |', tmp.get('goods_id'))

        pipeline.update_jumeiyoupin_xianshimiaosha_table(tmp)

    def wash_data(self, data):
        '''
        清洗数据
        :param data:
        :return:
        '''
        '''
        分开del, 避免都放在一块，一个del失败就跳出无法进行继续再往下的清洗
        '''
        try:
            del data['data']['area_icon']
            del data['data']['area_icon_v2']
        except: pass
        try: del data['data']['consumer_notice_data']
        except: pass
        try:
            del data['data']['description_url']
            del data['data']['description_url_set']
        except: pass
        try: del data['data']['guarantee']
        except: pass
        try: del data['data']['image_url_set']['dx_image']
        except: pass
        try: del data['data']['share_info']
        except: pass

        return data

    def wash_data_2(self, data):
        '''
        清洗数据
        :param data:
        :return:
        '''
        try:
            del data['data']['result']['address_list']
            del data['data']['result']['bottom_button']
            del data['data']['result']['default_address']
            del data['data']['result']['fen_qi']
            del data['data']['result']['icon_tag']
        except: pass
        try:
            del data['data']['result']['shop_info']['follow_num']
            del data['data']['result']['shop_info']['logo_url']
        except: pass

        return data

    def get_p_info(self, tmp_data):
        '''
        得到p_info
        :param tmp_data:
        :return: [xxx, ...] 表示success
        '''
        p_info = tmp_data.get('data', {}).get('properties', [])
        p_info = [{
            'p_name': item.get('name', ''),
            'p_value': item.get('value', ''),
        } for item in p_info]

        return p_info

    def get_goods_div_desc(self, tmp_data):
        '''
        获取div_desc
        :param tmp_data:
        :return: '' 表示出错
        '''
        tmp_div_desc = tmp_data.get('data', {}).get('description_info', {})
        if tmp_div_desc == {}:
            return ''

        description = tmp_div_desc.get('description', '')
        description_usage = tmp_div_desc.get('description_usage', '')
        description_images = tmp_div_desc.get('description_images', '')

        div_desc = '<div>' + description + description_usage + description_images + '</div>'

        return div_desc

    def get_sell_time(self, begin_time, end_time):
        '''
        得到上下架时间 (注意:聚美优品常规今日10点上新商品，销售时长都是24小时)
        :param begin_time: 类型int
        :param end_time: 类型int
        :return: [] 表示出错 | {'xx':'yyy'} 表示success
        '''
        if begin_time is None:
            print('获取到该商品的begin_time是None')
            raise Exception

        if isinstance(begin_time, int):
            sell_time = {
                'begin_time': self.timestamp_to_regulartime(int(begin_time)),
                'end_time': self.timestamp_to_regulartime(int(end_time)),
            }

        else:
            print('获取该商品的begin_time类型错误, 请检查!')
            raise Exception

        return sell_time

    def get_detail_name_list(self, size_attr):
        '''
        得到detail_name_list
        :param size_attr: 规格的说明的list
        :return:
        '''
        if size_attr is None or size_attr == []:
            print('size_attr为空[]')
            raise Exception

        detail_name_list = [{
            'spec_name': item.get('title', '')
        } for item in size_attr]

        return detail_name_list

    def get_true_sku_info(self, size):
        '''
        得到每个规格对应的库存, 价格, 图片等详细信息
        :param size:
        :return:
        '''
        if size is None or size == []:
            return []

        price_info_list = []
        for item in size:
            tmp_spec_value = item.get('name', '')   # 830白色2件,均码
            spec_value = tmp_spec_value.replace(',', '|')
            detail_price = item.get('jumei_price', '')
            normal_price = item.get('market_price', '')
            img_url = item.get('img', '')
            rest_number = int(item.get('stock', '0'))

            price_info_list.append({
                'spec_value': spec_value,
                'detail_price': detail_price,
                'normal_price': normal_price,
                'img_url': img_url,
                'rest_number': rest_number,
            })

        return price_info_list

    def timestamp_to_regulartime(self, timestamp):
        '''
        将时间戳转换成时间
        '''
        # 利用localtime()函数将时间戳转化成localtime的格式
        # 利用strftime()函数重新格式化时间

        # 转换成localtime
        time_local = time.localtime(timestamp)
        # 转换成新的时间格式(2016-05-05 20:28:54)
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)

        return dt

    def get_goods_id_from_url(self, jumei_url):
        '''
        得到goods_id
        :param jumei_url:
        :return: goods_id 类型list eg: [] 表示非法url | ['xxxx', 'type=yyyy']
        '''
        jumei_url = re.compile(r'http://').sub(r'https://', jumei_url)
        jumei_url = re.compile(r';').sub('', jumei_url)
        is_jumei_url = re.compile(r'https://h5.jumei.com/product/detail').findall(jumei_url)
        if is_jumei_url != []:
            if re.compile(r'https://h5.jumei.com/product/detail\?.*?item_id=(\w+)&{1,}.*?').findall(jumei_url) != []:
                goods_id = re.compile(r'item_id=(\w+)&{1,}').findall(jumei_url)[0]
                # print(goods_id)
                try:
                    type = re.compile(r'&type=(.*)').findall(jumei_url)[0]
                except IndexError:
                    print('获取url的type时出错, 请检查!')
                    return []
                print('------>>>| 得到的聚美商品id为: ', goods_id, 'type为: ', type)

                return [goods_id, type]
            else:
                print('获取goods_id时出错, 请检查!')
                return []

        else:
            print('聚美优品商品url错误, 非正规的url, 请参照格式(https://h5.jumei.com/product/detail)开头的...')
            return []

    def __del__(self):
        gc.collect()

if __name__ == '__main__':
    jumei = JuMeiYouPinParse()
    while True:
        jumei_url = input('请输入待爬取的聚美优品商品地址: ')
        jumei_url.strip('\n').strip(';')
        goods_id = jumei.get_goods_id_from_url(jumei_url)
        data = jumei.get_goods_data(goods_id=goods_id)
        jumei.deal_with_data()
        pprint(data)
