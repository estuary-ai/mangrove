#Standard Packages
from typing import Any, Text, Dict, List

#Rasa Packages
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import Restarted


# class ActionHelloWorld(Action):

#     def name(self) -> Text:
#         return "action_greet"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

#         dispatcher.utter_message(text="Hello World!")

#         return [Restarted()]

# # class ActionRestart(Action):

# #     def name(self) -> Text:
# #         return "action_restart"

# #     def run(self, dispatcher: CollectingDispatcher,
# #             tracker: Tracker,
# #             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
# #         return [Restarted()]