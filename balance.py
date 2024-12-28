import random

import pymysql
from dbutils.pooled_db import PooledDB
from docplex.mp.model import Model

# 数据库配置信息
# 采用连接池，减少建立连接的创建时间
# jdbc:mysql://42.193.15.68:3306
pool = PooledDB(pymysql,
                host='42.193.15.68',
                port=3306,
                user='root',
                password='testpass',
                db='fm_quant',
                charset='utf8',
                autocommit=True
                )


def get_connection():
    return pool.connection()


# ----------------------------------------------------------------------------
# Initialize the problem data
# ----------------------------------------------------------------------------

# 从财汇数据库中获取shibor利率
# 财汇数据库大约11：10am左右，入库当天的shibor利率
# 未来可以考虑5日平均、10日平均以及投研系统利率走势预测来拟合短期的shibor利率
def get_shibor_rate(begin_date):
    cursor = get_connection().cursor()
    sql = 'select SH001D,SH001W,SH002W,SH001M,SH003M,SH006M,SH009M,SH001Y from TQ_RT_SHIBOR where TRADEDATE  = ' \
          '%s'
    cursor.execute(sql, begin_date)
    res = cursor.fetchall()
    if len(res) < 1:
        return None

    day_array = [1, 7, 14, 30, 90, 180, 270, 360]
    shibor_rate = []
    index = 0

    for i in range(360):
        if i >= day_array[index]:
            index = index + 1
        shibor_rate.append(float(res[0][index]))
    return shibor_rate


def get_history_amt(begin_date):
    return [random.randint(0, 500) for _ in range(360)]


# 获取特定日期至未来1年的节假日情况
def get_holiday(begin_date):
    cursor = get_connection().cursor()
    sql = 'select ISHOLIDAY from (select isholiday from holiday where DATE_DAY >= %s order by DATE_DAY) t where 1=1 ' \
          'limit 360'
    cursor.execute(sql, begin_date)
    res = cursor.fetchall()
    holiday = []
    for i in res:
        holiday.append(int(i[0]))
    return holiday


# 开始定义模型种类、变量、目标函数、约束条件
# 混合整数规划
# 决策变量X_{ij}
# x_matrix = {(i,j) for i in range(360) for j in range(360)}
# 定义决策变量x_ij为第i天拆入j天x手，每手100w。
# ex: x_12 = 10，第1天，拆入期限为2天的
# 决策变量下界为0，上界为受拆借余额限制
# 拆借余额为28.15亿元
upper_bound = 28.15 * 100
open_door = 8 * 100

# funding_gap = [1500 for _ in range(360)]
funding_gap = [random.randint(-400,1500) for _ in range(360)]
# 从资金落点表中获取未来一段时间的资金缺口
# 目前资金落点表功能已经
# 随机获取-4亿元 到 20亿元 的缺口
def get_funding_gap(begin_date):
    return funding_gap
    # return [random.randint(-400, 2000) for _ in range(360)]


def build_balance_model(begin_date):
    # 准备模型所需参数
    # 获取shibor利率
    shibor_rate = get_shibor_rate(begin_date)
    # 获取节假日列表
    holiday = get_holiday(begin_date)
    # 获取资金缺口
    # 参数缺失则直接退出
    if shibor_rate is None or holiday is None or funding_gap is None:
        return

    # 开始建模流程
    model = Model(name="balance MIP")
    x = model.integer_var_matrix(keys1=[i for i in range(1, 51)], keys2=[j for j in range(1, 21)], name="x", lb=0,
                                 ub=open_door)

    # 设置目标函数，持有天数*利率*金额 使得金额（成本）最低
    # i表示第i天，j表示购买期限(天数)
    # 考虑到节假日，j是自然日，需要根据节假日和到期日期计算出实际持仓天数
    # 理论上，节假日并不需要计算利息，但是在实际操作过程中

    model.minimize(model.sum(
        [x[i, j] * get_holding_days(holiday, i, j) * shibor_rate[j] / 100
         for i in range(1, 51) for j in range(1, 21)]))

    # 设置约束条件
    # 先解决节假日的问题
    # 获取节假日
    # 当第i天为节假日时，x[i][j] 都等于0，因为节假日银行间市场不营业
    model.add_constraints(cts=(x[i, j] == 0 for i in range(1, 51) if holiday[i - 1] == 1 for j in range(1, 21)),
                          names='holiday_constraint')

    holiday_temp_amt = []
    # 开门还款金额应该小于特定金额
    for t in range(1, 51):

        maturity_amt = [x[i, t - i if (t - i > 1) & (t - i < 21) else 1] for i in range(1, t - 1 if t - 1 > 0 else 1)]
        if holiday[t] == 1:
            holiday_temp_amt = holiday_temp_amt.__add__(maturity_amt)
        if holiday[t] == 0:
            holiday_temp_amt = holiday_temp_amt.__add__(maturity_amt)
            if len(holiday_temp_amt) != 0:
                model.add_constraint(model.sum(x for x in holiday_temp_amt) <= open_door,
                                     ctname='open door repay amount' + str(t))
            holiday_temp_amt = []

    # 借的钱必须要能覆盖资金缺口
    for t in range(1, 51):
        ct = model.sum(x[t, j] for j in range(1, 21)) >= funding_gap[t] - model.sum(
            x[i, j] for i in range(t - 20 if t - 20 > 1 else 1, t) for j in range(t - i +1, 21))
        model.add_constraint(ct=ct, ctname="t balance")
    # 拆借余额受人行规定限制，即各项存款余额的8%
    for t in range(1, 51):
        model.add_constraint(model.sum(x[i, j] for i in range(1, t + 1) for j in range(t - i + 1, 21)) <= upper_bound)

    return model


# 根据节假日情况，以及资产起始到期日期，计算出实际持有时间
def get_holding_days(holiday, i, j):
    if holiday is None or j is None or i is None:
        return j
    # 考虑节假日列表长度（360），落在列表之外的应该抛弃
    for m in range(len(holiday) - i - j):
        if holiday[i + j + m] == 0:
            return j + m + 1


if __name__ == '__main__':
    date = '20230804'
    print(get_shibor_rate(date))
    print(get_funding_gap(date))
    print(get_holiday(date))
    holding_days = get_holding_days(get_holiday(date), 1, 4)
    print(holding_days)
    print([i for i in range(1, 5)])
    model = build_balance_model(date)
    print(model.solve())
# 拆借利率
