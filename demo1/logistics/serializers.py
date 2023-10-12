import datetime
import json

import dateutil.parser
import pandas as pd
from django.utils import timezone
from rest_framework import serializers

from .models import DeliverySlot


class DeliverySlotSerializer(serializers.ModelSerializer):
    available_slots = serializers.SerializerMethodField()
    nextDate = serializers.SerializerMethodField()
    response_next_date = timezone.now()

    def get_available_slots(self, obj):
        start_date = timezone.now()

        next_date = self.context["request"].query_params.get("nextDate")
        no_printer = self.context["request"].query_params.get("no_printer") == "true"

        start_hour = datetime.time(9)
        end_hour = datetime.time(15)
        numdays = 30
        date_list = []
        day_indices = obj.day_indices()
        iteration = 0

        if next_date:
            # if receive date from api, then consider that date as a start date #
            start_date = dateutil.parser.parse(next_date).replace(hour=9)

        # if start_date is today date then check for hours #
        if start_date.date() == timezone.now().date():
            # if current hour is more then or equal to 14, then consider next day #
            if start_date.hour >= (end_hour.hour - 1):
                start_date = (start_date + datetime.timedelta(days=1)).replace(
                    hour=start_hour.hour, minute=0, second=0
                )
            else:
                # consider next hour as a start hour for today date #
                start_date = (start_date + datetime.timedelta(hours=1)).replace(
                    minute=0, second=0
                )

        if len(day_indices) == 0:
            return []

        # generate a time range for the next 30 days for every hour #
        time_range = pd.date_range(
            start_date,
            (start_date + datetime.timedelta(days=7)).replace(hour=23, minute=0),
            freq="H",
        )

        # convert time range into the data frame #
        date_list_df = pd.DataFrame(time_range)

        # rename the column to start, so when we have to generate JSON we don't need to change anything #
        date_list_df.rename(columns={0: "start"}, inplace=True)

        # added end column with +1 hour in start column hour #
        date_list_df["end"] = date_list_df["start"] + pd.Timedelta(hours=1)

        # added weekday column for layoff days as per the selection #
        date_list_df["weekday"] = date_list_df["start"].dt.dayofweek

        # consider only those weekdays which are selected for the service #
        date_list_df = date_list_df[(date_list_df["weekday"].isin(day_indices))]

        # consider hours from start hour to end hour #
        date_list_df = date_list_df[
            (date_list_df["start"].dt.hour >= start_hour.hour)
            & (date_list_df["start"].dt.hour < end_hour.hour)
        ]

        # convert the date to the desired format #
        date_list_df["start"] = date_list_df["start"].apply(
            lambda end_date: end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        date_list_df["end"] = date_list_df["end"].apply(
            lambda end_date: end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )

        # added for match keys of previous output #
        date_list_df["last"] = date_list_df["end"]

        # drop columns that are not required for output #
        date_list_df.drop(columns=["weekday"], axis=1, inplace=True)

        # convert data frame into the JSON #
        date_list = date_list_df.to_json(orient="records")

        self.response_next_date = (start_date + datetime.timedelta(days=8)).date()

        return json.loads(date_list)

    def get_nextDate(self, obj):
        return self.response_next_date

    class Meta:
        model = DeliverySlot
        fields = ["id", "available_slots", "nextDate"]
