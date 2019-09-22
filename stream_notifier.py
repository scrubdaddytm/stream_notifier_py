import boto3
import json
import os
import requests
from botocore.exceptions import ClientError


TWITCH_CLIENT_ID = os.environ["CLIENT_ID"]
TWITCH_USER_ID = os.environ["TWITCH_USER_ID"]
SLACK_AUTH_TOKEN = os.environ["SLACK_AUTH_TOKEN"]
SLACK_CHANNEL_NAME = os.environ["SLACK_CHANNEL_NAME"]


def handler(event, context):
    dynamodb = boto3.resource("dynamodb")

    streamer_ids = get_followee_ids(TWITCH_USER_ID)
    live_streams = get_live_streams(streamer_ids)

    for stream in live_streams:
        last_stream_id = get_last_stream_id(
            dynamodb,
            stream["user_id"],
        )

        if last_stream_id != stream["id"]:
            notify_slack_stream_started(
                stream,
            )
            update_last_stream_id(
                dynamodb,
                stream["user_id"],
                stream["id"],
            )


def get_last_stream_id(
    dynamodb,
    twitch_user_id,
):
    stream_cache = dynamodb.Table("stream_cache")
    user_last_stream_id = stream_cache.get_item(
        Key={
            "user_id": twitch_user_id,
        },
    )
    if user_last_stream_id.get("Item"):
        return user_last_stream_id["Item"]["last_stream_id"]
    return None


def update_last_stream_id(
    dynamodb,
    twitch_user_id,
    stream_id,
):
    stream_cache = dynamodb.Table("stream_cache")
    stream_cache.put_item(
        Item={
            "user_id": twitch_user_id,
            "last_stream_id": stream_id,
        },
    )


def get_followee_ids(
    twitch_user_id,
):
    follow_relationships = twitch_get(
        "https://api.twitch.tv/helix/users/follows",
        params={
            "from_id": twitch_user_id,
        },
    )
    return [
        follow["to_id"]
        for follow
        in follow_relationships
    ]


def get_live_streams(
    streamer_ids,
):
    streams = twitch_get(
        "https://api.twitch.tv/helix/streams",
        params=[
            ("user_id", user_id)
            for user_id
            in streamer_ids
        ],
    )
    for stream in streams:
        stream["game"] = get_game(stream["game_id"])
        stream["streamer"] = get_user(stream["user_id"])
    return streams


def get_game(
    game_id,
):
    game = twitch_get(
        "https://api.twitch.tv/helix/games",
        params={
            "id": game_id,
        },
    )[0]
    game['box_art_url'] = game['box_art_url'].format(
        width=192,
        height=256,
    )
    return game


def get_user(
    user_id,
):
    return twitch_get(
        "https://api.twitch.tv/helix/users",
        params={
            "id": user_id,
        },
    )[0]


def twitch_get(
    url,
    params,
):
    req = requests.get(
        url,
        headers={
            "Client-ID": TWITCH_CLIENT_ID,
        },
        params=params,
    )
    if req.status_code == 200:
        return req.json()["data"]
    req.raise_for_status()


def notify_slack_stream_started(
    stream,
):
    message_data={
        "channel": SLACK_CHANNEL_NAME,
        "attachments": [
            {
                "pretext": "I'm streaming!",
                "title": "twitch.tv/{}".format(stream["user_name"]),
                "title_link": "https://www.twitch.tv/{}".format(stream["user_name"]),
                "text": "{} : {}".format(
                    stream["game"]["name"],
                    stream["title"],
                ),
                "image_url": stream["game"]["box_art_url"],
            },
        ],
        "icon_url": stream["streamer"]["profile_image_url"],
        "username": stream["streamer"]["display_name"],
    }
    req = requests.post(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(message_data),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer " + SLACK_AUTH_TOKEN,
        }
    )
    if req.status_code != 200:
        req.raise_for_status()
