"""
Sorts channels in the given sections based on activity
When channels have equal activity, they are one currently higher will remain higher
"""
import time

from channel import Channel
from settings import Settings

required_modules = {"channel_activity", "channel_order_information"}
Settings.load_settings({"channel_sorting", "channel_freeze"})
settings = Settings.settings


def init(ts, db):

    # Calculate the total activity including the successors for all sub-channels if applicable
    def get_sorting_activity(self, db):
        if not hasattr(self, "sorting_activity"):
            current_time = int(time.time())
            hour = int(current_time / 60 / 60)
            min_hour = hour - settings["channel_sorting"]["hours_to_consider"]

            self.sorting_activity = self.get_activity(min_hour, db)

            if settings["channel_sorting"]["include_subchannel_activity"]:
                for successor in self.successors:
                    self.sorting_activity += successor.get_activity(min_hour, db)

        return self.sorting_activity

    setattr(Channel, "get_sorting_activity", get_sorting_activity)


def execute(ts, db):
    for section_cid in settings["channel_sorting"]["sections_to_sort"]:
        sort_section(section_cid, ts, db)


# Sorts a section's sub-channels
def sort_section(section_cid, ts, db):
    frozen_channels = settings["channel_freeze"]  # Channel IDs

    section = Channel.channels[section_cid]

    # If there are no children to sort, get out of here
    if len(section.children) <= 0:
        return

    # Find all channels to sort, so exclude any potential frozen channels
    sort_channels = {channel for channel in section.children if channel.cid not in frozen_channels}

    # Actually sort them based on the total_activity field
    sorted_channels = sorted(sort_channels,
                             key=lambda channel: (channel.get_sorting_activity(db), -channel.pos_in_section),
                             reverse=True)

    # Find the bottom frozen channel if applicable and mark it as the channel that will be above the highest sorted one
    above = None
    channel = next(iter(section.children))  # Start at any channel
    while channel.below is not None:        # Go all the way down
        channel = channel.below
    while channel is not None:        # Go up until a frozen channel is found
        if channel.cid in frozen_channels:
            above = channel                 # Mark that this channel should be above all other sorted channels
            break
        channel = channel.above

    # If a channel is not under the right channel, move it there
    for channel in sorted_channels:
        if channel.above != above:
            if above is None:
                order = 0
            else:
                order = above.cid
            channel.edit_channel({"channel_order": order}, ts, db)
        above = channel
