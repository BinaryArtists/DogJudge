# -*- encoding:utf-8 -*-
from __future__ import print_function # must occur at the beginning of the file

import os
import random
import shutil
import hashlib
import glob
import imghdr

import pandas as pd

from binascii import crc32
from decorator import warnings_filter

import PIL.Image
from PIL import ImageFile

'''
' cPickle是C语言写的，速度快，pickle是纯Python写的，速度慢
'''
try:
    import cPickle as pickle
except ImportError:
    import pickle

######################################
# ???
######################################

def write_chr(f, ch):
    f.write(chr(ch))


def write_int(f, no):
    if no > 65535:
        print(no)
    b1 = no & 0xff
    b2 = no >> 8
    f.write(chr(b1))
    f.write(chr(b2))


def write_long(f, no):  # int32
    no1 = no & 0xffff
    write_int(f, no1)
    no2 = no >> 16
    write_int(f, no2)


def write_int64(f, no):
    no1 = no & 0xffffffff
    write_long(f, no1)
    no2 = no >> 32
    write_long(f, no2)


def read_chr(f):
    ch = f.read(1)
    return ch


def read_int(f):
    b1 = ord(f.read(1))
    b2 = ord(f.read(1))
    cnt = b2 << 8 | b1
    return cnt


def read_long(f):
    no1 = read_int(f)
    no2 = read_int(f)
    num = no2 << 16 | no1
    return num


def read_int64(f):
    no1 = read_long(f)
    no2 = read_long(f)
    num = no2 << 64 | no1
    return num


def get_file_array_from_name(root_dir, name, ret_array):
    for lists in os.listdir(root_dir):
        path = os.path.join(root_dir, lists)
        if os.path.isdir(path):
            get_file_array_from_name(path, name, ret_array)
        elif os.path.basename(path) == name:
            ret_array.append(path)


def list_all_file(root_dir, all_ext_list):
    print(root_dir)
    for lists in os.listdir(root_dir):
        path = os.path.join(root_dir, lists)
        if os.path.isdir(path):
            list_all_file(path, all_ext_list)
        else:
            all_ext_list.append(path)


def list_all_ext_file(root_dir, ext_type, all_ext_list):
    for lists in os.listdir(root_dir):
        path = os.path.join(root_dir, lists)
        if os.path.isdir(path):
            list_all_ext_file(path, ext_type, all_ext_list)
        elif path.endswith(ext_type):
            all_ext_list.append(path)


def str_is_num10(a_str):
    try:
        int(a_str, 10)
        return True
    except:
        return False


def str_is_num16(a_str):
    try:
        int(a_str, 16)
        return True
    except:
        return False


def str_xor(a_str, key):
    a = []
    for x in a_str:
        rs = ord(x) ^ key
        a.append(chr(rs))
    return ''.join(a)


def str_replace_infile_once(target_name, a_str, match_str):
    f = open(target_name, "rb")
    lines = f.readlines()
    f.close()
    f = open(target_name, "wb")
    find = False
    for line in lines:
        if (not find) and (line.find(match_str) >= 0):
            line = line.replace(match_str, a_str)
            find = True
        f.write(line)
    f.close()


def str_replace_infile(target_name, a_str, match_str):
    f = open(target_name, "rb")
    lines = f.readlines()
    f.close()
    f = open(target_name, "wb")
    for line in lines:
        if line.find(match_str):
            line = line.replace(match_str, a_str)
        f.write(line)
    f.close()


def str_insert_infile(target_name, a_str, match_str):
    f = open(target_name, "rb")
    lines = f.readlines()
    f.close()
    f = open(target_name, "wb")
    for line in lines:
        if line.find(match_str) > 0:
            d_pos = line.find(match_str)
            tmp_str = line[
                      0:d_pos + len(match_str)] + " " + a_str + line[d_pos + len(match_str):]
            line = tmp_str
        f.write(line)
    f.close()


def str_insert_infile_before(target_name, a_str, match_str):
    f = open(target_name, "rb")
    lines = f.readlines()
    f.close()
    f = open(target_name, "wb")
    for line in lines:
        if line.find(match_str) > 0:
            d_pos = line.find(match_str)
            tmp_str = line[0:d_pos] + " " + a_str + " " + line[d_pos:]
            line = tmp_str
        f.write(line)
    f.close()


def ch_is_num(ch):
    if len(ch) > 1:
        return False
    if ch == '0' or ch == '1' or ch == '2' or ch == '3' or ch == '4' or ch == '5' \
            or ch == '6' or ch == '7' or ch == '8' or ch == '9':
        return True
    return False


def force_change_str_to_int10(will_str):
    index = 0

    while index < len(will_str):
        if not str_is_num10(will_str[index]):
            will_str = will_str[index + 1:]
        else:
            break
        index += 1
    int_value = int(will_str, 10)
    return int_value


def create_random_tmp_name_with_num(salt_count):
    seed = "0123456789"
    sa = []
    for i in range(salt_count):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    # print("* createRandomTmpNameWithNum name = " + salt)
    return salt


def create_random_tmp_name(salt_count):
    seed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    sa = []
    for i in range(salt_count):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    print('* CreateRandomTmpName name = ' + salt)
    return salt


def create_random_tmp_name_with_num_low(salt_count):
    seed = "abcdefghijklmnopqrstuvwxyz0123456789"
    sa = []
    for i in range(salt_count):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    # print "* createRandomTmpNameWithNumAndLow name = " + salt
    return salt


def ensure_dir(a_dir):
    # ZEnv.print_Str("ensureDir:" + aDir)
    a_dir = os.path.dirname(a_dir)
    if not os.path.exists(a_dir):
        os.makedirs(a_dir)
        # print("makedirs " + a_dir)


def file_exist(a_file):
    if os.path.exists(a_file):
        return True
    return False


def move_fileto(source, target_dir):
    shutil.copy(source, target_dir)


def load_pickle(file_name):
    if not file_exist(file_name):
        return None
    fr = open(file_name)
    ret = pickle.load(fr)
    fr.close()
    return ret


def dump_pickle(input_obj, file_name):
    ensure_dir(file_name)
    fw = open(file_name, 'w')
    pickle.dump(input_obj, fw)
    fw.close()


@warnings_filter
def dump_hdf5(input_obj, input_key, file_name):
    """
    warnings 有优化数据结构提示警告, 忽略
    :param input_obj:
    :param input_key:
    :param file_name:
    :return:
    """
    # h5s = pd.HDFStore(file_name, 'w')
    # h5s[input_key] = input_obj
    # h5s.close()
    with pd.HDFStore(file_name, 'w') as h5s:
        h5s[input_key] = input_obj


def load_hdf5(file_name, load_key):
    if not file_exist(file_name):
        return None
    with pd.HDFStore(file_name, 'r') as h5s:
        # h5s = pd.HDFStore(file_name, 'r')
        # h5s.close()
        ret = h5s[load_key]
    return ret


def save_file(ct, file_name):
    ensure_dir(file_name)
    with open(file_name, 'w') as f:
        f.write(ct)


def save_list_file(file_name, str_list):
    target_file = open(file_name, "wb")
    for x in str_list:
        target_file.write(str(x))
        target_file.write('\n')
    target_file.close()


def get_class(kls):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__(module)
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m


def is_iterable(obj):
    try:
        iter(obj)
        return True
    except:
        return False


######################################
# md5
######################################

def md5_from_binary(str):
    try:
        m = hashlib.new("md5")
        m.update(str)
    except:
        pass
    return m.hexdigest()


def md5_from_file(filename, blockM=1):
    opened = False
    fobj = None
    if hasattr(filename, "read"):
        fobj = filename
    else:
        if os.path.exists(filename) and os.path.isfile(filename):
            fobj = open(filename, "rb")
            opened = True
    if fobj:
        blockB = blockM * 1024 * 1024
        try:
            m = hashlib.new("md5")
            while True:
                fb = fobj.read(blockB)
                if not fb:
                    break
                m.update(fb)
        finally:
            if opened:
                fobj.close()
        return m.hexdigest()
    else:
        return 0


def crc32_from_file(filename, blockM=1):  # block with (M)
    if os.path.exists(filename) and os.path.isfile(filename):
        blockB = blockM * 1024 * 1024
        crc = 0
        f = open(filename, "rb")
        while True:
            fb = f.read(blockB)
            if not fb:
                break
            crc = crc32(fb, crc)
        f.close()
        res = ''
        for i in range(4):
            t = crc & 0xFF
            crc >>= 8
            res = '%02x%s' % (t, res)
        return "0x" + res
    else:
        return 0

######################################
# Image process
######################################

ImageFile.LOAD_TRUNCATED_IMAGES = True

def std_img_from_root_dir(root_dir, a_ext):
    """
    找到某一个ext的图片所有，都转换正真实类型，不是jpeg的
    全部转换为jpeg
    Parameters
    ----------
    root_dir
    a_ext

    Returns
    -------

    """
    img_list = find_img_by_ext(a_ext, root_dir)
    all_ext = change_to_real_type(img_list)
    for ext in all_ext:
        if ext <> 'jpeg':
            if ext is None:
                ext = a_ext
            sub_img_list = find_img_by_ext(ext, root_dir)
            _ = map(lambda img: covert_to_jpeg(img), sub_img_list)
            change_to_real_type(sub_img_list)


def covert_to_jpeg(org_img, dst_img=None):
    im = PIL.Image.open(org_img)
    if dst_img is None:
        dst_img = org_img
    im.convert('RGB').save(dst_img, 'JPEG')


def find_img_by_ext(ext, root_dir):
    """
    只遍历根目录及一级子目录
    Parameters
    ----------
    ext
    root_dir

    Returns
    -------

    """
    dirs = [root_dir + name for name in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, name))]
    dirs.append(root_dir)
    img_list = list()
    for dr in dirs:
        sub_list = glob.glob(dr + "/*." + ext)
        img_list.extend(sub_list)
    return img_list


def change_to_real_type(img_list):
    all_type = []
    for img in img_list:
        if not file_exist(img):
            continue
        real_type = imghdr.what(img)
        if all_type.count(real_type) == 0:
            all_type.append(real_type)
        if real_type is None:
            continue
        real_name = img[:img.rfind('.')] + '.' + real_type
        os.rename(img, real_name)
    return all_type

######################################
# Unit test
######################################

def run_unittest():
    # md5 test
    print(md5_from_binary("24d30c4e25a2dc6f4f7d8be89f002605020fd938"))

if __name__ == "__main__":
    run_unittest()



