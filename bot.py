##
# meta, created by @darkrilin
# for the gamemakerdevs slack community
#
##

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


def get_channel_name(id):
    channels = get_channels()
    for i in channels["channels"]:
        if i["id"] == id:
            return i["name"]
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
        if "is_admin" in i:
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


def get_rules():
    # Fetch rules hosted from pastebin
    # TODO: Move these over to something like an amazon S3 instance or a server where I host my own files
    rules = bytes.decode(request.urlopen("https://pastebin.com/raw/Hm5hHjbB").read())
    return rules


def get_joke():
    jokes = bytes.decode(request.urlopen("https://pastebin.com/raw/qvucRTSE").read())  # TODO: Same here
    jokes = jokes.split("\r\n***\r\n")
    return choice(jokes)


def welcome_user(user_id="", channel_id=""):
    rules = get_rules()
    name = get_user_name(user_id)

    # introduce user in #lounge
    client.api_call("chat.postMessage", channel=channel_id, text=choice(resp["greetings"]).format(name), as_user=True)

    # message user rules, other info
    welcome_string = "Hi {}! Welcome to the official gamemaker slack!".format(name)
    client.api_call("chat.postMessage", channel=user_id, text=welcome_string, as_user=True)
    client.api_call("chat.postMessage", channel=user_id, text=rules, as_user=True)
    client.api_call("chat.postMessage", channel=user_id, text=resp["intro"][0], as_user=True)


def studio_update(force_print=False, admin=False):
    update = json.loads(bytes.decode(request.urlopen("http://gmapi.gnysek.pl/version/gm2ide").read()))
    version = update["gm2ide"]["version"]
    days_ago = update["gm2ide"]["daysAgo"]

    if days_ago <= 1 or force_print or admin:
        rss = bytes.decode(request.urlopen("http://gms.yoyogames.com/update-win.rss").read())
        rss = rss[rss.rfind("<item>"): rss.rfind("</item>")+7]
        download = rss[rss.find("<link>")+6: rss.find("</link>")]
        description = rss[rss.find("<description>")+13: rss.find("</description>")].replace("&lt;p&gt;", "").replace("&lt;/p&gt;", "")

        rn_url = "http://gms.yoyogames.com/ReleaseNotes.html"
        version_name = "GMS2"
        attachments = [
            {
                "fallback": "{0} has been updated to version {1}: {2}".format(version_name, version, rn_url),
                "pretext": choice(resp["update"]).format(version_name),
                "title": "Version {}".format(version),
                "text": "{0} has been updated to <{2}|version {1}>!".format(version_name, version, rn_url),
                "fields": [
                    {
                        "title": "Summary",
                        "value": description
                    },
                    {
                        "title": "Release Notes",
                        "value": "You can read the release notes <{}|here>!".format(rn_url)
                    },
                    {
                        "title": "Download",
                        "value": download
                    }
                ],
                "color": "#039E5C"
            }
        ]

        client.api_call("chat.postMessage", as_user=True, channel=get_channel_id("lounge"),
                        text="", attachments=json.dumps(attachments))
        print("gms2 has updated to version {}\n".format(version))
        if admin:
            return True
    else:
        print("No updates found for gms2\n")

    return False


def parse_slack_output(slack_rtm_output):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output["type"] == "channel_join" or ("subtype" in output and output["subtype"] == "channel_join"):
                # New user joins
                msg = "New user: {}".format(output["user"])
                client.api_call("chat.postMessage", channel=get_user_id("rilin"), text=msg, as_user=True)
                if output["channel"] == get_channel_id("lounge"):
                    welcome_user(output["user"], output["channel"])

            elif output["type"] == "message":
                # Normal message responses
                if "text" in output and "channel" in output:
                    if output["channel"][0] == "D" and "user" in output and output["user"] != BOT_ID:
                        # Direct message to bot
                        return output["text"].lower().strip(), output["channel"], output["user"]

                    elif output["channel"][0] in ["C", "G"]:
                        # Message in a group chat
                        if output["text"].startswith(BOT_NAME):
                            return output["text"].split(BOT_NAME)[1].lower().strip(), output["channel"], output["user"]
                        elif output["text"].startswith("meta"):
                            return output["text"].lower().strip(), output["channel"], output["user"]

    return None, None, None


def handle_command(command, channel, caller):
    user_name = get_user_name(caller)
    is_admin = user_name in get_admins()

    response = choice(resp["unsure"])

    if "rules" in command.lower():
        client.api_call("chat.postMessage", channel=caller, text=get_rules(), as_user=True)
        response = choice(resp["rules_response"])

    elif "joke" in command.lower():
        response = get_joke()

    elif "update" in command.lower():
        if is_admin:
            force = False
            if "force" in command.lower():
                force = True
            if studio_update(admin=True, force_print=force):
                response = "GMS2 updated!"
            else:
                response = "No updates found"

    if response != "":
        client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)


if __name__ == "__main__":

    HOSTED = int(getenv("SLACK_HOSTED", 0))
    BOT_ID = getenv("SLACK_BOT_ID", None)
    BOT_NAME = "<@" + str(BOT_ID) + ">"

    DEBUG_TOKEN = environ["SLACK_TEST_TOKEN"]
    WEBSOCKET_DELAY = .5

    client = SlackClient(getenv("SLACK_BOT_TOKEN", 0))

    with open("data/responses.json") as data_file:
        resp = json.load(data_file)

    if client.rtm_connect():
        print("\n----- BOT STARTING -----")

        if HOSTED:
            client.api_call("chat.postMessage", channel=get_user_id("rilin"), text="Starting...", as_user=True)
            client.api_call("chat.postMessage", channel=get_channel_id("lounge"), text="Whimmy wham wham whazzle, I'm back everybody!", as_user=True)

        # studio_update()

        while True:
            command, channel, caller = parse_slack_output(client.rtm_read())
            if command and channel:
                print(channel, caller, command)
                handle_command(command, channel, caller)
            sleep(WEBSOCKET_DELAY)

    else:
        print("Connection failed. Invalid Slack token or bot ID?")
