#Standard Packages
import json
import os
from typing import Any, Text, Dict, List

#Rasa Packages
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import Restarted

class ActionShowPanel(Action):

    def name(self) -> Text:
        return 'action_show_panel'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        panel = tracker.get_slot('panel')
        switch_ = tracker.get_slot('switch_')
        if switch_ is None:
            switch_ = 'on'
        elif switch_ not in ['on', 'off']:
            panel = switch_
            switch_ = 'on'

        dispatcher.utter_message(text='Opening up the %s panel' % panel, custom={'toggle': True, 'feature': panel, 'switch_': switch_})

        return [Restarted()]

class ActionNavigationText(Action):

    def name(self) -> Text:
        return 'action_navigation_text'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')
        if switch_ is None or switch_ == 'on':
            dispatcher.utter_message(text='Opening up the navigation menu for you')
        else:
            dispatcher.utter_message(text='Closing the navigation menu for you')
        return [Restarted()]

class ActionTerrainText(Action):
    
    def name(self) -> Text:
        return 'action_terrain_text'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')
        if switch_ is None or switch_ == 'on':
            dispatcher.utter_message(text='Showing terrain markers')
        else:
            dispatcher.utter_message(text='Hiding terrain markers')
        return [Restarted()]
