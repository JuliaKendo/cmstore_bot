import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
STATICFILES_DIRS = (os.path.join(PROJECT_ROOT, "static"))


def set_bot_variables(bot, env):
    bot.data['use_webhook'] = env.bool('USE_WEBHOOK', True)
    bot.data['webhook_url'] = f"{env.str('WEBHOOK_HOST', '')}{env.str('WEBHOOK_PATH', '')}"
    bot.data['webapp_host'] = env.str('WEBAPP_HOST', '0.0.0.0')
    bot.data['webapp_port'] = env.int('WEBAPP_PORT', 5000)
    bot.data['sms_api_id'] = env.str('SMS_API_ID', '')
    bot.data['1c_url'] = env.str('URL_1C', '')
    bot.data['chat_ids_deleted_messages'] = env.str('CHAT_IDS_DELETED_MESSAGES', '')
    bot.data['insta_bot'] = None
