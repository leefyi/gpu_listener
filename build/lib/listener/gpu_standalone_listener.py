# coding=utf-8
# author: lifangyi
# date: 2021/4/2 下午3:22
# file: gpu_standalone_listener.py

from __future__ import print_function

import os
import platform
import sys
import threading
import time
import argparse
from subprocess import Popen, PIPE
from distutils import spawn
import decimal

GPUs = []


class GPU:
    """
    GPU实体类
    """

    def __init__(
        self,
        ID,
        uuid,
        gpu_util,
        memory_total,
        memory_used,
        memory_free,
        driver,
        gpu_name,
        serial,
        display_mode,
        display_active,
        temp_gpu,
    ):
        self.id = ID
        self.uuid = uuid
        self.gpu_util = gpu_util
        self.memory_util = float(memory_used) / float(memory_total)
        self.memory_total = memory_total
        self.memory_used = memory_used
        self.memory_free = memory_free
        self.driver = driver
        self.name = gpu_name
        self.serial = serial
        self.display_mode = display_mode
        self.display_active = display_active
        self.temperature = temp_gpu


def get_gpus():
    """
    nvidia-smi命令统计单次GPU资源利用情况, 幂等, 支持多卡、多次调用
    主要统计  device_id,
            uuid,
            gpu_util,
            mem_total,
            mem_used,
            mem_free,
            driver,
            gpu_name,
            serial,
            display_mode,
            display_active,
            temp_gpu

    :return: None
    """
    if platform.system() == "Windows":
        # If the platform is Windows and nvidia-smi
        # could not be found from the environment path,
        # try to find it from system drive with default installation path
        nvidia_smi = spawn.find_executable("nvidia-smi")
        if nvidia_smi is None:
            nvidia_smi = (
                "%s\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe"
                % os.environ["systemdrive"]
            )
    else:
        nvidia_smi = "nvidia-smi"

    cmd = (
        "--query-gpu=index,uuid,utilization.gpu,memory.total,memory.used,memory.free,"
        "driver_version,name,gpu_serial,display_active,display_mode,temperature.gpu"
    )
    formatting = "--format=csv,noheader,nounits"
    popen_cmds = [nvidia_smi, cmd, formatting]

    # Get index, uuid, processing and memory utilization and so on for all GPUs
    try:
        p = Popen(
            popen_cmds,
            stdout=PIPE,
        )
        stdout, stderr = p.communicate()
    except BaseException as be:
        print("exception while monitoring - ", str(be))
        sys.exit(1)

    output = stdout.decode("UTF-8")
    # Parse output
    # split on operating system line break - Linux default is "\n"
    lines = output.split("\n")
    lines = [l for l in lines if l != ""]
    num_devices = len(lines)
    temp = []
    for g in range(num_devices):
        line = lines[g]
        vals = line.split(", ")
        for i in range(12):
            if i == 0:
                device_id = int(vals[i])
            elif i == 1:
                uuid = vals[i]
            elif i == 2:
                gpu_util = _safe_float_cast(vals[i]) / 100
            elif i == 3:
                mem_total = _safe_float_cast(vals[i])
            elif i == 4:
                mem_used = _safe_float_cast(vals[i])
            elif i == 5:
                mem_free = _safe_float_cast(vals[i])
            elif i == 6:
                driver = vals[i]
            elif i == 7:
                gpu_name = vals[i]
            elif i == 8:
                serial = vals[i]
            elif i == 9:
                display_active = vals[i]
            elif i == 10:
                display_mode = vals[i]
            elif i == 11:
                temp_gpu = _safe_float_cast(vals[i])
        gpu = GPU(
            device_id,
            uuid,
            gpu_util,
            mem_total,
            mem_used,
            mem_free,
            driver,
            gpu_name,
            serial,
            display_mode,
            display_active,
            temp_gpu,
        )
        # 每一次结果操作num_devices次
        temp.append(gpu)
    GPUs.append(temp)


def _safe_float_cast(str_number):
    """
    将字符串安全地转换为float
    :param str_number:
    :return: float
    """
    try:
        number = float(str_number)
    except ValueError:
        number = float("nan")
    return number


def median(data):
    """
    计算序列中的中位数
    :param data: gpu util data list
    :return: median number
    """
    data.sort()
    list_length = len(data)
    if list_length % 2 == 0:
        return (data[int(list_length / 2) - 1] + data[int(list_length / 2)]) / 2
    else:
        return data[int(list_length / 2)]


def major(data):
    """
    计算序列中的众数
    :param data: gpu util data list
    :return: major number
    """
    major_dict = {}
    for us in data:
        if str(us) not in major_dict.keys():
            major_dict[str(us)] = 1
        else:
            mv = major_dict[str(us)]
            mv += 1
            major_dict[str(us)] = mv
    smd = list(sorted(major_dict.items(), key=lambda x: x[1]))
    return smd[-1][0]


def report(header, messages, duration_time, interval):
    """
    打印统计报告
    :param header: 标题
    :param messages: 包含度量信息的二维数组
    :param duration_time: 观测持续时间(s)
    :param interval: 观测间隔(s)
    :return: None
    """
    print("=" * 50)
    print("统计 {0}s, 间隔 {1}s \n".format(duration_time, interval))
    print(header)
    for gpu_info in messages:
        print("-" * 50)
        gid = gpu_info[0][1]
        avg_gpu_util = gpu_info[1][1] * 100
        avg_memory_used = gpu_info[2][1]
        memory_total = gpu_info[3][1]
        median_gpu = gpu_info[5][1] * 100
        max_gpu = gpu_info[6][1] * 100
        min_gpu = gpu_info[7][1] * 100
        major_gpu = float(gpu_info[8][1]) * 100

        # decimal对一些关键指标作处理
        # 四舍五入规则切换
        decimal.getcontext().rounding = "ROUND_HALF_UP"
        quant = decimal.Decimal("0.00")

        avg_gpu_util_d = decimal.Decimal(avg_gpu_util)
        str_avg_gpu_util = decimal.Decimal(str(avg_gpu_util_d)).quantize(quant)
        avg_memory_used_d = decimal.Decimal(avg_memory_used)
        str_avg_memory_used = decimal.Decimal(str(avg_memory_used_d)).quantize(quant)
        median_gpu_d = decimal.Decimal(median_gpu)
        max_gpu_d = decimal.Decimal(max_gpu)
        min_gpu_d = decimal.Decimal(min_gpu)
        major_gpu_d = decimal.Decimal(major_gpu)
        str_median_gpu = decimal.Decimal(str(median_gpu_d)).quantize(quant)
        str_max_gpu = decimal.Decimal(str(max_gpu_d)).quantize(quant)
        str_min_gpu = decimal.Decimal(str(min_gpu_d)).quantize(quant)
        str_major_gpu = decimal.Decimal(str(major_gpu_d)).quantize(quant)

        print("GPU: ", gid)
        print("GPU平均利用率: {}%".format(str_avg_gpu_util))
        print("GPU显存平均利用: {} MB".format(str_avg_memory_used))
        print("GPU显存: {} MB".format(memory_total))
        print("GPU最大利用率: {}%".format(str_max_gpu))
        print("GPU最小利用率: {}%".format(str_min_gpu))
        print("GPU中位数利用率: {}%".format(str_median_gpu))
        print("GPU众数利用率: {}%".format(str_major_gpu))
        print("-" * 50)
    print("=" * 50)
    GPUs = []


def main():
    # arguments parser
    parser = argparse.ArgumentParser(description="Process some important options")
    parser.add_argument(
        "--d", metavar="d", help="duration(s) of statistics", type=int, required=True
    )

    parser.add_argument(
        "--l",
        metavar="l",
        help="delay or interval of sampler, in second",
        nargs="?",
        const=1,  # --l 后面什么都不接时候使用的
        type=int,
        default=1,  # 没有--l时使用的值
        required=False,
    )
    args = vars(parser.parse_args())

    duration = args["d"]
    delay = args["l"]

    if delay >= duration:
        print("invalid --l value, should be: delay < duration")
        sys.exit(1)
    mutex = threading.Lock()
    # timer
    def gpu_timer():
        # print("Hello Timer!")
        mutex.acquire()
        get_gpus()
        global timer
        timer = threading.Timer(delay, gpu_timer)
        timer.start()

    timer = threading.Timer(1, gpu_timer)
    timer.start()
    time.sleep(duration)
    timer.cancel()

    mutex.release()
    # statistics
    count = len(GPUs)
    title = "GPU Numbers: {0}\n" "Device: {1}\n" "Driver Version: {2}"
    gpu_name = GPUs[0][0].name
    width = len(GPUs[0])
    driver = GPUs[0][0].driver

    tms = []

    for i in range(width):
        # 有几个GPU大循环就循环几次
        t = 0
        iid = 0
        gutil = 0
        mem_total = 0
        mem_used = 0
        # 某号GPU的多次组合信息
        single_tms = []
        gutils_list = []
        for g in GPUs:
            # GPUs的数组，一个延迟区间一个list，每一个元素是一个snapshot的数组，为N个gpu信息，
            item = g[i]
            mem_total = item.memory_total
            mem_used += item.memory_used
            t += item.temperature
            gutils_list.append(item.gpu_util)
            gutil += item.gpu_util
            iid = item.id

        # 完成一张GPU的统计，将子数组加入tms
        t0 = ("gpu id", str(iid))
        t1 = ("avg gpu util", gutil / count)
        t2 = ("avg gpu memory used", mem_used / count)
        t3 = ("gpu memory total", mem_total)
        t4 = ("avg temperature", t / count)
        median_gu = median(gutils_list)
        max_gu = max(gutils_list)
        min_gu = min(gutils_list)
        major_gu = major(gutils_list)
        t5 = ("median gpu util", median_gu)
        t6 = ("max gpu util", max_gu)
        t7 = ("min gpu util", min_gu)
        t8 = ("major gpu util", major_gu)

        single_tms.append(t0)
        single_tms.append(t1)
        single_tms.append(t2)
        single_tms.append(t3)
        single_tms.append(t4)
        single_tms.append(t5)
        single_tms.append(t6)
        single_tms.append(t7)
        single_tms.append(t8)
        tms.append(single_tms)

    title = title.format(str(width), gpu_name, driver)
    report(title, tms, duration, delay)
    os._exit(1)


if __name__ == "__main__":
    main()


