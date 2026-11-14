"""Safety content shared by the web app and the bots.

First aid follows widely published public-health guidance for heat illness
(WHO, US CDC/NIOSH, India NDMA heat-wave guidelines). It is not medical advice.
"""

EMERGENCY_NUMBERS = [
    {"number": "108", "label": "Ambulance"},
    {"number": "112", "label": "All emergencies"},
]

SYMPTOM_FLOW = [
    {
        "id": "emergency",
        "question": "Is the person showing any of these?",
        "signs": [
            "Confusion, strange behaviour or slurred speech",
            "Fainting, or cannot be woken",
            "Fits (seizures)",
            "Very hot skin, whether dry or soaked with sweat",
            "Body temperature of 40 °C or more",
        ],
        "result": {
            "title": "This may be heat stroke. It is a medical emergency.",
            "severity": "extreme",
            "call": True,
            "steps": [
                "Call 108 or 112 now. Stay with the person until help arrives.",
                "Move them to shade or a cool room and remove outer clothing.",
                "Cool them fast: pour cool water over the skin and fan them.",
                "Put wet cloths or ice on the neck, armpits and groin.",
                "Do not give anything to drink if they are confused or not fully awake.",
                "If they are unconscious or vomiting, lay them on their side.",
            ],
        },
    },
    {
        "id": "exhaustion",
        "question": "Otherwise, are there any of these?",
        "signs": [
            "Heavy sweating with weakness or tiredness",
            "Dizziness or headache",
            "Nausea or vomiting",
            "Fast pulse or intense thirst",
            "Cool, pale, clammy skin",
        ],
        "result": {
            "title": "This looks like heat exhaustion. Act now so it does not become heat stroke.",
            "severity": "high",
            "call": False,
            "steps": [
                "Stop work and move to shade or a cool place.",
                "Loosen clothing and lie down with the legs slightly raised.",
                "Sip water or ORS slowly.",
                "Cool the skin with wet cloths and a fan.",
                "If not better within 30 minutes, or getting worse, call 108.",
                "Do not go back to work in the heat today.",
            ],
        },
    },
    {
        "id": "mild",
        "question": "Or only milder signs?",
        "signs": [
            "Muscle cramps in the legs, arms or stomach",
            "Prickly heat rash",
            "Thirst and feeling tired",
        ],
        "result": {
            "title": "These are early warning signs. Rest now.",
            "severity": "caution",
            "call": False,
            "steps": [
                "Rest in shade and drink water or ORS.",
                "Gently stretch and massage cramped muscles.",
                "Wait until the cramps have fully stopped before working again.",
                "Get medical help if cramps last more than an hour.",
            ],
        },
    },
]
