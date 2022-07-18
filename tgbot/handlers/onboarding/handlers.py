import datetime
import json

import requests
from django.utils import timezone
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, Filters

from tgbot.handlers.onboarding import static_text
from tgbot.handlers.utils.info import extract_user_data_from_update
from tgbot.models import User

LEETCODE, FINAL = range(2)


def command_start(update: Update, context: CallbackContext) -> None:
    u, created = User.get_user_and_created(update, context)

    if created:
        text = static_text.start_created.format(first_name=u.first_name)
    else:
        text = static_text.start_not_created.format(first_name=u.first_name)

    update.message.reply_text(
        text=f"{text} \n Leetcode profilizni tashang(username)")
    return LEETCODE


def get_user(update: Update, context: CallbackContext) -> None:
    leetcode_username = update.message.text
    user_id = update.message.from_user.id
    user = User.objects.filter(user_id=user_id)[0]
    try:
        get_profile(leetcode_username)
        user.leetcode_username = leetcode_username
        user.save()
        update.message.reply_text(
            f"your leetcode username {update.message.text}")
    except:
        update.message.reply_text("Bunday account yoq")
    return FINAL


def Me(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user = User.objects.filter(user_id=user_id)[0]
    func_data = get_profile(user.leetcode_username)
    text = ""
    text += f"|   field   |         value           |" \
        f"\n|-------------------------------------|" \
            f"\n| Username  | {func_data['username']} |" \
            f"\n| Ranking   | {func_data['ranking']}  |" \
            f"\n| Points    | {func_data['points']}   |" \
            f"\n| Total     | {func_data['total']}    |" \
            f"\n| Easy      | {func_data['easy']}     |" \
            f"\n| Medium    | {func_data['medium']}   |" \
            f"\n| Hard      | {func_data['hard']}     |" \
 \
        "\n"

    update.message.reply_text(text)


def Top(update: Update, context: CallbackContext) -> None:
    users = User.objects.all()
    text = "| № |    username    |    solved    |    rank    |    rating    |" \
        "\n|-------------------------------------------------------------------------|"

    for i, user in enumerate(users, start=1):
        func_data = get_profile(user.leetcode_username)
        text += f"\n|  {i} |    {func_data['username']}     |     {func_data['total']}     |      {func_data['ranking']}      |      {func_data['easy'] * 1 + func_data['medium'] * 2 + func_data['hard'] * 3}      |"

    update.message.reply_text(text)


def secret_level(update: Update, context: CallbackContext) -> None:
    # callback_data: SECRET_LEVEL_BUTTON variable from manage_data.py
    """ Pressed 'secret_level_button_text' after /start command"""
    user_id = extract_user_data_from_update(update)['user_id']
    text = static_text.unlock_secret_room.format(
        user_count=User.objects.count(),
        active_24=User.objects.filter(
            updated_at__gte=timezone.now() - datetime.timedelta(hours=24)).count()
    )

    context.bot.edit_message_text(
        text=text,
        chat_id=user_id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


BASE_URL = "https://leetcode.com/graphql"

data = {
    "operationName": "getUserProfile",
    "variables": {
        "username": None
    },
    "query": "query getUserProfile($username: String!) {\n  allQuestionsCount {\n    difficulty\n    count\n    __typename\n  }\n  matchedUser(username: $username) {\n    username\n    socialAccounts\n    githubUrl\n    contributions {\n      points\n      questionCount\n      testcaseCount\n      __typename\n    }\n    profile {\n      realName\n      websites\n      countryName\n      skillTags\n      company\n      school\n      starRating\n      aboutMe\n      userAvatar\n      reputation\n      ranking\n      __typename\n    }\n    submissionCalendar\n    submitStats: submitStatsGlobal {\n      acSubmissionNum {\n        difficulty\n        count\n        submissions\n        __typename\n      }\n      totalSubmissionNum {\n        difficulty\n        count\n        submissions\n        __typename\n      }\n      __typename\n    }\n    badges {\n      id\n      displayName\n      icon\n      creationDate\n      __typename\n    }\n    upcomingBadges {\n      name\n      icon\n      __typename\n    }\n    activeBadge {\n      id\n      __typename\n    }\n    __typename\n  }\n}\n"
}

headers = {
    "Content-Type": "application/json"
}


def get_profile(username):
    data['variables']['username'] = username

    response = requests.post(BASE_URL, data=json.dumps(data), headers=headers)
    response_data = response.json()['data']

    user_data = response_data['matchedUser']
    profile = user_data['profile']
    submissions = user_data['submitStats']['acSubmissionNum']

    profile = {
        "username": user_data['username'],
        "points": user_data['contributions']['points'],
        "realName": profile['realName'],
        "ranking": profile['ranking'],
        "total": submissions[0]['count'],
        "easy": submissions[1]['count'],
        "medium": submissions[2]['count'],
        "hard": submissions[3]['count']
    }

    return profile


def final(update: Update, context: CallbackContext) -> None:
    
    update.message.reply_text("Siz registratiyadan o`tgansiz")


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", command_start)],
    states={
        LEETCODE: [MessageHandler(Filters.text, get_user)],
        FINAL: [MessageHandler(Filters.text, final),
                CommandHandler("me", Me),
                CommandHandler("top", Top)],


    },
    fallbacks=[]

)
