# -*- encoding:utf-8 -*-
import threading
import os
import PIL.Image
import time
import selenium.webdriver.support.ui as ui
import requests
import numpy as np
import random

from selenium import webdriver # from 文件夹 import 模块名
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from proxy import SpiderProxy
from bs4 import BeautifulSoup
from tool import util
from tool import logger
from sklearn.externals.joblib import Parallel
from sklearn.externals.joblib import delayed
from concurrent.futures import ThreadPoolExecutor

"""
from ProcessMonitor import add_process_wrapper
代码地址：https://github.com/bbfamily/monitor_parallel

如需要控制多进程可以打开, 并且把do_spider上的add_process_wrapper装饰器的注释删除
"""

g_enable_monitor = False
if g_enable_monitor:
    from ProcessMonitor import add_process_wrapper

__author__ = 'BBFamily'

"""
    g_enable_show:是否使用有界面浏览器还是使用PHANTOMJS
"""
g_enable_show = True
"""
    g_enable_proxy:浏览器的进程是否启用代理，默认不需要，下载原图一定是使用代理没有开关
"""
g_enable_proxy = False
"""
    g_enable_debug:单进程，单线程调试模式可以debug断点
"""
g_enable_debug = True
"""
    使用流下载图片
"""
g_enable_stream = False


IMAGE_SERVER = "http://image.baidu.com/"
IMAGE_ROOT_DIR = '../gen/baidu/image/'

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko) " \
       "Chrome/32.0.1664.3 Safari/537.36"
PHANTOMJS_PATH = "/Users/f7/anaconda2/pkgs/phantomjs-2.1.1-0/bin/phantomjs"
MOVE_STEPS = 200
MOVE_SLEEP_TIME = 3
IMAGE_MAX_COUNT = 2000
PROCESS_MAX_COUNT = 1

# @add_process_wrapper
def do_spider_parallel(proxy_df, ind, search_name):
    """
    from ProcessMonitor import add_process_wrapper
    @add_process_wrapper
    代码地址：https://github.com/bbfamily/monitor_parallel
    如不需要控制多进程可以注释掉
    :param proxy_df:
    :param ind:
    :param search_name:
    :return:
    """

    proxy_list = [proxy_df.ix[index] for index in np.arange(len(proxy_df))]

    if g_enable_proxy:
        back_proxys = random.sample(proxy_list, 10)
    else:
        random.shuffle(proxy_list)
        back_proxys = proxy_list

    proxy = proxy_list[ind]
    manager = SpiderManager(proxy, back_proxys)
    manager.crawl_image_by_name(search_name)


def spider_main(search_list, use_cache=False):
    if use_cache:
        proxy_df = SpiderProxy.read_csv()
    else:
        pxy = SpiderProxy()
        # pxy.spider_proxy360()
        pxy.spider_xicidaili()
        pxy.check_proxy()
        pxy.save_csv()
        proxy_df = pxy.proxy_df

    if (len(proxy_df) <= 0):
        logger.info('代理失效，结束')
        return

    """
        由于代理太慢暂时每次只启动三个进程
    """
    n_jobs = PROCESS_MAX_COUNT
    if g_enable_debug:
        n_jobs = 1
    parallel = Parallel(
        n_jobs=n_jobs, verbose=0, pre_dispatch='2*n_jobs')

    parallel(delayed(do_spider_parallel)(proxy_df, ind, search_name) for ind, search_name in enumerate(search_list))


class SpiderManager(object):
    def __init__(self, a_proxy, back_proxys=None):
        self.proxy = a_proxy
        if back_proxys is None:
            back_proxys = []
        self.back_proxys = back_proxys

        while True:
            if self.__init_work(self.proxy):
                break
            if len(self.back_proxys) > 0:
                self.proxy = self.back_proxys.pop()
                continue
            raise RuntimeError('SpiderManager __init_work failed!!!')

    def __init_work(self, a_proxy):
        try:
            if g_enable_show:
                chrome_options = webdriver.ChromeOptions()
                chrome_options.add_argument('--proxy-server={}://{}'.format(a_proxy['type'].lower(), a_proxy['proxy']))
                if g_enable_proxy:
                    self.driver = webdriver.Chrome(chrome_options=chrome_options)
                else:
                    self.driver = webdriver.Chrome()
            else:
                d_cap = dict(DesiredCapabilities.PHANTOMJS)
                d_cap["phantomjs.page.settings.userAgent"] = (
                    USER_AGENT
                )

                service_args = [
                    '--proxy={}'.format(a_proxy['proxy']),
                    '--proxy-type={}'.format(a_proxy['type']),
                ]

                if g_enable_proxy:
                    self.driver = webdriver.PhantomJS(executable_path=PHANTOMJS_PATH,
                                                      desired_capabilities=d_cap,
                                                      service_args=service_args)
                else:
                    self.driver = webdriver.PhantomJS(executable_path=PHANTOMJS_PATH,
                                                      desired_capabilities=d_cap)
            self.requested_url = list()
            """
                scroll bar 当前位置
            """
            self.current_pos = 0
            """
                总成功收集数量
            """
            self.collect_cnt = 0

            self.driver.get(IMAGE_SERVER)

            return True
        except Exception as e:
            logger.exception(e)
            return False

    def __uinit_work():
        self.driver.quit()

    def _down_load_img_stream(self, img_url, file_name, headers, proxy_dict, thread_lock, img_url_thumb=None):
        response = requests.get(img_url, headers=headers, proxies=proxy_dict, timeout=(15, 90), stream=True)
        if response.status_code == 200:
            try:
                with open(file_name, 'wb') as f:
                    start_time = time.time()  # 文件下载开始时间
                    for chunk in response.iter_content(chunk_size=1024):
                        now_time = time.time()
                        if now_time - start_time > 90:
                            logger.debug('now_time - start_time > 90')
                            raise RuntimeError("now_time - start_time > 90")
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
                            f.flush()
                """
                    检测ok了，才可以，暂时就先算了，
                    需要添加重试次数限制
                """
                check_img = PIL.Image.open(file_name)
                check_img.close()
            except Exception:
                os.remove(file_name)
                return True
            # with open(file_name, 'wb') as out_file:
            #     shutil.copyfileobj(response.raw, out_file)
            with thread_lock:
                self.collect_cnt += 1

            if img_url_thumb is None:
                logger.debug('down_load_img img_url_thumb ok!')
            return True
        else:
            if img_url_thumb is None:
                logger.debug('down_load_img fail url={} code={}'.format(img_url, response.status_code))
                return False
            return self._down_load_img_stream(img_url_thumb, file_name, headers, proxy_dict, thread_lock,
                                              img_url_thumb=None)

    def _down_load_img_direct(self, img_url, file_name, headers, proxy_dict, thread_lock, img_url_thumb=None):
        response = requests.get(img_url, headers=headers, proxies=proxy_dict, timeout=(15, 360))
        if response.status_code == 200:
            try:
                with open(file_name, 'wb') as f:
                    f.write(response.content)
                    f.flush()
                """
                    检测ok了，才可以，暂时就先算了，
                    需要添加重试次数限制
                """
                check_img = PIL.Image.open(file_name)
                check_img.verify()
                check_img.close()
            except Exception:
                os.remove(file_name)
                return True
            with thread_lock:
                self.collect_cnt += 1

            if img_url_thumb is None:
                logger.debug('down_load_img img_url_thumb ok!')
            return True
        else:
            if img_url_thumb is None:
                logger.debug('down_load_img fail url={} code={}'.format(img_url, response.status_code))
                return False
            """
                 原始地址下载失败，改为下载thumb，要是再失败了就失败了
            """
            return self._down_load_img_stream(img_url_thumb, file_name, headers, proxy_dict, thread_lock,
                                              img_url_thumb=None)

    def down_load_img(self, url_dict, thread_lock):
        img_url = url_dict['url']
        img_url_thumb = url_dict['url_thumb']
        file_name = self.img_dir + util.md5_from_binary(img_url) + '.jpg'
        if util.file_exist(file_name):
            logger.debug('{} has already exist'.format(img_url))
            """
                也还是应该算成功收集了
            """
            with thread_lock:
                self.collect_cnt += 1
            return

        def begin_req(a_proxy):
            headers = {"User-Agent": USER_AGENT}
            if self.proxy['type'] == 'HTTP':
                proxy_dict = dict(http='http://{}'.format(a_proxy['proxy']),
                                  https='http://{}'.format(a_proxy['proxy']))
            else:
                proxy_dict = dict(http='socks5://{}'.format(a_proxy['proxy']),
                                  https='socks5://{}'.format(a_proxy['proxy']))

            try:
                if g_enable_stream:
                    return self._down_load_img_stream(img_url, file_name, headers, proxy_dict, thread_lock,
                                                      img_url_thumb=img_url_thumb)
                else:
                    return self._down_load_img_direct(img_url, file_name, headers, proxy_dict, thread_lock,
                                                      img_url_thumb=img_url_thumb)

            except Exception:
                # logger.exception(e)
                return False

        bps = self.back_proxys[:]
        random.shuffle(bps)
        for proxy in bps:
            if begin_req(proxy):
                break

    def _do_collect_work(self):
        with ThreadPoolExecutor(max_workers=len(self.back_proxys) * 3) as executor:
            """
                这里使用线程池还是因为代理的质量太差了， 要控制线程数量
            """
            thread_lock = threading.RLock()
            all_same_cnt = 0
            while True:
                soup = BeautifulSoup(self.driver.page_source, "lxml")
                img_objs = soup.select('#imgid > div > ul > li[data-objurl]')

                sub_same_cnt = 0
                for img in img_objs:
                    url = img['data-objurl']
                    url_thumb = img['data-thumburl']
                    if self.requested_url.count(url) > 0:
                        sub_same_cnt += 1
                        continue

                    url_dict = {'url': url, 'url_thumb': url_thumb}
                    if g_enable_debug:
                        self.down_load_img(url_dict, thread_lock)
                    else:
                        executor.submit(self.down_load_img, url_dict, thread_lock)

                    # 就在这里append否则里面还要线程同步
                    self.requested_url.append(url)

                js = "window.scrollTo({}, {})".format(self.current_pos, self.current_pos + MOVE_STEPS)
                self.current_pos += MOVE_STEPS
                self.driver.execute_script(js)
                time.sleep(MOVE_SLEEP_TIME)

                """
                    所有都在requested中记录全等一次否则重置
                """
                if sub_same_cnt == len(img_objs):
                    all_same_cnt += 1
                else:
                    all_same_cnt = 0

                """
                    达到一定次数，认为到底部了
                """
                if all_same_cnt > 30:
                    print '[Process] 图片流 结束，已下载图片数目=%d' %(self.collect_cnt)
                    break

                if self.collect_cnt >= IMAGE_MAX_COUNT:
                    logger.info('collect_cnt > %d task end' %(IMAGE_MAX_COUNT))

                    print '[Process] 下载图片数目 超过 %d' %(IMAGE_MAX_COUNT)
                    break

    def _start_collect_work(self):
        self._do_collect_work()

        print '[Process] 爬虫结束'

    def crawl_image_by_name(self, a_name):

        print '[Process] '+a_name

        self.driver.maximize_window()

        wait = ui.WebDriverWait(self.driver, 20)
        wait.until(lambda dr: dr.find_element_by_css_selector('#kw').is_displayed()) # kw : key word

        # wait.until(lambda dr: dr.find_element_by_css_selector('#homeSearchForm > span.s_btn_wr > input').is_displayed())
        wait.until(lambda dr: dr.find_element_by_css_selector('#homeSearchForm > span.s_search').is_displayed())

        self.driver.implicitly_wait(10)

        # 找到搜索输入框，填入关键字
        input_label = self.driver.find_element_by_css_selector('#kw')
        input_label.clear()
        input_label.send_keys(a_name)

        self.driver.implicitly_wait(5)

        # 找到搜索按钮，触发按钮点击
        # search_button = self.driver.find_element_by_css_selector('#homeSearchForm > span.s_btn_wr > input')
        search_button = self.driver.find_element_by_css_selector('#homeSearchForm > span.s_search')
        search_button.click()

        self.driver.implicitly_wait(3)

        self.img_dir = IMAGE_ROOT_DIR + a_name + '/'
        
        util.ensure_dir(self.img_dir)

        self._start_collect_work()

    def phantomjs_screen_shot(self):
        self.driver.get_screenshot_as_file('./hj.png')

    def phantomjs_screen_html(self):
        util.save_file(self.driver.page_source.encode('utf-8'), './hj.html')


if __name__ == "__main__":
    logger.init_logging()

    # u'哈士奇', u'金毛', u'萨摩耶', u'柯基', u'柴犬', u'边境牧羊犬', u'比格', u'巴吉度', u'德国牧羊犬', u'杜宾', u'泰迪犬', u'博美', u'巴哥', u'牛头梗'
    spider_main([u'拉布拉多'],
                False)
