# coding=utf-8
# author: lifangyi
# date: 2021/4/12 下午3:30
# file: test_listener.py

import os
import unittest

lp = os.path.abspath('listener')
gp = os.path.join(lp, 'gpu_standalone_listener.py')


class TestUtility(unittest.TestCase):

    def test_normal_u(self):
        cmd = 'python {} -h'.format(gp)
        os.system(cmd)

    def test_entrypoint(self):
        cmd='glistener -h'
        os.system(cmd)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestUtility)
    runner = unittest.TextTestRunner()
    runner.run(suite)
