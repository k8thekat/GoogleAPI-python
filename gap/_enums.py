from enum import IntEnum, StrEnum


class MailFormatEnum(StrEnum):
    minimal = "minimal"
    full = "full"
    raw = "raw"
    metadata = "metadata"


class MailMessageListVisibilityEnum(StrEnum):
    show = "show"
    hide = "hide"


class MailLabelListVisiblityEnum(StrEnum):
    label_show = "labelShow"
    label_show_if_unread = "labelShowIfUnread"
    label_hide = "labelHide"


class MailTypeEnum(StrEnum):
    """
    Enums
    ------
    system: str
        Labels created by Gmail.
    user: str
        Custom labels created by the user or application.

    """

    system = "system"
    user = "user"


class MailLabelColorEnum(StrEnum):
    black = "#000000"
    gray60 = "#999999"
    light_green = "#89d3b2"
    green = "#094228"
    white = "#ffffff"
    pumpkin_orange = "#aa8831"
    light_blue = "#6d9eeb"
