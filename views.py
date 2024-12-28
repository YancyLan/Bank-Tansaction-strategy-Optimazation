import re

from pyecharts import options as opts
from pyecharts.charts import Bar,Grid

from balance import *

date = '20230801'


def get_model(date):
    return build_balance_model(date)


def get_days(date='20230801', delta=50):
    cursor = get_connection().cursor()
    sql = 'select date_day from holiday where DATE_DAY >= %s order by DATE_DAY limit %d' % (date, delta)
    cursor.execute(sql)
    days = []
    for i in cursor.fetchall():
        days.append(i[0])
    return days


pattern = re.compile(r'x_(\d+)_(\d+)')


def initial_bar(date):
    x = get_days(date)
    res = get_model(date).solve()
    print(res)

    bar = (
        Bar()
        .add_xaxis(x)
        # .add_yaxis(series_name = "y",y_axis=y)
        .set_global_opts(title_opts=opts.TitleOpts(title="资金拆入策略"))
    )
    index = []
    for i in res.iter_var_values():
        index.append(pattern.match(i[0].name).groups().__add__(i))
        for m in range(int(pattern.match(i[0].name).group(2))):
            y = [0 for _ in range(51)]
            y[int(pattern.match(i[0].name).group(1)) + m] += i[1]

            y_mod = []
            for y_data in y:
                if y_data == 0:
                    y_mod.append('')
                else:
                    y_mod.append(y_data)

            bar.add_yaxis(i[0].name, y_mod, stack='stack',label_opts=opts.LabelOpts(is_show=False))

    return bar

def initial_gap_bar(date):
    funding_gap= get_funding_gap(date)
    x = get_days(date)
    bar =     bar = (
        Bar()
        .add_xaxis(x)
        .add_yaxis(series_name = "gap",y_axis=funding_gap,label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(title_opts=opts.TitleOpts(title="流动性缺口"))
    )
    return bar


def render(bar1,bar2):
    grid = Grid()
    grid.add(bar1, grid_opts=opts.GridOpts(pos_bottom="60%"))
    grid.add(bar2,  grid_opts=opts.GridOpts(pos_top="60%"))
    grid.render()

if __name__ == '__main__':
    print(get_days())
    bar1 = initial_bar(date)
    bar2 = initial_gap_bar(date)
    render(bar1,bar2)
