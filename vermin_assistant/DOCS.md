# Vermin Assistant

Open the panel from the add-on page or the sidebar. Turn **Active** on when you want the schedule to run. **Play** and **Stop** stay at the bottom and act on the speakers you selected.

## Speakers

The Speakers tab lists media players that can play audio. Select the rooms that should play.

Playback copies the tone into Home Assistant's media folder and asks each speaker to play `media-source://media_source/local/vermin_assistant/deterrent.wav`. The speaker replaces what it was playing for that pass. Volume is set first on players that accept a volume change.

## Schedule

- **Hours** plays from the start hour until the end hour. 8:00 PM until 7:00 AM continues overnight. The same hour for both means all day.
- **Away** plays while Home Assistant reports that nobody is home. It uses the home zone when people are set up, then person entities, then device trackers. If the home is not tracked yet, away mode stays off.
- **Both** plays only while the clock is inside the hours and nobody is home.

While the schedule is on, the hour-long tone repeats by itself. A failed pass waits two minutes, then tries again.

## Sound

The tone is an hour of chirps and pops aimed at the upper hearing range of the animals you turn on. It repeats when the hour ends. Mouse is 92 kHz, rat 76 kHz, cockroach 3 kHz, cricket 100 kHz, mosquito 2 kHz, and moth 80 kHz. A speaker plays up to the highest tone that speaker can make. Demo plays the same chirps on this computer.

Keep the volume modest. Dogs, cats, and pet rodents can hear these frequencies, and some people can too. The tone is not a promise that pests will leave.

The YouTube recording "Mouse & Rat Ultrasonic Deterrent" is not included.

## Requirements

The add-on needs access to the Home Assistant API and write access to the media folder. Both are set in the add-on configuration. Home Assistant 2024.11 or newer is required.
