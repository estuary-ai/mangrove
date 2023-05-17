#Standard Packages
import json
import os
from typing import Any, Text, Dict, List

#Rasa Packages
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import Restarted

class ActionStartEgress(Action):

    def name(self) -> Text:
        return 'action_start_egress'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        text = 'Starting egress procedure checklist'

        cmd = { 'target': 'UIA', 'action': 'start', 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionCurrentEgressStepNumber(Action):

    def name(self) -> Text:
        return 'action_current_egress_step_number'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        cmd = { 'target': 'UIA', 'action': 'current_step_number', 'additionalInfo': [] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]

class ActionCurrentEgressStep(Action):

    def name(self) -> Text:
        return 'action_current_egress_step'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        cmd = { 'target': 'UIA', 'action': 'current_step', 'additionalInfo': [] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]

class ActionNextEgressStep(Action):

    def name(self) -> Text:
        return 'action_next_egress_step'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        cmd = { 'target': 'UIA', 'action': 'next_step', 'additionalInfo': [] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]

class ActionExitEgress(Action):

    def name(self) -> Text:
        return 'action_exit_egress'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        text = 'Closing egress procedure checklist'

        cmd = { 'target': 'UIA', 'action': 'exit', 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionConfirmEgressCompletion(Action):

    def name(self) -> Text:
        return 'action_confirm_egress_completion'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        cmd = { 'target': 'UIA', 'action': 'confirm_completion', 'additionalInfo': [] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]
