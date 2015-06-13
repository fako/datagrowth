from __future__ import unicode_literals, absolute_import, print_function, division

from datetime import date

from core.management.commands.grow_community import Command as GrowCommand
from core.utils.configuration import DecodeConfigAction


class Command(GrowCommand):

    def add_arguments(self, parser):
        parser.add_argument('community', type=unicode, nargs="?", default="WikiNewsCommunity")
        parser.add_argument('-c', '--config', type=unicode, action=DecodeConfigAction, nargs="?", default={})

    def handle_community(self, community, **options):
        community.__class__.objects.all().delete()
        today_at_midnight = (date.today() - date(1970, 1, 1)).total_seconds()
        yesterday_at_midnight = today_at_midnight - 60 * 60 * 24
        community.config = {
            "start_time": yesterday_at_midnight,
            "end_time": today_at_midnight
        }
        super(Command, self).handle_community(community, **options)
