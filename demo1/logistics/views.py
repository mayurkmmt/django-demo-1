import datetime
import json

import dateutil.parser
import pandas as pd
from django.db.models import Q
from django.db.models.functions import Length
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeliverySlot
from .serializers import DeliverySlotSerializer


class DeliverySlotView(viewsets.ReadOnlyModelViewSet):
    queryset = DeliverySlot.objects.all()
    serializer_class = DeliverySlotSerializer

    def get_queryset(self):
        """Optionally restrict the returned slots by by filtering against a
        `postal_code` query parameter in the URL.

        """
        queryset = self.queryset
        postal_code = self.request.query_params.get("postal_code")

        if postal_code is not None:
            postal_code = postal_code.replace(" ", "").replace("-", "")
            queryset = (
                queryset.annotate(
                    start_len=Length("postal_code_range_start"),
                    end_len=Length("postal_code_range_end"),
                )
                .filter(
                    start_len=len(postal_code),
                    end_len__in=(0, len(postal_code)),
                )
                .filter(
                    Q(
                        postal_code_range_start__lte=postal_code,
                        postal_code_range_end__gte=postal_code,
                    )
                    | Q(postal_code_range_start=postal_code)
                )
            )
        return queryset


class PickupSlotView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            next_date = self.request.query_params.get("nextDate")

            start_hour = datetime.time(9)
            end_hour = datetime.time(15)
            start_date = timezone.now()

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

            time_range = pd.date_range(
                start_date, start_date.replace(hour=23, minute=0), freq="H"
            )

            # convert time range into the data frame #
            date_list_df = pd.DataFrame(time_range)

            # rename the column to start, so when we have to generate JSON we don't need to change anything #
            date_list_df.rename(columns={0: "start"}, inplace=True)

            # added end column with +1 hour in start column hour #
            date_list_df["end"] = date_list_df["start"] + pd.Timedelta(hours=1)

            # consider hours from start hour to end hour #
            date_list_df = date_list_df[
                (date_list_df["start"].dt.hour >= start_hour.hour)
                & (date_list_df["start"].dt.hour <= end_hour.hour)
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

            # convert data frame into the JSON #
            date_list = date_list_df.to_json(orient="records")

            response = {
                "nextDate": (start_date + datetime.timedelta(days=1)).date(),
                "availableSlots": json.loads(date_list),
            }

            return Response(status=status.HTTP_200_OK, data=response)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
