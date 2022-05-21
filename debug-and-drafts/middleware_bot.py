#Simulating how the frontend can speak to the Rasa server directly by loading the model
import sys
sys.path.insert(1, '../')
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


import asyncio
from flask import Flask, request
from BotController import BotController

app = Flask(__name__)

if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

bot = BotController(model_path='../models/rasa-model/model.tar.gz')

@app.route("/", methods=["POST"])
def sendUserMessage():

    user_message = request.values.get('Body')
    # conversation_id = request.values.get('From')
    if user_message == 'stop':
        return "End"

    bot_res = bot.send_user_message(user_message)
    print("EVA:", bot_res)
    return bot_res

if __name__ == '__main__':
    app.run()