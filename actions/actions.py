#Standard Packages
from typing import Any, Text, Dict, List

#Rasa Packages
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import Restarted

class ActionSampleTagging(Action):

    def name(self) -> Text:
        return "action_sample_tagging"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sample_details = {
            'Sample Details': {
                "Lighting Conditions": tracker.get_slot("lighting_conditions"),
                "Outcrop Appearance": tracker.get_slot("outcrop_appearance"),
                "Mechanism Used": tracker.get_slot("mechanism_used"),
                "Size and Shape": tracker.get_slot("size_and_shape"),
                "Sample Appearance": tracker.get_slot("sample_appearance"),
                "Geological Interpretation": tracker.get_slot("geo_interpretation")
            }
        }

        dispatcher.utter_message(response="utter_sample_tagged")
        dispatcher.utter_message(custom=sample_details)
        return []