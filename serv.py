import asyncio
import config

from environs import Env
from contextlib import suppress
from quart import Quart, request, render_template, jsonify

from cmstore_lib import update_config, decode_message
from notify_rollbar import anotify_rollbar

env = Env()
env.read_env()

app = Quart(__name__)
app.config.from_object(config)


@app.route('/')
async def index():
    return await render_template('index.html')


@app.route('/updateConfig/<name>', methods=['POST'])
@anotify_rollbar()
async def update_config_params(name):
    message = await request.get_data()
    if name == 'introduction':
        decoded_text = await decode_message(message, r'''[^&?text=]+[\w:-]*''')
        if decoded_text:
            await update_config(introduction_text=decoded_text)
    if name == 'startupImage' and message:
        path_to_img = f'{config.STATICFILES_DIRS}/startupImage.png'
        with open(path_to_img, mode='wb') as f:
            f.write(message)
        await update_config(startup_image=path_to_img)

    return jsonify(True)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        asyncio.run(app.run_task(host="0.0.0.0", port=5000))
