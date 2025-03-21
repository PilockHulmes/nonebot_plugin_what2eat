from typing import Any, Coroutine, List

from nonebot import logger, on_command, on_regex, require
from nonebot.adapters.onebot.v11 import (GROUP, GROUP_ADMIN, GROUP_OWNER, Bot,
                                         GroupMessageEvent, Message,
                                         MessageEvent, MessageSegment)
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgStr, CommandArg, Depends, RegexMatched
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from .data_source import eating_manager
from .utils import Meals, save_cq_image

from datetime import datetime, timedelta
import json

require("nonebot_plugin_apscheduler")

__what2eat_version__ = "v0.3.6"
__what2eat_usages__ = f'''
今天吃什么？ {__what2eat_version__}
[xx吃xx]    问bot吃什么
[xx喝xx]    问bot喝什么
[添加 xx]   添加菜品至群菜单
[移除 xx]   从菜单移除菜品
[加菜 xx]   添加菜品至基础菜单
[菜单]        查看群菜单
[基础菜单] 查看基础菜单
[开启/关闭小助手] 开启/关闭吃饭小助手
[添加/删除问候 时段 问候语] 添加/删除吃饭小助手问候语'''.strip()

__plugin_meta__ = PluginMetadata(
    name="今天吃什么？",
    description="选择恐惧症？让Bot建议你今天吃/喝什么！",
    usage=__what2eat_usages__,
    extra={
        "author": "KafCoppelia <k740677208@gmail.com>",
        "version": __what2eat_version__
    }
)
import re
eat_pattern = re.compile(
    r'^'
    r'(?:'  # 时间部分（可选）
        r'(?:今|明|后|每(?:\天|日|周)?|周|[早晚]|早上|晚上|下午|凌晨|今早|今晚|明早|明晚)'
        r'[天日周晨上下午晚钟]*(?:\的)?'
    r')?'  # 时间部分结束
    r'(?:早饭|早餐|早茶|午餐|午饭|下午茶|晚餐|晚饭|宵夜|夜宵)'  # 时间段
    r'吃什么'  # 固定部分
    r'.*$',
    re.UNICODE
).pattern
print(eat_pattern)
e_p = r"^(?:(?:今|明|后|每(?:\天|日|周)?|周|[早晚]|早上|晚上|下午|凌晨|今早|今晚|明早|明晚)[天日周晨上下午晚钟]*(?:\的)?)?(?:早饭|早餐|早茶|午餐|午饭|下午茶|下午|晚餐|晚饭|晚上|宵夜|夜宵)?吃什么.*$"
drink_pattern = re.compile(
    r'^'
    r'(?:'  # 时间部分（可选）
        r'(?:今|明|后|每(?:\天|日|周)?|周|[早晚]|早上|晚上|下午|凌晨|今早|今晚|明早|明晚)'
        r'[天日周晨上下午晚钟]*(?:\的)?'
    r')?'  # 时间部分结束
    r'(?:早饭|早餐|早茶|午餐|午饭|下午茶|晚餐|晚饭|宵夜|夜宵)'  # 时间段
    r'喝什么'  # 固定部分
    r'.*$',
    re.UNICODE
).pattern
print(drink_pattern)
d_p = r"^(?:(?:今|明|后|每(?:\天|日|周)?|周|[早晚]|早上|中午|上午|晚上|下午|凌晨|今早|今晚|明早|明晚)[天日周晨上下午晚钟]*(?:\的)?)?(?:早饭|早餐|早茶|午餐|午饭|下午茶|下午|晚餐|晚饭|晚上|宵夜|夜宵)喝什么.*$"
what2eat = on_regex(e_p, priority=15,block=True)
what2drink = on_regex(d_p, priority=15,block=True)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
what2eat_water = on_regex(
    r"^(今)?(天)?((早|晚)(?:上|餐)?|中午|午餐)(.){0,6}吃(什么|点啥|啥)(帮助)?", priority=16, block=True)
what2drink_water = on_regex(
    r"^(今)?(天)?((早|晚)(?:上|餐)?|中午|午餐)(.){0,6}喝(什么|点啥|啥)(帮助)?", priority=16, block=True)
group_add = on_command("添加", permission=SUPERUSER |
                       GROUP_ADMIN | GROUP_OWNER, priority=15, block=True)
group_remove = on_command("移除", permission=SUPERUSER |
                          GROUP_ADMIN | GROUP_OWNER, priority=15, block=True)
basic_add = on_command("加菜", permission=SUPERUSER, priority=15, block=True)
show_group_menu = on_command(
    "菜单", aliases={"群菜单", "查看菜单"}, permission=GROUP, priority=15, block=True)
show_basic_menu = on_command("基础菜单", permission=GROUP, priority=15, block=True)

greeting_on = on_command("开启小助手", aliases={
                         "启用小助手"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=12, block=True)
greeting_off = on_command("关闭小助手", aliases={
                          "禁用小助手"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=12, block=True)
add_greeting = on_command("添加问候", aliases={
                          "添加问候语"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=12, block=True)
remove_greeting = on_command("删除问候", aliases={
                             "删除问候语", "移除问候", "移除问候语"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=12, block=True)


# @what2eat.handle()
# async def _(event: MessageEvent, args: str = RegexMatched()):
#     logger.info("enter what2eat")
#     if args[-2:] == "帮助":
#         await what2eat.finish(__what2eat_usages__)
#     print("code goes here")
#     msg = eating_manager.get2eat(event)
#     await what2eat.finish(msg)

@what2eat.handle()
@what2eat_water.handle()
async def handleEat(event: GroupMessageEvent):
    if "帮助" in event.get_plaintext():
         await what2drink.finish(__what2eat_usages__)
    msg = eating_manager.get2eat(event)
    if datetime.today().isoweekday() == 4 and "肯德基" not in msg:
        msg += "，但因为今天是周四所以更推荐肯德基！"
    await what2eat.finish(msg)
    # await what2eat.finish("匹配到了")

@what2drink.handle()
@what2drink_water.handle()
async def handleDrink(event: GroupMessageEvent):
    if "帮助" in event.get_plaintext():
         await what2drink.finish(__what2eat_usages__)
    msg = eating_manager.get2drink(event)
    await what2drink.finish(msg)

# @what2drink.handle()
# async def _(event: MessageEvent, args: str = RegexMatched()):
#     logger.info("enter what2drink")
#     if args[-2:] == "帮助":
#         await what2drink.finish(__what2eat_usages__)

#     msg = eating_manager.get2drink(event)
#     await what2drink.finish(msg)


@group_add.handle()
async def _(event: GroupMessageEvent, args: Message = CommandArg()):
    args_str: List[str] = args.extract_plain_text().strip().split()
    if not args_str:
        await group_add.finish("还没输入你要添加的菜品呢~")
    elif len(args_str) > 1:
        await group_add.finish("添加菜品参数错误~")

    # If image included, save it, return the path in string
    await save_cq_image(args, eating_manager._img_dir)

    # Record the whole string, including the args after transfering
    msg: str = eating_manager.add_group_food(event, str(args))

    if "[CQ:image" in str(args):
        await group_add.finish(args.append(MessageSegment.text(" " + msg)))
    else:
        await group_add.finish(args.append(MessageSegment.text(msg)))


@basic_add.handle()
async def _(args: Message = CommandArg()):
    args_str: List[str] = args.extract_plain_text().strip().split()
    if not args_str:
        await basic_add.finish("还没输入你要添加的菜品呢~")
    elif len(args_str) > 1:
        await group_add.finish("添加菜品参数错误~")

    # The same as above
    await save_cq_image(args, eating_manager._img_dir)
    msg: str = eating_manager.add_basic_food(str(args))

    if "[CQ:image" in str(args):
        await group_add.finish(args.append(MessageSegment.text(" " + msg)))
    else:
        await group_add.finish(args.append(MessageSegment.text(msg)))


@group_remove.handle()
async def _(event: GroupMessageEvent, args: Message = CommandArg()):
    args: List[str] = args.extract_plain_text().strip().split()
    if not args:
        await group_remove.finish("还没输入你要移除的菜品呢~")
    elif len(args) > 1:
        await group_remove.finish("移除菜品参数错误~")

    msg: MessageSegment = eating_manager.remove_food(event, args[0])

    await group_remove.finish(MessageSegment.text(msg))


@show_group_menu.handle()
async def _(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
    gid = str(event.group_id)
    is_too_many_lines, msg = eating_manager.show_group_menu(gid)
    if is_too_many_lines:
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=MessageSegment.node_custom(int(bot.self_id), list(bot.config.nickname)[0], msg))
    else:
        await matcher.finish(msg)


@show_basic_menu.handle()
async def _(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
    is_too_many_lines, msg = eating_manager.show_basic_menu()
    if is_too_many_lines:
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=MessageSegment.node_custom(int(bot.self_id), list(bot.config.nickname)[0], msg))
    else:
        await matcher.finish(msg)


@greeting_on.handle()
async def _(event: GroupMessageEvent):
    gid = str(event.group_id)
    eating_manager.update_greeting_status(gid, True)
    await greeting_on.finish("已开启吃饭小助手喵~")


@greeting_off.handle()
async def _(event: GroupMessageEvent):
    gid = str(event.group_id)
    eating_manager.update_greeting_status(gid, False)
    await greeting_off.finish("已关闭吃饭小助手喵~")


def parse_greeting() -> Coroutine[Any, Any, None]:
    '''
        Parser the greeting input from user then store in state["greeting"]
    '''
    async def _greeting_parser(matcher: Matcher, state: T_State, input_arg: Message = Arg("greeting")) -> None:
        if input_arg.extract_plain_text() == "取消":
            await matcher.finish("操作已取消")
        else:
            state["greeting"] = input_arg

    return _greeting_parser


def parse_meal() -> Coroutine[Any, Any, None]:
    '''
        Parser the meal input from user then store in state["meal"]. If illigal, reject it
    '''
    async def _meal_parser(matcher: Matcher, state: T_State, input_arg: str = ArgStr("meal")) -> None:
        if input_arg == "取消":
            await matcher.finish("操作已取消")

        res = eating_manager.which_meals(input_arg)
        if res is None:
            await matcher.reject_arg("meal", "输入时段不合法")
        else:
            state["meal"] = res

    return _meal_parser


def parse_index() -> None:
    '''
        Parser the index of greeting to be removed input from user then store in state["index"]
    '''
    async def _index_parser(matcher: Matcher, state: T_State, input_arg: str = ArgStr("index")) -> None:
        try:
            arg2int = int(input_arg)
        except ValueError:
            await matcher.reject_arg("index", "输入序号不合法")

        if arg2int == 0:
            await matcher.finish("操作已取消")
        else:
            state["index"] = arg2int

    return _index_parser


@add_greeting.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    if args and len(args) <= 2:
        res = eating_manager.which_meals(args[0])
        if isinstance(res, Meals):
            matcher.set_arg("meal", args[0])
            if len(args) == 2:
                matcher.set_arg("greeting", args[1])

@remove_greeting.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    if args:
        res = eating_manager.which_meals(args[0])
        if isinstance(res, Meals):
            matcher.set_arg("meal", args[0])

@add_greeting.got(
    "meal",
    prompt="请输入添加问候语的时段，可选：早餐/午餐/摸鱼/晚餐/夜宵，输入取消以取消操作",
    parameterless=[Depends(parse_meal())]
)
async def handle_skip():
    add_greeting.skip()


@add_greeting.got(
    "greeting",
    prompt="请输入添加的问候语，输入取消以取消操作",
    parameterless=[Depends(parse_greeting())]
)
async def handle_add_greeting(state: T_State, greeting: Message = Arg()):
    meal = state["meal"]
    # Not support for text + image greeting, just extract the plain text
    msg = eating_manager.add_greeting(meal, greeting.extract_plain_text())
    await add_greeting.finish(msg)

@remove_greeting.got(
    "meal",
    prompt="请输入删除问候语的时段，可选：早餐/午餐/摸鱼/晚餐/夜宵，输入取消以取消操作",
    parameterless=[Depends(parse_meal())]
)
async def handle_show_greetings(meal: Meals = Arg()):
    msg = eating_manager.show_greetings(meal)
    await remove_greeting.send(msg)

@remove_greeting.got(
    "index",
    prompt="请输入删除的问候语序号，输入0以取消操作",
    parameterless=[Depends(parse_index())]
)
async def handle_remove_greeting(state: T_State, index: int = Arg()):
    meal = state["meal"]
    msg = eating_manager.remove_greeting(meal, index)
    await remove_greeting.finish(msg)

# ------------------------- Schedulers -------------------------
# 重置吃什么次数，包括夜宵
@scheduler.scheduled_job("cron", hour="6,11,17,22", minute=0, misfire_grace_time=60)
async def _():
    eating_manager.reset_count()
    logger.info("今天吃什么次数已刷新")

# 早餐提醒
@scheduler.scheduled_job("cron", hour=7, minute=0, misfire_grace_time=60)
async def time_for_breakfast():
    await eating_manager.do_greeting(Meals.BREAKFAST)

# 获取今年中国法定节假日以及调休日期
def get_dates_between(start_str, end_str):
    # 将字符串转换为日期对象
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    
    # 确保开始日期早于或等于结束日期
    if start > end:
        start, end = end, start
    
    # 计算总天数并生成日期列表
    num_days = (end - start).days + 1
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]

with open("./repo_plugins/nonebot_plugin_what2eat/nonebot_plugin_what2eat/china-holiday-calender/holidayAPI.json", "r", encoding="utf-8") as f:
    holiday_info = json.loads(f.read())
    this_year = datetime.now().year
    holidays = holiday_info["Years"][str(this_year)]
    comp_days = [] # 调休
    rest_days = [] # 休息
    for holiday in holidays:
        comp_days += holiday["CompDays"]
        rest_days += get_dates_between(holiday["StartDate"], holiday["EndDate"])

logger.info(f"{this_year} has comp_days: {", ".join(comp_days)}")
logger.info(f"{this_year} has rest_days: {", ".join(rest_days)}")
def isTodayWorkingDay():
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    if today.weekday() >= 5: # 周末
        return today_str in comp_days
    else: # 工作日
        return today_str not in rest_days

# 午餐提醒
@scheduler.scheduled_job("cron", hour=12, minute=0, misfire_grace_time=60)
async def time_for_lunch():
    if isTodayWorkingDay():
        await eating_manager.do_greeting(Meals.LUNCH)

# 下午茶/摸鱼提醒
@scheduler.scheduled_job("cron", hour=15, minute=0, misfire_grace_time=60)
async def time_for_snack():
    if isTodayWorkingDay():
        await eating_manager.do_greeting(Meals.SNACK)

# 晚餐提醒
@scheduler.scheduled_job("cron", hour=18, minute=0, misfire_grace_time=60)
async def time_for_dinner():
    if isTodayWorkingDay():
        await eating_manager.do_greeting(Meals.DINNER)

# 夜宵提醒
@scheduler.scheduled_job("cron", hour=22, minute=0, misfire_grace_time=60)
async def time_for_midnight():
    if isTodayWorkingDay():
        await eating_manager.do_greeting(Meals.MIDNIGHT)
