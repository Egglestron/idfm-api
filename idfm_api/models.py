from dataclasses import dataclass
from datetime import datetime, timezone
from functools import total_ordering
from enum import Enum, unique

@unique
class TransportType(str, Enum):
    """
    Represents the type of transport
    """
    METRO = "metro"
    TRAM = "tram"
    TRAIN = "rail"
    BUS = "bus"

@dataclass(frozen=True)
class LineData:
    """
    Represents a line of a transport
    """
    name: str
    id: str
    type: TransportType

@dataclass(frozen=True)
class StopData:
    """
    Represents a stop area of a line
    """
    name: str
    id: str
    x: float
    y: float
    zip_code: str
    city: str

    @staticmethod
    def from_json(data: dict):
        return StopData(name=data.get("name"), id=data.get("stop_id"), x=data.get("x"), y=data.get("y"), zip_code=data.get("zipCode"), city=data.get("city"))

@dataclass(frozen=True)
class InfoData:
    """
    Represents a traffic information fragment
    """
    id: str
    name: str
    message: str
    start_time: datetime
    end_time: datetime
    severity: int
    type: str

    @staticmethod
    def from_json(data: dict):
        name = ""
        message = ""
        if "Message" in data["Content"]:
            for i in data["Content"]["Message"]:
                if "MessageType" in i:
                    if i["MessageType"] == "TEXT_ONLY":
                        message = i["MessageText"]["value"]
                    if i["MessageType"] == "SHORT_MESSAGE":
                        name = i["MessageText"]["value"]

        return InfoData(
            name=name,
            id=data.get("id"),
            message=message,
            start_time=datetime.strptime(data.get("RecordedAtTime"), '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc),
            end_time=datetime.strptime(data.get("ValidUntilTime"), '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc),
            type=data["InfoChannelRef"]["value"],
            severity=data.get("InfoMessageVersion")
        )

@dataclass(frozen=True)
@total_ordering
class TrafficData:
    """
    Represents a schedule for a specific path
    """
    line_id: str
    note: str
    destination_name: str
    destination_id: str
    direction: str
    schedule: datetime
    retarted: bool
    at_stop: bool
    platform: str
    status: str

    @staticmethod
    def from_json(data: dict):
        try:
            dir = data["MonitoredVehicleJourney"]["DirectionName"][0]["value"]
        except KeyError:
            dir = data["MonitoredVehicleJourney"]["DestinationName"][0]["value"]

        try:
            note = data["MonitoredVehicleJourney"]["JourneyNote"][0]["value"]
        except KeyError:
            note = ""

        sch = None
        if "ExpectedArrivalTime" in data["MonitoredVehicleJourney"]["MonitoredCall"]:
            sch = datetime.strptime(data["MonitoredVehicleJourney"]["MonitoredCall"]["ExpectedArrivalTime"], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
        elif "ExpectedDepartureTime" in data["MonitoredVehicleJourney"]["MonitoredCall"]:
            sch = datetime.strptime(data["MonitoredVehicleJourney"]["MonitoredCall"]["ExpectedDepartureTime"], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
        else:
            return None

        try:
            atstop = data["MonitoredVehicleJourney"]["MonitoredCall"]["VehicleAtStop"]
        except KeyError:
            atstop = None

        try:
            plat = data["MonitoredVehicleJourney"]["MonitoredCall"]["ArrivalPlatformName"]["value"]
        except KeyError:
            plat = ""

        stat_raw = None
        if "ArrivalStatus" in data["MonitoredVehicleJourney"]["MonitoredCall"]:
            stat_raw = data["MonitoredVehicleJourney"]["MonitoredCall"]["ArrivalStatus"]
        elif "DepartureStatus" in data["MonitoredVehicleJourney"]["MonitoredCall"]:
            stat_raw = data["MonitoredVehicleJourney"]["MonitoredCall"]["DepartureStatus"]
        else:
            stat_raw = ""

        def stat_transform(stat_raw):
            # onTime | missed | arrived | notExpected | delayed | early | cancelled | noReport
            match stat_raw:
                case "onTime":
                    return "On time"
                case "missed":
                    return "Missed"
                case "arrived":
                    return "Arrived"
                case "notExpected":
                    return "Not expected"
                case "delayed":
                    return "Delayed"
                case "early":
                    return "Arrived"
                case "cancelled":
                    return "Cancelled"
                case "noReport":
                    return "No report"
                case _:
                    return "Unknown"

        return TrafficData(
            line_id=data["MonitoredVehicleJourney"]["LineRef"]["value"],
            note=note,
            destination_name=data["MonitoredVehicleJourney"]["DestinationName"][0]["value"],
            destination_id=data["MonitoredVehicleJourney"]["DestinationRef"]["value"],
            direction=dir,
            schedule=sch,
            retarted=data["MonitoredVehicleJourney"]["MonitoredCall"].get("ArrivalStatus") in [None, "onTime"],
            at_stop=atstop,
            platform=plat,
            status=stat_transform(stat_raw)
        )

    def __eq__(self, other):
        if type(other) is TrafficData:
            return self.schedule == other.schedule and self.line_id == other.line_id and self.destination_id == other.destination_id
        else:
            return False

    def __lt__(self, other):
        if type(other) is datetime:
            return self.schedule < other
        elif type(other) is TrafficData:
            return ((self.schedule is None or other.schedule is None) or self.schedule < other.schedule) or ((self.destination_name is None or other.destination_name is None) or self.destination_name < other.destination_name)
        else:
            return NotImplemented
    