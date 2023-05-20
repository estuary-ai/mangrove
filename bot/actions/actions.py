#Standard Packages
import json
import os
from typing import Any, Text, Dict, List

#Rasa Packages
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import Restarted, SlotSet

class ActionErrorMessage(Action):

    def name(self) -> Text:
        return 'action_error_message'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text='Sorry I did not get that', custom={ 'target': 'Error', 'additionalInfo': [] })

        return [Restarted()]


class ActionEvaTime(Action):

    def name(self) -> Text:
        return 'action_eva_time'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        cmd = { 'target': 'Time', 'action': 'open', 'additionalInfo': [] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]


class ActionPanelFollow(Action):

    def name(self) -> Text:
        return 'action_panel_follow'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            action = 'follow'
        else:
            action = 'unfollow'

        cmd = { 'target': 'Panel', 'action': action, 'additionalInfo': ['eye'] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]


class ActionClosePanel(Action):

    def name(self) -> Text:
        return 'action_close_panel'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        text='Closing the panel'

        cmd = { 'target': 'Panel', 'action': 'close', 'additionalInfo': ['eye'] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionShowPanel(Action):

    def name(self) -> Text:
        return 'action_show_panel'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        panel = tracker.get_slot('panel')
        if panel not in [ 'vitals','suit','spectrometry','warnings','cautions','tss','ai' ]:
            return ActionErrorMessage().run(dispatcher, tracker, domain)

        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            action = 'open'
            text='Opening up the %s panel' % panel
        else:
            action = 'close'
            text='Closing the %s panel' % panel

        cmd = { 'target': 'Panel', 'action': action, 'additionalInfo': [panel] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionNavigation(Action):

    def name(self) -> Text:
        return 'action_show_navigation'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            action = 'open'
            text='Opening up the long range navigation menu for you'
        else:
            action = 'close'
            text='Closing the long range navigation menu for you'

        cmd = { 'target': 'LongRangeNavigation', 'action': action, 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionShortRangeNavigation(Action):

    def name(self) -> Text:
        return 'action_short_range_navigation'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            action = 'enable'
            text='Showing short range navigation markers'
        else:
            action = 'disable'
            text='Hiding short range navigation markers'

        cmd = { 'target': 'ShortRangeNavigation', 'action': action, 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionShortRangeNavSettings(Action):

    def name(self) -> Text:
        return 'action_short_nav_settings'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            action = 'open'
            text='Opening up the short range navigation settings'
        else:
            action = 'close'
            text='Closing the short range navigation settings'

        cmd = { 'target': 'ShortRangeNavigation', 'action': action, 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionNavigate(Action):

    def name(self) -> Text:
        return 'action_navigate'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        point = tracker.get_slot('nav_target')

        if point is None or point == 'home':
            point = 'home'
            text = 'Calculating path back home'
        elif point == 'closest':
            text = 'Calculating path to the closest point'
        else:
            text = 'Calculating path to point %s' % point

        cmd = { 'target': 'Breadcrumb', 'action': 'navigate', 'additionalInfo': [point] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionShowBreadcrumbs(Action):

    def name(self) -> Text:
        return 'action_show_breadcrumbs'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            action = 'show'
            text='Displaying the breadcrumb trail'
        else:
            action = 'hide'
            text='Hiding the breadcrumb trail'

        cmd = { 'target': 'Breadcrumb', 'action': action, 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionNextSpectrometryGraph(Action):

    def name(self) -> Text:
        return 'action_next_spectrometry_graph'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        text = 'Switching to next spectrometry sample'

        cmd = { 'target': 'Spectrometry', 'action': 'next_graph', 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionAddWaypoint(Action):

    def name(self) -> Text:
        return 'action_add_waypoint'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        waypoint_type = tracker.get_slot('waypoint_type')

        if waypoint_type is None or waypoint_type == 'poi' or waypoint_type != 'hazard':
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

        cmd = { 'target': 'Waypoint', 'action': 'remove', 'additionalInfo': ['eye'] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionUndoWaypoint(Action):

    def name(self) -> Text:
        return 'action_undo_waypoint'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text='Undoing last waypoint'

        cmd = { 'target': 'Waypoint', 'action': 'remove', 'additionalInfo': ['last'] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionClearAllWaypoints(Action):

    def name(self) -> Text:
        return 'action_clear_all_waypoints'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text='Clearing all waypoints'

        cmd = { 'target': 'Waypoint', 'action': 'remove', 'additionalInfo': ['all'] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]

class ActionShowWaypoints(Action):
    
    def name(self) -> Text:
        return 'action_show_waypoints'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        switch_ = tracker.get_slot('switch_')

        if switch_ is None or switch_ == 'on' or switch_ != 'off':
            switch_ = 'on'
            action = 'show'
            text='Displaying waypoints'
        else:
            action = 'hide'
            text='Hiding waypoints'

        cmd = { 'target': 'Waypoint', 'action': action, 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionRoverGoTo(Action):

    def name(self) -> Text:
        return 'action_rover_go_to'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        vitals_type = tracker.get_intent_of_latest_message()[5:]

        cmd = { 'target': 'Vitals', 'action': 'distract', 'additionalInfo': [vitals_type] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]


class ActionRoverNavigate(Action):

    def name(self) -> Text:
        return 'action_rover_navigate'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        intent_type = tracker.get_intent_of_latest_message()[6:]

        if intent_type == 'come_back':
            text = 'Bringing rover back to you'
            target_dest = 'home'
        elif intent_type == 'go_to':
            target_dest = tracker.get_slot('nav_target')
            text = 'finding route to playstation location %s' % target_dest

        cmd = { 'Rover': 'Vitals', 'action': 'navigate', 'additionalInfo': [target_dest] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]


class ActionReadVitals(Action):

    def name(self) -> Text:
        return 'action_read_vitals'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        vitals_type = tracker.get_intent_of_latest_message()[5:]

        cmd = { 'target': 'Vitals', 'action': 'read', 'additionalInfo': [vitals_type] }

        dispatcher.utter_message(custom=cmd)
        return [Restarted()]


class ActionCalibrateCompass(Action):

    def name(self) -> Text:
        return 'action_calibrate_compass'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        text = 'Calibrating compass using GPS'

        cmd = { 'target': 'LongRangeNavigation', 'action': 'compass', 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]


class ActionSetNorth(Action):

    def name(self) -> Text:
        return 'action_set_north'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        text = 'Manually setting true North'

        cmd = { 'target': 'LongRangeNavigation', 'action': 'north', 'additionalInfo': [] }

        dispatcher.utter_message(text=text, custom=cmd)
        return [Restarted()]
