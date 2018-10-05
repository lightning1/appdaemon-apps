# Variables that need to be tracked globally
users = {
        "Max Mustermann": {
            # notification component (has to be telegram)
            "notify": "notify.telegram_max",
            # list of device_tracker entries that belong to the user
            "tracked_devices": ["device_tracker.max_handy"],
        },
        "Manuela Musterfrau": {
            "notify": "notify.telegram_manuela",
            "tracked_devices": ["device_tracker.manuela_handy", "device_tracker.manuela_tablet"],
        },
    }
