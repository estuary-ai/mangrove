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
        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            text='Opening up the %s panel' % panel
        else:
            text='Closing the %s panel' % panel

        cmd = { 'target': panel, 'action': 'set', 'additionalInfo': [switch_] }

        dispatcher.utter_message(text=text, custom=cmd)

        return [Restarted()]

class ActionNavigation(Action):

    def name(self) -> Text:
        return 'action_navigation'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            text='Opening up the navigation menu for you'
        else:
            text='Closing the navigation menu for you'

        cmd = { 'target': 'Navigation', 'action': 'set', 'additionalInfo': [switch_] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionShortRangeNavigation(Action):

    def name(self) -> Text:
        return 'action_short_range_navigation'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            text='Showing short range navigation markers'
        else:
            text='Hiding short range navigation markers'

        cmd = { 'target': 'ShortRangeNavigation', 'action': 'set', 'additionalInfo': [switch_] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionShortRangeNavSettings(Action):

    def name(self) -> Text:
        return 'action_short_nav_settings'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            text='Opening up the short range navigation settings'
        else:
            text='Closing the short range navigation settings'

        cmd = { 'target': 'ShortRangeNavigationSettings', 'action': 'set', 'additionalInfo': [switch_] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionMap(Action):
    
    def name(self) -> Text:
        return 'action_map'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            text='Opening up the map for you'
        else:
            text='Closing the map'

        cmd = { 'target': 'Map', 'action': 'set', 'additionalInfo': [switch_] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionAddWaypoint(Action):

    def name(self) -> Text:
        return 'action_add_waypoint'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        waypoint_type = tracker.get_slot('waypoint_type')

        if waypoint_type is None or waypoint_type == 'poi' or waypoint_type != 'warning':
            waypoint_type = 'poi'
            text='Adding a point of interest waypoint'
        else:
            text='Adding a warning waypoint'

        cmd = { 'target': 'Waypoint', 'action': 'add', 'additionalInfo': [waypoint_type] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionRemoveWaypoint(Action):

    def name(self) -> Text:
        return 'action_remove_waypoint'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text='Deleting the waypoint'

        cmd = { 'target': 'Waypoint', 'action': 'remove', 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionUndoWaypoint(Action):

    def name(self) -> Text:
        return 'action_undo_waypoint'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text='Undoing last waypoint'

        cmd = { 'target': 'Waypoint', 'action': 'undo', 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

    


