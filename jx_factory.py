#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/6/25 1:25 下午
# @File    : jx_factory.py
# @Project : jd_scripts
# @Desc    : 京喜App->惊喜工厂
import json
import aiohttp
import asyncio
from datetime import datetime
import re
from furl import furl
from urllib.parse import unquote, urlencode
from utils.console import println
from utils.algo import *


class JxFactory:
    """
    京喜工厂
    """
    headers = {
        'referer': 'https://st.jingxi.com/',
        'user-agent': 'jdpingou;android;4.11.0;11;a27b83d3d1dba1cc;network/wifi;model/RMX2121;appBuild/17304;partner'
                      '/oppo01;;session/136;aid/a27b83d3d1dba1cc;oaid/;pap/JA2019_3111789;brand/realme;eu'
                      '/1623732683334633;fv/4613462616133636;Mozilla/5.0 (Linux; Android 11; RMX2121 '
                      'Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 '
                      'Chrome/91.0.4472.120 Mobile Safari/537.36'
    }

    def __init__(self, pt_pin, pt_key):
        """
        """
        self._pt_pin = unquote(pt_pin)
        self._cookies = {
            'pt_pin': pt_pin,
            'pt_key': pt_key
        }
        self._host = 'https://m.jingxi.com/'
        self._factory_id = None  # 工厂ID
        self._nickname = None  # 用户昵称
        self._encrypt_pin = None
        self._inserted_electric = 0   # 已投入电量
        self._need_electric = 0  # 总共需要的电量
        self._production_id = 0  # 商品ID
        self._production_stage_progress = ''  # 生产进度
        self._phone_id = ''  # 设备ID
        self._pin = ''  # 账号ID

        self._token = None  # 签名的TOKEN
        self._algo = None  # 签名算法
        self._fp = generate_fp()  # 签名算法参数
        self._appid = '10001'  #
        self._random = None  #

        self._can_help = True  # 是否能帮好友打工

    async def request(self, session, path, params, method='GET'):
        """
        """
        try:
            time_ = datetime.now()
            default_params = {
                '_time': int(time_.timestamp()*1000),
                'g_ty': 'ls',
                'callback': 'jsonp',
                'sceneval': '2',
                'g_login_type': '1',
                '_': int(time.time() * 1000),
                '_ste': '1',
                'timeStamp': int(time.time()*1000),
                'zone': 'dream_factory'
            }
            params.update(default_params)
            url = self._host + path + '?' + urlencode(params)
            h5st = await self.encrypt(time_, url)
            params['h5st'] = h5st
            url = self._host + path + '?' + urlencode(params)
            if method == 'GET':
                response = await session.get(url=url)
            else:
                response = await session.post(url=url)
            text = await response.text()
            temp = re.search(r'\((.*)', text).group(1)
            data = json.loads(temp)
            if data['ret'] != 0:
                return data
            else:
                result = data['data']
                result['ret'] = 0
                return result
        except Exception as e:
            println('{}, 请求服务器数据失败:{}'.format(self._pt_pin, e.args))
            return {
                'ret': 50000,
                'msg': '请求服务器失败'
            }

    async def get_encrypt(self):
        """
        获取签名算法
        """
        url = 'https://cactus.jd.com/request_algo?g_ty=ajax'
        headers = {
            'Authority': 'cactus.jd.com',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Content-Type': 'application/json',
            'Origin': 'https://st.jingxi.com',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://st.jingxi.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8,en;q=0.7'
        }
        body = {
            "version": "1.0",
            "fp": self._fp,
            "appId": self._appid,
            "timestamp": int(time.time()*1000),
            "platform": "web",
            "expandParams": ""
        }
        algo_map = {
            'md5': md5,
            'hmacmd5': hmacMD5,
            'sha256': sha256,
            'hmacsha256': hmacSha256,
            'sha512': sha512,
            'hmacsha512': sha512,
        }
        try:
            async with aiohttp.ClientSession(cookies=self._cookies, headers=headers) as session:
                response = await session.post(url=url, data=json.dumps(body))
                text = await response.text()
                data = json.loads(text)
                if data['status'] == 200:
                    self._token = data['data']['result']['tk']
                    self._random = re.search("random='(.*)';", data['data']['result']['algo']).group(1)
                    algo = re.search(r'algo\.(.*)\(', data['data']['result']['algo']).group(1)
                    if algo.lower() in algo_map:
                        self._algo = algo_map[algo.lower()]
                    else:
                        self._algo = algo_map['hmacsha512']
                        self._random = '5gkjB6SpmC9s'
                        self._token = 'tk01wcdf61cb3a8nYUtHcmhSUFFCfddDPRvKvYaMjHkxo6Aj7dhzO+GXGFa9nPXfcgT' \
                                      '+mULoF1b1YIS1ghvSlbwhE0Xc '
                else:
                    println('{}, 获取签名算法失败!'.format(self._pt_pin))

        except Exception as e:
            println('{}, 获取签名算法失败, {}!'.format(self._pt_pin, e.args))

    async def encrypt(self, timestamp=None, url='',  stk=''):
        """
        获取签名
        """
        timestamp = 20210721161534621
        if not stk:
            url = furl(url)
            stk = url.args.get('_stk', '')

        s = '{}{}{}{}{}'.format(self._token, self._fp, timestamp, self._appid, self._random)
        try:
            hash1 = self._algo(s, self._token)
        except Exception as e:
            hash1 = self._algo(s)
        tmp = []
        tmp_url = furl(url)
        for key in stk.split(','):
            if key == '':
                continue
            tmp_s = '{}:{}'.format(key, tmp_url.args.get(key, ''))
            tmp.append(tmp_s)
        st = '&'.join(tmp)
        hash2 = hmacSha256(st, hash1)
        return ';'.join([str(timestamp), str(self._fp), self._appid, self._token, hash2])

    async def get_user_info(self, session):
        """
        获取用户信息
        """
        path = 'dreamfactory/userinfo/GetUserInfo'
        params = {
            'pin': '',
            'sharePin': '',
            'shareType': '',
            'materialTuanPin': '',
            'materialTuanId': '',
            'source': ''
        }
        data = await self.request(session, path, params)
        if data['ret'] != 0:
            println('{}, 获取用户数据失败, {}!'.format(self._pt_pin, data['msg']))
            return None
        return data

    async def collect_user_electricity(self, session):
        """
        收取电量
        :param session:
        :return:
        """
        path = 'dreamfactory/generator/CollectCurrentElectricity'
        params = {
            'pgtimestamp': str(int(time.time()*1000)),
            'apptoken': 'a65979d104f9154076c8c47d2846d516',
            'phoneID': self._phone_id,
            'factoryid': self._factory_id,
            'doubleflag': 1,
            'timeStamp': 'undefined',
            'zone': 'dream_factory',
            '_stk': '_time,apptoken,doubleflag,factoryid,pgtimestamp,phoneID,zone',
        }
        data = await self.request(session, path, params, 'GET')
        if not data or data['ret'] != 0:
            println('{}, 收取电量失败, {}'.format(self._pt_pin, data))
        else:
            println('{}, 成功收取电量:{}!'.format(self._pt_pin, data['CollectElectricity']))

    async def get_user_electricity(self, session):
        """
        查询用户电量, 如果满了就收取电量
        """
        path = 'dreamfactory/generator/QueryCurrentElectricityQuantity'
        body = {
            'factoryid': self._factory_id,
            '_stk': '_time,factoryid,zone',
        }
        data = await self.request(session, path, body)
        if not data or data['ret'] != 0:
            println('{}, 查询用户电量失败!'.format(self._pt_pin))
            return

        # 电量满了收取电量
        if int(data['currentElectricityQuantity']) >= data['maxElectricityQuantity']:
            await self.collect_user_electricity(session)
        else:
            println('{}, 当前电量:{}/{}，暂不收取!'.format(self._pt_pin, int(data['currentElectricityQuantity']),
                                                  data['maxElectricityQuantity']))

    async def init(self, session):
        """
        初始化
        """
        user_info = await self.get_user_info(session)
        if not user_info:
            return False
        if 'factoryList' not in user_info:
            println('{}, 未开启活动!'.format(self._pt_pin))
            return False
        self._factory_id = user_info['factoryList'][0]['factoryId']

        if 'productionList' not in user_info:
            println('{}, 未选择商品!'.format(self._pt_pin))
        else:
            self._inserted_electric = user_info['productionList'][0]['investedElectric']
            self._need_electric = user_info['productionList'][0]['needElectric']
            self._production_id = user_info['productionList'][0]['productionId']

        if 'user' not in user_info:
            println('{}, 没有找到用户信息!'.format(self._pt_pin))
            return False
        self._pin = user_info['user']['pin']
        self._phone_id = user_info['user']['deviceId']
        self._encrypt_pin = user_info['user']['encryptPin']
        self._nickname = user_info['user']['nickname']
        return True

    async def query_friend_list(self, session):
        """
        查询招工情况
        :param session:
        :return:
        """
        path = 'dreamfactory/friend/QueryFriendList'
        params = {
            'body': '',
            '_stk': '_time,zone'
        }
        data = await self.request(session, path, params)
        if not data:
            return
        println('{}, 今日帮好友打工:{}/{}次!'.format(self._pt_pin, len(data['assistListToday']), data['assistNumMax']))

        # 打工次数满了，无法打工
        if len(data['assistListToday']) >= data['assistNumMax']:
            self._can_help = False

        println('{}, 今日招工:{}/{}次!'.format(self._pt_pin, len(data['hireListToday']), data['hireNumMax']))

    async def get_task_award(self, session, task):
        """
        领取任务奖励
        :param task:
        :param session:
        :return:
        """
        path = 'newtasksys/newtasksys_front/Award'
        params = {
            'bizCode': 'dream_factory',
            'source': 'dream_factory',
            'taskId': task['taskId'],
            '_stk': '_time,bizCode,source,taskId'
        }
        data = await self.request(session, path, params)

        if not data or data['ret'] != 0:
            println('{}, 领取任务:《{}》奖励失败, {}'.format(self._pt_pin, task['taskName'], data['msg']))
            return
        num = data['prizeInfo'].replace('\n', '')
        println('{}, 领取任务:《{}》奖励成功, 获得电力:{}!'.format(self._pt_pin, task['taskName'], num))

    async def get_task_list(self, session):
        """
        获取任务列表
        :param session:
        :return:
        """
        path = 'newtasksys/newtasksys_front/GetUserTaskStatusList'
        params = {
            'bizCode': 'dream_factory',
            'source': 'dream_factory',
            '_stk': '_time,bizCode,source'
        }
        data = await self.request(session, path, params)
        if not data or data['ret'] != 0:
            println('{}, 获取任务列表失败!'.format(self._pt_pin))
            return
        task_list = data['userTaskStatusList']

        for task in task_list:
            # 任务完成并且没有领取过奖励去领取奖励
            if task['completedTimes'] >= task['targetTimes'] and task['awardStatus'] != 1:
                await self.get_task_award(session, task)
                await asyncio.sleep(1)

            #println(task['awardStatus'])

    async def run(self):
        """
        程序入口
        """
        await self.get_encrypt()
        async with aiohttp.ClientSession(headers=self.headers, cookies=self._cookies) as session:
            success = await self.init(session)
            if not success:
                println('{}, 初始化失败!'.format(self._pt_pin))
                return

            # await self.get_user_electricity(session)
            # await self.query_friend_list(session)
            await self.get_task_list(session)


def start(pt_pin, pt_key):
    """
    """
    app = JxFactory(pt_pin, pt_key)
    asyncio.run(app.run())


if __name__ == '__main__':
    from config import JD_COOKIES
    start(*JD_COOKIES[0].values())
    #println(sha256('_time:1626856317724&apptoken:&doubleflag:1&factoryid:1099558512495&pgtimestamp:&phoneID:&timeStamp:&zone:dream_factory', '1cb64d2c5e8979479ca7a1a047dcd22311fb91344abf42522d5415251616c41c'))