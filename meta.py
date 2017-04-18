from slackclient import SlackClient
from os import environ, getenv
from urllib import request
from random import choice
from time import sleep
import json


def get_channels(only_names=False):
    channels = client.api_call("channels.list", token=DEBUG_TOKEN)
    if only_names:
        names = []
        for i in channels["channels"]:
            if not i["is_archived"]:
                names.append(i["name"], i["id"])
        return names
    return channels


def get_channel_id(name):
    channels = get_channels()
    for i in channels["channels"]:
        if i["name"] == name:
            return i["id"]
    return None


def get_users(only_names=False):
    users = client.api_call("users.list", token=DEBUG_TOKEN)
    if only_names:
        names = []
        for i in users["members"]:
            names.append(i["name"])
        return names
    return users


def get_admins():
    users = get_users()
    names = []
    for i in users["members"]:
        if i["is_admin"]:
            names.append(i["name"])
    return names


def get_user_id(name):
    users = get_users()
    for i in users["members"]:
        if i["name"] == name:
            return i["id"]
    return None


def get_user_name(id):
    users = get_users()
    for i in users["members"]:
        if i["id"] == id:
            return i["name"]
    return None


def welcome_user(id, channel):
    name = get_user_name(id)
    client.api_call("chat.postMessage", channel=channel, text=choice(DEFAULT["greetings"]).replace("<N>", name), as_user=True)
    client.api_call("chat.postMessage", channel=id, text=DEFAULT["intro"][0].replace("<N>", name).replace("<A>", "@"+", @".join(get_admins()[:-1])+" &amp; @" + get_admins(True)[-1]), as_user=True)


def studio_update(force_print=False):
    update = json.loads(bytes.decode(request.urlopen("http://gmapi.gnysek.pl/version/gm2ide").read()))
    version = update["gm2ide"]["version"]
    days_ago = update["gm2ide"]["daysAgo"]

    if days_ago == 0 or force_print:
        rss = bytes.decode(request.urlopen("http://gms.yoyogames.com/update-win.rss").read())
        rss = rss[rss.rfind("<item>") : rss.rfind("</item>")+7]
        download = rss[rss.find("<link>")+6 : rss.find("</link>")]
        description = rss[rss.find("<description>")+13 : rss.find("</description>")].replace("&lt;p&gt;", "").replace("&lt;/p&gt;", "")
        attachments = [
            {
                "fallback": "Gamemaker Studio 2 has been updated to version " + version + ": http://gms.yoyogames.com/ReleaseNotes.html",
                "pretext": choice(DEFAULT["update2"]),
                "title": "Version " + version,
                "text": "Gamemaker Studio 2 has been updated to <http://gms.yoyogames.com/ReleaseNotes.html|version " + version + ">!",
                "fields": [
                    {
                        "title": "Release Notes",
                        "value": description
                    },
                    {
                        "title": "Download",
                        "value": download
                    }
                ],
                "color": "#039E5C"
            }
        ]

        client.api_call("chat.postMessage", as_user=True, channel=get_channel_id("gms2"), text="", attachments=json.dumps(attachments))
        print("gms2 has updated to version " + version + "\n")
    else:
        print("No updates found for gms2\n")


def parse_slack_output(slack_rtm_output):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output["type"] == "message":
                # Normal message responses
                if "text" in output and "channel" in output:
                    if output["channel"][0] == "D" and output["user"] != BOT_ID:
                        # Direct message to bot
                        return output["text"].lower().strip(), output["channel"], output["user"]

                    elif output["channel"][0] == "C":
                        # Message in a group chat
                        if output["text"].startswith(BOT_NAME):
                            return output["text"].split(BOT_NAME)[1].lower().strip(), output["channel"], output["user"]
                        elif output["text"].startswith("meta"):
                            return output["text"].lower().strip(), output["channel"], output["user"]

            elif output["type"] == "channel_join" or ("subtype" in output and output["subtype"] == "channel_join"):
                # New user joins
                client.api_call("chat.postMessage", channel=get_user_id("rilin"), text="New user: " + output["user"], as_user=True)
                if output["channel"] == get_channel_id("lounge"):
                    welcome_user(output["user"], output["channel"])


    return None, None, None


def handle_command(command, channel, caller):
    response = choice(DEFAULT["unsure"])
    client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)


if __name__ == "__main__":
    HOSTED = int(getenv("SLACK_HOSTED", 0))
    BOT_ID = environ["SLACK_BOT_ID"]
    BOT_NAME = "<@" + str(BOT_ID) + ">"

    DEBUG_TOKEN = environ["SLACK_TEST_TOKEN"]
    WEBSOCKET_DELAY = .5

    client = SlackClient(environ["SLACK_BOT_TOKEN"])

    with open("data/defaultresponses.json") as data_file:
        DEFAULT = json.load(data_file)

    if client.rtm_connect():
        print("\n----- BOT STARTING -----")

        if HOSTED:
            client.api_call("chat.postMessage", channel=get_user_id("rilin"), text="Starting...", as_user=True)

        studio_update()

        while True:
            command, channel, caller = parse_slack_output(client.rtm_read())
            if command and channel:
                print(channel, caller, command)
                handle_command(command, channel, caller)
            sleep(WEBSOCKET_DELAY)

    else:
        print("Connection failed. Invalid Slack token or bot ID?")