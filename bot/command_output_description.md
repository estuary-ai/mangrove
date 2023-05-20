- Open EVA time:
    ```
    {
        target: 'Time',
        action: 'open',
        additionalInfo: []
    }
    ```
    - Displays the EVA elapsed time

- Make a panel follow your view:
    ```
    {
        target: 'Panel',
        action: 'follow',
        additionalInfo: [
            switch (on/off)
        ]
    }
    ```
    - if switch == 'on' then set the panel under gaze to follow the user's field of view
    - if switch == 'off' then set the panel under gaze to remain static in the world

- Close panel under observation:
    ```
    {
        target: 'Panel',
        action: 'close',
        additionalInfo: []
    }
    ```
    - close the panel that is pointed to

- Show/Hide panels:
    ```
    {
        target: 'Panel',
        action: (open/close),
        additionalInfo: [
            panel (vitals/suit/spectrometry/warnings/cautions)
        ]
    }
    ```
    - if action == 'open' then show 'panel' panel
    - if action == 'close' then hide 'panel' panel

- Show/Hide Long-Distance Navigation (3D map):
    ```
    {
        target: 'LongRangeNavigation',
        action: (open/close),
        additionalInfo: []
    }
    ```
    - if action == 'open' then show long-range navigation
    - if action == 'close' then hide long-range navigation

- Enable/Disable short-range navigation (terrain markers):
    ```
    {
        target: 'ShortRangeNavigation',
        action: (enable/disable),
        additionalInfo: []
    }
    ```
    - if action == 'enable' then show short-range navigation
    - if action == 'disable' then hide short-range navigation

- Open/Close short-range navigation settings:
    ```
    {
        target: 'ShortRangeNavigation',
        action: (open/close),
        additionalInfo: []
    }
    ```
    - if action == 'open' then show short-range navigation settings
    - if action == 'close' then hide short-range navigation settings

- Navigate to a point:
    ```
    {
        target: 'Breadcrumb',
        action: 'navigate',
        additionalInfo: [
            point (home/closest/a/b/c/d/e/f/g/h/i/j)
        ]
    }
    ```
    - if point == 'home' then show trail to starting position
    - if point == 'closest' then show trail to closest point of interest
    - if point == 'a'/'b'/.../'j' then show trail to that particular point of interest

- Switch to next Spectrometry graph:
    ```
    {
        target: 'Spectrometry',
        action: 'next_graph',
        additionalInfo: []
    }
    ```
    - switch to the next spectrometry sample's graph in the list

- Add Waypoint:
    ```
    {
        target: 'Waypoint',
        action: 'add',
        additionalInfo: [
            waypoint_type (poi/warning)
        ]
    }
    ```
    - if waypoint_type == 'poi' then place a point of interest waypoint at the location pointed to on the map
    - if waypoint_type == 'warning' then place a warning waypoint at the location pointed to on the map

- Remove Waypoint/Undo placing last Waypoint/Clear all Waypoints:
    ```
    {
        target: 'Waypoint',
        action: 'remove',
        additionalInfo: [
            selection_type (selected/last/all)
        ]
    }
    ```
    - if selection_type == 'selected' remove the waypoint pointed to on the map
    - if selection_type == 'last' remove the latest placed waypoint (i.e. undo placing waypoint)
    - if selection_type == 'all' remove all the waypoints

- Show/Hide Waypoints:
    ```
    {
        target: 'Waypoint',
        action: (show/hide),
        additionalInfo: []
    }
    ```
    - if action == 'show' then show waypoints in the field
    - if action == 'hide' then hide waypoints in the field

- Read out Vitals information:
    ```
    {
        target: 'Vitals',
        action: 'read',
        additionalInfo: [
            vitals_type (battery/battery_time/primary_o2/primary_o2_pressure/secondary_o2/secondary_o2_pressure/o2_time/heart_rate/suit_pressure/suit_o2_pressure)
        ]
    }
    ```
    - read value of vitals_type data from the TSS


----

### UIA actions:

- Start egress procedure:
    ```
    {
        target: 'UIA',
        action: 'start',
        additionalInfo: []
    },
    {
        target: 'UIA',
        action: 'open',
        additionalInfo: []
    }
    ```
    - UIA:start denotes that the processes related to the egress procedure guidance should start - vision stream, error checking, etc.
    - UIA:open is a panel open action that informs the UI to open the UIA checklist

- Read current egress step number:
    ```
    {
        target: 'UIA',
        action: 'current_step_number',
        additionalInfo: [
            cur_step_id (ex. '1.2')
        ]
    }
    ```
    - returns the step ID for the current step in the egress procedure

- Read the current egress step:
    ```
    {
        target: 'UIA',
        action: 'current_step',
        additionalInfo: [
            cur_step_id (ex. '1.2'),
            cur_step_target (emu1_pwr_switch/o2_vent_switch/emu1_o2_supply_switch/ev1_water_waste_switch/ev1_supply_switch/depress_pump_switch)
        ]
    }
    ```
    - returns the step ID and the target switch for the current step in the egress procedure

- Read the next egress step:
    ```
    {
        target: 'UIA',
        action: 'next_step',
        additionalInfo: [
            cur_step_id (ex. '1.2'),
            cur_step_target (emu1_pwr_switch/o2_vent_switch/emu1_o2_supply_switch/ev1_water_waste_switch/ev1_supply_switch/depress_pump_switch)
        ]
    }
    ```
    - returns the step ID and the target switch for the next step in the egress procedure
 
- Exit the egress procedure:
    ```
    {
        target: 'UIA',
        action: 'exit',
        additionalInfo: []
    },
    {
        target: 'UIA',
        action: 'close',
        additionalInfo: []
    }
    ```
    - UIA:exit denotes that the processes related to the egress procedure guidance should exit - vision stream, error checking, etc.
    - UIA:open is a panel close action that informs the UI to close the UIA checklist

- Confirm completion of egress steps:
    ```
    {
        target: 'UIA',
        action: 'confirm_completion',
        additionalInfo: [
            state (true/false)
        ]
    }
    ```
    - if state == 'true' then the procedure has been successfully completed
    - if state == 'false' then the procedure is still in progress or was aborted before completion

... more to come
