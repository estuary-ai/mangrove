- Show/Hide panels:
    ```
    {
        target: 'Panel',
        action: 'set',
        additionalInfo: [
            panel (vitals/suit/spectrometry/warnings/cautions),
            switch (on/off)
        ]
    }
    ```
    - if switch == 'on' then show 'panel' panel
    - if switch == 'off' then hide 'panel' panel

- Show/Hide Long-Distance Navigation (3D map):
    ```
    {
        target: 'Navigation',
        action: 'set',
        additionalInfo: [
            switch (on/off)
        ]
    }
    ```
    - if switch == 'on' then show long-range navigation
    - if switch == 'off' then hide long-range navigation

- Enable/Disable short-range navigation (terrain markers)
    ```
    {
        target: 'ShortRangeNavigation',
        action: 'set',
        additionalInfo: [
            switch (on/off)
        ]
    }
    ```
    - if switch == 'on' then show short-range navigation
    - if switch == 'off' then hide short-range navigation

- Open/Close short-range navigation settings
    ```
    {
        target: 'ShortRangeNavigationSettings',
        action: 'set',
        additionalInfo: [
            switch (on/off)
        ]
    }
    ```
    - if switch == 'on' then show short-range navigation settings
    - if switch == 'off' then hide short-range navigation settings

- Navigate to a point
    ```
    {
        target: 'Navigation',
        action: 'navigate',
        additionalInfo: [
            point (home/closest/a/b/c/d/e/f/g/h/i/j)
        ]
    }
    ```
    - if point == 'home' then show trail to starting position
    - if point == 'closest' then show trail to closest point of interest
    - if point == 'a'/'b'/.../'j' then show trail to that particular point of interest

- Add Waypoint
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

- Remove Waypoint/Undo placing last Waypoint
    ```
    {
        target: 'Waypoint',
        action: 'remove',
        additionalInfo: [
            selection_type (selected/last)
        ]
    }
    ```
    - if selection_type == 'selected' remove the waypoint pointed to on the map
    - if selection_type == 'last' remove the latest placed waypoint (i.e. undo placing waypoint)

... more to come
