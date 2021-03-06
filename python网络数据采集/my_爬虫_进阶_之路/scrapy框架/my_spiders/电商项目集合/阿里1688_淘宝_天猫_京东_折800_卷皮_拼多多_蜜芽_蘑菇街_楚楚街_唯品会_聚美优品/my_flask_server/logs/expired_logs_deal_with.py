# coding:utf-8

'''
@author = super_fazai
@File    : expired_logs_deal_with.py
@Time    : 2018/3/31 11:22
@connect : superonesfazai@gmail.com
'''

import sys
sys.path.append('..')

from settings import MY_SPIDER_LOGS_PATH, IS_BACKGROUND_RUNNING
import glob, gc
import asyncio
from time import sleep
import os
import pytz
import datetime, re

async def get_now_time_from_pytz():
    '''
    得到log文件的时间名字
    :return: 格式: 2016-03-25 类型datetime
    '''
    # 时区处理，时间处理到上海时间
    # pytz查询某个国家时区
    country_timezones_list = pytz.country_timezones('cn')
    # print(country_timezones_list)

    tz = pytz.timezone('Asia/Shanghai')  # 创建时区对象
    now_time = datetime.datetime.now(tz)
    # print(type(now_time))

    now_time = re.compile(r'\..*').sub('', str(now_time))       # 处理为精确到秒位，删除时区信息
    now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')        # 将字符串类型转换为datetime类型
    # print(now_time)

    _ = str(now_time)[0:10].split('-')
    _ = datetime.datetime(year=int(_[0]), month=int(_[1]), day=int(_[2]))

    return _

async def deal_with_logs():
    file_re_path = MY_SPIDER_LOGS_PATH + '/*/*/*.txt'
    for item in glob.iglob(pathname=file_re_path):  # iglob() 获取一个可编历对象，使用它可以逐个获取匹配的文件路径名。
        # print(item)
        file_name_contain_extension_name = os.path.basename(item)   # 2016-02-01.txt
        try:
            file_name = os.path.splitext(file_name_contain_extension_name)[0]   # 2016-03-30
            # print(file_name)
        except IndexError:
            continue

        file_name_list = file_name.split('-')
        file_name_date = datetime.datetime(year=int(file_name_list[0]), month=int(file_name_list[1]), day=int(file_name_list[2]))
        now_date = await get_now_time_from_pytz()
        if file_name_date == now_date:
            print('当天日志, 跳过!')
            continue
        try: result = int(str(now_date - file_name_date).split(' ')[0])     # 当前日期 - 文件名的日期 的相差的day
        except IndexError: continue

        if result > 6:
            os.remove(item)
            print('删除过期日志文件 [%s] 成功!' % item)
        else:
            print('未过期跳过!')

    return True

def restart_program():
    import sys
    import os
    python = sys.executable
    os.execl(python, python, * sys.argv)

def daemon_init(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    '''
    杀掉父进程，独立子进程
    :param stdin:
    :param stdout:
    :param stderr:
    :return:
    '''
    sys.stdin = open(stdin, 'r')
    sys.stdout = open(stdout, 'a+')
    sys.stderr = open(stderr, 'a+')
    try:
        pid = os.fork()
        if pid > 0:     # 父进程
            os._exit(0)
    except OSError as e:
        sys.stderr.write("first fork failed!!" + e.strerror)
        os._exit(1)

    # 子进程， 由于父进程已经退出，所以子进程变为孤儿进程，由init收养
    '''setsid使子进程成为新的会话首进程，和进程组的组长，与原来的进程组、控制终端和登录会话脱离。'''
    os.setsid()
    '''防止在类似于临时挂载的文件系统下运行，例如/mnt文件夹下，这样守护进程一旦运行，临时挂载的文件系统就无法卸载了，这里我们推荐把当前工作目录切换到根目录下'''
    os.chdir("/")
    '''设置用户创建文件的默认权限，设置的是权限“补码”，这里将文件权限掩码设为0，使得用户创建的文件具有最大的权限。否则，默认权限是从父进程继承得来的'''
    os.umask(0)

    try:
        pid = os.fork()  # 第二次进行fork,为了防止会话首进程意外获得控制终端
        if pid > 0:
            os._exit(0)  # 父进程退出
    except OSError as e:
        sys.stderr.write("second fork failed!!" + e.strerror)
        os._exit(1)

    # 孙进程
    #   for i in range(3, 64):  # 关闭所有可能打开的不需要的文件，UNP中这样处理，但是发现在python中实现不需要。
    #       os.close(i)
    sys.stdout.write("Daemon has been created! with pid: %d\n" % os.getpid())
    sys.stdout.flush()  # 由于这里我们使用的是标准IO，这里应该是行缓冲或全缓冲，因此要调用flush，从内存中刷入日志文件。

def just_fuck_run():
    while True:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(deal_with_logs())
        try: loop.close()
        except: pass
        gc.collect()
        sleep(60*60)

        restart_program()       # 通过这个重启环境, 避免log重复打印

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

