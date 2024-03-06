from bot import BotController

from langchain.globals import set_debug

set_debug(True)

bot = BotController()


while True:
    input_msg = input("User: ")
    if input_msg == "exit" or input_msg == "quit" or input_msg == "q":
        break
    print("Bot: ", end="")
    print(list(bot.respond(input_msg))[-1]['text'][0])
